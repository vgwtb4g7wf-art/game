"""Бот для оценки колоды; видит текущую руку и намерение, не будущие броски."""
from combat import CARDS,card_damage,card_heal

def choose(g,weights=(1.,.85)):
    """Перебор доступных последовательностей руки до ответа врага, с ожидаемым уроном."""
    b=g.battle;s=g.combat_stats();health_weight,armor_weight=weights
    cache={}
    for key in b['hand']:
        c=CARDS[key];hit=max(5,min(100,s['hit']+c['accuracy']))/100
        damage=card_damage(c,g.hero)*hit*(1+s['crit_chance']/100*(s['crit_multiplier']/100-1))
        cache[key]=(c,damage,card_heal(c,g.hero))
    best=(-float('inf'),None)
    def visit(hand,energy,hp,armor,block,enemy,ea,eb,bank,path):
        nonlocal best
        incoming=b['intent_value'] if b['intent']=='attack' and enemy>0 else 0
        received=max(0,incoming-block);a=max(0,armor-received);h=hp-max(0,received-armor)
        score=-(enemy+ea*.8)+health_weight*(h+armor_weight*a)+bank*s['damage']*.65
        if enemy<=0:score=100000+hp+armor*.5-len(path)*.01
        elif h<=0:score-=100000
        score+=len(path)*.005
        if score>best[0]+1e-7:best=(score,path[0] if path else None)
        if enemy<=0:return
        seen=set()
        for idx in hand:
            key=b['hand'][idx]
            if key in seen:continue
            seen.add(key);c,damage,healing=cache[key]
            if c['cost']>energy:continue
            absorbed=min(eb,damage);damage-=absorbed
            armored=min(ea,damage);damage-=armored
            visit(tuple(i for i in hand if i!=idx),energy-c['cost'],min(s['hp'],hp+healing),
                  armor+c.get('armor',0),block+c['block'],max(0,enemy-damage),ea-armored,eb-absorbed,
                  bank+c['bank'],path+(idx,))
    visit(tuple(range(len(b['hand']))),b['energy'],g.hp,b['armor'],b['block'],b['enemy_hp'],b['enemy_armor'],b['enemy_block'],b['next_energy'],())
    return best[1]
