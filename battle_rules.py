"""Исполнение дуэли. Состояние и генератор случайностей сохраняются вместе с игрой."""
import random
from balance_rewards import event_reward
from combat import CARDS, ITEM_POWER, SKILL_POWER, deck, stats, effects, card_damage, card_heal, critical_damage
from world_content import CONSUMABLES, tavern, enemy_profile
from eterion import REGIONS, Game
from bestiary import guard_for,intent,GUARDS
from social_rules import GEAR_PRICES,fame_stage,reputation_stage


from economy import EconomyRules

class BattleRules(EconomyRules):
    def ensure_free(self):
        if self.dead:raise ValueError('Герой погиб. Загрузите сохранение или создайте нового героя.')
        if self.battle is not None or self.preparation is not None:
            raise ValueError('Сначала завершите дуэль или отмените подготовку.')
        if self.event is not None:
            raise ValueError('Сначала решите случайное событие.')

    def combat_stats(self):
        self.hero.level=1+self.xp//100
        return stats(self.hero)

    def move(self, destination, approach=None):
        self.ensure_free()
        if destination not in dict(self.neighbors()):raise ValueError('Можно перейти только в соседний регион.')
        if REGIONS[destination].blocked:raise ValueError('Регион закрыт для путешественников.')
        war=self.war_gate(destination)
        gate=self.reputation_gate(destination)
        total=(war['fee'] if war else 0)+(gate['fee'] if gate else 0)
        if war and approach!='pay':
            raise ValueError(f'Военная граница: для прохода нужно заплатить {total} золота.')
        if gate and approach in ('fight','risk') and not war:
            self.border_checks+=1
            seed=f'{self.hero.name}:{self.turn}:{destination}:{self.border_checks}'
            if random.Random(seed).random()<.5:
                self.preparation=dict(kind='border',target=destination,quest_id=None,
                                      enemy=guard_for(gate['country'],seed),tier=3)
                self.journal.append('Попытка пройти без оплаты: стража остановила героя. Побег оставит вас у прежней границы.')
                return
            source=self.hero.region
            self.hero.region=destination;self.in_city=False
            self.record('Стража не остановила героя: граница пересечена без оплаты.')
            self.maybe_event('Переход:'+next((k for a,b,k in __import__('eterion').ROUTES if {a,b}=={destination,source}), 'суша'))
            return
        if gate and approach!='pay':raise ValueError('Из-за репутации стража требует плату или поединок.')
        if total and self.hero.gold<total:raise ValueError('Недостаточно золота для прохода границы.')
        if total:
            self.hero.gold-=total
            self.journal.append(f'Пограничная пошлина: {total} золота'+(' (в том числе военный пропуск 60).' if war else '.'))
        source=self.hero.region
        self.hero.region=destination;self.in_city=False
        self.record(f'Переход: {source} → {destination}. Вы за городскими воротами.')
        self.maybe_event('Переход:'+dict(__import__('eterion').Game.neighbors(self)).get(source,'суша'))

    def enter_city(self):
        self.ensure_free()
        if self.in_city:raise ValueError('Вы уже в городе.')
        fee=self.entry_fee()
        if self.hero.gold<fee:raise ValueError('Недостаточно золота для входа.')
        self.hero.gold-=fee
        self.in_city=True
        self.journal.append(f'Вход в город {self.hero.region}: уплачено {fee} золота. Без расхода дня.')
        self.maybe_event('Городские ворота')

    def leave_city(self):
        self.ensure_free()
        if not self.in_city:raise ValueError('Вы уже за городом.')
        self.in_city=False
        self.journal.append('Выход за городские ворота. Без расхода дня.')

    def set_relation(self, first, second, war):
        self.ensure_free()
        super().set_relation(first, second, war)

    def roll(self):
        b = self.battle
        rng = random.Random(f'{b["seed"]}:{b["roll"]}')
        b['roll'] += 1
        return rng

    def battle_log(self, text):
        self.battle['log'].append(text)
        self.battle['log'] = self.battle['log'][-50:]

    def draw_round(self):
        b = self.battle
        b['block'] = effects(self.hero).get('round_block',0)
        b['energy_max']=max(0,2+b['next_energy'])
        b['energy']=b['energy_max']
        b['next_energy']=0
        while len(b['hand']) < 4:
            if not b['draw']:
                if not b['discard']:
                    break
                b['draw'] = b['discard']
                b['discard'] = []
                self.roll().shuffle(b['draw'])
            b['hand'].append(b['draw'].pop())
        b['intent'],b['intent_value']=intent(b['profile'],b['round'])
        label={'attack':'удар','guard':'защиту','heal':'лечение'}[b['intent']]
        self.battle_log(f'Раунд {b["round"]}: противник готовит {label} {b["intent_value"]}.')

    def prepare_battle(self,quest):
        self.preparation=dict(kind='quest',quest_id=quest.id,target=None,enemy=quest.monster,tier=quest.monster_tier)

    def cancel_preparation(self):
        if self.battle:raise ValueError('Дуэль уже началась.')
        border=self.preparation and self.preparation['kind']=='border'
        self.preparation=None
        if border:self.record('Отказ от встречи со стражей: потрачен день, герой остался у границы.')

    def begin_battle(self,chosen):
        if not self.preparation or self.battle:raise ValueError('Нет подготовки к дуэли.')
        if not isinstance(chosen,dict) or any(k not in CONSUMABLES or type(v) is not int or v<1 or v>self.consumables.get(k,0) for k,v in chosen.items()) or sum(chosen.values())>4:
            raise ValueError('Выберите не больше четырёх имеющихся одноразовых карт.')
        if self.hp<=0:raise ValueError('Сначала отдохните.')
        p=self.preparation
        tier=p['tier']
        profile=enemy_profile(p['enemy'],tier)
        enemy_hp=profile['hp']
        self.battle=dict(quest_id=p['quest_id'],kind=p['kind'],target=p['target'],enemy=p['enemy'],tier=tier,
                        enemy_hp=enemy_hp,enemy_max=enemy_hp,enemy_armor=profile['armor'],enemy_armor_max=profile['armor'],enemy_block=0,
                        armor=self.combat_stats()['armor'],armor_max=self.combat_stats()['armor'],profile=profile,
                        next_energy=0,energy_max=2,exhausted=[],damage_taken=0,
                        round=1,energy=2,block=0,retained=None,draw=[k for k,_ in deck(self.hero,chosen)],
                        discard=[],hand=[],log=[],seed=f'{p["enemy"]}:{self.turn}',roll=0,
                        intent='attack',intent_value=0)
        self.preparation=None
        self.last_battle=None
        self.roll().shuffle(self.battle['draw'])
        self.draw_round()

    def start_battle(self,quest):
        self.prepare_battle(quest)

    def play_card(self, index):
        b = self.battle
        if b is None:
            raise ValueError('Сейчас нет дуэли.')
        if type(index) is not int or not 0 <= index < len(b['hand']):
            raise ValueError('Выберите карту из руки.')
        key = b['hand'][index]
        c = CARDS[key]
        if c.get('once') and key in b['exhausted']:
            raise ValueError('Артефакт уже использован в этой дуэли.')
        if c['cost'] > b['energy']:
            raise ValueError('Не хватает энергии. Завершите раунд.')
        if key in CONSUMABLES and self.consumables.get(key,0) < 1:
            raise ValueError('Расходуемая карта уже использована.')
        b['energy'] -= c['cost']
        held=b.get('retained')
        if held==index:b['retained']=None
        elif held is not None and held>index:b['retained']-=1
        b['hand'].pop(index)
        if key in CONSUMABLES:
            self.consume(key)
        elif c.get('once'):
            b['exhausted'].append(key)
        else:
            b['discard'].append(key)
        b['next_energy']+=c.get('bank',0)
        stats = self.combat_stats()
        self.battle_log(f'Карта «{c["name"]}» (энергия −{c["cost"]}).')
        if c['damage'] or c.get('ratio'):
            chance = max(5,min(100,stats['hit']+c['accuracy']))
            if self.roll().randint(1,100) <= chance:
                damage=card_damage(c,self.hero)
                critical=self.roll().randint(1,100)<=stats['crit_chance']
                if critical:damage=critical_damage(damage,self.hero)
                absorbed=min(b['enemy_block'],damage);b['enemy_block']-=absorbed;damage-=absorbed
                armored=min(b['enemy_armor'],damage);b['enemy_armor']-=armored;damage-=armored
                b['enemy_hp']=max(0,b['enemy_hp']-damage)
                self.battle_log(('Критический удар! ' if critical else 'Попадание: ')+f'{damage} урона здоровью; блок поглотил {absorbed}, броня {armored}.')
            else:
                self.battle_log(f'Промах! Шанс попадания был {chance}%.')
        b['block'] += c['block']
        b['armor']+=c.get('armor',0)
        b['armor_max']=max(b['armor_max'],b['armor'])
        self.hp = min(stats['hp'],self.hp+card_heal(c,self.hero))
        if b['enemy_hp'] == 0:
            self.finish_battle('victory')

    def retain_card(self,index):
        b=self.battle
        if b is None:raise ValueError('Сейчас нет дуэли.')
        if index is not None and (type(index) is not int or not 0<=index<len(b['hand'])):
            raise ValueError('Выберите одну карту из руки.')
        b['retained']=None if b.get('retained')==index else index

    def end_round(self):
        b = self.battle
        if b is None:
            raise ValueError('Сейчас нет дуэли.')
        stats = self.combat_stats()
        b['enemy_block'] = 0
        if b['intent']=='heal':
            healed=min(b['intent_value'],b['enemy_max']-b['enemy_hp'])
            b['enemy_hp']+=healed
            self.battle_log(f'{b["enemy"]} лечит {healed} здоровья вместо атаки.')
        elif b['intent'] == 'guard':
            b['enemy_block'] = b['intent_value']
            self.battle_log(f'{b["enemy"]} защищается: {b["enemy_block"]} блока.')
        else:
            damage=b['intent_value']
            absorbed=min(damage,b['block']);damage-=absorbed
            armored=min(damage,b['armor']);damage-=armored;b['armor']-=armored
            b['damage_taken']+=min(self.hp,damage)
            self.hp=max(0,self.hp-damage)
            self.battle_log(f'Удар врага: −{damage} здоровья; блок поглотил {absorbed}, запас брони {armored}.')
        if self.hp == 0:
            self.finish_battle('defeat')
            return
        held=b.get('retained')
        keep=b['hand'][held] if held is not None else None
        remaining=[key for i,key in enumerate(b['hand']) if i!=held]
        b['discard'].extend(key for key in remaining if key not in CONSUMABLES)
        b['draw'].extend(key for key in remaining if key in CONSUMABLES)
        b['hand']=[keep] if keep is not None else []
        b['retained']=None
        b['round'] += 1
        self.draw_round()

    def finish_battle(self, outcome):
        b = self.battle
        if b is None:
            raise ValueError('Сейчас нет дуэли.')
        quest=next((q for q in self.active if q.id==b['quest_id']),None)
        self.last_battle=dict(outcome=outcome,enemy=b['enemy'],rounds=b['round'],log=list(b['log']),damage_taken=b['damage_taken'])
        self.battle=None
        if outcome=='victory':
            if b.get('kind','quest')=='border':
                country=REGIONS[b['target']].country
                self.repute(country,-5,5)
                Game.move(self,b['target'])
                self.journal.append('Стража побеждена. Общая репутация −5, известность +5.')
                self.last_action_message=self.journal[-1]
            elif b.get('kind')=='event':
                reward=event_reward(b['tier'])
                previous=self.xp//100;self.xp+=reward['xp']
                self.level_points+=self.xp//100-previous;self.stat_points+=(self.xp//100)//2-previous//2
                if self.xp//100>previous:self.level_notice=1+self.xp//100
                self.hero.gold+=reward['gold'];self.gain_branch('Мощь',reward['progress']);self.record(f"Стычка завершена: +{reward['xp']} XP, +{reward['gold']} монет, +{reward['progress']} опыта мощи.")
            else:
                self.reward(quest,f'Победа в карточной дуэли над {b["enemy"]}. ')
        else:
            country=REGIONS[quest.target if quest else b.get('target') or self.hero.region].country
            lost=min(self.fame,b['profile']['fame_loss'])
            self.repute(country,0,-lost)
            if quest:
                self.active.remove(quest);self.failed.append(quest.id)
            if outcome=='flee':
                damage=b['profile']['escape']
                self.last_battle['damage_taken']+=min(self.hp,damage)
                self.hp=max(0,self.hp-damage)
                message=f'Побег: удар вслед −{damage} здоровья (обходит броню и блок).'
            else:
                self.hp=0;message='Поражение в дуэли.'
            self.dead=self.hp==0
            self.record(message+f' Известность −{lost}.'+(' Задание провалено.' if quest else '')+(' Герой погиб.' if self.dead else ''))
            self.last_battle['dead']=self.dead
        if outcome=='victory' and b.get('kind')!='border':
            loot=self.roll_loot(b['tier'],b['seed'])
            self.last_battle['loot']=loot
        self.last_battle['message'] = getattr(self,'last_action_message',self.journal[-1])

    def flee(self):
        self.finish_battle('flee')

    def validate_battle(self):
        b = self.battle
        if b is None:
            return
        try:
            if b.get('kind','quest')=='border':
                target=b['target']
                if (target not in REGIONS or self.travel_error(target) or self.reputation_gate(target) is None
                    or b['enemy'] not in GUARDS[REGIONS[target].country] or b['tier']!=3):
                    raise ValueError('Некорректный пограничный бой.')
            elif b.get('kind')=='event':
                if b['enemy'] not in __import__('bestiary').BESTIARY:raise ValueError('Неизвестный противник.')
            else:
                q=next(q for q in self.active if q.id==b['quest_id'])
                if not q.monster or q.monster!=b['enemy'] or q.target!=self.hero.region or q.monster_tier!=b['tier']:
                    raise ValueError('Дуэль не соответствует заданию.')
            for key in ('damage_taken','tier','enemy_hp','enemy_max','enemy_armor','enemy_block','round','energy','block','roll','intent_value','armor','armor_max','enemy_armor_max','energy_max'):
                if type(b[key]) is not int or b[key]<0:
                    raise ValueError('Повреждено состояние дуэли.')
            if (not 1<=b['tier']<=5 or not 0<b['enemy_hp']<=b['enemy_max'] or b['round']<1
                or b['energy']>b['energy_max'] or not 0<=b['energy_max']<=3
                or type(b['next_energy']) is not int or not -3<=b['next_energy']<=1
                or b['armor']>b['armor_max'] or b['enemy_armor']>b['enemy_armor_max']):
                raise ValueError('Некорректные параметры дуэли.')
            if b['intent'] not in ('attack','guard','heal') or not isinstance(b['seed'],str):
                raise ValueError('Некорректное намерение.')
            for key in ('hand','draw','discard','exhausted'):
                if not isinstance(b[key],list) or any(c not in CARDS for c in b[key]) or len(b[key])>100:
                    raise ValueError('Некорректная колода.')
            if self.dead:raise ValueError('Погибший герой не может находиться в бою.')
            if b.get('profile')!=enemy_profile(b['enemy'],b['tier']):raise ValueError('Некорректные параметры противника.')
            if len(set(b['exhausted']))!=len(b['exhausted']) or any(k in b['hand']+b['draw']+b['discard'] for k in b['exhausted']):raise ValueError('Артефакт повторно попал в колоду.')
            if any(not CARDS[k].get('once') for k in b['exhausted']):raise ValueError('Некорректные исчерпанные артефакты.')
            held=b.get('retained')
            if held is not None and (type(held) is not int or not 0<=held<len(b['hand'])):
                raise ValueError('Некорректная сохраняемая карта.')
            if len(b['hand'])>4 or not isinstance(b['log'],list) or not all(isinstance(x,str) for x in b['log']):
                raise ValueError('Некорректная рука.')
        except (KeyError,TypeError,StopIteration) as exc:
            raise ValueError('Повреждённое состояние дуэли.') from exc
