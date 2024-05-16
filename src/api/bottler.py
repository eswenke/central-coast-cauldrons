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
        threshold = potion_capacity // len(result)

        for i, row in enumerate(result):
            if inventory[i] >= threshold:
                del result[i]
                del inventory[i]

        
        # max_bottle_each = potions_left // len(result)

        for i, row in enumerate(inventory):
            till_cap = (threshold - inventory[i]) if (threshold - inventory[i]) <= potions_left else potions_left
            inventory[i] = till_cap
            potions_left -= till_cap

        # if potions_left < len(result):
        #     max_bottle_each = potions_left

        i = 0
        for row in result:
            max_from_mls = max_quantity(mls, row.type)
            if max_from_mls == 0 or inventory[i] >= threshold or potions_left <= 0:
                i += 1
                continue

            # till_cap = threshold - inventory[i]
            till_cap = inventory[i]

            # final_quantity = (
            #     max_from_mls if max_from_mls <= max_bottle_each else max_bottle_each
            # )
            # final_quantity = final_quantity if final_quantity <= till_cap else till_cap
            final_quantity = max_from_mls if max_from_mls <= till_cap else till_cap

            mls = sub_ml(mls, row.type, final_quantity)
            potions_left -= final_quantity

            plan.append({"potion_type": row.type, "quantity": final_quantity})
            i += 1

        print("bottling plan:")
        print(plan)
        return plan
    
def max_quantity(arr1, arr2):
    result = []
    for x, y in zip(arr1, arr2):
        if y != 0:
            result.append(x // y)
        else:
            result.append(float("inf"))

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
                    SELECT day, hour
                    FROM timestamps
                    ORDER BY id DESC
                    LIMIT 1;
                """
            )
        ).first()
        return result

# def which_potions():
#     with db.engine.begin() as connection:
#         day, hour = get_day()

#         pot_list = connection.execute(
#             sqlalchemy.text(
#                 """
#                     SELECT pot_pref
#                     FROM preferences
#                     WHERE day = :day
#                 """
#             ),
#             [{"day": day}],
#         ).first()[0]

#     return tuple(pot_list)

def which_potions():
    with db.engine.begin() as connection:
        # day, hour = get_day()

        # pot_list = connection.execute(
        #     sqlalchemy.text(
        #         """
        #             with days as (
        #                 SELECT 
        #                     day, 
        #                     pot_pref, 
        #                     LEAD(day, 1, 'Edgeday') OVER (ORDER BY id) AS next_day
        #                 FROM preferences 
        #             )
        #             select
        #             case
        #                 when :hour = 22 THEN (select 
        #                                     pot_pref 
        #                                     from days 
        #                                     where day = (select next_day from days where day = :day))
        #                 else (select pot_pref from days where day = :day)
        #             end as potion_preferences
        #         """
        #     ),
        #     [{"day": day, "hour": hour}],
        # ).first()[0]

        pot_list = connection.execute(
            sqlalchemy.text(
                """
                SELECT all_pots 
                FROM constants
                """
            )
        ).first()[0]

    return tuple(pot_list)


if __name__ == "__main__":
    print(get_bottle_plan())
