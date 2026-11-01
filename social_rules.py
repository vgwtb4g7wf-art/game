"""Ступени славы, магазины, дорожные сцены и мирные диалоги."""
from random import Random
from balance_rewards import peace_reward
from eterion import COUNTRIES,REGIONS
from combat import CARDS,card_damage,card_heal,deck,effects
from bestiary import LOCAL_POOLS
from narrative_content import EVENTS,PEACE_QUESTS

GEAR_PRICES={'Железный меч':40,'Короткий кинжал':35,'Дорожный лук':45,'Кожаная куртка':25,'Кольчуга':50,'Кольцо янтаря':30,'Медный амулет':35}
FAME_STAGES=((0,'Неизвестный'),(20,'На слуху'),(50,'Известное имя'),(120,'Знаменитость'),(250,'Легенда Этериона'))
REP_NAMES={-3:'Презираемый',-2:'Злодей',-1:'Дурная слава',0:'Нейтральный',1:'Доброе имя',2:'Уважаемый',3:'Образец чести'}

def fame_stage(value):return max(i for i,(limit,_) in enumerate(FAME_STAGES) if value>=limit)
def reputation_stage(value):
    n=sum(abs(value)>=v for v in (10,35,70));return n if value>=0 else -n

class SocialRules:
    def social_status(self):
        f=fame_stage(self.fame);r=reputation_stage(self.reputation)
        return dict(fame_level=f,fame_name=FAME_STAGES[f][1],reputation_level=r,reputation_name=REP_NAMES[r],
                    next_fame=FAME_STAGES[f+1][0] if f<4 else None)

    def combat_rating(self):
        # Одинаковые независимые пробы до изменения экипировки/навыков/здоровья.
        import copy
        from combat_ai import choose
        from bestiary import BESTIARY
        s=self.combat_stats()
        if self.hp<=0:return dict(tier=0,probes=[],method='Герой погиб')
        key=repr((s,self.hp,self.hero.equipment,self.hero.branches,self.paths,self.selected_skills))
        if getattr(self,'_combat_cache',None) and self._combat_cache[0]==key:return self._combat_cache[1]
        safe=1;trials=[]
        for tier in range(1,6):
            pool=[n for n,m in BESTIARY.items() if m['tier']==tier and not m['guard']]
            wins=0;health=0
            for seed in (17,29,43,59,71,89,101,127,149):
                clone=copy.deepcopy(self);clone.battle=None;clone.event=None;clone.preparation=None;clone.dead=False
                clone.auto_diplomacy=False;clone.active=[];clone.hp=self.hp
                enemy=Random(f'power:{tier}:{seed}').choice(pool)
                clone.turn=seed;clone.preparation=dict(kind='event',quest_id=None,target=None,enemy=enemy,tier=tier)
                clone.begin_battle({})
                for _ in range(100):
                    if not clone.battle:break
                    index=choose(clone)
                    if index is not None:clone.play_card(index)
                    else:clone.end_round()
                won=not clone.battle and clone.last_battle['outcome']=='victory'
                wins+=won
                health+=clone.hp/max(1,s['hp']) if won else 0
            trials.append(dict(tier=tier,wins=wins,runs=9))
            if wins>=8 and health/9>=.25:safe=tier
            else:break
        result=dict(tier=safe,probes=trials,method='Девять проб на сложность; нужно 8 побед и запас здоровья; без расходников')
        self._combat_cache=(key,result)
        return result

    def social_event(self,kind,**data):
        self.event_serial+=1
        self.event=dict(id=self.event_serial,kind=kind,country=REGIONS[self.hero.region].country,
                        region=self.hero.region,context='Дорожная история' if kind=='travel' else 'Мирное поручение',**data)

    def travel_event(self,mode):
        if self.event or self.battle or self.turn==self.last_event_check:return
        self.last_event_check=self.turn
        if self.turn-self.last_event_turn<5:return
        rng=Random(f'journey:{self.hero.name}:{self.turn}:{mode}')
        if rng.random()>=.12:return
        pool=[k for k,v in EVENTS.items() if v['mode']==mode and k not in self.seen_events]
        if not pool:pool=[k for k,v in EVENTS.items() if v['mode']==mode]
        key=rng.choice(pool);self.seen_events.append(key);self.seen_events=list(dict.fromkeys(self.seen_events))
        self.last_event_turn=self.turn;self.social_event('travel',template=key)

    def add_followup(self):
        if len(self.active)>=self.quest_limit():raise ValueError('Нет свободного места для поручения. Можно отказаться от него.')
        rng=Random(f'followup:{self.event_serial}:{self.turn}')
        template=rng.choice(list(PEACE_QUESTS));targets=[r for r in self.reachable() if r!=self.hero.region]
        q=self.make_peace_quest(template,rng.choice(targets) if targets else self.hero.region,f'event-{self.event_serial}')
        q.due_turn=self.turn+8+min(2,q.distance//2)
        self.active.append(q);self.journal.append(f'Взято дорожное поручение «{q.title}».')

    def make_peace_quest(self,key,target,quest_id):
        from adventure import Quest
        t=PEACE_QUESTS[key];distance=self.distances().get(target,0)
        difficulty=1 if t['delivery'] else 2
        reward=peace_reward(t['delivery'],distance)
        return Quest(quest_id,t['title'],t['brief']+' Место: '+target+'.',difficulty,t['branch'],self.hero.region,target,
                     self.in_city,None,reward['xp'],reward['gold'],reward['progress'],None,
                     distance,0,self.in_city,'Передать получателю' if t['delivery'] else 'Поговорить',0,key,0)

    def open_dialogue(self,q):
        if q not in self.active:return
        self.social_event('dialogue',quest_id=q.id)

    def narrative_view(self):
        e=self.event
        if not e or e['kind'] not in ('travel','dialogue'):return None
        if e['kind']=='travel':
            t=EVENTS[e['template']]
            impact={'help':'+2 репутации, +1 известности','pay':'● −3, +3 репутации, +1 известности',
                'return':'+3 репутации, +1 известности','mediate':'+2 репутации, +2 опыта дипломатии',
                'investigate':'+1 репутации, +2 опыта хитрости','study':'+2 опыта знаний','fame':'+3 известности',
                'quest':'Займёт одно место в журнале','fight':f"Дуэль силы {self.combat_rating()['tier']}; можно избежать"}[t['effect']]
            return dict(title=t['title'],text=t['text'],options=[dict(id='good',label=t['label'],detail=impact),
                dict(id='bad',label={'help':'Взять плату, но не помочь','pay':'Обманом выманить пожертвование себе','return':'Присвоить и продать находку','mediate':'Взять плату за заведомо пристрастное решение','investigate':'Продать ложное свидетельство','study':'Продать заведомо неверную подсказку','fame':'Продать чужую историю как собственный подвиг','quest':'Взять аванс и отказаться от обещания','fight':'Выманить плату за бой и уйти'}[t['effect']],detail='● +4, репутация −5, известность +1'),
                dict(id='ignore',label='Пройти дальше',detail='Без последствий')])
        q=next(q for q in self.active if q.id==e['quest_id']);t=PEACE_QUESTS[q.template]
        if t['delivery']:
            return dict(title=q.title,text=t['brief']+' Получатель готов принять посылку.',options=[dict(id='good',label='Передать лично и получить расписку',detail='Завершить поручение'),dict(id='ignore',label='Вернуться позже',detail='Поручение останется активным')])
        if q.stage==0:
            return dict(title=q.title,text=t['brief']+' Собеседник предлагает сначала изложить обстоятельства.',options=[dict(id='listen',label='Выслушать объяснение и проверить детали',detail='День работы; появится предметный вопрос'),dict(id='ignore',label='Завершить разговор без решения',detail='День потрачен, задание остаётся активным')])
        options=[dict(id='good',label=t['good'],detail='● −3; затем награда' if t['fee'] else 'Ответить собеседнику'),
                 dict(id='bad',label=t['bad'],detail='Может обострить конфликт' if t['combat'] else 'Настоять на этой версии'),
                 dict(id='ignore',label='Предложить отложить решение',detail='Задание останется активным')]
        Random('dialogue:'+q.template).shuffle(options)
        return dict(title=q.title,text=t['question']+' '+('Проверенный выкуп составляет ● 3.' if t['fee'] else ''),options=options)

    def resolve_narrative(self,choice):
        e=self.event;country=e['country']
        view=self.narrative_view()
        if choice not in [o['id'] for o in view['options']]:raise ValueError('Нет такого ответа.')
        if e['kind']=='travel':
            t=EVENTS[e['template']];kind=t['effect']
            if choice=='good' and kind=='pay' and self.hero.gold<3:raise ValueError('Нужно 3 монеты. Можно пройти дальше.')
            if choice=='good' and kind=='quest':self.add_followup()
            self.event=None
            if choice=='bad':self.hero.gold+=4;self.repute(country,-5,1)
            elif choice=='good':
                if kind=='pay':self.hero.gold-=3
                if kind in ('help','pay','return','mediate','investigate'):self.repute(country,3 if kind in ('pay','return') else 2,1)
                if kind in ('study','investigate','mediate'):self.gain_branch({'study':'Знания','investigate':'Хитрость','mediate':'Дипломатия'}[kind],2)
                if kind=='fame':self.repute(country,0,3)
                if kind=='fight':
                    tier=self.combat_rating()['tier'];enemy=Random(f'{self.turn}:{e["id"]}').choice(LOCAL_POOLS[country][tier])
                    self.preparation=dict(kind='event',quest_id=None,target=None,enemy=enemy,tier=tier)
            self.journal.append(t['title']+': '+next(o['label'] for o in view['options'] if o['id']==choice)+'.')
            return
        q=next(q for q in self.active if q.id==e['quest_id']);t=PEACE_QUESTS[q.template]
        if choice=='good' and t['fee'] and self.hero.gold<t['fee']:raise ValueError('Для выкупа нужно 3 монеты.')
        self.event=None
        if choice=='listen':
            q.stage=1;self.record('Разговор: '+q.title+'. Обстоятельства выяснены.');self.open_dialogue(q)
        elif choice=='good':
            self.hero.gold-=t['fee'];self.reward(q,'Поручение решено: ')
        elif choice=='bad':
            self.repute(country,-2,0)
            if t['combat']:
                tier=self.combat_rating()['tier'];q.monster=LOCAL_POOLS[country][tier][0];q.monster_tier=tier;q.difficulty=tier
                q.method='Начать дуэль';self.prepare_battle(q)
            else:self.record('Разговор зашёл в тупик: '+q.title+'. Можно вернуться позже.')
        else:self.record('Разговор завершён без результата: '+q.title+'.')
