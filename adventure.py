"""Правила графического прототипа: задания, развитие и снаряжение."""
from dataclasses import asdict, dataclass
from pathlib import Path
import json
import random

from eterion import Game, ITEMS, REGIONS, BRANCHES
from battle_rules import BattleRules
from world_content import BIOMES, REGION_LORE, monster_tier, CONSUMABLES
from combat import stats

ITEMS.update({
    'Железный меч': ('Оружие', 'Прямой клинок городской стражи.'),
    'Боевой топор': ('Оружие', 'Тяжёлый дварфийский топор.'),
    'Короткий кинжал': ('Оружие', 'Неприметный клинок разведчика.'),
    'Охотничье копьё': ('Оружие', 'Ясеневое древко и стальной наконечник.'),
    'Арбалет': ('Оружие', 'Простой арбалет с деревянной ложей.'),
    'Кольчуга': ('Доспех', 'Переплетённые стальные кольца.'),
    'Латный нагрудник': ('Доспех', 'Кованая броня имперского образца.'),
    'Мантия учёного': ('Доспех', 'Дорожная мантия с карманами для записей.'),
    'Плащ следопыта': ('Доспех', 'Зелёный плащ лесных дозорных.'),
    'Кольцо янтаря': ('Артефакт', 'Внутри янтаря застыла золотая искра.'),
    'Лунный камень': ('Артефакт', 'Светлый камень с эльфийскими письменами.'),
    'Печать посланника': ('Артефакт', 'Бронзовая печать забытого дома.'),
    'Рунная монета': ('Артефакт', 'Дварфийская монета с древней руной.'),
})

MONSTERS = {
    1: [('Пещерная крыса', 'Обитает в подвалах и заброшенных рудниках.'), ('Серый волк', 'Охотится у лесных дорог.'), ('Болотный слизень', 'Скрывается в стоячей воде.')],
    2: [('Гоблин-разведчик', 'Устраивает засады вдоль трактов.'), ('Гигантский паук', 'Оплетает паутиной старые тропы.'), ('Костяной страж', 'Охраняет забытые захоронения.')],
    3: [('Орк-налётчик', 'Опасный воин из вольной банды.'), ('Каменный тролль', 'Подстерегает путников у горных перевалов.'), ('Лесной призрак', 'Блуждает среди древних деревьев.')],
    4: [('Огр-разрушитель', 'Один удар способен проломить ворота.'), ('Древний голем', 'Создание давно исчезнувших мастеров.'), ('Виверна', 'Крылатая хищница скалистых вершин.')],
    5: [('Древний дракон', 'Хранитель сокровищ и забытых тайн.'), ('Лич безмолвия', 'Повелитель нежити в запечатанном склепе.'), ('Титан глубин', 'Колосс, пробудившийся под землёй.')],
}
QUEST_TYPES = (
    ('Охота', 'Мощь', 'Устраните угрозу на окраине региона.', False),
    ('Забытые письмена', 'Знания', 'Изучите руины и расшифруйте найденную надпись.', False),
    ('Пропавшая реликвия', 'Хитрость', 'Отыщите украденную реликвию и незаметно верните её владельцу.', False),
    ('Спор гильдий', 'Дипломатия', 'Помогите двум гильдиям заключить мирное соглашение.', True),
    ('Письмо через границу', 'Дипломатия', 'Доставьте запечатанное письмо городскому посланнику.', True),
    ('Лесная лечебница', 'Знания', 'Соберите и опишите редкие лекарственные растения.', False),
)
SAVE = Path(__file__).parent / 'adventure-save.json'


@dataclass
class Quest:
    id: str
    title: str
    description: str
    difficulty: int
    branch: str
    origin: str
    target: str
    city: bool
    monster: str | None
    xp: int
    gold: int
    progress: int
    loot: str
    distance: int = 0
    monster_tier: int = 0
    origin_city: bool = False


