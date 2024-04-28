from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(auth.get_api_key)],
)


@router.post("/reset")
def reset():
    """
    Reset the game state. Gold goes to 100, all potions are removed from
    inventory, and all barrels are removed from inventory. Carts are all reset.
    """

    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text("TRUNCATE potions_ledger"))
        connection.execute(sqlalchemy.text("TRUNCATE gold_ledger"))
        connection.execute(sqlalchemy.text("TRUNCATE ml_ledger"))
        connection.execute(sqlalchemy.text("TRUNCATE carts CASCADE"))
        connection.execute(sqlalchemy.text("TRUNCATE processed"))
        connection.execute(sqlalchemy.text("INSERT INTO ml_ledger DEFAULT VALUES"))
        connection.execute(sqlalchemy.text("INSERT INTO potions_ledger (quantity, sku) VALUES (0, 'RED_POTION')"))
        connection.execute(
            sqlalchemy.text("INSERT INTO gold_ledger (gold) VALUES (100)")
        )
        connection.execute(
            sqlalchemy.text("UPDATE constants SET potion_capacity = 50, ml_capacity = 10000")
        )
        # an empty potions ledger will return None ******************

    return "OK"
