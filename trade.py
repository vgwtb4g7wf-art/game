"""Снаряжение и запрещённые товары. Начальный редактор сохраняет прежние семь вещей."""
from combat import card,item
from eterion import ITEMS
from world_content import consumable
from social_rules import GEAR_PRICES

ITEMS['Амулет теневого договора']=('Артефакт','Чёрный рынок: 6 блока и лечение 2, один раз за бой.')
item('Амулет теневого договора',[card('artifact:shadow','Теневая сделка',block=6,heal=2,once=True)])
GEAR_PRICES['Амулет теневого договора']=55
consumable('black:veil','Завеса контрабандиста',9,cost=0,block=5)
consumable('black:balm','Нелегальный бальзам',8,cost=1,heal=5)
consumable('black:blade','Скрытый клинок',10,cost=1,ratio=175,accuracy=5)

# Дополнительные варианты прежних трёх типов оружия и пяти доспехов.
from combat import ITEM_POWER
from eterion import COUNTRIES
from world_content import CONSUMABLES
META={n:dict(alignment='neutral',black=n=='Амулет теневого договора',rare=False,passive='') for n in GEAR_PRICES}

def gear(name,slot,price,cards,armor=0,hit=0,passive=None,description='',alignment='neutral',black=False,rare=False):
    ITEMS[name]=(slot,description);item(name,cards,armor=armor,hit=hit)
    ITEM_POWER[name]['passives']=passive or {}
    GEAR_PRICES[name]=price
    META[name]=dict(alignment=alignment,black=black,rare=rare or bool(passive),passive=description if passive else '')

gear('Дуэльная шпага','Оружие',55,[card('gear:rapier:thrust','Точный выпад',ratio=125,accuracy=10),card('gear:rapier:parry','Лёгкая парировка',ratio=75,block=3)],description='Меч: точность и защита вместо тяжёлого удара.')
gear('Охотничий длинный лук','Оружие',60,[card('gear:longbow:shot','Натяжной выстрел',cost=2,ratio=325),card('gear:longbow:step','Отход лучника',block=3)],description='Лук: более сильный выстрел, меньше блока.')
for name,price,armor,hit,desc in [
 ('Стёганая куртка путника',20,3,0,'Недорогой доспех: 3 брони.'),
 ('Бригантина',65,9,-5,'9 брони; −5% попадания.'),
 ('Чешуйчатый панцирь',60,7,0,'7 брони без штрафа к попаданию.'),
 ('Пластинчатый доспех',80,11,-10,'11 брони; −10% попадания.'),
 ('Мантия лекаря',55,2,0,'2 брони; все карты лечения сильнее на 25%.')]:
    gear(name,'Доспех',price,[],armor,hit,{'healing_bonus':25} if name=='Мантия лекаря' else None,desc)
for name,price,key,title,kw in [
 ('Печать каменного круга',45,'stone','Каменная печать',dict(armor=5)),
 ('Брошь полевого лекаря',45,'medic','Тёплый свет',dict(heal=5)),
 ('Линза меткого взгляда',55,'lens','Световой луч',dict(ratio=125,accuracy=10)),
 ('Талисман равновесия',50,'balance','Равновесие',dict(block=4,heal=3))]:
    gear(name,'Артефакт',price,[card('artifact:'+key,title,once=True,**kw)],description='Одна карта за 1 энергию, один раз за бой.')

# Дорогие варианты с небольшими постоянными бонусами.
gear('Меч верного слова','Оружие',85,ITEM_POWER['Железный меч']['cards'],passive={'hp':2},description='Меч; постоянно +2 HP.',alignment='good',rare=True)
gear('Кинжал ночного дозора','Оружие',85,ITEM_POWER['Короткий кинжал']['cards'],passive={'crit_chance':3},description='Кинжал; +3% шанса крита.',alignment='bad',rare=True)
gear('Кольчуга рубежа','Доспех',95,[],8,-5,{'hp':2},'Кольчуга; +2 HP, −5% попадания.',rare=True)
gear('Амулет ясной памяти','Артефакт',85,ITEM_POWER['Медный амулет']['cards'],passive={'hit':5},description='Амулет: блок 8 раз за бой, постоянно +5% попадания.',alignment='good',rare=True)
gear('Кинжал контрабандиста','Оружие',90,ITEM_POWER['Короткий кинжал']['cards'],passive={'hit':5},description='Кинжал: +5% попадания.',black=True,rare=True)
gear('Панцирь сборщика долгов','Доспех',90,[],6,0,{'hp':2},'6 брони и +2 HP.',alignment='bad',rare=True)
gear('Печать подпольного лекаря','Артефакт',85,[card('artifact:blackmedic','Тёмный бальзам',heal=4,block=3,once=True)],passive={'healing_bonus':25},description='Карта лечения 4 и блока 3; постоянно +25% лечения.',black=True,rare=True)

