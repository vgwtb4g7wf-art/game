"""Карты и параметры: урон в процентах, броня — возобновляемый запас."""
from progression import TREES,unlocked
CARDS={}
ITEM_POWER={}
SKILL_POWER={}


def card(key,name,cost=1,damage=0,block=0,heal=0,accuracy=0,ratio=0,once=False,bank=0,armor=0):
    CARDS[key]=dict(id=key,name=name,cost=cost,damage=damage,block=block,heal=heal,accuracy=accuracy,ratio=ratio,once=once,bank=bank,armor=armor)
    return key


card('strike','Удар',ratio=50)
card('guard','Уворот',block=2)
card('breath','Поддержка',heal=2)
card('strike:1','Усиленный удар',ratio=75)
card('strike:2','Защитный удар',ratio=75,block=2)
card('strike:3','Разящий удар',ratio=100)
card('guard:1','Усиленный уворот',block=3)
card('guard:2','Теневой выпад',block=4,ratio=100)
card('guard:3','Неуловимость',block=6)
card('breath:1','Усиленная поддержка',heal=3)
card('breath:2','Выжигание',ratio=125)
card('breath:3','Живительная поддержка',heal=4)


def item(name,cards,armor=0,hit=0):
    ITEM_POWER[name]=dict(cards=cards,hp=0,armor=armor,hit=hit)


item('Железный меч',[card('weapon:sword:cut','Рубящий удар',ratio=150),card('weapon:sword:parry','Парирующий выпад',ratio=100,block=2)])
knife=card('weapon:dagger','Двойное остриё',ratio=150)
item('Короткий кинжал',[knife,knife])
item('Дорожный лук',[card('weapon:bow:shot','Мощный выстрел',cost=2,ratio=300),card('weapon:bow:roll','Подкат',block=4)])
item('Кожаная куртка',[],armor=4)
item('Кольчуга',[],armor=8,hit=-5)
item('Кольцо янтаря',[card('artifact:ring','Запасённая искра',cost=1,once=True,bank=1)])
item('Медный амулет',[card('artifact:amulet','Покров амулета',block=8,once=True)])
# Только для миграции старого снаряжения, в новом каталоге этих вещей нет.
LEGACY_ITEMS={'Учебный меч':'Железный меч','Боевой топор':'Железный меч','Охотничье копьё':'Железный меч','Арбалет':'Дорожный лук','Посох ученика':'Железный меч','Стёганый доспех':'Кожаная куртка','Латный нагрудник':'Кольчуга','Мантия учёного':'Кожаная куртка','Плащ следопыта':'Кожаная куртка','Медный оберег':'Медный амулет','Компас морехода':'Медный амулет','Лунный камень':'Медный амулет','Рунная монета':'Медный амулет','Печать посланника':'Кольцо янтаря'}
for old,new in LEGACY_ITEMS.items():ITEM_POWER[old]=ITEM_POWER[new]


def skill(name,kind,description,effects=None,card_id=None,once=None):
    SKILL_POWER[name]=dict(kind=kind,description=description,effects=effects or {},card=card_id,grant=once or {})


# У специализаций разные замены одной базовой карты.
for name,key,stage,description in [
 ('Тяжёлый удар','strike',1,'Все базовые удары наносят 75% базового урона.'),
 ('Защитный удар','strike',2,'Каждый базовый удар наносит 75% урона и даёт 2 блока.'),
 ('Разящий удар','strike',3,'Все базовые удары наносят 100% базового урона.'),
 ('Лёгкий уворот','guard',1,'Базовый уворот даёт 3 блока.'),
 ('Теневой выпад','guard',2,'Базовый уворот даёт 4 блока и наносит 100% урона.'),
 ('Неуловимость','guard',3,'Базовый уворот даёт 6 блока.'),
 ('Малая поддержка','breath',1,'Базовая поддержка лечит 3 здоровья.'),
 ('Выжигание','breath',2,'Базовая поддержка больше не лечит: наносит 125% урона.'),
 ('Живительная поддержка','breath',3,'Базовая поддержка лечит 4 здоровья.'),
]:skill(name,'upgrade',description,{key:stage})

