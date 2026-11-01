"""Первые 12 охот без бесплатного лечения, с заработком на восстановление."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from adventure import Adventure
from eterion import RACES,BACKGROUNDS
from combat import CARDS,ITEM_POWER,selectable
from combat_ai import choose


def play(race,bg,weapon,seed):
    g=Adventure.create('Ранний путь','Мужской',race,bg,weapon,'Глыба',BACKGROUNDS[bg][0])
    g.auto_diplomacy=False;g.maybe_event=lambda _:None;g.turn=seed
    hunted=worked=rest_cost=entry_cost=0
    for step in range(12):
        while g.level_points:g.spend_level('Мощь')
        if g.hero.branches['Мощь']==3 and g.branch_xp['Мощь']>=100:g.choose_path('Мощь','left')
        while g.stat_points:g.choose_growth('hp' if seed==2 else 'damage')
        g.selected_skills=selectable(g.hero)[:3];g.sync_skills()
        for n in g.bag:
            if __import__('eterion').ITEMS[n][0]=='Доспех' and ITEM_POWER[n]['armor']>g.combat_stats()['armor']:g.equip(n)
        for k in list(g.consumables):
            if CARDS[k]['heal'] and g.hp<=g.combat_stats()['hp']-CARDS[k]['heal']:g.use_item(k)
        for _ in range(30):
            if g.hp>=g.combat_stats()['hp']*.85:break
            if not g.in_city and g.hero.gold>=g.entry_fee()+4:
                entry_cost+=g.entry_fee();g.enter_city()
            if g.in_city and g.hero.gold>=4:
                rest_cost+=4;g.wait();continue
            # Без монет можно выполнить мирное поручение, а не бесплатно лечиться ожиданием.
            g.search();q=next((q for q in g.offers if not q.monster and q.target==g.hero.region),None)
            if not q:continue
            if __import__('narrative_content').PEACE_QUESTS[q.template]['fee']>g.hero.gold:continue
            g.accept(q.id);g.complete(q.id)
            while g.event:
                options=g.narrative_view()['options'];g.resolve_event('listen' if any(o['id']=='listen' for o in options) else 'good')
            worked+=1
        if g.hp<g.combat_stats()['hp']*.85:break
        for o in g.shop()['gear']:
            if __import__('eterion').ITEMS[o['item']][0]=='Доспех' and o['item'] not in g.bag and g.hero.gold>=o['price']+13 and ITEM_POWER[o['item']]['armor']>g.combat_stats()['armor']:
                g.buy('gear:'+o['item']);g.equip(o['item'])
        if g.in_city:g.leave_city()
        g.search();q=g.offers[0];g.accept(q.id);g.complete(q.id)
        if not g.preparation:g.complete(q.id)
        g.begin_battle({k:min(v,1) for k,v in g.consumables.items()})
        for _ in range(150):
            if not g.battle:break
            i=choose(g)
            if i is not None:g.play_card(i)
            else:g.end_round()
        if g.battle or g.dead:break
        hunted+=1
    return dict(race=race,background=bg,weapon=weapon,seed=seed,hunts=hunted,peace=worked,dead=g.dead,gold=g.hero.gold,rest_cost=rest_cost,entry_cost=entry_cost,level=1+g.xp//100,day=g.turn,failed=len(g.failed))

if __name__=='__main__':
    rows=[]
    for race in RACES:
        for bg in BACKGROUNDS:
            for weapon in ('Железный меч','Короткий кинжал','Дорожный лук'):
                for seed in (1,2):rows.append(play(race,bg,weapon,seed))
            print(race,bg,'готово',flush=True)
    Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/start-economy.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
