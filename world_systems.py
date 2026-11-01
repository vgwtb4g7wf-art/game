"""Календарь, известность, репутация, события и развитие героя."""
from random import Random
from diplomacy import DiplomacyRules
from social_rules import SocialRules,fame_stage
from bestiary import GUARDS
from eterion import BRANCHES, COUNTRIES, REGIONS, ROUTES
from progression import COSTS, TREES, unlocked
from combat import SKILL_POWER,selectable,effects

MONTHS = ('Капель','Цветень','Солнцевей','Жарник','Листопад','Туманник','Иней','Снеговей')
DAYS = ('Искра','Камень','Ветер','Ручей','Звезда')
SEASONS = ('Весна','Лето','Осень','Зима')


def calendar(turn):
    day=turn-1
    month=day//10%8
    return dict(year=1+day//80,month=MONTHS[month],season=SEASONS[month//2],
                week=('Солнечная','Лунная')[day//5%2],day=DAYS[day%5],date=day%10+1)


class WorldSystems(SocialRules,DiplomacyRules):
    def init_world(self):
        self.paths=dict.fromkeys(BRANCHES,None)
        self.selected_skills=selectable(self.hero)[:3]
        self.level_points=0
        self.avatar="✦"
        self.level_notice=0
        self.skill_notices=[]
        self.attitudes=dict.fromkeys(COUNTRIES,0)
        self.seen_events=[]
        self.reputation=0
        self.fame=0
        self.last_fame_event=self.turn
        self.item_costs={}
        self.consumable_costs={}
        self.border_checks=0
        self.stat_points=0
        self.stat_hp=0
        self.stat_damage=0
        self.init_diplomacy()
        self.event=None
        self.event_serial=0
        self.last_event_turn=-10
        self.last_event_check=0
        self.preparation=None
        self.dead=False
        self.failed=[]
        self.applied_grants=[]
        self.sync_skills()
        self.apply_unlocks()

    def sync_skills(self):
        self.hero.level=1+self.xp//100
        self.hero.bonus_hp=self.stat_hp
        self.hero.bonus_damage=self.stat_damage
        self.hero.paths=self.paths
        self.hero.selected_skills=self.selected_skills

    def record(self,message):
        super().record(message)
        self.last_action_message=self.journal[-1]
        self.expire_quests()
        if self.turn-self.last_fame_event>30 and self.turn%10==0:self.fame=max(0,self.fame-1)
        self.tick_diplomacy()

    def pass_turn(self):
        self.ensure_free()
        self.record('Ожидание: ход потрачен, здоровье не восстанавливается.')

    def expire_quests(self):
        for q in list(self.active):
            if q.due_turn and self.turn>=q.due_turn:
                self.active.remove(q)
                if q.id not in self.failed:self.failed.append(q.id)
                if self.event and self.event.get('quest_id')==q.id:self.event=None
                if self.preparation and self.preparation.get('quest_id')==q.id:self.preparation=None
                self.journal.append(f'Срок задания «{q.title}» истёк. Награда не выдана, место в журнале освобождено.')
        self.offers=[q for q in self.offers if not q.due_turn or self.turn<q.due_turn]

    def gain_branch(self,branch,amount):
        before=set(unlocked(self.hero))
        self.branch_xp[branch]+=amount
        while self.hero.branches[branch]<6:
            level=self.hero.branches[branch]
            if level==3 and not self.paths[branch]:
                break
            cost=COSTS[level]
            if self.branch_xp[branch]<cost:
                break
            self.branch_xp[branch]-=cost
            self.hero.branches[branch]+=1
        if self.hero.branches[branch]==6:
            self.branch_xp[branch]=0
        self.sync_skills()
        self.apply_unlocks()
        self.skill_notices=list(dict.fromkeys(self.skill_notices+[s for s in unlocked(self.hero) if s not in before]))

    def choose_path(self,branch,path):
        self.ensure_free()
        if branch not in TREES or path not in ('left','right'):
            raise ValueError('Неизвестный путь.')
        if self.hero.branches[branch]!=3 or self.paths[branch] or self.branch_xp[branch]<COSTS[3]:
            raise ValueError('Сначала накопите 100 опыта для первой ступени специализации.')
        self.paths[branch]=path
        self.gain_branch(branch,0)

    def select_skill(self,name):
        self.ensure_free()
        if name not in selectable(self.hero):
            raise ValueError('Выбирать можно только открытые навыки-карты. Улучшения и пассивки работают автоматически.')
        if name in self.selected_skills:
            self.selected_skills.remove(name)
        elif len(self.selected_skills)>=3:
            raise ValueError('Можно использовать максимум три карточных навыка. Сначала снимите другой.')
        else:
            self.selected_skills.append(name)
        self.sync_skills()
        self.hp=min(self.hp,self.combat_stats()['hp'])

    def spend_level(self,branch):
        self.ensure_free()
        if branch not in BRANCHES or self.level_points<1:
            raise ValueError('Нет награды уровня или неизвестная ветвь.')
        if self.hero.branches[branch]>=6:
            raise ValueError('Эта ветвь уже полностью развита.')
        self.level_points-=1
        self.gain_branch(branch,20)
        self.journal.append(f'Награда уровня: +20 опыта ветви «{branch}».')

    def choose_growth(self,kind):
        self.ensure_free()
        if kind not in ('hp','damage') or self.stat_points<1:raise ValueError('Нет награды за нечётный уровень.')
        self.stat_points-=1
        if kind=='hp':self.stat_hp+=3
        else:self.stat_damage+=1
        self.sync_skills()
        if kind=='hp':self.hp=min(self.combat_stats()['hp'],self.hp+3)
        self.journal.append('Награда уровня: '+('+3 здоровья.' if kind=='hp' else '+1 базового урона.'))

    def repute(self,country=None,rep=0,fame=0):
        if rep>0 and fame>0:
            e=effects(self.hero)
            fame+=e.get('fame_bonus',0)
            rep+=e.get('reputation_bonus',0)
        if country in self.attitudes:self.attitudes[country]=max(-100,min(100,self.attitudes[country]+rep))
        self.reputation=max(-100,min(100,self.reputation+rep))
        self.fame=max(0,min(1000,self.fame+fame))
        self.last_fame_event=self.turn

    def quest_limit(self):return 2+effects(self.hero).get('quest_limit',0)

    def offer_limit(self):return 3+effects(self.hero).get('offer_limit',0)+(1 if fame_stage(self.fame)>=4 and self.attitudes[REGIONS[self.hero.region].country]>=10 else 0)

    def apply_unlocks(self):
        country=REGIONS[self.hero.region].country
        for name in unlocked(self.hero):
            grant=SKILL_POWER[name]['grant']
            if not grant or name in self.applied_grants:continue
            self.applied_grants.append(name)
            self.hero.gold+=grant.get('gold',0)
            if grant.get('fame'):self.repute(country,0,grant['fame'])
            if grant.get('reputation'):self.repute(None,grant['reputation'],0)

    def skills_notice(self):
        return bool(self.level_points or self.skill_notices or any(level==3 and not self.paths[b] and self.branch_xp[b]>=COSTS[3] for b,level in self.hero.branches.items()))

    def war_gate(self,target):
        source=REGIONS[self.hero.region].country
        country=REGIONS[target].country
        if source!=country and tuple(sorted((source,country))) in self.wars:
            return dict(country=country,fee=60,kind='war')
        return None

    def entry_fee(self):
        country=REGIONS[self.hero.region].country
        capital=REGIONS[self.hero.region].capital
        if self.attitudes[country]>=10 and fame_stage(self.fame)>=(2 if capital else 1):
            return 0
        return 10 if capital else 5

    def reputation_gate(self,target):
        current=REGIONS[self.hero.region].country
        country=REGIONS[target].country
        if current!=country and self.reputation<=-20:
            return dict(country=country,fee=10+abs(self.reputation)//2)
        return None

    def maybe_event(self,context):
        if context.startswith('Переход'):
            return self.travel_event('море' if 'море' in context else 'суша')
        if self.event or self.battle or self.turn==self.last_event_check:
            return
        self.last_event_check=self.turn
        if self.turn-self.last_event_turn<5:
            return
        rng=Random(f'event:{self.hero.name}:{self.turn}:{context}')
        if rng.random()>=.08:
            return
        self.event_serial+=1
        self.last_event_turn=self.turn
        variant=rng.choice(('traveler','purse','rumor'))
        self.event=dict(id=self.event_serial,kind=variant,country=REGIONS[self.hero.region].country,
                        context=context,region=self.hero.region)
        self.journal.append('Случайная встреча: '+{'traveler':'путник просит помощи.','purse':'на дороге найден кошель.','rumor':'сказитель собирает истории.'}[variant])

    def resolve_event(self,choice):
        if self.event and self.event['kind'] in ('travel','dialogue'):return self.resolve_narrative(choice)
        if not self.event or choice not in ('good','bad','ignore'):
            raise ValueError('Нет такого выбора события.')
        e=self.event
        if choice=='good' and e['kind']=='traveler':
            if self.hero.gold<2:raise ValueError('Для помощи нужно 2 золота.')
            self.hero.gold-=2
        if choice=='bad':
            self.hero.gold+=4
            self.repute(e['country'],-6,4)
            text='Вы воспользовались встречей ради выгоды. +4 золота, −6 репутации, +4 известности.'
        elif choice=='good':
            rep,fame=self.reputation,self.fame
            self.repute(e['country'],3,2)
            text=f'Добрый поступок: +{self.reputation-rep} репутации, +{self.fame-fame} известности.'
        else:
            text='Вы прошли мимо.'
        self.journal.append(text)
        self.event=None

    def validate_world(self):
        from adventure import AVATARS
        self.validate_diplomacy()
        if any(type(q.due_turn) is not int or q.due_turn<0 for q in self.active+self.offers):raise ValueError('Некорректный срок задания.')
        from social_rules import GEAR_PRICES
        from world_content import CONSUMABLES
        if (not isinstance(self.item_costs,dict) or any(n not in self.bag or type(v) is not int or v<1 or v>GEAR_PRICES[n] for n,v in self.item_costs.items())
            or not isinstance(self.consumable_costs,dict) or any(k not in self.consumables or not isinstance(v,list) or len(v)!=self.consumables[k] or any(type(c) is not int or c<1 or c>CONSUMABLES[k]['price'] for c in v) for k,v in self.consumable_costs.items())):raise ValueError('Некорректные цены приобретения.')
        from narrative_content import EVENTS
        if (set(self.attitudes)!=set(COUNTRIES) or any(type(v) is not int or not -100<=v<=100 for v in self.attitudes.values())
            or not isinstance(self.seen_events,list) or any(k not in EVENTS for k in self.seen_events)):raise ValueError('Некорректные отношения или дорожные истории.')
        if type(self.border_checks) is not int or self.border_checks<0:raise ValueError('Некорректные попытки прохода границы.')
        if (type(self.reputation) is not int or not -100<=self.reputation<=100 or type(self.fame) is not int or not 0<=self.fame<=1000
            or type(self.last_fame_event) is not int or not 1<=self.last_fame_event<=self.turn):raise ValueError('Некорректная общая репутация.')
        available=(self.xp//100)//2
        if (any(type(v) is not int or v<0 for v in (self.stat_points,self.stat_hp,self.stat_damage))
            or self.stat_hp%3 or self.stat_points+self.stat_hp//3+self.stat_damage!=available):raise ValueError('Некорректные награды нечётных уровней.')
        if type(self.dead) is not bool or self.dead!=(self.hp==0):raise ValueError('Некорректное состояние жизни героя.')
        if (not isinstance(self.failed,list) or not all(isinstance(x,str) for x in self.failed) or len(set(self.failed))!=len(self.failed)
            or any(x in self.completed or any(q.id==x for q in self.active+self.offers) for x in self.failed)):
            raise ValueError('Некорректные проваленные задания.')
        if not isinstance(self.applied_grants,list) or any(n not in unlocked(self.hero) for n in self.applied_grants):raise ValueError('Некорректные разовые награды.')
        if (self.avatar not in AVATARS or type(self.level_notice) is not int or not 0<=self.level_notice<=1+self.xp//100
            or not isinstance(self.skill_notices,list) or any(s not in unlocked(self.hero) for s in self.skill_notices)):
            raise ValueError('Некорректные уведомления или значок героя.')
        if self.event is not None:
            e=self.event
            if (not isinstance(e,dict) or e.get('kind') not in ('traveler','purse','rumor','travel','dialogue')
                or e.get('country') not in COUNTRIES or e.get('region')!=self.hero.region
                or not isinstance(e.get('context'),str) or type(e.get('id')) is not int):
                raise ValueError('Некорректное событие.')
        if self.event and self.event['kind']=='travel' and self.event.get('template') not in EVENTS:raise ValueError('Нет такого дорожного события.')
        if self.event and self.event['kind']=='dialogue' and not any(q.id==self.event.get('quest_id') and q.template for q in self.active):raise ValueError('Диалог без задания.')
        p=self.preparation
        if p is not None:
            if not isinstance(p,dict) or self.battle or self.event or p.get('kind') not in ('quest','border','event'):
                raise ValueError('Некорректная подготовка к бою.')
            if type(p.get('tier')) is not int or not 1<=p['tier']<=5 or not isinstance(p.get('enemy'),str):
                raise ValueError('Некорректный противник.')
            if p['kind']=='quest':
                q=next((q for q in self.active if q.id==p.get('quest_id')),None)
                if not q or q.target!=self.hero.region or q.monster!=p['enemy'] or q.monster_tier!=p['tier']:
                    raise ValueError('Подготовка не соответствует заданию.')
            elif p['kind']=='event':
                if p['enemy'] not in __import__('bestiary').BESTIARY:raise ValueError('Неизвестный противник события.')
            elif (p.get('target') not in REGIONS or self.travel_error(p['target']) or not self.reputation_gate(p['target'])
                  or p['enemy'] not in GUARDS[REGIONS[p['target']].country] or p['tier']!=3):
                raise ValueError('Некорректная пограничная подготовка.')
        for k in ('event_serial','last_event_turn','last_event_check'):
            if type(getattr(self,k)) is not int:raise ValueError('Некорректное время события.')
