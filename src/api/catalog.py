from fastapi import APIRouter
import sqlalchemy
from src import database as db

router = APIRouter()


@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """

    ## SELL ONE FOR RIGHT NOW
    ## AFTER WE CAN SELL ONE, CHANGE AND MAKE SURE WE CAN SELL MANY

    plan = []

    with db.engine.begin() as connection:
        result = connection.execute(
            sqlalchemy.text(
                "SELECT num_green_potions, num_red_potions, num_blue_potions FROM global_inventory"
            )
        ).first()
        num_g, num_r, num_b = result

        if num_g > 0:
            plan.append(
                {
                    "sku": "GREEN_POTION_0",
                    "name": "green potion",
                    "quantity": 1,
                    "price": 25,
                    "potion_type": [0, 100, 0, 0],
                }
            )
        if num_r > 0:
            plan.append(
                {
                    "sku": "RED_POTION_0",
                    "name": "red potion",
                    "quantity": 1,
                    "price": 25,
                    "potion_type": [100, 0, 0, 0],
                }
            )
        if num_b > 0:
            plan.append(
                {
                    "sku": "BLUE_POTION_0",
                    "name": "blue potion",
                    "quantity": 1,
                    "price": 25,
                    "potion_type": [0, 0, 100, 0],
                }
            )

    return plan
