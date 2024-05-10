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
        # write an if to change to select only those in the pot pref list if the day has just restarted
        # write firesale to sell everything with positive inventory that is not in pot pref list
        pot_list = which_potions()
        result = connection.execute(
            sqlalchemy.text(
                "SELECT sku, type, price FROM potions WHERE sku in :pot_list"
            ),
            [{"pot_list": pot_list}],
        ).fetchall()

        # get the 6 most recent, unique potions sold
        # result = connection.execute(
        #     sqlalchemy.text(
        #         """
        #             SELECT sku, MAX(timestamp) as latest
        #             FROM potions_ledger
        #             WHERE quantity < 0
        #             GROUP BY sku
        #             ORDER BY latest DESC
        #             LIMIT 3
        #         """
        #     )
        # ).fetchall()

        # res_tuple = tuple([row.sku for row in result])
        # firesale_pots = firesale()
        # if len(firesale_pots) != 0:


        # limit -= len(result)
        # added_result = connection.execute(
        #     sqlalchemy.text(
        #         """
        #             SELECT sku, MAX(timestamp) as latest
        #             FROM potions_ledger
        #             WHERE sku NOT IN :recents AND quantity > 0
        #             GROUP BY sku
        #             ORDER BY latest DESC
        #             LIMIT :limit
        #         """
        #     ),
        #     [{"recents": res_tuple, "limit": limit}],
        # ).fetchall()

        # for i in range(len(added_result)):
        #     result.append(added_result[i])

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
    #   if firesale = true
    #   change the price of whatever is in the constants table to 1 gold
    #   return these potions

    with db.engine.begin() as connection:
        result = connection.execute(
            sqlalchemy.text(
                """
                    SELECT 
                    CASE
                        WHEN firesale = 'true'
                        THEN firesale_potions
                    END AS firesale_pref
                    FROM constants
                """
                )
            ).fetchall()

        print(result)

    return result
