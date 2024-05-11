from fastapi import APIRouter
import sqlalchemy
from src import database as db

router = APIRouter()

@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """
    plan = []
    limit = 6

    with db.engine.begin() as connection:
        # backup catalog plan:
        # write an if to change to select only those in the pot pref list if the day has just restarted
        # write firesale to sell everything with positive inventory that is not in pot pref list
        # pot_list = which_potions()
        # result = connection.execute(
        #     sqlalchemy.text(
        #         "SELECT sku, type, price FROM potions WHERE sku in :pot_list"
        #     ),
        #     [{"pot_list": pot_list}],
        # ).fetchall()

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

        # firesale_pots = firesale()
        # if len(firesale_pots) != 0:
        #     for i in range(len(firesale_pots)):
        #         result.append(firesale_pots[i])

        res_tuple = tuple([row.sku for row in result])

        limit -= len(result)
        added_result = connection.execute(
            sqlalchemy.text(
                """
                    SELECT sku, MAX(timestamp) as latest
                    FROM potions_ledger
                    WHERE sku NOT IN :recents AND quantity > 0
                    GROUP BY sku
                    ORDER BY latest DESC
                    LIMIT :limit
                """
            ),
            [{"recents": res_tuple, "limit": limit}],
        ).fetchall()

        for i in range(len(added_result)):
            if limit > 0:
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

        if result == None:
            return ()
        
        pot_list = tuple(result[0][0])

        connection.execute(
            sqlalchemy.text(
                """
                    UPDATE potions SET price = 1 WHERE sku in :pot_list;
                    UPDATE constants SET firesale = 'false';
                """
            ),
            [{"pot_list": pot_list}],
        )

        result = connection.execute(
            sqlalchemy.text(
                "SELECT sku, type, 1 AS price FROM potions WHERE sku in :pot_list"
            ),
            [{"pot_list": pot_list}],
        ).fetchall()

    return result
