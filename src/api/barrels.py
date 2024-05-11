from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from sqlalchemy.exc import IntegrityError
from src import database as db
import random
import math

router = APIRouter(
    prefix="/barrels",
    tags=["barrels"],
    dependencies=[Depends(auth.get_api_key)],
)


class Barrel(BaseModel):
    sku: str

    ml_per_barrel: int
    potion_type: list[int]
    price: int

    quantity: int

# add a function that will buy large barrel early on before we have 750*4 gold
#       this function should figure out what the best type to buy would be based on potions sold in the last day

# write a query that sums all potions over the last 24 hours
#       creates a list of the most sold potions and their quantities
#       can use this to determine which large barrel to buy for the above function
#       can use this to figure out what ml to bottle more of? catalog?

def buy_mini(gold, mls):
    mini = False
    i = 0
    for ml in mls:
        if ml < 250:
            i += 1
    if i >= 3 and gold < 100:
        mini = True

    return mini

def buy_small(gold, ml_capacity):
    small = True
    if gold > 3500 and ml_capacity > 10000:
        small = False

    return small

def buy_large(gold, mls, ml_capacity, ml_limit):
    # index_to_buy = -1
    # lowest = math.inf
    type = -1

    if ml_capacity == 10000 or gold < 750 or ml_limit < 10000:
        return -1
    
    if mls[3] < 500:
        type = [0, 0, 0, 1]

    # for i in range(len(mls)):
    #     if mls[i] < lowest:
    #         lowest = mls[i]
    #         index_to_buy = i

    # type = [0,0,0,0]
    # if index_to_buy > 0:
    #     type[i] = 1

    # sum_ml = sum(mls)
    # for i in range(len(mls)):
    #     mls[i] = mls[i] / sum_ml
    #     if mls[i] < .20 and i != 3: # exclude dark ml from this loop
    #         index_to_buy[i] = 1
    #         large = True

    return type



def create_wpp(
    wholesale_catalog: list[Barrel],
    plan: list[Barrel],
    potion_type,
    gold,
    ml_limit,
    mls,
    ml_capacity,
    index,
    selling_large
):
    """ """
    gold = int(gold)
    mini = buy_mini(gold, mls)
    small = buy_small(gold, ml_capacity)
    type = buy_large(gold, mls, ml_capacity, ml_limit)
    threshold = .33 * ml_capacity

    print("large: " + str(selling_large))
    print("type: " + str(type))
    print("potion_type: " + str(potion_type))

    for barrel in wholesale_catalog:
        if (
            (gold >= barrel.price)
            and (potion_type == barrel.potion_type)
            and (barrel not in plan)
        ):
            if not mini and ("MINI" in barrel.sku):
                continue
            elif not small and ("SMALL" in barrel.sku):
                continue       
            elif not selling_large and ("LARGE" in barrel.sku):
                continue
            elif selling_large and potion_type != type: # only buy the large of dark and nothing else on that tick
                continue
            else:
                q_max = ml_limit // barrel.ml_per_barrel
                q_buyable = gold // barrel.price
                q_threshold = (threshold - mls[index]) // barrel.ml_per_barrel

                if selling_large and barrel.potion_type == type and ml_limit > 10000: # skip to the dark barrel
                    if "LARGE" not in barrel.sku:
                        continue
                    q_threshold = 1

                q_final = q_buyable if q_max >= q_buyable else q_max
                q_final = q_final if q_final <= barrel.quantity else barrel.quantity
                q_final = q_final if q_final <= q_threshold else q_threshold

                print("q_max: " + str(q_max))
                print("q_buy: " + str(q_buyable))
                print("q_threshold: " + str(q_threshold))
                print("q_final: " + str(q_final))

                if q_final <= 0:
                    continue
                else:
                    return {
                        "sku": barrel.sku,
                        "quantity": q_final,
                    }

    return None



