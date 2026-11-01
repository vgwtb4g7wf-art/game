"""Проверка каждого врага: шесть классов, три оружия и варианты экипировки."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.audit_balance import BUILDS,WEAPONS,duel
from bestiary import BESTIARY


def run(matched=False):
    rows=[]
    for name in BUILDS:
        for tier in range(1,6):
            outcomes=[];by_enemy={}
            for enemy,m in BESTIARY.items():
                if m['tier']!=tier:continue
                results=[]
                for w in WEAPONS:
                    for seed in (1,2,3):
                        armor=None if name=='Берсерк' else ('Кожаная куртка' if seed==2 else 'Кольчуга')
                        artifact={1:None,2:'Кольцо янтаря',3:'Медный амулет'}[seed]
                        if matched and tier<=2:
                            armor=None if tier==1 or name=='Берсерк' else 'Кожаная куртка'
                            artifact=None
                        result=duel(name,w,tier,seed,enemy=enemy,armor=armor,artifact=artifact,
                                    skill_mode='common' if seed==2 else 'all',
                                    level=tier if matched else 5,rank=(1,2,3,5,6)[tier-1] if matched else 6,
                                    consumables={'supply:heal':1,'supply:smoke':1} if seed==3 and (not matched or tier>1) else None)
                        results.append(result)
                outcomes.extend(results);by_enemy[enemy]=sum(o['win'] for o in results)/len(results)
            row=dict(build=name,tier=tier,n=len(outcomes),win=sum(o['win'] for o in outcomes)/len(outcomes),
                rounds=sum(o['rounds'] for o in outcomes)/len(outcomes),health=sum(o['health'] for o in outcomes)/len(outcomes),
                zero_damage=sum(o['damage_taken']==0 for o in outcomes)/len(outcomes),damage=sum(o['damage_taken'] for o in outcomes)/len(outcomes),
                timeouts=sum(o['timeout'] for o in outcomes),worst=sorted(by_enemy.items(),key=lambda p:p[1])[:5])
            rows.append(row);print(name,tier,row['n'],f"{row['win']:.1%}",f"{row['rounds']:.1f}",row['timeouts'],f"без урона {row['zero_damage']:.1%}, урон {row['damage']:.1f}",flush=True)
    return rows

if __name__=='__main__':
    Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/bestiary-balance.json').write_text(json.dumps(run(matched='--matched' in sys.argv),ensure_ascii=False,indent=2))
