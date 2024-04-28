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
        # get the 6 most recent, unique potions sold
        result = connection.execute(
            sqlalchemy.text(
                """
                SELECT DISTINCT sku
                FROM (
                    SELECT *
                    FROM potions_ledger
                    WHERE quantity < 0
                    ORDER BY timestamp DESC
                ) as skus
                LIMIT 6
                """
            )
        ).fetchall()

        if len(result) < 6:
            # if there are not 6 recently sold potions, the rest in the catalog will be recently bottled
            limit -= len(result)
            added_result = connection.execute(
                sqlalchemy.text(
                    """
                SELECT DISTINCT sku
                FROM (
                    SELECT *
                    FROM potions_ledger
                    ORDER BY timestamp DESC
                ) as skus
                LIMIT :limit
                """
                ),
                [{"limit": limit}],
            ).fetchall()

            for i in range(len(added_result)):
                if added_result[i] not in result:
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

    return plan
