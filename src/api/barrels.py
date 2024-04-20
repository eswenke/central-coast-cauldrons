from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from sqlalchemy.exc import IntegrityError
from src import database as db

router = APIRouter(
    prefix="/barrels",
    tags=["barrels"],
    dependencies=[Depends(auth.get_api_key)],
)


class Barrel(BaseModel):
    sku: str

    ml_per_barrel: int
    potion_type: list[int]
    price: int

    quantity: int


@router.post("/deliver/{order_id}")
def post_deliver_barrels(barrels_delivered: list[Barrel], order_id: int):
    """ """
    print(f"barrels delievered: {barrels_delivered} order_id: {order_id}")

    g_ml = 0
    r_ml = 0
    b_ml = 0
    price = 0
    for barrel in barrels_delivered:
        if barrel.potion_type == [0, 1, 0, 0]:
            g_ml += barrel.ml_per_barrel * barrel.quantity
            price += barrel.price * barrel.quantity
        if barrel.potion_type == [1, 0, 0, 0]:
            r_ml += barrel.ml_per_barrel * barrel.quantity
            price += barrel.price * barrel.quantity
        if barrel.potion_type == [0, 0, 1, 0]:
            b_ml += barrel.ml_per_barrel * barrel.quantity
            price += barrel.price * barrel.quantity

    with db.engine.begin() as connection:
        try:
            connection.execute(sqlalchemy.text("INSERT INTO processed (id, type) VALUES (:order_id, 'barrels')"), [{"order_id": order_id}])
        except IntegrityError as e:
            return "OK"

        connection.execute(
            sqlalchemy.text(
                "UPDATE global_inventory SET num_green_ml = num_green_ml + "
                + str(g_ml)
                + ", num_red_ml = num_red_ml + "
                + str(r_ml)
                + ", num_blue_ml = num_blue_ml + "
                + str(b_ml)
                + ", gold = gold - "
                + str(price)
            )
        )

    return "OK"


# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print(wholesale_catalog)

    # probably will need to edit barrel purchasing logic at some point
    # implement capacity checking:
    # and ml_limit - (barrel.ml_per_barrel * barrel.quantity) > 0

    with db.engine.begin() as connection:
        result = connection.execute(
            sqlalchemy.text(
                "SELECT num_green_potions, num_red_potions, num_blue_potions, num_green_ml, num_red_ml, num_blue_ml, gold FROM global_inventory"
            )
        ).first()
        num_g, num_r, num_b, g_ml, r_ml, b_ml, gold = result
        ml_limit = 10000 - g_ml - r_ml - b_ml
        plan = []

        for barrel in wholesale_catalog:
            if barrel.sku == "SMALL_GREEN_BARREL":
                if num_g < 10 and gold >= barrel.price: # * barrel.quantity)
                    plan.append(
                        {
                            "sku": "SMALL_GREEN_BARREL",
                            "quantity": 1,
                        }
                    )
                    gold -= barrel.price # * barrel.quantity
            if barrel.sku == "SMALL_RED_BARREL":
                if num_r < 10 and gold >= barrel.price: # * barrel.quantity:
                    plan.append(
                        {
                            "sku": "SMALL_RED_BARREL",
                            "quantity": 1,
                        }
                    )
                    gold -= barrel.price# * barrel.quantity
            if barrel.sku == "SMALL_BLUE_BARREL":
                if num_b < 10 and gold >= barrel.price: # * barrel.quantity:
                    plan.append(
                        {
                            "sku": "SMALL_BLUE_BARREL",
                            "quantity": 1,
                        }
                    )
                    gold -= barrel.price # * barrel.quantity

    return plan
