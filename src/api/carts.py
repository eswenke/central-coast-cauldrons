from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
from enum import Enum
import sqlalchemy
from sqlalchemy.exc import IntegrityError
from src import database as db
from collections import defaultdict
from operator import itemgetter
import random


router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)


class search_sort_options(str, Enum):
    customer_name = "customer_name"
    item_sku = "item_sku"
    line_item_total = "line_item_total"
    timestamp = "timestamp"


class search_sort_order(str, Enum):
    asc = "asc"
    desc = "desc"


@router.get("/search/", tags=["search"])
def search_orders(
    customer_name: str = "",
    potion_sku: str = "",
    search_page: str = "",
    sort_col: search_sort_options = search_sort_options.timestamp,
    sort_order: search_sort_order = search_sort_order.desc,
):
    """
    Search for cart line items by customer name and/or potion sku.

    Customer name and potion sku filter to orders that contain the
    string (case insensitive). If the filters aren't provided, no
    filtering occurs on the respective search term.

    Search page is a cursor for pagination. The response to this
    search endpoint will return previous or next if there is a
    previous or next page of results available. The token passed
    in that search response can be passed in the next search request
    as search page to get that page of results.

    Sort col is which column to sort by and sort order is the direction
    of the search. They default to searching by timestamp of the order
    in descending order.

    The response itself contains a previous and next page token (if
    such pages exist) and the results as an array of line items. Each
    line item contains the line item id (must be unique), item sku,
    customer name, line item total (in gold), and timestamp of the order.
    Your results must be paginated, the max results you can return at any
    time is 5 total line items.
    """

    search_page = 0 if search_page == "" else search_page
    prev = "" if int(search_page) - 5 < 0 else int(search_page) - 5
    next = ""
    results = []

    potion_sku = "%" + potion_sku
    customer_name = "%" + customer_name

    print(potion_sku)
    print(customer_name)

    with db.engine.begin() as connection:
        result = connection.execute(
            sqlalchemy.text(
                f"""
                    SELECT id, item_sku, customer_name, line_item_total, timestamp, potion_sku FROM orders
                    WHERE 1=1
                    {("" if potion_sku == "" else "AND potion_sku ILIKE :potion_sku")}
                    {("" if customer_name == "" else "AND customer_name ILIKE :customer_name")}
                    ORDER BY {sort_col.name} {sort_order.name}
                    LIMIT 6
                    OFFSET :page
                """
            ), [{"potion_sku": potion_sku, "customer_name": customer_name, "page": search_page}]
        )

        for i, row in enumerate(result):
            if i == 5:
                next = int(search_page) + 5
                break  

            results.append(
                {
                    "line_item_id": row.id,
                    "item_sku": row.item_sku,
                    "customer_name": row.customer_name,
                    "line_item_total": row.line_item_total,
                    "timestamp": row.timestamp,
                }
            ) 

    return {
        "previous": str(prev),
        "next": str(next),
        "results": results
    }


class Customer(BaseModel):
    customer_name: str
    character_class: str
    level: int


@router.post("/visits/{visit_id}")
def post_visits(visit_id: int, customers: list[Customer]):
    """
    Which customers visited the shop today?
    """
    print(customers)
    id = get_recent_id()
    if id is None:
        return "OK"

    class_counts = defaultdict(int)
    for customer in customers:
        class_counts[customer.character_class] += 1

    sorted_class_counts = sorted(class_counts.items(), key=itemgetter(1), reverse=True)
    visits = [f"{class_name}: {count}" for class_name, count in sorted_class_counts]

    with db.engine.begin() as connection:
        connection.execute(
            sqlalchemy.text(
                """
                UPDATE timestamps SET visits = :visits WHERE id = :id
                """
            ),
            [{"visits": visits, "id": id}],
        )

    return "OK"