@router.post("/deliver/{order_id}")
def post_deliver_barrels(barrels_delivered: list[Barrel], order_id: int):
    """ """
    print(f"barrels delievered: {barrels_delivered} order_id: {order_id}")

    g_ml = 0
    r_ml = 0
    b_ml = 0
    d_ml = 0
    price = 0
    for barrel in barrels_delivered:
        price += barrel.price * barrel.quantity
        if barrel.potion_type == [0, 1, 0, 0]:
            g_ml += barrel.ml_per_barrel * barrel.quantity
        if barrel.potion_type == [1, 0, 0, 0]:
            r_ml += barrel.ml_per_barrel * barrel.quantity
        if barrel.potion_type == [0, 0, 1, 0]:
            b_ml += barrel.ml_per_barrel * barrel.quantity
        if barrel.potion_type == [0, 0, 0, 1]:
            d_ml += barrel.ml_per_barrel * barrel.quantity

    with db.engine.begin() as connection:
        try:
            connection.execute(
                sqlalchemy.text(
                    "INSERT INTO processed (id, type) VALUES (:order_id, 'barrels')"
                ),
                [{"order_id": order_id}],
            )
        except IntegrityError as e:
            return "OK"

        connection.execute(
            sqlalchemy.text(
                """
                INSERT INTO ml_ledger (red_ml, green_ml, blue_ml, dark_ml) 
                VALUES (:r_ml, :g_ml, :b_ml, :d_ml)"""
            ),
            [{"r_ml": r_ml, "g_ml": g_ml, "b_ml": b_ml, "d_ml": d_ml}],
        )

        connection.execute(
            sqlalchemy.text(
                """
                INSERT INTO gold_ledger (gold) 
                VALUES (-:price)"""
            ),
            [{"price": price}],
        )

    return "OK"


# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print(wholesale_catalog)

    

    with db.engine.begin() as connection:
        mls = connection.execute(
            sqlalchemy.text(
                "SELECT SUM(ml_ledger.red_ml), SUM(ml_ledger.green_ml), SUM(ml_ledger.blue_ml), SUM(ml_ledger.dark_ml) FROM ml_ledger"
            )
        ).first()

        ml_capacity = connection.execute(
            sqlalchemy.text(
                "SELECT ml_capacity FROM constants"
            )
        ).scalar_one()

        potions = connection.execute(
            sqlalchemy.text(
                "SELECT SUM(potions_ledger.quantity) FROM potions_ledger"
            )
        ).scalar_one()

        gold = connection.execute(
            sqlalchemy.text(
                "SELECT SUM(gold_ledger.gold) FROM gold_ledger"
            )
        ).scalar_one()
        
        r_ml, g_ml, b_ml, d_ml = mls
        ml_arr = [r_ml, g_ml, b_ml, d_ml]
        current_ml = sum(ml_arr)

        selling_large = any(item.sku.startswith("LARGE") for item in wholesale_catalog)
        threshold = .15 * ml_capacity 
        gold_dec = False

        plan = []

        for i, ml in enumerate(ml_arr):
            ml_limit = ml_capacity - current_ml
            if ml < threshold:
                potion_type = [int(j == i) for j in range(4)]
                if (
                    gold < 240
                ):  # if gold less than 240, decrement gold each iteration. if not, do not.
                    gold_dec = True

                barrel_purchase = create_wpp(
                    wholesale_catalog,
                    plan,
                    potion_type,
                    gold / 4 if (not gold_dec) else gold,
                    ml_limit,
                    ml_arr,
                    ml_capacity,
                    i,
                    selling_large
                )
                if barrel_purchase is not None:
                    price = next(
                        item.price
                        for item in wholesale_catalog
                        if item.sku == barrel_purchase["sku"]
                    )
                    ml_per_barrel = next(
                        item.ml_per_barrel
                        for item in wholesale_catalog
                        if item.sku == barrel_purchase["sku"]
                    )
                    plan.append(barrel_purchase)
                    if (
                        gold_dec
                    ):  # not decremented when gold can be divisible by 4 for more variety
                        gold -= price * barrel_purchase["quantity"]
                    current_ml += ml_per_barrel * barrel_purchase["quantity"]

    print("barreling plan:")
    print(plan)
    return plan
