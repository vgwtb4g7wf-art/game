"""Детерминированная выборка дуэлей. Запуск: python tools/check_balance.py."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from adventure import Adventure
from combat import CARDS,card_damage,card_heal,stats
from world_content import BIOMES


def fight(weapon,tier,level,day):
    game=Adventure.create('Проверка','Мужской','Человек','Воришка',weapon,'Глыба','Знания')
    game.maybe_event=lambda _:None
    game.auto_diplomacy=False
    game.turn=day
    game.xp=(level-1)*100;game.stat_points=(level-1)//2
    while game.stat_points:game.choose_growth('damage')
    game.sync_skills();game.hp=stats(game.hero)['hp']
    if level>=3:
        game.bag.append('Кожаная куртка');game.equip('Кожаная куртка')
    game.search();q=game.offers[0];q.monster=BIOMES['Княжество Бреннор'][1][tier-1];q.monster_tier=tier
    game.accept(q.id);game.complete(q.id);game.begin_battle(dict(game.consumables))
    for _ in range(160):
        b=game.battle
        if not b:return game.last_battle['outcome']=='victory',game.last_battle['rounds']
        choices=[]
        for i,key in enumerate(b['hand']):
            c=CARDS[key]
            if c['cost']>b['energy']:continue
            damage=card_damage(c,game.hero)
            missing=game.combat_stats()['hp']-game.hp
            incoming=b['intent_value'] if b['intent']=='attack' else 0
            value=damage+min(missing,card_heal(c,game.hero))*.8+min(max(0,incoming-b['block']),c['block'])*.6+c['bank']
            if damage>=b['enemy_hp']+b['enemy_armor']+b['enemy_block'] and damage:value+=20
            if value>0:choices.append((value/max(1,c['cost']),i))
        if choices:game.play_card(max(choices)[1])
        else:
            if b['hand']:
                index=max(range(len(b['hand'])),key=lambda i:card_damage(CARDS[b['hand'][i]],game.hero))
                game.retain_card(index)
            game.end_round()
    raise AssertionError('Бой не завершился за 160 действий')


def sample(runs=80):
    rows=[]
    for level,tier in ((1,1),(1,3),(3,3),(5,5)):
        for weapon in ('Железный меч','Короткий кинжал','Дорожный лук'):
            results=[fight(weapon,tier,level,day) for day in range(1,runs+1)]
            wins=sum(w for w,_ in results);rounds=sum(n for _,n in results)/runs
            rows.append((level,tier,weapon,wins/runs,rounds))
    for item in ('Кожаная куртка','Кольчуга','Кольцо янтаря','Медный амулет'):
        results=[fight(item,1,1,day) for day in range(1,runs+1)]
        rows.append((1,1,item,sum(w for w,_ in results)/runs,sum(n for _,n in results)/runs))
    return rows


if __name__=='__main__':
    for level,tier,item,wins,rounds in sample():
        print(f'Уровень {level}, враг {tier}, {item}: победы {wins:.0%}, раундов {rounds:.1f}')
