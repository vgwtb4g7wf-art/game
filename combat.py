"""Небольшая самостоятельная карточная система: одна цель, три энергии."""
from eterion import BRANCHES

CARDS = {}


def card(key, name, cost=1, damage=0, block=0, heal=0, accuracy=0):
    CARDS[key] = dict(id=key, name=name, cost=cost, damage=damage, block=block,
                      heal=heal, accuracy=accuracy)
    return key


card('strike', 'Удар', damage=6)
card('guard', 'Прикрыться', block=6)
card('breath', 'Перевести дух', heal=5)
# Каждый предмет имеет собственную пару карт. Числа — временный баланс.
ITEM_POWER = {}


def item(name, hp, armor, dodge, hit, moves):
    keys = []
    for i, (title, cost, damage, block, heal, accuracy) in enumerate(moves):
        keys.append(card(f'item:{name}:{i}', title, cost, damage, block, heal, accuracy))
    ITEM_POWER[name] = dict(hp=hp, armor=armor, dodge=dodge, hit=hit, cards=keys)


item('Учебный меч',0,0,0,0,[('Пробный выпад',1,8,0,0,5),('Учебная стойка',1,4,5,0,0)])
item('Железный меч',0,0,0,0,[('Рубящий удар',1,10,0,0,0),('Парирование',1,5,7,0,0)])
item('Боевой топор',0,0,0,0,[('Раскол',2,20,0,0,-10),('Удар обухом',1,9,3,0,0)])
item('Короткий кинжал',0,0,3,0,[('Быстрый укол',0,4,0,0,5),('Точный выпад',1,9,0,0,15)])
item('Охотничье копьё',0,0,0,0,[('Дальний выпад',1,11,0,0,5),('Держать дистанцию',1,5,8,0,0)])
item('Дорожный лук',0,0,0,0,[('Выстрел',1,9,0,0,5),('Прицельная стрела',2,18,0,0,15)])
item('Арбалет',0,0,0,0,[('Тяжёлый болт',2,21,0,0,0),('Навскидку',1,10,0,0,-5)])
item('Посох ученика',0,0,0,0,[('Искра',1,9,0,0,10),('Рунный заслон',1,3,8,0,0)])
item('Кожаная куртка',2,1,5,0,[('Лёгкая стойка',1,0,8,0,0),('Уход с линии',0,0,3,0,0)])
item('Стёганый доспех',4,2,0,0,[('Смягчить удар',1,0,10,0,0),('Выдержка',1,0,4,4,0)])
item('Кольчуга',4,3,0,-3,[('Кольчужная защита',1,0,12,0,0),('Ответный выпад',1,7,5,0,0)])
item('Латный нагрудник',8,4,-3,-5,[('Стальная стена',2,0,22,0,0),('Таран',1,8,5,0,-5)])
item('Мантия учёного',2,0,2,0,[('Защитная вязь',1,0,9,0,0),('Восстановление',1,0,0,8,0)])
item('Плащ следопыта',2,1,8,0,[('Тень леса',0,0,5,0,0),('Из укрытия',1,8,3,0,10)])
item('Медный оберег',2,0,0,0,[('Тепло оберега',1,0,0,7,0),('Медный круг',1,0,9,0,0)])
item('Компас морехода',0,0,3,3,[('Верный курс',1,8,0,0,20),('Морская выдержка',1,0,5,4,0)])
item('Кольцо янтаря',3,0,0,0,[('Янтарный свет',1,0,0,10,0),('Искра янтаря',1,10,0,0,5)])
item('Лунный камень',0,0,3,0,[('Лунный луч',1,11,0,0,10),('Серебряный покров',1,0,11,0,0)])
item('Печать посланника',2,0,0,3,[('Слово власти',1,7,6,0,5),('Непоколебимость',1,0,7,4,0)])
item('Рунная монета',0,1,0,0,[('Рунный удар',1,10,0,0,5),('Каменная руна',1,0,12,0,0)])

SKILL_POWER = {}
BONUSES = {
    'Мощь': [('hp',6),('damage',2),('armor',1)],
    'Знания': [('hit',3),('hp',4),('damage',2)],
    'Хитрость': [('dodge',4),('hit',5),('damage',2)],
    'Дипломатия': [('hp',4),('dodge',3),('armor',1)],
}
for branch, names in BRANCHES.items():
    for i, name in enumerate(names):
        if branch == 'Мощь':
            key = card('skill:'+name, name, 1, 8+i*2, 2+i*2)
        elif branch == 'Знания':
            key = card('skill:'+name, name, 1, 5+i*2, 0, 3+i, 10)
        elif branch == 'Хитрость':
            key = card('skill:'+name, name, 1, 7+i*2, 2+i, 0, 15)
        else:
            key = card('skill:'+name, name, 1, 0, 7+i*2, 2+i)
        stat, amount = BONUSES[branch][i]
        SKILL_POWER[name] = dict(card=key, stat=stat, amount=amount)


def stats(hero):
    result = dict(hp=36, armor=0, dodge=3, hit=90, damage=0)
    for name in hero.equipment.values():
        if name:
            for key in ('hp','armor','dodge','hit'):
                result[key] += ITEM_POWER[name][key]
    for branch, level in hero.branches.items():
        for name in BRANCHES[branch][:level]:
            effect = SKILL_POWER[name]
            result[effect['stat']] += effect['amount']
    result['dodge'] = max(0, min(45, result['dodge']))
    result['hit'] = max(50, min(98, result['hit']))
    return result


def deck(hero, consumables):
    entries = [(key, 'Основы') for key in ['strike']*3 + ['guard']*2 + ['breath']]
    for name in hero.equipment.values():
        if name:
            entries.extend((key, name) for key in ITEM_POWER[name]['cards'] for _ in range(2))
    for branch, level in hero.branches.items():
        entries.extend((SKILL_POWER[name]['card'], name) for name in BRANCHES[branch][:level])
    entries.extend((key, 'Расходуемая карта') for key, count in consumables.items() for _ in range(count))
    return entries
