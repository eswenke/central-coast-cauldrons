from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from sqlalchemy.exc import IntegrityError
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

    g_p = 0
    r_p = 0
    b_p = 0

    for potion in potions_delivered:
        if potion.potion_type == [100, 0, 0, 0]:
            r_p += potion.quantity
        if potion.potion_type == [0, 100, 0, 0]:
            g_p += potion.quantity
        if potion.potion_type == [0, 0, 100, 0]:
            b_p += potion.quantity

    g_ml = g_p * 100
    r_ml = r_p * 100
    b_ml = b_p * 100

    with db.engine.begin() as connection:
        try:
            connection.execute(sqlalchemy.text("INSERT INTO processed (id, type) VALUES (:order_id, 'potions')"), [{"order_id": order_id}])
        except IntegrityError as e:
            return "OK"
        
        connection.execute(
            sqlalchemy.text(
                "UPDATE global_inventory SET num_green_ml = num_green_ml - "
                + str(g_ml)
                + ", num_green_potions = num_green_potions + "
                + str(g_p)
                + ", num_red_ml = num_red_ml - "
                + str(r_ml)
                + ", num_red_potions = num_red_potions + "
                + str(r_p)
                + ", num_blue_ml = num_blue_ml - "
                + str(b_ml)
                + ", num_blue_potions = num_blue_potions + "
                + str(b_p)
            )
        )

    return "OK"


@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """

    with db.engine.begin() as connection:
        result = connection.execute(
            sqlalchemy.text(
                "SELECT num_green_ml, num_red_ml, num_blue_ml, num_green_potions, num_red_potions, num_blue_potions FROM global_inventory"
            )
        ).first()
        g_ml, r_ml, b_ml, num_gp, num_rp, num_bp = result

    plan = []
    g_ml //= 100
    r_ml //= 100
    b_ml //= 100
    pot_limit = 50 - num_bp - num_gp - num_rp

    # dont bottle past 50 potions, maybe worry about that in the next version tho
    # and pot_limit - g_ml > 0

    if g_ml > 0:
        plan.append(
            {
                "potion_type": [0, 100, 0, 0],
                "quantity": g_ml,
            }
        )
    if r_ml > 0:
        plan.append(
            {
                "potion_type": [100, 0, 0, 0],
                "quantity": r_ml,
            }
        )
    if b_ml > 0:
        plan.append(
            {
                "potion_type": [0, 0, 100, 0],
                "quantity": b_ml,
            }
        )

    return plan


if __name__ == "__main__":
    print(get_bottle_plan())
