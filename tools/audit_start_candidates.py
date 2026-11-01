"""Сравнение исходного старта и старта без готового навыка."""
import sys,json,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from adventure import Adventure
from eterion import RACES,BACKGROUNDS
from combat_ai import choose
from bestiary import BESTIARY

rows=[]
for model in ('existing','xp25'):
 for race in RACES:
  for bg in BACKGROUNDS:
   rr=[]
   for weapon in ('Железный меч','Короткий кинжал','Дорожный лук'):
    for enemy,m in BESTIARY.items():
     if m['tier']!=1:continue
     g=Adventure.create('Старт','Мужской',race,bg,weapon,'Глыба',BACKGROUNDS[bg][0]);g.auto_diplomacy=False
     branch=BACKGROUNDS[bg][0]
     g.hero.branches=dict.fromkeys(g.hero.branches,0)
     g.branch_xp=dict.fromkeys(g.branch_xp,0)
     if model=='existing':g.hero.branches[branch]=1
     else:g.branch_xp[branch]=25
     if race=='Человек':g.branch_xp[branch]+=40
     g.applied_grants=[];g.fame=0;g.gain_branch(branch,0)
     g.hp=g.combat_stats()['hp'];g.preparation=dict(kind='event',target=None,quest_id=None,enemy=enemy,tier=1);g.begin_battle({})
     for _ in range(150):
      if not g.battle:break
      i=choose(g)
      if i is not None:g.play_card(i)
      else:g.end_round()
     rr.append((not g.battle and g.last_battle['outcome']=='victory',g.last_battle['damage_taken'] if not g.battle else g.battle['damage_taken']))
   rows.append(dict(model=model,race=race,background=bg,n=len(rr),win=sum(x[0] for x in rr)/len(rr),damage=sum(x[1] for x in rr)/len(rr)))
 Path('/tmp/start-candidates.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
 print(model,'готово',flush=True)