skill('Натиск','card','150% урона за 1 энергию.',card_id=card('skill:Натиск','Натиск',ratio=150))
skill('Неприступный бастион','card','10 блока за 1 энергию.',card_id=card('skill:Неприступный бастион','Неприступный бастион',block=10))
skill('Прорыв','card','350% урона за 2 энергии.',card_id=card('skill:Прорыв','Прорыв',cost=2,ratio=350))
skill('Манёвр','card','50% урона и 4 блока за 1 энергию.',card_id=card('skill:Манёвр','Манёвр',ratio=50,block=4))
skill('Смертельный выпад','card','300% урона и +5% к попаданию за 2 энергии.',card_id=card('skill:Смертельный выпад','Смертельный выпад',cost=2,ratio=300,accuracy=5))
skill('Ловкая передышка','card','50% урона, 3 блока и лечение 3 здоровья за 1 энергию.',card_id=card('skill:Ловкая передышка','Ловкая передышка',ratio=50,block=3,heal=3))
skill('Передышка','card','3 блока и лечение 3 здоровья за 1 энергию.',card_id=card('skill:Передышка','Передышка',block=3,heal=3))
skill('Огненный столб','card','250% урона за 1 энергию сейчас; на следующем раунде энергии на 1 меньше, даже при промахе.',card_id=card('skill:Огненный столб','Огненный столб',ratio=250,bank=-1))
skill('Восстановление','card','Добавляет 3 брони до конца боя и лечит 3 здоровья за 1 энергию.',card_id=card('skill:Восстановление','Восстановление',armor=3,heal=3))
for name,bonus,description in [
 ('Закалка',{'hp':6},'Постоянно +6 максимального здоровья.'),
 ('Мастер доспехов',{'armor_accuracy':1,'armor':2},'Доспех больше не снижает попадание; дополнительно +2 брони в начале каждого боя.'),
 ('Сила берсерка',{'unarmored_ratio':50},'Без надетого доспеха атакующие карты наносят дополнительно 50% базового урона: 100% → 150%. Блок и лечение не меняются.'),
 ('Острый глаз',{'crit_chance':6},'+6 процентных пунктов к шансу крита: с базовых 3% до 9%. Максимум — 15%.'),
 ('Смертельная точность',{'crit_multiplier':50,'crit_chance':6},'Крит наносит 200% итогового урона вместо 150%; +6% к шансу крита, до максимальных 15%.'),
 ('Звон монет',{'gold_damage':1,'gold_damage_cap':3},'+1 базового урона за полные 100 монет, максимум +3 урона. Бонус меняется вместе с запасом золота.'),
 ('Ясный разум',{'hit':5},'Постоянно +5 процентных пунктов к попаданию.'),
 ('Сила пламени',{'damage':1},'Постоянно +1 базового урона.'),
 ('Дар исцеления',{'healing_bonus':50},'Все карты лечения восстанавливают на 50% больше здоровья. Половины округляются вверх; выше максимума лечить нельзя.'),
]:skill(name,'passive',description,bonus)
skill('Добрая молва','passive','+1 к получаемой известности за добрые дела и разово +5 общей известности.',{'fame_bonus':1},once={'fame':5})
skill('Крепкое здоровье','passive','Постоянно +2 максимального здоровья.',{'hp':2})
skill('Покровитель','passive','Разово получите 40 золота.',once={'gold':40})
skill('Уважение','passive','Разово +5 общей репутации; за добрые дела получаете дополнительно +1 репутации.',{'reputation_bonus':1},once={'reputation':5})
skill('Сеть поручений','passive','Можно принять на одно задание больше: 3 вместо 2.',{'quest_limit':1})
skill('Союз гильдий','passive','Цены таверн ниже на 15%, открыт гильдейский товар.',{'discount':15,'stock':1})
skill('Слава','passive','Разово +10 общей известности, +1 к известности за добрые дела.',{'fame_bonus':1},once={'fame':10})
skill('Осведомители','passive','Поиск предлагает на два задания больше: 5 вместо 3.',{'offer_limit':2})
skill('Торговые связи','passive','Цены таверн ниже на 25%, открыт гильдейский товар.',{'discount':25,'stock':1})


def effects(hero):
    result={}
    for name in unlocked(hero):
        for key,value in SKILL_POWER[name]['effects'].items():
            if key in ('strike','guard','breath'):result[key]=max(result.get(key,0),value)
            else:result[key]=result.get(key,0)+value
    for name in hero.equipment.values():
        if name:
            for key,value in ITEM_POWER[name].get('passives',{}).items():result[key]=result.get(key,0)+value
    return result


def selectable(hero):return [n for n in unlocked(hero) if SKILL_POWER[n]['kind']=='card']


def active_skills(hero):
    available=selectable(hero)
    return [s for s in getattr(hero,'selected_skills',available[:3]) if s in available][:3]


def stats(hero):
    e=effects(hero)
    result=dict(hp=14+getattr(hero,'bonus_hp',0)+(3 if hero.race=='Дварф' else 0),
                damage=4+getattr(hero,'bonus_damage',0)+(1 if hero.race=='Лесной эльф' else 0),armor=0,hit=90,
                crit_chance=3,crit_multiplier=150)
    for slot,name in hero.equipment.items():
        if name:
            for key in ('hp','armor','hit'):
                value=ITEM_POWER[name][key]
                if key=='hit' and slot=='Доспех' and value<0 and e.get('armor_accuracy'):continue
                result[key]+=value
    for key,value in e.items():
        if key in result:result[key]+=value
    result['damage']+=min(e.get('gold_damage_cap',0),e.get('gold_damage',0)*(hero.gold//100))
    result['hit']=max(50,min(100,result['hit']))
    result['crit_chance']=max(3,min(15,result['crit_chance']))
    return result


def card_ratio(c,hero):
    bonus=effects(hero).get('unarmored_ratio',0) if not hero.equipment.get('Доспех') else 0
    return c.get('ratio',0)+(bonus if c.get('ratio') or c['damage'] else 0)


def card_damage(c,hero):
    return (stats(hero)['damage']*card_ratio(c,hero)+50)//100+c['damage']


def card_heal(c,hero):
    return (c['heal']*(100+effects(hero).get('healing_bonus',0))+50)//100


def critical_damage(damage,hero):
    return (damage*stats(hero)['crit_multiplier']+50)//100


def deck(hero,consumables):
    e=effects(hero)
    upgraded=lambda key:key+':'+str(e[key]) if e.get(key) else key
    entries=[(upgraded(k),'Основы') for k in ('strike','strike','guard','breath')]
    for name in hero.equipment.values():
        if name:entries.extend((k,name) for k in ITEM_POWER[name]['cards'])
    entries.extend((SKILL_POWER[n]['card'],n) for n in active_skills(hero))
    entries.extend((k,'Одноразовая карта') for k,count in consumables.items() for _ in range(count))
    return entries
