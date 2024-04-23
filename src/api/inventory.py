from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import math
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
    dependencies=[Depends(auth.get_api_key)],
)


@router.get("/audit")
def get_inventory():
    """ """

    with db.engine.begin() as connection:
        result = connection.execute(
            sqlalchemy.text(
                "SELECT green_ml, red_ml, blue_ml, dark_ml, gold, potions FROM global_inventory"
            )
        ).first()
        green_ml, red_ml, blue_ml, dark_ml, gold, potions = result
        ml = green_ml + red_ml + blue_ml + dark_ml

    return {"number_of_potions": potions, "ml_in_barrels": ml, "gold": gold}


# Gets called once a day
@router.post("/plan")
def get_capacity_plan():
    """
    Start with 1 capacity for 50 potions and 1 capacity for 10000 ml of potion. Each additional
    capacity unit costs 1000 gold.
    """

    with db.engine.begin() as connection:
        result = connection.execute(
            sqlalchemy.text(
                "SELECT green_ml, red_ml, blue_ml, dark_ml, potions, potion_capacity, ml_capacity FROM global_inventory"
            )
        ).first()
        green_ml, red_ml, blue_ml, dark_ml, potions, potion_capacity, ml_capacity = result
        ml = green_ml + red_ml + blue_ml + dark_ml

    return {"potion_capacity": potion_capacity - potions, "ml_capacity": ml_capacity - ml}


class CapacityPurchase(BaseModel):
    potion_capacity: int
    ml_capacity: int


# Gets called once a day
@router.post("/deliver/{order_id}")
def deliver_capacity_plan(capacity_purchase: CapacityPurchase, order_id: int):
    """
    Start with 1 capacity for 50 potions and 1 capacity for 10000 ml of potion. Each additional
    capacity unit costs 1000 gold.
    """

    # DONT NEED TO EDIT THIS YET

    print(f"capacity purchase: {capacity_purchase} order_id: {order_id}")


    return "OK"
