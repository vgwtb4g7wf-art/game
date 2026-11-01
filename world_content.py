"""Местные истории, обитатели и карты таверн."""
from eterion import REGIONS
from bestiary import BESTIARY,profile_for
from combat import card, CARDS

# Пять ступеней обитателей в каждой стране. Демоны остаются за закрытой границей.
BIOMES = {
 'Дваллинхорг': ('горные штольни', ['Рудничная крыса','Пещерный паук','Каменный тролль','Рунный голем','Титан глубин'], 'Дварфийские руны', 'Знания', 'Расшифруйте метки старых мастеров в заброшенной штольне.'),
 'Княжество Бреннор': ('северные леса', ['Снежный волк','Ледяной паук','Морозный призрак','Северная виверна','Ледяной дракон'], 'Зимний тракт', 'Дипломатия', 'Доставьте припасы смотрителю зимнего тракта и договоритесь о проходе.'),
 'Азалтир': ('островные руины', ['Морской слизень','Рифовый краб','Страж руин','Кристальный голем','Лич приливов'], 'Память прилива', 'Знания', 'Составьте перевод эльфийских надписей на затопленных камнях.'),
 'Лесное царство Талласа': ('древний лес', ['Лесной волк','Гигантский паук','Лесной призрак','Древень','Дракон изумрудной чащи'], 'Травы Талласы', 'Знания', 'Соберите лекарственные травы, не тревожа священные рощи.'),
 'Тротенфорская империя': ('имперские равнины', ['Полевой кабан','Гоблин-мародёр','Орк-наёмник','Огр-разрушитель','Чёрный рыцарь'], 'Печать империи', 'Дипломатия', 'Уладьте спор караванщиков и получите подпись гильдии.'),
 'Королевство Алдория': ('пески и оазисы', ['Песчаный шакал','Скорпион-великан','Песчаный призрак','Дюнный голем','Дракон барханов'], 'Вода для каравана', 'Дипломатия', 'Договоритесь с хранителями оазиса о воде для путников.'),
 'Аграмор': ('болотные тропы', ['Болотный слизень','Гоблин-разведчик','Орк-налётчик','Болотный огр','Гидра трясин'], 'Тайная тропа', 'Хитрость', 'Отыщите безопасный путь через трясину и спрячьте дорожные метки.'),
 'Владычество Нархаз': ('пепельные земли', ['Пепельная крыса','Бес','Адский пёс','Палач бездны','Владыка пепла'], 'Запечатанные врата', 'Знания', 'Изучите историю закрытых врат.'),
}
REGION_LORE = {
 'Бронзовый Пик':'королевские кузницы', 'Храм Камня':'залы каменных предков',
 'Бреннор':'северный княжеский двор', 'Глыба':'пограничная застава',
 'Келебран':'приливные архивы', 'Азалтир':'башни высших эльфов',
 'Таллас':'двор лесного царя', 'Эланиэль':'священные рощи',
 'Тротенфор':'имперская канцелярия', 'Марктбург':'большая ярмарка',
 'Штальбург':'сталелитейные мастерские', 'Мерилион':'караванные стоянки',
 'Алдория':'дворец среди песков', 'Трущобы':'тайные болотные рынки',
 'Аграмор':'закрытая орочья крепость', 'Нархаз':'демонические врата',
}
CONSUMABLES = {}


def consumable(key, title, price, **effects):
    card(key, title, **effects)
    CONSUMABLES[key] = dict(price=price, limit=3)
    CARDS[key]['consumable'] = True
    return key


consumable('supply:heal','Настой путника',5,cost=1,heal=4)
consumable('supply:smoke','Дымовая завеса',6,cost=0,block=4)
COUNTRY_CARDS = {}
for i, (country, (biome, _, _, _, _)) in enumerate(BIOMES.items()):
    titles = ['Кузнечный огонь','Морозный настой','Свиток прилива','Сок лесного древа',
              'Имперская бомба','Песчаная пыль','Болотный яд','Пепельный свиток']
    COUNTRY_CARDS[country] = consumable(f'country:{i}', titles[i], 9,
                                       cost=1, damage=4 if i%2==0 else 0,
                                       block=0 if i%2==0 else 4, heal=1, accuracy=10 if i%2==0 else 0)
REGION_CARDS = {}
for i, (name, region) in enumerate(REGIONS.items()):
    REGION_CARDS[name] = consumable(f'region:{i}', f'Талисман: {name}', 8,
                                   cost=1, damage=2+i%2, block=2+i%2, accuracy=5)
consumable('city:tonic','Аптекарский эликсир',10,cost=1,heal=6)
consumable('guild:kit','Гильдейский резерв',8,cost=1,heal=3,block=3)
consumable('capital:seal','Свиток королевской защиты',15,cost=1,block=8,heal=2)


def tavern(region, in_city, cycle=0):
    r = REGIONS[region]
    kind = 'Столичная таверна' if in_city and r.capital else 'Городская таверна' if in_city else 'Дорожная таверна'
    keys = ['supply:heal', COUNTRY_CARDS[r.country]]
    if cycle%2==0:keys.append(REGION_CARDS[region])
    else:keys.append('supply:smoke')
    if in_city:
        keys += ['supply:smoke', 'city:tonic']
        if r.capital:
            keys += ['capital:seal']
    return dict(id=f'{region}:{int(in_city)}', name=f'{kind} · {region}',
                description=REGION_LORE[region], keys=list(dict.fromkeys(keys)))


def monster_tier(name):
    if name in BESTIARY:return BESTIARY[name]['tier']
    for _, names, *_ in BIOMES.values():
        if name in names:
            return names.index(name)+1
    return None


def enemy_profile(name,tier):
    if name in BESTIARY:return profile_for(name,tier)
    hp=(8,15,26,36,48)[tier-1]
    attack=(2,3,5,7,8)[tier-1]
    armor=(0,0,2,3,4)[tier-1]
    escape=(2,3,4,6,8)[tier-1]
    defensive=False
    lower=name.lower()
    if any(w in lower for w in ('слизень','голем','страж','краб','титан')):
        armor+=1;hp=max(6,hp-1);defensive=True
    if any(w in lower for w in ('волк','шакал','паук','виверна')):
        hp=max(6,hp-1);escape+=1
    if 'дракон' in lower:hp+=2;escape+=1
    return dict(hp=hp,attack=attack,armor=armor,escape=escape,block=1+tier//2,defensive=defensive,fame_loss=1+tier)
