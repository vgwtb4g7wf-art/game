"""Награды 0.13: стоимость риска и умеренное ускорение старших сложностей."""
HUNT_XP=(16,24,34,44,56)
HUNT_GOLD=(13,17,21,25,29)
HUNT_BRANCH=(8,11,15,19,24)

def hunt_reward(tier):
    return dict(xp=HUNT_XP[tier-1],gold=HUNT_GOLD[tier-1],progress=HUNT_BRANCH[tier-1])

def peace_reward(delivery,distance):
    bonus=0 if not distance else 1 if distance<=2 else 2 if distance<=5 else 3
    return dict(xp=12 if delivery else 18,gold=(7 if delivery else 10)+bonus,progress=5 if delivery else 7)

def event_reward(tier):
    return dict(xp=(8,12,16,22,28)[tier-1],gold=(3,4,6,8,10)[tier-1],progress=(3,4,6,8,10)[tier-1])
