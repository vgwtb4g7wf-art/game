"""Сравнение вещей и трёх наборов против всех типов монстров силы 5."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.audit_balance import BUILDS,duel
from trade import META
from eterion import ITEMS
from bestiary import BESTIARY


def run(sets=False):
    pool=list({m['kind']:n for n,m in BESTIARY.items() if m['tier']==5 and not m['guard']}.values())
    configs=[]
    if sets:
        configs=[('Верность','Меч верного слова',dict(armor='Кольчуга рубежа',artifact='Амулет ясной памяти')),
                 ('Подполье','Кинжал ночного дозора',dict(armor='Панцирь сборщика долгов',artifact='Печать подпольного лекаря')),
                 ('Лечение','Дуэльная шпага',dict(armor='Мантия лекаря',artifact='Печать подпольного лекаря'))]
    else:
        for name in META:
            slot=ITEMS[name][0];kwargs={};weapon='Железный меч'
            if slot=='Оружие':weapon=name
            elif slot=='Доспех':kwargs['armor']=name
            else:kwargs['artifact']=name
            configs.append((name,weapon,kwargs))
    rows=[]
    for label,weapon,kwargs in configs:
        for cls in BUILDS:
            results=[duel(cls,weapon,5,seed,enemy=enemy,**kwargs) for enemy in pool for seed in range(1,21)]
            row=dict(build=cls,n=len(results),win=sum(r['win'] for r in results)/len(results),
                     rounds=sum(r['rounds'] for r in results)/len(results),zero=sum(r['damage_taken']==0 for r in results)/len(results),
                     damage=sum(r['damage_taken'] for r in results)/len(results),timeouts=sum(r['timeout'] for r in results))
            row['set' if sets else 'item']=label
            if not sets:row['slot']=ITEMS[label][0]
            rows.append(row)
        rr=rows[-len(BUILDS):]
        print(label,f"побед {sum(r['win'] for r in rr)/len(rr):.1%}",f"без урона {sum(r['zero'] for r in rr)/len(rr):.1%}",flush=True)
    return rows

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('output',nargs='?',type=Path,default=Path('/tmp/equipment-balance.json'));parser.add_argument('--sets',action='store_true')
    args=parser.parse_args();args.output.write_text(json.dumps(run(args.sets),ensure_ascii=False,indent=2))
