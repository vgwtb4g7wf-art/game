"""Календарь, известность, репутация, события и развитие героя."""
from random import Random
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
                week=('Солнечная','Ночная')[day//5%2],day=DAYS[day%5],date=day%10+1)


class WorldSystems:
    def init_world(self):
        self.paths=dict.fromkeys(BRANCHES,None)
        self.selected_skills=selectable(self.hero)[:3]
        self.level_points=0
        self.avatar="✦"
        self.level_notice=0
        self.skill_notices=[]
        self.reputation=dict.fromkeys(COUNTRIES,0)
        self.fame=dict.fromkeys(COUNTRIES,0)
        self.last_fame_event=dict.fromkeys(COUNTRIES,self.turn)
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
        self.hero.paths=self.paths
        self.hero.selected_skills=self.selected_skills

    def record(self,message):
        super().record(message)
        for country in COUNTRIES:
            if self.turn-self.last_fame_event[country]>30 and self.turn%10==0:
                self.fame[country]=max(0,self.fame[country]-1)

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
        if self.hero.branches[branch]<3 or self.paths[branch]:
            raise ValueError('Путь выбирается один раз после третьей ступени.')
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

    def repute(self,country,rep=0,fame=0):
        if rep>0 and fame>0:fame+=effects(self.hero).get('fame_bonus',0)
        self.reputation[country]=max(-100,min(100,self.reputation[country]+rep))
        self.fame[country]=max(0,min(1000,self.fame[country]+fame))
        self.last_fame_event[country]=self.turn
        if self.fame[country]>=20 and fame>0:
            neighbors=set()
            for a,b,_ in ROUTES:
                ca,cb=REGIONS[a].country,REGIONS[b].country
                if ca==country and cb!=country:neighbors.add(cb)
                if cb==country and ca!=country:neighbors.add(ca)
            for neighbor in neighbors:
                self.fame[neighbor]=min(1000,self.fame[neighbor]+max(1,fame//3))
                self.last_fame_event[neighbor]=self.turn

    def quest_limit(self):return 2+effects(self.hero).get('quest_limit',0)

    def offer_limit(self):return 3+effects(self.hero).get('offer_limit',0)

    def apply_unlocks(self):
        country=REGIONS[self.hero.region].country
        for name in unlocked(self.hero):
            grant=SKILL_POWER[name]['grant']
            if not grant or name in self.applied_grants:continue
            self.applied_grants.append(name)
            self.hero.gold+=grant.get('gold',0)
            if grant.get('fame'):self.repute(country,0,grant['fame'])
            if grant.get('reputation_all'):
                for c in COUNTRIES:self.repute(c,grant['reputation_all'],0)

    def skills_notice(self):
        return bool(self.level_points or self.skill_notices or any(level==3 and not self.paths[b] for b,level in self.hero.branches.items()))

    def war_gate(self,target):
        source=REGIONS[self.hero.region].country
        country=REGIONS[target].country
        if source!=country and tuple(sorted((source,country))) in self.wars:
            return dict(country=country,fee=60,kind='war')
        return None

    def entry_fee(self):
        country=REGIONS[self.hero.region].country
        capital=REGIONS[self.hero.region].capital
        if self.reputation[country]>=20 and self.fame[country]>=(50 if capital else 20):
            return 0
        return 10 if capital else 5

    def reputation_gate(self,target):
        current=REGIONS[self.hero.region].country
        country=REGIONS[target].country
        if current!=country and self.reputation[country]<=-20:
            return dict(country=country,fee=10+abs(self.reputation[country])//2)
        return None

    def maybe_event(self,context):
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
            self.repute(e['country'],3,2)
            text='Добрый поступок: +3 репутации, +2 известности.'
        else:
            text='Вы прошли мимо.'
        self.journal.append(text)
        self.event=None

    def validate_world(self):
        from adventure import AVATARS
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
            if (not isinstance(e,dict) or e.get('kind') not in ('traveler','purse','rumor')
                or e.get('country') not in COUNTRIES or e.get('region')!=self.hero.region
                or not isinstance(e.get('context'),str) or type(e.get('id')) is not int):
                raise ValueError('Некорректное событие.')
        p=self.preparation
        if p is not None:
            if not isinstance(p,dict) or self.battle or self.event or p.get('kind') not in ('quest','border'):
                raise ValueError('Некорректная подготовка к бою.')
            if type(p.get('tier')) is not int or not 1<=p['tier']<=5 or not isinstance(p.get('enemy'),str):
                raise ValueError('Некорректный противник.')
            if p['kind']=='quest':
                q=next((q for q in self.active if q.id==p.get('quest_id')),None)
                if not q or q.target!=self.hero.region or q.monster!=p['enemy']:
                    raise ValueError('Подготовка не соответствует заданию.')
            elif p.get('target') not in REGIONS or self.travel_error(p['target']) or not self.reputation_gate(p['target']):
                raise ValueError('Некорректная пограничная подготовка.')
        for k in ('event_serial','last_event_turn','last_event_check'):
            if type(getattr(self,k)) is not int:raise ValueError('Некорректное время события.')
