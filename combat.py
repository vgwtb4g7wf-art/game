"""Карты и параметры: урон в процентах, броня — возобновляемый запас."""
from progression import TREES,unlocked
CARDS={}
ITEM_POWER={}
SKILL_POWER={}


def card(key,name,cost=1,damage=0,block=0,heal=0,accuracy=0,ratio=0,once=False,bank=0):
    CARDS[key]=dict(id=key,name=name,cost=cost,damage=damage,block=block,heal=heal,accuracy=accuracy,ratio=ratio,once=once,bank=bank)
    return key


card('strike','Удар',ratio=50)
card('guard','Уворот',block=2)
card('breath','Поддержка',heal=2)
card('strike:1','Усиленный удар',ratio=75)
card('strike:2','Мастерский удар',ratio=100)
card('guard:1','Усиленный уворот',block=3)
card('guard:2','Мастерский уворот',block=4)
card('breath:1','Усиленная поддержка',heal=3)
card('breath:2','Мастерская поддержка',heal=4)


def item(name,cards,armor=0,dodge=0):
    ITEM_POWER[name]=dict(cards=cards,hp=0,armor=armor,dodge=dodge,hit=0)


item('Железный меч',[card('weapon:sword:cut','Рубящий удар',ratio=150),card('weapon:sword:parry','Парирующий выпад',ratio=100,block=2)])
knife=card('weapon:dagger','Двойное остриё',ratio=150)
item('Короткий кинжал',[knife,knife])
item('Дорожный лук',[card('weapon:bow:shot','Мощный выстрел',cost=2,ratio=300),card('weapon:bow:roll','Подкат',block=4)])
item('Кожаная куртка',[],armor=4)
item('Кольчуга',[],armor=8,dodge=-5)
item('Кольцо янтаря',[card('artifact:ring','Запасённая искра',cost=1,once=True,bank=1)])
item('Медный амулет',[card('artifact:amulet','Покров амулета',block=8,once=True)])
# Только для миграции старого снаряжения, в новом каталоге этих вещей нет.
LEGACY_ITEMS={'Учебный меч':'Железный меч','Боевой топор':'Железный меч','Охотничье копьё':'Железный меч','Арбалет':'Дорожный лук','Посох ученика':'Железный меч','Стёганый доспех':'Кожаная куртка','Латный нагрудник':'Кольчуга','Мантия учёного':'Кожаная куртка','Плащ следопыта':'Кожаная куртка','Медный оберег':'Медный амулет','Компас морехода':'Медный амулет','Лунный камень':'Медный амулет','Рунная монета':'Медный амулет','Печать посланника':'Кольцо янтаря'}
for old,new in LEGACY_ITEMS.items():ITEM_POWER[old]=ITEM_POWER[new]


def skill(name,kind,description,effects=None,card_id=None,once=None):
    SKILL_POWER[name]=dict(kind=kind,description=description,effects=effects or {},card=card_id,grant=once or {})


for branch,key,upgrades in [('Мощь','strike',[75,100]),('Знания','breath',[3,4]),('Хитрость','guard',[3,4])]:
    t=TREES[branch]
    for name,stage in [(t['common'][0],1),(t['left'][0],2),(t['right'][0],2)]:
        description={'strike':f'Все базовые удары наносят {upgrades[stage-1]}% урона героя.','guard':f'Базовый уворот даёт {upgrades[stage-1]} блока.','breath':f'Базовая поддержка лечит {upgrades[stage-1]} здоровья.'}[key]
        skill(name,'upgrade',description,{key:stage})

