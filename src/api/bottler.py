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
                [{"order_id": order_id}],
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
                mls[i] += potion_type[i] * potion.quantity

            connection.execute(
                sqlalchemy.text(
                    "UPDATE potions SET inventory = inventory + :quantity WHERE type = :type"
                ),
                [{"quantity": quantity, "type": potion_type}],
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
                {
                    "g_ml": mls[1],
                    "r_ml": mls[0],
                    "b_ml": mls[2],
                    "d_ml": mls[3],
                    "global_q": global_q,
                },
            ],
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
                "SELECT green_ml, red_ml, blue_ml, dark_ml, potions, potion_capacity FROM global_inventory"
            )
        ).first()
        green_ml, red_ml, blue_ml, dark_ml, potions, potions_capacity = result
        mls = [red_ml, green_ml, blue_ml, dark_ml]
        quantity = 0

        result = connection.execute(
            sqlalchemy.text(
                "SELECT inventory, type FROM potions WHERE sku IN ('GREEN_POTION', 'RED_POTION', 'PEPPER_POTION', 'BERRY_POTION', 'SWAMP_POTION', 'BLUE_POTION')"
            )
        ).fetchall()

        # write future threshold logic to increase based on potion capacity from global inventory
        threshold = 8

        # current logic: 
        # bottle each type the max it can up to its potion capacity 

        # future logic:
        # instead of going all in on one, i want to loop through every potion and increase its quantity by 1 until:
            # no more potions can be bottled or
            # capacity is reached for that individual potion or potions inventory

        # collect current mls, potions, and potion capacity from global inventory
        # while potions < potions_capacity and there is still ml available to bottle at least one of the potions in catalog
            # for loop like the one i currently have
                # every iteration adds 1 to that potion if it is possible to be bottled
                # if that potion type is already in the potions list, just increment the quantity by one if possible
                # if that potion type is not already in the list and can be bottled, add to the list with 1 quantity
                # if not possible, continue to next in the for loop
                # subtract any ml bottled from the current amounts of ml
                # keep track of that potions capacity in relation to the threshold
                # keep track of the global inventory's potion capacity

        print(result)

        for row in result:
            # print(row.inventory)
            if row.inventory >= threshold:
                continue
            else:
                max = max_quantity(mls, row.type)
                if max == 0:
                    continue

                quantity = threshold - row.inventory
                final_quantity = quantity if max >= quantity else max
                cap_quantity = (
                    final_quantity
                    if (final_quantity + potions) <= potions_capacity
                    else (potions_capacity - potions)
                )
                potions += cap_quantity
                mls = sub_ml(mls, row.type, max)

                plan.append({"potion_type": row.type, "quantity": cap_quantity})

    return plan


def max_quantity(arr1, arr2):
    result = []
    for x, y in zip(arr1, arr2):
        if y != 0:
            result.append(x // y)
        else:
            result.append(float("inf"))

    # print(result)
    return min(result)


def sub_ml(arr1, arr2, max):
    result = []
    for x, y in zip(arr1, arr2):
        result.append(x - (max * y))
    return result


if __name__ == "__main__":
    print(get_bottle_plan())
