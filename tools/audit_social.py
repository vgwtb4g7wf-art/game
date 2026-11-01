"""Боевые пробы готовности на независимых противниках и оценка расовых стартов."""
import json,copy,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from adventure import Adventure
from combat import stats,selectable
from combat_ai import choose
from social_rules import GEAR_PRICES
from bestiary import BESTIARY
from tools.audit_balance import build,BUILDS

def fight(g,name,tier,seed):
    g=copy.deepcopy(g);g.auto_diplomacy=False;g.event=None;g.battle=None;g.preparation=dict(kind='event',quest_id=None,target=None,enemy=name,tier=tier)
    g.turn=seed;g.begin_battle({})
    for _ in range(180):
        if not g.battle:return dict(win=g.last_battle['outcome']=='victory',damage=g.last_battle['damage_taken'],rounds=g.last_battle['rounds'])
        index=choose(g)
        if index is not None:g.play_card(index)
        else:g.end_round()
    return dict(win=False,damage=g.battle['damage_taken'],rounds=g.battle['round'])

rows=[]
for cls in BUILDS:
    for level,rank in ((1,0),(2,2),(3,3),(5,6)):
        for weapon in ('Железный меч','Дорожный лук'):
            g=build(cls,weapon,1,rank=rank,level=level);rating=g.combat_rating()['tier']
            enemies=[n for n,m in BESTIARY.items() if m['tier']==rating and not m['guard']][:12]
            results=[fight(g,n,rating,s) for n in enemies for s in (101,137,179)]
            rows.append(dict(cls=cls,level=level,rank=rank,weapon=weapon,tier=rating,n=len(results),win=sum(r['win'] for r in results)/len(results)))
races=[]
for race in ('Человек','Дварф','Лесной эльф','Высший эльф'):
    g=Adventure.create('Оценка','Мужской',race,'Оруженосец','Железный меч','Глыба','Знания')
    results=[fight(g,n,m['tier'],s) for n,m in BESTIARY.items() if m['tier'] in (1,2) and not m['guard'] for s in (101,137)]
    races.append(dict(race=race,stats=stats(g.hero),gold=g.hero.gold,branch_xp=g.branch_xp,
                      affordable=[n for n,p in GEAR_PRICES.items() if p<=g.hero.gold and n not in g.bag and n!='Амулет теневого договора'],
                      n=len(results),win=sum(r['win'] for r in results)/len(results),damage=sum(r['damage'] for r in results)/len(results)))
out=dict(readiness=rows,races=races)
Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/social-audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
for r in races:print(r,flush=True)
for cls in BUILDS:
    rr=[r for r in rows if r['cls']==cls];print(cls,round(sum(r['win'] for r in rr)/len(rr),3),flush=True)
