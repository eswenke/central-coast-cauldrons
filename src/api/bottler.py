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

    with db.engine.begin() as connection:
        try:
            connection.execute(
                sqlalchemy.text(
                    "INSERT INTO processed (id, type) VALUES (:order_id, 'potions')"
                ),
                [{"order_id": order_id}]
            )
        except IntegrityError as e:
            return "OK"

        mls = [0, 0, 0, 0]
        global_q = 0
        for potion in potions_delivered:
            quantity = potion.quantity
            global_q += quantity
            potion_type = potion.potion_type
            for i in range(4):
                mls[i] += potion_type[i]

            connection.execute(
                sqlalchemy.text(
                    "UPDATE potions SET inventory = inventory + :quantity WHERE type = :type"
                ),
                [{"quantity": quantity}, {"type": potion_type}]
            )

        connection.execute(
            sqlalchemy.text(
                """
                UPDATE global_inventory 
                SET green_ml = green_ml - :g_ml,
                red_ml = red_ml - :r_ml,
                blue_ml = blue_ml - :b_ml,
                dark_ml = dark_ml - :d_ml,
                potions = potions + :global_q"""
            ),
            [
                {"g_ml": mls[1]},
                {"r_ml": mls[0]},
                {"b_ml": mls[2]},
                {"d_ml": mls[3]},
                {"global_q": global_q},
            ]
        )

    return "OK"


@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """

    plan = []
    with db.engine.begin() as connection:
        result = connection.execute(
            sqlalchemy.text(
                "SELECT green_ml, red_ml, blue_ml, dark_ml, potions, potions_capacity FROM global_inventory"
            )
        ).first()
        green_ml, red_ml, blue_ml, dark_ml, potions, potions_capacity = result
        mls = [red_ml, green_ml, blue_ml, dark_ml]
        quantity = 0

        result = connection.execute(
            sqlalchemy.text(
                "SELECT inventory, potion_type FROM potions WHERE sku IN ('BERRY_POTION', 'SWAMP_POTION', 'RAINBOW_POTION', 'GREEN_POTION', 'RED_POTION', 'BLUE_POTION')"
            )
        ).fetchall()

        for row in result:
            if row.inventory > 8:
                continue
            else:
                max = max_quantity(mls, row.potion_type)
                if max == 0:
                    continue

                quantity = 8 - row.inventory
                final_quantity = quantity if max >= quantity else max
                cap_quantity = (
                    final_quantity
                    if (final_quantity + potions) <= potions_capacity
                    else (potions_capacity - potions)
                )
                potions += cap_quantity

                plan.append({"potion_type": row.type, "quantity": cap_quantity})

    return plan


def max_quantity(arr1, arr2):
    result = []
    for x, y in zip(arr1, arr2):
        if y != 0:
            result.append(x // y)
        else:
            result.append(float("inf"))
    return min(result)


if __name__ == "__main__":
    print(get_bottle_plan())
