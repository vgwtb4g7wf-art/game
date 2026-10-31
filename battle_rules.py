"""Исполнение дуэли. Состояние и генератор случайностей сохраняются вместе с игрой."""
import random
from combat import CARDS, ITEM_POWER, SKILL_POWER, deck, stats
from world_content import CONSUMABLES, tavern


class BattleRules:
    def ensure_free(self):
        if self.battle is not None:
            raise ValueError('Сначала завершите дуэль или отступите.')

    def combat_stats(self):
        return stats(self.hero)

    def move(self, destination):
        self.ensure_free()
        super().move(destination)

    def enter_city(self):
        self.ensure_free()
        super().enter_city()

    def leave_city(self):
        self.ensure_free()
        super().leave_city()

    def wait(self):
        self.ensure_free()
        self.hp = min(self.combat_stats()['hp'], self.hp + 12)
        self.record('Отдых: восстановлено до 12 здоровья.')

    def set_relation(self, first, second, war):
        self.ensure_free()
        super().set_relation(first, second, war)

    def shop(self):
        shop = tavern(self.hero.region, self.in_city)
        shop['offers'] = [dict(card=key, price=CONSUMABLES[key]['price'],
                               left=max(0, 3-self.purchases.get(shop['id']+'|'+key, 0)))
                          for key in shop.pop('keys')]
        return shop

    def buy(self, key):
        self.ensure_free()
        shop = self.shop()
        offer = next((o for o in shop['offers'] if o['card'] == key), None)
        if offer is None or offer['left'] <= 0:
            raise ValueError('Карта отсутствует в ассортименте этой таверны.')
        if self.hero.gold < offer['price']:
            raise ValueError('Недостаточно золота.')
        if sum(self.consumables.values()) >= 15:
            raise ValueError('Можно нести не более 15 расходуемых карт.')
        self.hero.gold -= offer['price']
        self.consumables[key] = self.consumables.get(key, 0)+1
        purchase = shop['id']+'|'+key
        self.purchases[purchase] = self.purchases.get(purchase, 0)+1
        self.journal.append(f'Куплена карта «{CARDS[key]["name"]}» за {offer["price"]} золота.')

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
        b['block'] = 0
        b['energy'] = 3
        while len(b['hand']) < 5:
            if not b['draw']:
                if not b['discard']:
                    break
                b['draw'] = b['discard']
                b['discard'] = []
                self.roll().shuffle(b['draw'])
            b['hand'].append(b['draw'].pop())
        b['intent'] = 'guard' if b['round'] % 3 == 0 else 'attack'
        b['intent_value'] = (5 + b['tier']*2) if b['intent']=='guard' else (3+b['tier']*2)
        self.battle_log(f'Раунд {b["round"]}: противник готовит '+
                        (f'защиту {b["intent_value"]}.' if b['intent']=='guard' else f'удар {b["intent_value"]}.'))

    def start_battle(self, quest):
        if self.hp <= 0:
            raise ValueError('Сначала отдохните.')
        tier = quest.monster_tier
        enemy_hp = 12 + tier*8
        self.battle = dict(quest_id=quest.id, enemy=quest.monster, tier=tier,
                          enemy_hp=enemy_hp, enemy_max=enemy_hp, enemy_armor=max(0,tier-2),
                          enemy_block=0, round=1, energy=3, block=0,
                          draw=[key for key, _ in deck(self.hero, self.consumables)],
                          discard=[], hand=[], log=[], seed=f'{quest.id}:{self.turn}', roll=0,
                          intent='attack', intent_value=0)
        self.last_battle = None
        self.roll().shuffle(self.battle['draw'])
        self.draw_round()

    def play_card(self, index):
        b = self.battle
        if b is None:
            raise ValueError('Сейчас нет дуэли.')
        if type(index) is not int or not 0 <= index < len(b['hand']):
            raise ValueError('Выберите карту из руки.')
        key = b['hand'][index]
        c = CARDS[key]
        if c['cost'] > b['energy']:
            raise ValueError('Не хватает энергии. Завершите раунд.')
        if key in CONSUMABLES and self.consumables.get(key,0) < 1:
            raise ValueError('Расходуемая карта уже использована.')
        b['energy'] -= c['cost']
        b['hand'].pop(index)
        if key in CONSUMABLES:
            self.consumables[key] -= 1
            if self.consumables[key] == 0:
                del self.consumables[key]
        else:
            b['discard'].append(key)
        stats = self.combat_stats()
        self.battle_log(f'Карта «{c["name"]}» (энергия −{c["cost"]}).')
        if c['damage']:
            chance = max(5,min(100,stats['hit']+c['accuracy']))
            if self.roll().randint(1,100) <= chance:
                damage = max(0,c['damage']+stats['damage']-b['enemy_armor'])
                absorbed = min(b['enemy_block'],damage)
                b['enemy_block'] -= absorbed
                damage -= absorbed
                b['enemy_hp'] = max(0,b['enemy_hp']-damage)
                self.battle_log(f'Попадание: {damage} урона (защита поглотила {absorbed}).')
            else:
                self.battle_log(f'Промах! Шанс попадания был {chance}%.')
        b['block'] += c['block']
        self.hp = min(stats['hp'],self.hp+c['heal'])
        if b['enemy_hp'] == 0:
            self.finish_battle('victory')

    def end_round(self):
        b = self.battle
        if b is None:
            raise ValueError('Сейчас нет дуэли.')
        stats = self.combat_stats()
        b['enemy_block'] = 0
        if b['intent'] == 'guard':
            b['enemy_block'] = b['intent_value']
            self.battle_log(f'{b["enemy"]} защищается: {b["enemy_block"]} блока.')
        elif self.roll().randint(1,100) > max(5,85-stats['dodge']):
            self.battle_log('Враг промахнулся. Вы избежали удара.')
        else:
            damage = max(0,b['intent_value']-stats['armor'])
            absorbed = min(damage,b['block'])
            damage -= absorbed
            self.hp = max(0,self.hp-damage)
            self.battle_log(f'Удар врага: −{damage} здоровья; блок поглотил {absorbed}, броня {stats["armor"]}.')
        if self.hp == 0:
            self.finish_battle('defeat')
            return
        b['discard'].extend(key for key in b['hand'] if key not in CONSUMABLES)
        # Неиспользованные расходники не тратятся и возвращаются в колоду.
        b['draw'].extend(key for key in b['hand'] if key in CONSUMABLES)
        b['hand'] = []
        b['round'] += 1
        self.draw_round()

    def finish_battle(self, outcome):
        b = self.battle
        if b is None:
            raise ValueError('Сейчас нет дуэли.')
        quest = next(q for q in self.active if q.id==b['quest_id'])
        self.last_battle = dict(outcome=outcome, enemy=b['enemy'], rounds=b['round'], log=list(b['log']))
        self.battle = None
        if outcome == 'victory':
            self.reward(quest, f'Победа в карточной дуэли над {b["enemy"]}. ')
        elif outcome == 'defeat':
            lost = min(10,self.hero.gold)
            self.hero.gold -= lost
            self.hp = 1
            self.record(f'Поражение: {b["enemy"]}. Потеряно {lost} золота; здоровье 1. Задание остаётся активным.')
        else:
            self.record(f'Отступление от {b["enemy"]}. Задание остаётся активным.')
        self.last_battle['message'] = self.journal[-1]

    def flee(self):
        self.finish_battle('flee')

    def validate_battle(self):
        b = self.battle
        if b is None:
            return
        try:
            q = next(q for q in self.active if q.id==b['quest_id'])
            if not q.monster or q.monster!=b['enemy'] or q.target!=self.hero.region or q.monster_tier!=b['tier']:
                raise ValueError('Дуэль не соответствует заданию.')
            for key in ('tier','enemy_hp','enemy_max','enemy_armor','enemy_block','round','energy','block','roll','intent_value'):
                if type(b[key]) is not int or b[key]<0:
                    raise ValueError('Повреждено состояние дуэли.')
            if not 1<=b['tier']<=5 or not 0<b['enemy_hp']<=b['enemy_max'] or b['round']<1 or b['energy']>3:
                raise ValueError('Некорректные параметры дуэли.')
            if b['intent'] not in ('attack','guard') or not isinstance(b['seed'],str):
                raise ValueError('Некорректное намерение.')
            for key in ('hand','draw','discard'):
                if not isinstance(b[key],list) or any(c not in CARDS for c in b[key]) or len(b[key])>100:
                    raise ValueError('Некорректная колода.')
            if len(b['hand'])>5 or not isinstance(b['log'],list) or not all(isinstance(x,str) for x in b['log']):
                raise ValueError('Некорректная рука.')
        except (KeyError,TypeError,StopIteration) as exc:
            raise ValueError('Повреждённое состояние дуэли.') from exc
