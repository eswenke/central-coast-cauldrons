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
    
    # EDIT SO THAT WE ADD THE ML AND POTIONS FROM RED AND BLUE AS WELL

    with db.engine.begin() as connection:
        num_pots = connection.execute(sqlalchemy.text("SELECT num_green_potions FROM global_inventory")).scalar_one()
        num_ml = connection.execute(sqlalchemy.text("SELECT num_green_ml FROM global_inventory")).scalar_one()
        num_gold = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory")).scalar_one()


    return {"number_of_potions": num_pots, "ml_in_barrels": num_ml, "gold": num_gold}

# Gets called once a day
@router.post("/plan")
def get_capacity_plan():
    """ 
    Start with 1 capacity for 50 potions and 1 capacity for 10000 ml of potion. Each additional 
    capacity unit costs 1000 gold.
    """

    # EDIT SO THAT WE GET THE AMOUNT OF POTIONS/ML FROM RED AND BLUE AS WELL

    with db.engine.begin() as connection:
        num_pots = connection.execute(sqlalchemy.text("SELECT num_green_potions FROM global_inventory")).scalar_one()
        num_ml = connection.execute(sqlalchemy.text("SELECT num_green_ml FROM global_inventory")).scalar_one()

    return {
        "potion_capacity": 50 - num_pots,
        "ml_capacity": 10000 - num_ml
        }

class CapacityPurchase(BaseModel):
    potion_capacity: int
    ml_capacity: int

# Gets called once a day
@router.post("/deliver/{order_id}")
def deliver_capacity_plan(capacity_purchase : CapacityPurchase, order_id: int):
    """ 
    Start with 1 capacity for 50 potions and 1 capacity for 10000 ml of potion. Each additional 
    capacity unit costs 1000 gold.
    """

    # DONT NEED TO EDIT THIS YET

    return "OK"