@router.post("/")
def create_cart(new_cart: Customer):
    """ """

    with db.engine.begin() as connection:
        id = connection.execute(
            sqlalchemy.text(
                "INSERT INTO carts (customer, class, level) VALUES (:customer, :class, :level) RETURNING id"
            ),
            [
                {
                    "customer": new_cart.customer_name,
                    "class": new_cart.character_class,
                    "level": new_cart.level,
                }
            ],
        ).scalar_one()

    return {"cart_id": id}


class CartItem(BaseModel):
    quantity: int


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ """

    print(f"cart: {cart_id} item: {item_sku} quantity: {cart_item.quantity}")

    with db.engine.begin() as connection:
        connection.execute(
            sqlalchemy.text(
                """
                INSERT INTO cart_items (cart, potion, quantity)
                VALUES (:cart, :potion, :quantity)"""
            ),
            [{"cart": cart_id, "potion": item_sku, "quantity": cart_item.quantity}],
        )

    return "OK"


class CartCheckout(BaseModel):
    payment: str


@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """

    set_order(cart_id)

    with db.engine.begin() as connection:
        connection.execute(
            sqlalchemy.text(
                """
                INSERT INTO potions_ledger (quantity, sku)
                SELECT -cart_items.quantity, cart_items.potion
                FROM potions
                JOIN cart_items ON potions.sku = cart_items.potion
                WHERE cart_items.cart = :cart_id"""
            ),
            [{"cart_id": cart_id}],
        )

        result = connection.execute(
            sqlalchemy.text(
                """
                SELECT
                    SUM(potions.price * cart_items.quantity) AS sum_table1,
                    SUM(cart_items.quantity) AS sum_table2
                FROM potions
                JOIN cart_items ON potions.sku = cart_items.potion
                WHERE cart_items.cart = :cart_id
                """
            ),
            [{"cart_id": cart_id}],
        ).first()
        sum_gold, sum_potions = result

        connection.execute(
            sqlalchemy.text("INSERT INTO gold_ledger (gold) VALUES (:sum_gold)"),
            [{"sum_gold": sum_gold}],
        ),

    return {"total_potions_bought": sum_potions, "total_gold_paid": sum_gold}


def get_recent_id():
    with db.engine.begin() as connection:
        result = connection.execute(
            sqlalchemy.text(
                """
                    SELECT id
                    FROM timestamps
                    ORDER BY id DESC
                    LIMIT 1;
                """
            )
        ).first()[0]

    return result


def set_order(cart_id):
    # get the customer name from the cart_id
    # for order row, we need:
    #       id : automatically generated
    #       item_sku: quantity + potion_sku
    #       customer_name
    #       line_item_total : total price (quantity * price)
    #       timestamp : default (now)
    #       potion_sku : just the potion sku
    # we get each of these by:
    #       id : automatic
    #       item_sku : append quantity to potion_sku
    #       customer_name: acquired from carts with cart_id
    #       line_item_total : price acquired from potions, quantity acquired from potions_ledger
    #       timestamp : default (now)
    #       potion_sku : acquired from potions_ledger

    with db.engine.begin() as connection:
        customer_name = connection.execute(
            sqlalchemy.text(
                """
                    SELECT customer FROM carts WHERE id = :cart_id
                """
            ), [{"cart_id": cart_id}]
        ).first()[0]

        potion_sku, quantity = connection.execute(
            sqlalchemy.text(
                """
                    SELECT potion, quantity FROM cart_items WHERE cart = :cart_id
                """
            ), [{"cart_id": cart_id}]
        ).first()

        item_sku = str(quantity) + " " + str(potion_sku)

        price = connection.execute(
            sqlalchemy.text(
                """
                    SELECT price FROM potions WHERE sku = :potion_sku
                """
            ), [{"potion_sku": potion_sku}]
        ).scalar_one()

        line_item_total = price * quantity

        connection.execute(
            sqlalchemy.text(
                """
                    INSERT INTO orders (item_sku, customer_name, line_item_total, potion_sku)
                    VALUES (:item_sku, :customer_name, :line_item_total, :potion_sku)
                """
            ), [{"item_sku": item_sku, "customer_name": customer_name, "line_item_total": line_item_total, "potion_sku": potion_sku}]
        )

    return

