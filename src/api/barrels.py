from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
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

    # EDIT TO BE SPECIFIC TO RED, BLUE, GREEN BARRELS

    ml = 0
    price = 0
    for barrel in barrels_delivered:
        ml += barrel.ml_per_barrel * barrel.quantity
        price += barrel.price * barrel.quantity

    with db.engine.begin() as connection:
        connection.execute(
            sqlalchemy.text(
                "UPDATE global_inventory SET num_green_ml = num_green_ml + "
                + str(ml)
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

    # CHECKS FOR GOLD TO MAKE SURE WE HAVE ENOUGH TO BUY

    with db.engine.begin() as connection:
        result = connection.execute(
            sqlalchemy.text("SELECT num_green_potions, gold FROM global_inventory")
        ).first()
        potions, gold = result
        plan = []
        for barrel in wholesale_catalog:
            if barrel.sku == "SMALL_GREEN_BARREL":
                if potions < 10 and gold >= barrel.price:
                    plan.append(
                        {
                            "sku": "SMALL_GREEN_BARREL",
                            "quantity": 1,
                        }
                    )

    if len(plan) > 0:
        return plan
    else:
        return []
