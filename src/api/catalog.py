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
    # pot_list = which_potions()
    plan = []
    limit = 6
    # firesale()

    with db.engine.begin() as connection:
        # get the 6 most recent, unique potions sold
        result = connection.execute(
            sqlalchemy.text(
                """
                    SELECT sku, MAX(timestamp) as latest
                    FROM potions_ledger
                    WHERE quantity < 0
                    GROUP BY sku
                    ORDER BY latest DESC
                    LIMIT 3
                """
            )
        ).fetchall()

        res_tuple = tuple([row.sku for row in result])

        limit -= len(result)
        added_result = connection.execute(
            sqlalchemy.text(
                """
                    SELECT sku, MAX(timestamp) as latest
                    FROM potions_ledger
                    WHERE sku NOT IN :recents AND quantity >= 0
                    GROUP BY sku
                    ORDER BY latest DESC
                    LIMIT :limit
                """
            ),
            [{"recents": res_tuple, "limit": limit}],
        ).fetchall()

        for i in range(len(added_result)):
            result.append(added_result[i])

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
    #   below is SQL to get the first two potion skus that have not sold in the last 12 hours (needs testing)
    #   add two potions to firesale at a max
    #   check for potions that have not sold in the last 3-4 ticks (6-8 hours) that also have positive inventories > 0
    #   NEED TO IMPLEMENT VERSIONING FOR THIS.
    #       could add another row to each potion type that signifies a cheaper version (add a column to signal firesale price)
    #       could add a catalog table that sets prices for that tick (since catalog is called first), reference when needed
    #   potential to sell a lot of points that are bottled even if they are about to be purchased in the next tick/day
    #   could make this a more manual option and only firesale certain potions that i pick via the database, use a flag

    #   could also change this to give a chance to potions that haven't sold in a while to see if any of them sell.
    #   if not, set a flag that says as much and then firesale them with the next tick or so.
    #   or just try and sell the potions every 6-12 ticks

    #     with db.engine.begin() as connection:
    #         result = connection.execute(
    #             sqlalchemy.text(
    #                 """
    #                     SELECT DISTINCT sku
    #                     FROM potions_ledger
    #                     WHERE timestamp <= (SELECT MAX(timestamp) - interval '12 hours' FROM potions_ledger), quantity > 0
    #                     ORDER BY timestamp DESC
    #                     LIMIT 2;
    #                 """
    #                 )
    #             ).fetchall()

    #         print(result)

    return
