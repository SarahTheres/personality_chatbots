import random
from dataIO import *
from start import bot_personality_states


def personality_order(participant_id: int):
    # 0: dei, 1: ide, 2: eid
    pers = get_personality_order_counters()[1]
    order_dei = pers.get("order_dei")
    order_ide = pers.get("order_ide")
    order_eid = pers.get("order_eid")

    if (order_dei != 10 and order_ide != 10 and order_eid != 10) or \
            (order_dei >= 10 and order_ide >= 10 and not order_eid >= 10):
        pers = random.randint(0, 2)

    elif order_dei == 10:
        if order_ide == 10:
            pers = 2
        elif order_eid == 10:
            pers = 1
        else:
            pers = random.randint(1, 2)

    elif order_ide == 10:
        if order_eid == 10:
            pers = 0
        else:
            pers = random.choice([0, 2])

    elif order_eid == 10:
        pers = random.choice([0, 1])

    set_personality_order(participant_id, pers)
    bot_personality_states(participant_id, 0, pers)

    return update_counters(pers, order_dei, order_ide, order_eid)


def update_counters(order: int, order_dei: int, order_ide: int, order_eid: int):
    # 0: dei, 1: ide, 2: eid
    if order == 0:
        counter = order_dei
    elif order == 1:
        counter = order_ide
    else:
        counter = order_eid

    return set_personality_order_counters(order, counter + 1)