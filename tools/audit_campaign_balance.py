"""Все расы/предыстории и противники; последовательные прохождения экономики."""
import argparse,copy,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from adventure import Adventure,Quest
from bestiary import BESTIARY
from combat import CARDS,ITEM_POWER,selectable,stats
from combat_ai import choose
from eterion import RACES,BACKGROUNDS,ITEMS
from progression import COSTS
from trade import GEAR_PRICES,META


def fight(g,enemy,tier,seed,consumables=None,quest=False):
    g.turn=max(g.turn,seed);g.preparation=dict(kind='event',quest_id=None,target=None,enemy=enemy,tier=tier)
    if isinstance(quest,Quest):
        g.preparation.update(kind='quest',quest_id=quest.id)
    elif quest:
        g.search_count+=1
        from balance_rewards import hunt_reward
        reward=hunt_reward(tier)
        q=Quest(f'audit-{g.search_count}',enemy,'Аудит охоты',tier,'Мощь',g.hero.region,g.hero.region,False,enemy,**reward,loot=None,monster_tier=tier)
        g.active.append(q);g.preparation.update(kind='quest',quest_id=q.id)
    g.begin_battle(consumables or {})
    for _ in range(200):
        if not g.battle:return dict(win=g.last_battle['outcome']=='victory',damage=g.last_battle['damage_taken'],rounds=g.last_battle['rounds'])
        if g.battle['round']>40:break
        i=choose(g)
        if i is not None:g.play_card(i)
        else:g.end_round()
    return dict(win=False,damage=g.battle['damage_taken'],rounds=g.battle['round'],timeout=True)


def grow(g,branch,side,rank):
    needed=sum(COSTS[:rank])-sum(COSTS[:g.hero.branches[branch]])
    g.gain_branch(branch,max(0,needed))
    if rank>3 and not g.paths[branch]:g.choose_path(branch,side)
    g.selected_skills=selectable(g.hero)[:3];g.sync_skills()


def matrix():
    gear=list(META);rows=[]
    for race in RACES:
        for background in BACKGROUNDS:
            outcomes={t:[] for t in range(1,6)}
            for index,(enemy,m) in enumerate(BESTIARY.items()):
                tier=m['tier']
                for seed in (1,2,3):
                    weapon=('Железный меч','Короткий кинжал','Дорожный лук')[seed-1]
                    g=Adventure.create('Проверка','Мужской',race,background,weapon,'Глыба','Мощь')
                    g.auto_diplomacy=False;g.maybe_event=lambda _:None
                    g.xp=(tier-1)*100;g.stat_points=(tier-1)//2
                    while g.stat_points:g.choose_growth('damage' if seed!=2 else 'hp')
                    branch=('Мощь','Хитрость','Знания')[(index+seed)%3]
                    grow(g,branch,'left' if seed%2 else 'right',(1,2,3,5,6)[tier-1])
                    if tier>=2:
                        arm=('Кожаная куртка','Кольчуга','Стёганая куртка путника')[seed-1]
                        g.bag.append(arm);g.equip(arm)
                    if tier>=3:
                        n=gear[(index*3+seed)%len(gear)]
                        if n not in g.bag:g.bag.append(n)
                        g.equip(n)
                    c={'common:bandage':1,'common:smoke':1} if seed==3 else {}
                    g.consumables=dict(c);g.hp=stats(g.hero)['hp']
                    result=fight(g,enemy,tier,seed,consumables=c)
                    outcomes[tier].append(result)
            for t,rr in outcomes.items():
                rows.append(dict(race=race,background=background,tier=t,n=len(rr),win=sum(x['win'] for x in rr)/len(rr),zero=sum(x['damage']==0 for x in rr)/len(rr),damage=sum(x['damage'] for x in rr)/len(rr),rounds=sum(x['rounds'] for x in rr)/len(rr),timeouts=sum(x.get('timeout',False) for x in rr)))
            print(race,background,'готово',flush=True)
    return rows


