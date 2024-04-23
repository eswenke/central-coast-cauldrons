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

    with db.engine.begin() as connection:
        result = connection.execute(
            sqlalchemy.text(
                "SELECT * FROM potions WHERE sku IN ('GREEN_POTION', 'RED_POTION', 'BLUE_POTION', 'BERRY_POTION', 'SWAMP_POTION', 'RAINBOW_POTION') AND inventory > 0"
            )
        ).fetchall()

        for row in result:
            plan.append({"sku": row.sku, "quantity": row.inventory, "price": row.price, "potion_type": row.type})

    return plan