# Уровень доступа: 0 — везде, 1 — город, 2 — столица.
SUPPLIES={}
def supply(key,title,price,tier=0,country=None,alignment='neutral',black=False,**kw):
    consumable(key,title,price,**kw)
    SUPPLIES[key]=dict(tier=tier,country=country,alignment=alignment,black=black)

for key,title,price,tier,kw in [
 ('common:tea','Походный чай',5,0,dict(heal=3,block=1)),
 ('common:bandage','Чистая повязка',6,0,dict(heal=4)),
 ('common:stone','Пращный камень',5,0,dict(damage=3)),
 ('common:smoke','Дорожная дымовая шашка',7,0,dict(cost=0,block=3)),
 ('common:salve','Защитная мазь',7,0,dict(armor=3)),
 ('town:tonic','Тоник аптекаря',10,1,dict(heal=6)),
 ('town:shield','Свиток городского заслона',10,1,dict(block=6)),
 ('town:fire','Алхимический огонь',11,1,dict(ratio=175)),
 ('capital:elixir','Придворный эликсир',16,2,dict(heal=8)),
 ('capital:seal','Печать столичной гильдии',16,2,dict(block=6,heal=2))]:supply(key,title,price,tier,**kw)

COUNTRY_SUPPLIES={
 'Дваллинхорг':['Шахтёрский отвар','Кварцевая пыль','Кузнечная накладка','Рунный пластырь','Огненная стружка','Печать Бронзового Пика'],
 'Княжество Бреннор':['Северный чай','Инейный порошок','Шерстяная перевязь','Бреннорский настой','Ледяной осколок','Свиток княжеской стражи'],
 'Азалтир':['Соль прилива','Коралловая крошка','Морская перевязь','Эликсир жемчужниц','Кристальный заряд','Печать островного совета'],
 'Лесное царство Талласа':['Лесной сбор','Терновая пыль','Моховой компресс','Сок священной рощи','Капсула живицы','Лист королевского древа'],
 'Тротенфорская империя':['Полевой отвар','Имперский порох','Солдатский бинт','Гильдейский эликсир','Сигнальная ракета','Указ столичного лекаря'],
 'Королевство Алдория':['Оазисный напиток','Пыль барханов','Полотно караванщика','Сироп финиковой пальмы','Стеклянный снаряд','Печать золотого дворца'],
 'Аграмор':['Горький болотный настой','Топяная пыль','Повязка пустоши','Орочий тоник','Колба гоблинского огня','Знак военного шамана'],
 'Владычество Нархаз':['Пепельный настой','Серный порошок','Обугленная перевязь','Бальзам угольного сердца','Искра горнила','Печать пепельного трона'],
}
for i,(country,names) in enumerate(COUNTRY_SUPPLIES.items()):
    for j,title in enumerate(names):
        kw=[dict(heal=3,block=1),dict(cost=0,block=3),dict(armor=3),dict(heal=5,block=1),dict(ratio=175),dict(armor=4,heal=3)][j]
        supply(f'local:{i}:{j}',title,(6,7,7,11,12,17)[j],0 if j<3 else 1 if j<5 else 2,country,**kw)

# Репутационные линии: нейтральные видят простые товары обеих сторон; сильные — только своей.
for alignment,titles in [('good',['Помощь общины','Освящённая повязка','Свиток хранителя']),('bad',['Тайный порошок','Настой наёмника','Свиток устрашения'])]:
    for j,title in enumerate(titles):
        supply(f'rep:{alignment}:{j}',title,(7,11,15)[j],0 if j==0 else 1,alignment=alignment,**([dict(block=3,heal=2),dict(heal=6),dict(block=7,heal=1)][j] if alignment=='good' else [dict(damage=3,block=2),dict(ratio=150,heal=2),dict(ratio=225)][j]))
for key,title,price,kw in [
 ('black:needle','Игла подпольного охотника',12,dict(ratio=200,accuracy=5)),
 ('black:powder','Контрабандный порошок',12,dict(cost=0,block=4,heal=1)),
 ('black:resin','Ночная смола',10,dict(armor=4)),
 ('black:tincture','Настой теневых переулков',13,dict(heal=6))]:supply(key,title,price,black=True,**kw)
for key in ('black:veil','black:balm','black:blade'):SUPPLIES[key]=dict(tier=0,country=None,alignment='bad',black=True)
# Старые сохранённые расходники остаются действительными и продаваемыми.
BASE_SUPPLY_COUNT=10+len(COUNTRIES)*6
SUPPLIES['guild:kit']=dict(tier=1,country=None,alignment='neutral',black=False,guild=True)

# Баланс 0.13: расходники — трата дохода от боя, пассивные вещи требуют накоплений.
from math import ceil
for data in CONSUMABLES.values():data['price']=max(10,ceil(data['price']*1.8))
for name,meta in META.items():
    if meta['rare']:GEAR_PRICES[name]=ceil(GEAR_PRICES[name]*1.15)
