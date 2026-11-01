"""Сравнение специализаций на одинаковом бюджете. Реальные бои, бот без знания бросков.

python tools/audit_balance.py --runs 40 --output /tmp/balance.json
"""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from adventure import Adventure
from combat import CARDS,card_damage,card_heal,selectable
from progression import COSTS,PATH_NAMES
from world_content import BIOMES

WEAPONS=('Железный меч','Короткий кинжал','Дорожный лук')
BUILDS={PATH_NAMES[b][i]:(b,side) for b in ('Мощь','Хитрость','Знания') for i,side in enumerate(('left','right'))}


def build(name,weapon,seed,rank=6,gold=200,extra=None,level=5):
    g=Adventure.create('Аудит','Мужской','Человек','Торговец',weapon,'Глыба','Дипломатия')
    g.auto_diplomacy=False;g.maybe_event=lambda _:None;g.turn=seed
    g.xp=(level-1)*100;g.stat_points=(level-1)//2
    for _ in range(g.stat_points):g.choose_growth('damage')
    if name in BUILDS:
        branch,side=BUILDS[name]
        g.gain_branch(branch,sum(COSTS[:min(rank,3)]))
        if rank>3:g.gain_branch(branch,sum(COSTS[3:rank]));g.choose_path(branch,side)
    if extra:
        allocations=extra if isinstance(extra,list) else [extra]
        for b,side,r in allocations:
            g.gain_branch(b,sum(COSTS[:r]))
            if r>3:g.choose_path(b,side)
    g.selected_skills=selectable(g.hero)[:3];g.sync_skills()
    if name!='Берсерк' and (name in BUILDS or extra):
        g.bag.append('Кольчуга');g.equip('Кольчуга')
    g.hero.gold=gold;g.hp=g.combat_stats()['hp']
    return g


from combat_ai import choose


def duel(name,weapon,tier,seed,rank=6,gold=200,biome='Княжество Бреннор',extra=None,weights=(1.,.85),armor='default',skill_mode='all',enemy=None,artifact=None,consumables=None,level=5):
    g=build(name,weapon,seed,rank,gold,extra,level)
    if armor!='default':
        g.hero.equipment['Доспех']=None
        if armor:
            if armor not in g.bag:g.bag.append(armor)
            g.equip(armor)
    if skill_mode!='all':
        available=selectable(g.hero)
        g.selected_skills=[] if skill_mode=='none' else available[:1] if skill_mode=='common' else available[-1:]
        g.sync_skills()
    if artifact:
        g.bag.append(artifact);g.equip(artifact)
    if consumables:g.consumables=dict(consumables)
    initial=g.hp
    assess=g.combat_rating;g.combat_rating=lambda:dict(tier=5)
    g.search();g.combat_rating=assess;q=g.offers[0]
    q.monster=enemy or BIOMES[biome][1][tier-1];q.monster_tier=tier
    g.accept(q.id);g.complete(q.id);g.begin_battle(consumables or {})
    for _ in range(250):
        if not g.battle:break
        if g.battle['round']>40:return dict(win=False,rounds=40,health=0,timeout=True,damage_taken=g.battle['damage_taken'])
        index=choose(g,weights)
        if index is not None:g.play_card(index)
        else:
            # Сохраняется наиболее эффективная карта, без знания следующей руки.
            b=g.battle
            if b['hand']:
                incoming=b['profile']['attack']
                def value(i):
                    c=CARDS[b['hand'][i]]
                    return (card_damage(c,g.hero)+min(incoming,c['block'])+min(incoming,card_heal(c,g.hero))*.8+c.get('armor',0))/max(1,c['cost']+max(0,-c['bank']))
                g.retain_card(max(range(len(b['hand'])),key=value))
            g.end_round()
    else:raise AssertionError('Слишком много действий')
    return dict(win=g.last_battle['outcome']=='victory',rounds=g.last_battle['rounds'],health=g.hp/initial,timeout=False,damage_taken=g.last_battle['damage_taken'])


def run(runs=40):
    rows=[]
    for name in BUILDS:
        for tier in (3,4,5):
            outcomes=[duel(name,w,tier,seed,biome=biome) for w in WEAPONS
                      for biome in ('Княжество Бреннор','Дваллинхорг') for seed in range(1,runs+1)]
            rows.append(dict(build=name,tier=tier,n=len(outcomes),win=sum(o['win'] for o in outcomes)/len(outcomes),
                rounds=sum(o['rounds'] for o in outcomes)/len(outcomes),health=sum(o['health'] for o in outcomes)/len(outcomes),timeouts=sum(o['timeout'] for o in outcomes)))
    return rows


def run_stress(runs=30):
    configs=[('Три общие ветки','Смешанная',dict(extra=[(b,None,3) for b in ('Мощь','Хитрость','Знания')]))]
    configs += [(f'Плут, золото {gold}','Плут',dict(gold=gold)) for gold in (0,100,300,10000)]
    configs += [(f'{name}, ранг {rank}',name,dict(rank=rank)) for name in ('Защитник','Ассасин','Маг огня') for rank in (3,4,5)]
    configs += [(f'Берсерк, {armor or "без брони"}','Берсерк',dict(armor=armor)) for armor in (None,'Кожаная куртка','Кольчуга')]
    configs += [(f'{name}, стиль бота {weight}',name,dict(weights=(weight,.85))) for name in BUILDS for weight in (.65,1.35)]
    rows=[]
    for label,name,kwargs in configs:
        outcomes=[duel(name,w,5,seed,**kwargs) for w in WEAPONS for seed in range(1,runs+1)]
        rows.append(dict(build=label,tier=5,n=len(outcomes),win=sum(o['win'] for o in outcomes)/len(outcomes),
            rounds=sum(o['rounds'] for o in outcomes)/len(outcomes),health=sum(o['health'] for o in outcomes)/len(outcomes),timeouts=sum(o['timeout'] for o in outcomes)))
    return rows


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--runs',type=int,default=40);parser.add_argument('--output',type=Path)
    parser.add_argument('--stress',action='store_true',help='Смешанные ветви, золото, промежуточные ранги и разные приоритеты бота')
    args=parser.parse_args();rows=run_stress(args.runs) if args.stress else run(args.runs)
    if args.output:args.output.write_text(json.dumps(rows,ensure_ascii=False,indent=2))
    for r in rows:print(f'{r["build"]:18} враг {r["tier"]}: побед {r["win"]:.0%}, раундов {r["rounds"]:.1f}, здоровья {r["health"]:.0%}, зависаний {r["timeouts"]}',flush=True)
