from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/bottler",
    tags=["bottler"],
    dependencies=[Depends(auth.get_api_key)],
)


class PotionInventory(BaseModel):
    potion_type: list[int]
    quantity: int


@router.post("/deliver/{order_id}")
def post_deliver_bottles(potions_delivered: list[PotionInventory], order_id: int):
    """ """
    print(f"potions delievered: {potions_delivered} order_id: {order_id}")

    # EDIT PLAN TO UPDATE VALUES FOR RED, GREEN, AND BLUE POTIONS AND ML

    potions = 0
    for potion in potions_delivered:
        potions += potion.quantity
    ml = potions * 100

    with db.engine.begin() as connection:
        connection.execute(
            sqlalchemy.text(
                "UPDATE global_inventory SET num_green_ml = num_green_ml - "
                + str(ml)
                + ", num_green_potions = num_green_potions + "
                + str(potions)
            )
        )

    return "OK"


@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """

    # EDIT PLAN FOR BOTTLE RED, GREEN, AND BLUE

    with db.engine.begin() as connection:
        result = connection.execute(
            sqlalchemy.text("SELECT num_green_ml FROM global_inventory")
        ).first()[0]
        result = result // 100

    if result != 0:
        return [
            {
                "potion_type": [0, 100, 0, 0],
                "quantity": result,
            }
        ]
    else:
        return []


if __name__ == "__main__":
    print(get_bottle_plan())
