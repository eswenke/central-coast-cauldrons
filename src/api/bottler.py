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
                    """INSERT INTO potions_ledger (quantity, sku) 
                    VALUES (:quantity, (SELECT potions.sku FROM potions WHERE type = :type))"""
                ),
                [{"quantity": quantity, "type": potion_type}],
            )

        connection.execute(
            sqlalchemy.text(
                """
                INSERT INTO ml_ledger (red_ml, green_ml, blue_ml, dark_ml) 
                VALUES (-:r_ml, -:g_ml, -:b_ml, -:d_ml)"""
            ),
            [
                {"r_ml": mls[0], "g_ml": mls[1], "b_ml": mls[2], "d_ml": mls[3]},
            ],
        )

    return "OK"


@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """

    pot_list = which_potions()
    plan = []

    with db.engine.begin() as connection:
        potions = connection.execute(
            sqlalchemy.text(
                "SELECT SUM(potions_ledger.quantity) FROM potions_ledger"
            )
        ).scalar_one()
        result = connection.execute(
            sqlalchemy.text(
                "SELECT type, price FROM potions WHERE sku in :pot_list"
            ),[{"pot_list": pot_list}]
        ).fetchall()
        mls = connection.execute(
            sqlalchemy.text(
                "SELECT SUM(ml_ledger.red_ml), SUM(ml_ledger.green_ml), SUM(ml_ledger.blue_ml), SUM(ml_ledger.dark_ml) FROM ml_ledger"
            )
        ).first()
        potion_capacity = connection.execute(
            sqlalchemy.text(
                "SELECT potion_capacity FROM constants"
            )
        ).scalar_one()

        print(result)

        red_ml, green_ml, blue_ml, dark_ml = mls
        mls = [red_ml, green_ml, blue_ml, dark_ml]
        threshold = 8
        quantity = 0
        potions_left = potion_capacity - potions
        max_bottle_each = potions_left // len(result)
            
        for row in result:
            max_from_mls = max_quantity(mls, row.type)
            if max_from_mls == 0:
                continue

            final_quantity = max_from_mls if max_from_mls <= max_bottle_each else max_bottle_each
            mls = sub_ml(mls, row.type, final_quantity)

            plan.append({"potion_type": row.type, "quantity": final_quantity})

        return plan

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

        # for row in result:
        #     # print(row.inventory)
        #     # print(mls)
        #     # print(row)
        #     if row.quantity >= threshold:
        #         continue
        #     else:
        #         max = max_quantity(mls, row.type)
        #         # print("max: " + str(max))
        #         if max == 0:
        #             continue

        #         quantity = threshold - row.inventory
        #         final_quantity = quantity if max >= quantity else max
        #         cap_quantity = (
        #             final_quantity
        #             if (final_quantity + potions) <= potion_capacity
        #             else (potion_capacity - potions)
        #         )
        #         potions += cap_quantity
        #         mls = sub_ml(mls, row.type, cap_quantity)

        #         plan.append({"potion_type": row.type, "quantity": cap_quantity})

    # print("bottling plan: " + str(plan))

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

def get_day():
    with db.engine.begin() as connection:
        result = connection.execute(
            sqlalchemy.text(
                """
                    SELECT day
                    FROM timestamps
                    ORDER BY id DESC
                    LIMIT 1;
                """
                )
            ).first()[0]
        return result

def which_potions():
    # return a list of potions to pass to my result query
    # goal is to bottle potions that i know will sell   

    # if there are not 6 potion types with a quantity greater than 0
        # just return those that do have quantity > 0 with a select
    # elif there are more than 6 potion types with quantity greater than 0

        # bottle based on what day it is (hardcode IN THE DB):
            # if edgeday, bottle 
            # if bloomday, bottle more red potions for fighters / rgb potions for monks
            # if arcanaday, bottle 
            # if hearthday, bottle
            # if crownday, bottle 
            # if blesseday, bottle
            # if soulday, bottle green and blue potions / green and blue mixes

        # more advanced bottling plan based on popularity:
        # make a bottling plan that just selects random potion types to bottle (not dark if dont have any):
            # run this bottling plan for a week and gather intel into a new table (referenced below)
            # for each day, show what potions were bottled and what potions sold the most
        # if it has been 7 days since the last reset, start bottling based on sells the most:
            # make a new table that selects the most popular potions from each day
            # table will have an entry for each day of the potions week, along with the top 4 selling potions
            # leaving 2 for firesale spots

    with db.engine.begin() as connection:
        day = get_day()
        pot_list = connection.execute(
            sqlalchemy.text(
                """
                    SELECT pot_pref
                    FROM preferences
                    WHERE day = :day
                """
                ),[{"day": day}]
            ).first()[0]

    return tuple(pot_list)


if __name__ == "__main__":
    print(get_bottle_plan())
