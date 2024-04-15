from fastapi import APIRouter
import sqlalchemy
from src import database as db

router = APIRouter()


@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """

    # OFFER ALL GREEN AND RED AND BLUE POTIONS, (ADD THOSE RED AND BLUE COLUMNS TO THE DB)
    # MAKE THEM CHEAP TO TEST

    with db.engine.begin() as connection:
        result = connection.execute(
            sqlalchemy.text("SELECT num_green_potions FROM global_inventory")
        ).first()[0]

    if result > 0:
        return [
            {
                "sku": "GREEN_POTION_0",
                "name": "green potion",
                "quantity": 1,
                "price": 1,
                "potion_type": [0, 100, 0, 0],
            }
        ]
    else:
        return []
