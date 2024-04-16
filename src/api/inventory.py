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
                "SELECT num_green_potions, num_red_potions, num_blue_potions, num_green_ml, num_red_ml, num_blue_ml, gold FROM global_inventory"
            )
        ).first()
        num_gpots, num_rpots, num_bpots, num_gml, num_rml, num_bml, num_gold = result
        ml = num_gml + num_rml + num_bml
        pots = num_gpots + num_rpots + num_bpots
    return {"number_of_potions": pots, "ml_in_barrels": ml, "gold": num_gold}


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
                "SELECT num_green_potions, num_red_potions, num_blue_potions, num_green_ml, num_red_ml, num_blue_ml FROM global_inventory"
            )
        ).first()
        num_gpots, num_rpots, num_bpots, num_gml, num_rml, num_bml = result
        ml = num_gml + num_rml + num_bml
        pots = num_gpots + num_rpots + num_bpots

    return {"potion_capacity": 50 - pots, "ml_capacity": 10000 - ml}


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

    return "OK"
