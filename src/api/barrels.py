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
    d_ml = 0
    price = 0
    for barrel in barrels_delivered:
        price += barrel.price * barrel.quantity
        if barrel.potion_type == [0, 1, 0, 0]:
            g_ml += barrel.ml_per_barrel * barrel.quantity
        if barrel.potion_type == [1, 0, 0, 0]:
            r_ml += barrel.ml_per_barrel * barrel.quantity
        if barrel.potion_type == [0, 0, 1, 0]:
            b_ml += barrel.ml_per_barrel * barrel.quantity
        if barrel.potion_type == [0, 0, 0, 1]:
            d_ml += barrel.ml_per_barrel * barrel.quantity

    with db.engine.begin() as connection:
        try:
            connection.execute(
                sqlalchemy.text(
                    "INSERT INTO processed (id, type) VALUES (:order_id, 'barrels')"
                ),
                [{"order_id": order_id}],
            )
        except IntegrityError as e:
            return "OK"

        connection.execute(
            sqlalchemy.text(
                """
                UPDATE global_inventory 
                SET green_ml = green_ml + :g_ml,
                red_ml = red_ml + :r_ml,
                blue_ml = blue_ml + :b_ml,
                dark_ml = dark_ml + :d_ml,
                gold = gold - :price"""
            ),
            [{"g_ml": g_ml, "r_ml": r_ml, "b_ml": b_ml, "d_ml": d_ml, "price": price}],
        )

    return "OK"


# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print(wholesale_catalog)

    with db.engine.begin() as connection:
        result = connection.execute(
            sqlalchemy.text(
                "SELECT green_ml, red_ml, blue_ml, dark_ml, gold, ml_capacity FROM global_inventory"
            )
        ).first()
        g_ml, r_ml, b_ml, d_ml, gold, ml_capacity = result
        ml_arr = [r_ml, g_ml, b_ml, d_ml]
        current_ml = sum(ml_arr)

        selling_large = any(item.sku.startswith("LARGE") for item in wholesale_catalog)
        normal_threshold = 3000
        large_threshold = 1000
        threshold = large_threshold if selling_large else normal_threshold

        plan = []

        for i, ml in enumerate(ml_arr):
            ml_limit = ml_capacity - current_ml
            if ml < threshold:
                potion_type = [int(j == i) for j in range(4)]
                print(gold)
                barrel_purchase = create_wpp(
                    wholesale_catalog,
                    plan,
                    potion_type,
                    gold / 4 if gold >= 300 else gold,
                    ml_limit,
                    ml_arr
                )
                if barrel_purchase is not None:
                    price = next(
                        item.price
                        for item in wholesale_catalog
                        if item.sku == barrel_purchase["sku"]
                    )
                    ml_per_barrel = next(
                        item.ml_per_barrel
                        for item in wholesale_catalog
                        if item.sku == barrel_purchase["sku"]
                    )
                    plan.append(barrel_purchase)
                    gold -= price * barrel_purchase["quantity"]
                    current_ml += ml_per_barrel * barrel_purchase["quantity"]

    return plan


def create_wpp(
    wholesale_catalog: list[Barrel], plan: list[Barrel], potion_type, gold, ml_limit, mls
):
    """ """
    mini = False
    i = 0
    for ml in mls:
        if ml < 250:
            i += 1
    if i >= 3 and gold < 100:
        mini = True

    # add similar logic for "LARGE" later on

    for barrel in wholesale_catalog:
        if (
            (gold >= barrel.price)
            and (potion_type == barrel.potion_type)
            and ("LARGE" not in barrel.sku)
            and (barrel not in plan)
        ):
            if not mini and ("MINI" in barrel.sku):
                continue
            else:
                q_max = ml_limit // barrel.ml_per_barrel
                q_buyable = gold // barrel.price
                q_final = q_buyable if q_max >= q_buyable else q_max
                q_final = q_final if q_final <= barrel.quantity else barrel.quantity

                if q_max < 0:
                    return None
                else:
                    return {
                        "sku": barrel.sku,
                        "quantity": q_final,
                    }

    return None