def campaign(race,background,style,seed,liquidate=False):
    g=Adventure.create('Кампания','Мужской',race,background,'Железный меч','Глыба','Мощь')
    g.auto_diplomacy=False;g.maybe_event=lambda _:None
    earned=spent=rest_days=potions=bought=0;history=[]
    for step in range(30):
        while g.level_points:g.spend_level('Мощь') if g.hero.branches['Мощь']<6 else g.spend_level('Знания')
        if g.hero.branches['Мощь']==3 and g.branch_xp['Мощь']>=100:g.choose_path('Мощь','left')
        g.selected_skills=selectable(g.hero)[:3];g.sync_skills()
        while g.stat_points:g.choose_growth('damage')
        # Город — рабочая база; полные закупки доступны только из текущей поставки.
        g.in_city=False
        if style!='frugal' and g.hero.gold>=g.entry_fee():
            fee=g.entry_fee();g.enter_city();spent+=fee
        def value(n):
            if not n:return 0
            e=ITEM_POWER[n];p=e.get('passives',{})
            return e['armor']+e['hit']*.35+p.get('hp',0)+p.get('hit',0)*.35+p.get('healing_bonus',0)*.06+sum((CARDS[k]['block']+CARDS[k]['heal']+CARDS[k].get('armor',0)+CARDS[k]['ratio']*.03)/max(1,CARDS[k]['cost']) for k in e['cards'])
        if liquidate and g.shop()['accessible']:
            for slot in ('Оружие','Доспех','Артефакт'):
                options=[n for n in g.bag if ITEMS[n][0]==slot]
                if options:
                    best=max(options,key=value)
                    if value(best)>value(g.hero.equipment[slot]):g.equip(best)
            for n in list(g.bag):
                if n not in g.hero.equipment.values():
                    price=g.sale_price('gear:'+n);g.sell('gear:'+n);earned+=price
        for offer in g.shop()['gear']:
            n=offer['item']
            if n not in g.bag and g.hero.gold>=offer['price'] and ITEMS[n][0]!='Оружие' and value(n)>value(g.hero.equipment[ITEMS[n][0]])+.5:
                g.buy('gear:'+n);spent+=offer['price'];bought+=1;g.equip(n)
        if style=='supplies':
            for offer in g.shop()['offers']:
                if CARDS[offer['card']]['heal'] and g.hero.gold>=offer['price'] and sum(g.consumables.values())<4 and offer['left']:
                    g.buy(offer['card']);spent+=offer['price'];potions+=1
        for k in list(g.consumables):
            while g.consumables.get(k,0) and g.hp<g.combat_stats()['hp']:g.use_item(k)
        while g.hp<g.combat_stats()['hp']:
            if not g.in_city and g.hero.gold>=g.entry_fee()+4:
                fee=g.entry_fee();g.enter_city();spent+=fee
            if g.in_city and g.hero.gold>=g.rest_offer()['cost']:
                cost=g.rest_offer()['cost'];g.wait();spent+=cost
            else:break
        if g.hp<g.combat_stats()['hp']:break
        # Платный отдых/городская база; вход считается один раз, как при стоянке в городе.
        if g.in_city:g.leave_city()
        g.search();q=g.offers[0];g.accept(q.id);g.complete(q.id)
        if not g.preparation:g.complete(q.id)
        tier=q.monster_tier;enemy=q.monster;before=g.hero.gold
        chosen={k:1 for k,v in list(g.consumables.items())[:2] if v} if style=='supplies' else {}
        result=fight(g,enemy,tier,g.turn,chosen,q)
        earned+=g.hero.gold-before
        history.append(dict(quest=step+1,tier=tier,xp=g.xp,level=1+g.xp//100,gold=g.hero.gold,power_rank=g.hero.branches['Мощь'],branch_xp=g.branch_xp['Мощь'],damage=result['damage'],win=result['win'],day=g.turn))
        if not result['win']:break
    return dict(race=race,background=background,style=style,seed=seed,completed=len(g.completed),dead=g.dead,gold=g.hero.gold,earned=earned,spent=spent,gear_bought=bought,potions_bought=potions,free_rest_days=rest_days,days=g.turn,level=1+g.xp//100,power_rank=g.hero.branches['Мощь'],history=history)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('output',type=Path);parser.add_argument('--matrix',action='store_true');parser.add_argument('--liquidate',action='store_true');args=parser.parse_args()
    rows=matrix() if args.matrix else [campaign(r,b,s,seed,args.liquidate) for r in RACES for b in BACKGROUNDS for s in ('frugal','comfort','supplies') for seed in ((1,) if args.liquidate else (1,2,3))]
    args.output.write_text(json.dumps(rows,ensure_ascii=False,indent=2))