class Adventure(BattleRules, Game):
    def __init__(self, hero):
        super().__init__(hero)
        self.xp = 0
        self.branch_xp = dict.fromkeys(BRANCHES, 0)
        self.bag = [x for x in hero.equipment.values() if x]
        self.offers: list[Quest] = []
        self.active: list[Quest] = []
        self.completed: list[str] = []
        self.search_count = 0
        self.hp = stats(hero)["hp"]
        self.consumables = {}
        self.purchases = {}
        self.battle = None
        self.last_battle = None

    def reachable(self):
        seen = {self.hero.region}
        todo = [self.hero.region]
        from eterion import ROUTES
        while todo:
            current = todo.pop()
            for a, b, _ in ROUTES:
                if current not in (a, b):
                    continue
                nxt = b if a == current else a
                border = tuple(sorted((REGIONS[current].country, REGIONS[nxt].country)))
                if nxt not in seen and not REGIONS[nxt].blocked and border not in self.wars:
                    seen.add(nxt)
                    todo.append(nxt)
        return sorted(seen)

    def distances(self):
        from eterion import ROUTES
        distances = {self.hero.region: 0}
        queue = [self.hero.region]
        for current in queue:
            for a, b, _ in ROUTES:
                if current not in (a,b):
                    continue
                nxt = b if a==current else a
                border = tuple(sorted((REGIONS[current].country,REGIONS[nxt].country)))
                if nxt not in distances and not REGIONS[nxt].blocked and border not in self.wars:
                    distances[nxt] = distances[current]+1
                    queue.append(nxt)
        return distances

    def search(self):
        self.ensure_free()
        self.search_count += 1
        rng = random.Random(f'{self.hero.region}:{self.in_city}:{self.search_count}')
        distances = self.distances()
        other = sorted(r for r in distances if r!=self.hero.region)
        self.offers = []
        for index in range(5):
            target = self.hero.region if index in (0,2) or not other else rng.choice(other)
            distance = distances[target]
            country = REGIONS[target].country
            biome, monsters, local_title, local_branch, local_description = BIOMES[country]
            lore = REGION_LORE[target]
            monster = None
            tier = 0
            if index in (0,3):
                tier = 1 if index==0 else rng.randint(2,5)
                monster = monsters[tier-1]
                title, branch = f'Охота: {monster}', 'Мощь'
                description = f'{lore.capitalize()}: местным жителям угрожает {monster}. Найдите противника в регионе {target}. Земли: {biome}.'
                city = False
                base = tier
            elif index==2:
                title, branch, description = local_title+' · '+target, local_branch, local_description+' Место: '+lore+'.'
                city = self.in_city
                base = 1 + int(self.in_city) + int(self.in_city and REGIONS[target].capital)
            else:
                if self.in_city:
                    title, branch, description = ('Поручение двора' if REGIONS[self.hero.region].capital else 'Заказ городской гильдии'), 'Дипломатия', 'Доставьте документы и согласуйте условия с представителем гильдии.'
                    city = True
                    base = 2+int(REGIONS[self.hero.region].capital)
                else:
                    title, branch, description = 'Пропажа на тракте', 'Хитрость', 'Отыщите потерянные вещи каравана и верните их смотрителю стоянки.'
                    city = False
                    base = 1
                title += ' · '+target
                description += ' Место: '+lore+'.'
            difficulty = min(5, base+(distance+1)//2)
            loot = list(ITEMS)[(self.search_count*5+index)%len(ITEMS)]
            self.offers.append(Quest(f'{self.search_count}-{index}',title,description,difficulty,branch,
                                     self.hero.region,target,city,monster,difficulty*30,difficulty*12,
                                     difficulty*20,loot,distance,tier,self.in_city))
        self.record(f'Поиск заданий: {self.hero.region}, '+('город' if self.in_city else 'регион')+'. Найдено пять поручений.')

    def accept(self, quest_id):
        self.ensure_free()
        if len(self.active) >= 3:
            raise ValueError('Можно взять не больше трёх заданий одновременно.')
        quest = next((q for q in self.offers if q.id == quest_id), None)
        if quest is None or quest.origin != self.hero.region or quest.origin_city != self.in_city:
            raise ValueError('Задание недоступно. Найдите поручения в текущем регионе.')
        self.active.append(quest)
        self.offers.remove(quest)
        self.journal.append(f'Принято задание «{quest.title}».')

    def complete(self, quest_id):
        self.ensure_free()
        quest = next((q for q in self.active if q.id == quest_id), None)
        if quest is None:
            raise ValueError('Активное задание не найдено.')
        if self.hero.region != quest.target:
            raise ValueError(f'Сначала доберитесь в регион {quest.target}.')
        if quest.city and not self.in_city:
            raise ValueError('Для этого поручения нужно войти в город.')
        if quest.monster:
            self.start_battle(quest)
            return
        self.reward(quest, 'Мирное поручение выполнено. ')

    def reward(self, quest, prefix):
        self.xp += quest.xp
        self.hero.gold += quest.gold
        branch = quest.branch
        self.branch_xp[branch] += quest.progress
        while self.hero.branches[branch] < 3 and self.branch_xp[branch] >= 60:
            self.branch_xp[branch] -= 60
            self.hero.branches[branch] += 1
        if self.hero.branches[branch] == 3:
            self.branch_xp[branch] = 0
        if quest.loot not in self.bag:
            self.bag.append(quest.loot)
        self.active.remove(quest)
        self.completed.append(quest.id)
        self.record(prefix + f'«{quest.title}»: +{quest.xp} опыта, +{quest.gold} золота, '
                    f'+{quest.progress} к ветви «{branch}», предмет: {quest.loot}.')

    def abandon(self, quest_id):
        self.ensure_free()
        quest = next((q for q in self.active if q.id == quest_id), None)
        if not quest:
            raise ValueError('Задание не найдено.')
        self.active.remove(quest)
        self.journal.append(f'Отказ от задания «{quest.title}».')

    def equip(self, item):
        self.ensure_free()
        if item not in self.bag or item not in ITEMS:
            raise ValueError('Этого предмета нет в рюкзаке.')
        self.hero.equipment[ITEMS[item][0]] = item
        self.hp = min(self.hp, stats(self.hero)['hp'])

    def unequip(self, slot):
        self.ensure_free()
        if slot not in self.hero.equipment:
            raise ValueError('Неизвестный слот.')
        self.hero.equipment[slot] = None
        self.hp = min(self.hp, stats(self.hero)["hp"])

    def save(self, path=SAVE):
        data = {'version': 3, 'hero': asdict(self.hero), 'turn': self.turn,
                'in_city': self.in_city, 'wars': sorted(self.wars), 'journal': self.journal,
                'xp': self.xp, 'branch_xp': self.branch_xp, 'bag': self.bag,
                'offers': [asdict(q) for q in self.offers], 'active': [asdict(q) for q in self.active],
                'completed': self.completed, 'search_count': self.search_count,
                'hp': self.hp, 'consumables': self.consumables, 'purchases': self.purchases,
                'battle': self.battle}
        path = Path(path)
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        temp.replace(path)

    @classmethod
    def load(cls, path=SAVE):
        # Версия 1 остаётся доступной через старый консольный запуск.
        try:
            data = json.loads(Path(path).read_text(encoding='utf-8'))
            h = data['hero']
            if data['version'] not in (2,3):
                raise ValueError('Неизвестная версия графического сохранения.')
            item = next((x for x in h['equipment'].values() if x), 'Учебный меч')
            game = cls.create(h['name'], h['gender'], h['race'], h['background'], item, h['region'])
            def natural(v):
                return type(v) is int and v >= 0
            if (not natural(data['xp']) or not natural(data['search_count'])
                or not natural(h['gold']) or not natural(data['turn']) or data['turn'] < 1
                or type(data['in_city']) is not bool
                or set(h['branches']) != set(BRANCHES)
                or any(type(x) is not int or not 0 <= x <= 3 for x in h['branches'].values())
                or set(data['branch_xp']) != set(BRANCHES)
                or any(not natural(x) or x >= 60 for x in data['branch_xp'].values())
                or not isinstance(data['bag'], list) or any(x not in ITEMS for x in data['bag'])
                or set(h['equipment']) != {'Оружие', 'Доспех', 'Артефакт'}
                or any(x is not None and (x not in data['bag'] or ITEMS[x][0] != slot)
                       for slot, x in h['equipment'].items())
                or not isinstance(data['journal'], list) or not all(isinstance(x, str) for x in data['journal'])
                or not isinstance(data['completed'], list) or not all(isinstance(x, str) for x in data['completed'])):
                raise ValueError('Некорректное сохранение.')
            for key in ('offers', 'active'):
                quests = [Quest(**q) for q in data[key]]
                for q in quests:
                    if q.monster and q.monster_tier==0:
                        q.monster_tier = monster_tier(q.monster) or next((t for t, names in MONSTERS.items() if q.monster in [n for n,_ in names]), 1)
                for q in quests:
                    if (type(q.difficulty) is not int or not 1 <= q.difficulty <= 5
                        or q.branch not in BRANCHES or q.target not in REGIONS or REGIONS[q.target].blocked
                        or q.origin not in REGIONS or q.loot not in ITEMS or type(q.city) is not bool
                        or any(not natural(x) for x in (q.xp, q.gold, q.progress))
                        or not all(isinstance(x, str) for x in (q.id, q.title, q.description))
                        or type(q.distance) is not int or q.distance<0 or type(q.origin_city) is not bool
                        or type(q.monster_tier) is not int or not 0<=q.monster_tier<=5
                        or (q.monster is not None and (q.monster_tier<1 or
                            (monster_tier(q.monster) is None and not any(q.monster==n for names in MONSTERS.values() for n,_ in names))))):
                        raise ValueError('Некорректное задание.')
                setattr(game, key, quests)
            ids = [q.id for q in game.offers + game.active] + data['completed']
            if len(game.active) > 3 or len(game.offers) > 5 or len(ids) != len(set(ids)):
                raise ValueError('Повторяющиеся задания в сохранении.')
            from eterion import Hero
            game.hero = Hero(**h)
            for key in ('turn', 'in_city', 'journal', 'xp', 'branch_xp', 'bag', 'completed', 'search_count'):
                setattr(game, key, data[key])
            for a, b in data['wars']:
                game.set_relation(a, b, True)
            game.hp = stats(game.hero)['hp']
            if data['version']==3:
                if (not natural(data['hp']) or not 1<=data['hp']<=stats(game.hero)['hp']
                    or not isinstance(data['consumables'],dict) or not isinstance(data['purchases'],dict)
                    or any(k not in CONSUMABLES or not natural(v) or v<1 for k,v in data['consumables'].items())
                    or sum(data['consumables'].values())>15
                    or any(not isinstance(k,str) or not natural(v) or v>3 for k,v in data['purchases'].items())):
                    raise ValueError('Некорректное здоровье или расходуемые карты.')
                for key in ('hp','consumables','purchases','battle'):
                    setattr(game,key,data[key])
                if game.battle is not None and not isinstance(game.battle,dict):
                    raise ValueError('Некорректная дуэль.')
                game.validate_battle()
            return game
        except (KeyError, TypeError, AttributeError) as exc:
            raise ValueError('Повреждённый файл сохранения.') from exc
