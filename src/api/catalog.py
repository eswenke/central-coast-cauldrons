from fastapi import APIRouter
import sqlalchemy
from src import database as db

router = APIRouter()


def which_potions():
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

@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """
    pot_list = which_potions()
    plan = []
    limit = 6
    # firesale()

    with db.engine.begin() as connection:
        # LIMIT TO 4 on day of comp, then the last 2 either firesale or recently bottled
        # potions that need to be firesaled:
        #       any potion that has not sold in 3 ticks but has more than 0 inventory, limit 2
        #       set price from 10 - 20 gold at random
        #       return those potion skus and prices, add them to the main catalog
        # if no firesaled potions:
        #       grab the most recently bottled potions (that are not already in the results, 6 - len(result) for number)
        #       already have the sql to do this

        result = connection.execute(
            sqlalchemy.text(
                "SELECT sku, type, price FROM potions WHERE sku in :pot_list"
            ),
            [{"pot_list": pot_list}],
        ).fetchall()

        # # get the 6 most recent, unique potions sold
        # result = connection.execute(
        #     sqlalchemy.text(
        #         """
        #         SELECT DISTINCT sku
        #         FROM (
        #             SELECT *
        #             FROM potions_ledger
        #             WHERE quantity < 0
        #             ORDER BY timestamp DESC
        #         ) as skus
        #         LIMIT 3
        #         """
        #     )
        # ).fetchall()

        # res_tuple = tuple([row.sku for row in result])
        # print(res_tuple)

        # limit -= len(result)
        # added_result = connection.execute(
        #     sqlalchemy.text(
        #         """
        #     SELECT DISTINCT sku
        #     FROM (
        #         SELECT *
        #         FROM potions_ledger
        #         WHERE sku NOT IN :recents AND quantity > 0
        #         ORDER BY timestamp DESC
        #     ) as skus
        #     LIMIT :limit
        #     """
        #     ),
        #     [{"recents" : res_tuple, "limit": limit}],
        # ).fetchall()

        # for i in range(len(added_result)):
        #         result.append(added_result[i])
            
        for row in result:
            # get inventory
            inventory = connection.execute(
                sqlalchemy.text(
                    """
                    SELECT SUM(potions_ledger.quantity)
                    FROM potions_ledger
                    WHERE potions_ledger.sku = :sku
                    """
                ),
                [{"sku": row.sku}],
            ).scalar_one()

            if inventory is None or inventory <= 0:
                continue

            # get price and sku
            price_and_sku = connection.execute(
                sqlalchemy.text(
                    """
                    SELECT price, type
                    FROM potions
                    WHERE potions.sku = :sku
                    """
                ),
                [{"sku": row.sku}],
            ).first()
            price, type = price_and_sku

            plan.append(
                {
                    "sku": row.sku,
                    "quantity": inventory,
                    "price": price,
                    "potion_type": type,
                }
            )

    print("catalog: ")
    print(plan)
    return plan


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


def firesale():
#     # return a list of potions to change the price of to very cheap because they are not selling
#     # maybe pick a max of 2 potions every catalog that will have their prices lowered based on:
#         # grab the first 2 potion type that have not sold in over a day:
#             # and put their price to 10 (ONLY IN THE PLAN, NOT THE ACTUAL POTIONS TABLE)
#         # add those to the end of the catalog

#     # we could also just take the previous day's catalog and firesale whatever potions are not 

#     # for all the potion types in potions
#     # filter for all those that have a positive inventory
#     # filter for one row of the most recent negative quantity transaction for each potion type
#     # for any potion types that haven't sold in the last 12 hours since the most recent time, 
#     #   lower their price to 10 gold
#     #   (can add a time column to constant that updates to the most recent time when time is called in game, use that
#     #   for most recent time for all potions)


#     with db.engine.begin() as connection:
#         result = connection.execute(
#             sqlalchemy.text(
#                 """
#                     SELECT DISTINCT sku
#                     FROM potions_ledger
#                     WHERE timestamp <= (SELECT MAX(timestamp) - interval '12 hours' FROM potions_ledger), quantity > 0
#                     ORDER BY timestamp DESC
#                     LIMIT 3;
#                 """
#                 )
#             ).fetchall()
        
#         print(result)

    return