skill('Натиск','card','Атакующий приём за 1 энергию.',card_id=card('skill:Натиск','Натиск',ratio=125))
skill('Ответный выпад','card','Удар с защитой.',card_id=card('skill:Ответный выпад','Ответный выпад',ratio=100,block=3))
skill('Прорыв','card','Сильный удар за 2 энергии.',card_id=card('skill:Прорыв','Прорыв',cost=2,ratio=200,accuracy=5))
skill('Передышка','card','Лечение за 1 энергию.',card_id=card('skill:Передышка','Передышка',heal=4))
skill('Восстановление','card','Лечение и немного блока.',card_id=card('skill:Восстановление','Восстановление',heal=5,block=1))
skill('Рунный заслон','card','Лечебный защитный приём.',card_id=card('skill:Рунный заслон','Рунный заслон',heal=2,block=4))
skill('Манёвр','card','Удар и уклоняющая стойка.',card_id=card('skill:Манёвр','Манёвр',ratio=50,block=3))
skill('Тень','card','Защита за 1 энергию.',card_id=card('skill:Тень','Тень',block=5))
skill('Прицельный укол','card','Точная атака.',card_id=card('skill:Прицельный укол','Прицельный укол',ratio=150,accuracy=10))
for name,effects in {'Закалка':{'hp':2},'Стальная стойкость':{'armor':2},'Сила берсерка':{'damage':2},'Ясный разум':{'hp':2},'Жизненная сила':{'hp':3},'Руническая кожа':{'armor':2},'Острый глаз':{'hit':5},'Быстрые ноги':{'dodge':5},'Хладнокровие':{'hit':5}}.items():
    skill(name,'passive','Постоянный бонус после открытия.',effects)
skill('Добрая молва','passive','+1 к получаемой известности за добрые дела и разово +5 известности в текущей стране.',{'fame_bonus':1},once={'fame':5})
skill('Крепкое здоровье','passive','Постоянно +2 максимального здоровья.',{'hp':2})
skill('Покровитель','passive','Разово получите 15 золота.',once={'gold':15})
skill('Уважение','passive','Разово +5 репутации во всех странах.',once={'reputation_all':5})
skill('Сеть поручений','passive','Можно принять на одно задание больше: 3 вместо 2.',{'quest_limit':1})
skill('Союз гильдий','passive','Цены таверн ниже на 10%, открыт гильдейский товар.',{'discount':10,'stock':1})
skill('Слава','passive','Разово +10 известности в текущей стране, +1 к известности за добрые дела.',{'fame_bonus':1},once={'fame':10})
skill('Осведомители','passive','Поиск предлагает на два задания больше: 5 вместо 3.',{'offer_limit':2})
skill('Торговые связи','passive','Цены таверн ниже на 15%, открыт гильдейский товар.',{'discount':15,'stock':1})


def effects(hero):
    result={}
    for name in unlocked(hero):
        for key,value in SKILL_POWER[name]['effects'].items():
            if key in ('strike','guard','breath'):result[key]=max(result.get(key,0),value)
            else:result[key]=result.get(key,0)+value
    return result


def selectable(hero):return [n for n in unlocked(hero) if SKILL_POWER[n]['kind']=='card']


def active_skills(hero):
    available=selectable(hero)
    return [s for s in getattr(hero,'selected_skills',available[:3]) if s in available][:3]


def stats(hero):
    level=getattr(hero,'level',1)
    result=dict(hp=14+2*(level-1),damage=4+level-1,armor=0,hit=90,dodge=10)
    for name in hero.equipment.values():
        if name:
            for key in ('hp','armor','hit','dodge'):result[key]+=ITEM_POWER[name][key]
    for key,value in effects(hero).items():
        if key in result:result[key]+=value
    result['hit']=max(50,min(95,result['hit']))
    result['dodge']=max(0,min(45,result['dodge']))
    return result


def card_damage(c,hero):
    return (stats(hero)['damage']*c.get('ratio',0)+50)//100+c['damage']


def deck(hero,consumables):
    e=effects(hero)
    upgraded=lambda key:key+':'+str(e[key]) if e.get(key) else key
    entries=[(upgraded(k),'Основы') for k in ('strike','strike','guard','breath')]
    for name in hero.equipment.values():
        if name:entries.extend((k,name) for k in ITEM_POWER[name]['cards'])
    entries.extend((SKILL_POWER[n]['card'],n) for n in active_skills(hero))
    entries.extend((k,'Одноразовая карта') for k,count in consumables.items() for _ in range(count))
    return entries
