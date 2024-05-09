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


def is_pure(type):
    res = 0
    for i in range(len(type)):
        if type[i] > 0:
            res += 1

    if res > 1:
        return False
    return True


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

    # more advanced bottling plan based on popularity:
    # make a bottling plan that just selects random potion types to bottle (not dark if dont have any):
    # run this bottling plan for a week and gather intel into a new table (referenced below)
    # for each day, show what potions were bottled and what potions sold the most
    # if it has been 7 days since the last reset, start bottling based on sells the most:
    # make a new table that selects the most popular potions from each day
    # table will have an entry for each day of the potions week, along with the top 4 selling potions
    # leaving 2 for firesale spots

    # for bottling randomly, uses subquery to get all potions that do not have a dark ml
    # SELECT DISTINCT *, RANDOM() as random_value
    # FROM  (
    #         SELECT sku
    #         FROM potions
    #         WHERE type[array_length(type, 1)] = 0
    #     ) as nondark
    # ORDER BY random_value
    # LIMIT 6;
    # if we need to base this on what mls we have, we could maybe do:
    # HERE type[1] < 60 AND type[2] < 60 AND type[3] < 1 AND type[4] < 1, where the number after < is :ml[1] or 2,3,4

    with db.engine.begin() as connection:
        day = get_day()
        pot_list = connection.execute(
            sqlalchemy.text(
                """
                    SELECT pot_pref
                    FROM preferences
                    WHERE day = :day
                """
            ),
            [{"day": day}],
        ).first()[0]

    return tuple(pot_list)


def is_popular():
    # if a potion type has sold multiple times in the last 6 hours, return true and then raise its threshold
    # can keep threshold values in an array before bottling loop or something
    # need smarter bottling logic. pot preferences is good for research purposes, but we need a more efficient
    # bottling method. use is_poplar to bottle extra. maybe change pots pref to only have 2-3 potion types, and
    # we focus our bottling on them?

    # for example:
    #   red pots sell back to back to back on bloomday
    #   raise their threshold by 10 or so (increases with higher potion capacity and ml?)
    #   space will be cleared by firesale and hopefully the sale of other potions normally

    # with db.engine.begin() as connection:
    #     result = connection.execute(
    #         sqlalchemy.text(
    #             """
    #                 SELECT DISTINCT sku
    #                 FROM potions_ledger
    #                 WHERE timestamp <= (SELECT MAX(timestamp) - interval '12 hours' FROM potions_ledger), quantity > 0
    #                 ORDER BY timestamp DESC
    #                 LIMIT 3;
    #             """
    #         )
    #     ).fetchall()

    #     print(result)

    return


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
            sqlalchemy.text("SELECT SUM(potions_ledger.quantity) FROM potions_ledger")
        ).scalar_one()
        result = connection.execute(
            sqlalchemy.text(
                "SELECT sku, type, price FROM potions WHERE sku in :pot_list"
            ),
            [{"pot_list": pot_list}],
        ).fetchall()
        mls = connection.execute(
            sqlalchemy.text(
                "SELECT SUM(ml_ledger.red_ml), SUM(ml_ledger.green_ml), SUM(ml_ledger.blue_ml), SUM(ml_ledger.dark_ml) FROM ml_ledger"
            )
        ).first()
        potion_capacity = connection.execute(
            sqlalchemy.text("SELECT potion_capacity FROM constants")
        ).scalar_one()

        inventory = []
        for row in result:
            inventory.append(
                connection.execute(
                    sqlalchemy.text(
                        "SELECT COALESCE(SUM(quantity), 0) FROM potions_ledger WHERE sku = :sku"
                    ),
                    [{"sku": row.sku}],
                ).scalar_one()
            )

        red_ml, green_ml, blue_ml, dark_ml = mls
        mls = [red_ml, green_ml, blue_ml, dark_ml]
        potions_left = potion_capacity - potions
        pre_threshold = potion_capacity // len(result)

        for i, row in enumerate(result):
            if inventory[i] >= pre_threshold:
                del result[i]
                del inventory[i]

        post_threshold = potion_capacity // len(result)
        max_bottle_each = potions_left // len(result)

        if potions_left < len(result):
            max_bottle_each = potions_left

        i = 0
        for row in result:
            max_from_mls = max_quantity(mls, row.type)
            if max_from_mls == 0 or inventory[i] >= post_threshold or potions_left == 0:
                i += 1
                continue

            till_cap = post_threshold - inventory[i]
            final_quantity = (
                max_from_mls if max_from_mls <= max_bottle_each else max_bottle_each
            )
            final_quantity = final_quantity if final_quantity <= till_cap else till_cap

            print("potion: " + row.sku)
            print("till cap: " + str(till_cap))
            print("max from mls: " + str(max_from_mls))
            print("max bottle each: " + str(max_bottle_each))
            print("final quantity: " + str(final_quantity))

            mls = sub_ml(mls, row.type, final_quantity)
            potions_left -= final_quantity

            plan.append({"potion_type": row.type, "quantity": final_quantity})
            i += 1

        print("bottling plan:")
        print(plan)
        return plan


if __name__ == "__main__":
    print(get_bottle_plan())
