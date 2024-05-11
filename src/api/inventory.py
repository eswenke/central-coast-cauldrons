from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import math
import sqlalchemy
from sqlalchemy.exc import IntegrityError
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
        potions = connection.execute(
            sqlalchemy.text("SELECT SUM(potions_ledger.quantity) FROM potions_ledger")
        ).scalar_one()
        gold = connection.execute(
            sqlalchemy.text("SELECT SUM(gold_ledger.gold) FROM gold_ledger")
        ).scalar_one()
        ml = connection.execute(
            sqlalchemy.text(
                "SELECT SUM(ml_ledger.red_ml + ml_ledger.green_ml + ml_ledger.blue_ml + ml_ledger.dark_ml) FROM ml_ledger"
            )
        ).scalar_one()

        print("ml: " + str(ml))
        print("gold: " + str(gold))
        print("potions: " + str(potions))

    return {"number_of_potions": potions, "ml_in_barrels": ml, "gold": gold}

# Gets called once a day
@router.post("/plan")
def get_capacity_plan():
    """
    Start with 1 capacity for 50 potions and 1 capacity for 10000 ml of potion. Each additional
    capacity unit costs 1000 gold.
    """

    with db.engine.begin() as connection:
        potions = connection.execute(
            sqlalchemy.text("SELECT SUM(potions_ledger.quantity) FROM potions_ledger")
        ).scalar_one()
        gold = connection.execute(
            sqlalchemy.text("SELECT SUM(gold_ledger.gold) FROM gold_ledger")
        ).scalar_one()
        ml = connection.execute(
            sqlalchemy.text(
                "SELECT SUM(ml_ledger.red_ml + ml_ledger.green_ml + ml_ledger.blue_ml + ml_ledger.dark_ml) FROM ml_ledger"
            )
        ).scalar_one()
        results = connection.execute(
            sqlalchemy.text(
                "SELECT potion_capacity, ml_capacity FROM constants"
            )
        ).first()

        potion_capacity, ml_capacity = results
        pot_cap = 0
        ml_cap = 0

        if gold >= 1500:
            if (potion_capacity == 50): # early pot cap increase
                pot_cap = 1
                ml_cap = 0
            elif (ml_capacity == 10000): # early ml increase so we can buy a large barrel
                ml_cap = 1
                pot_cap = 0
            elif (gold >= (2500 * (ml_capacity // 10000))): # logic for every purchase after that
                ml_cap = 2 # if ml_capacity - ml <= 2500 else 0
                pot_cap = 2 # if potion_capacity - potions <= 15 else 0

    return {
        "potion_capacity": pot_cap,
        "ml_capacity": ml_cap,
    }


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

    print(f"capacity purchase: {capacity_purchase} order_id: {order_id}")

    with db.engine.begin() as connection:
        try:
            connection.execute(
                sqlalchemy.text(
                    "INSERT INTO processed (id, type) VALUES (:order_id, 'capacity')"
                ),
                [{"order_id": order_id}],
            )
        except IntegrityError as e:
            return "OK"

        connection.execute(
            sqlalchemy.text(
                """UPDATE constants SET 
                potion_capacity = potion_capacity + (:pot_cap * 50), 
                ml_capacity = ml_capacity + (:ml_cap * 10000)"""
            ),
            [
                {
                    "pot_cap": capacity_purchase.potion_capacity,
                    "ml_cap": capacity_purchase.ml_capacity,
                }
            ],
        )
        connection.execute(
            sqlalchemy.text(
                """INSERT INTO gold_ledger (gold) VALUES (-1000 * (:pot_cap + :ml_cap))"""
            ),
            [
                {
                    "pot_cap": capacity_purchase.potion_capacity,
                    "ml_cap": capacity_purchase.ml_capacity,
                }
            ],
        )

    return {
        "potion_capacity": capacity_purchase.potion_capacity,
        "ml_capacity": capacity_purchase.ml_capacity,
    }
