"""Правила графического прототипа: задания, развитие и снаряжение."""
from dataclasses import asdict, dataclass
from pathlib import Path
import json
import random

from eterion import Game, ITEMS, REGIONS, BRANCHES
from battle_rules import BattleRules
from world_content import BIOMES, REGION_LORE, monster_tier, CONSUMABLES
from combat import stats
from progression import COSTS, TREES, unlocked
from world_systems import WorldSystems

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

ALIASES = {'Учебный меч':'Железный меч','Посох ученика':'Охотничье копьё'}
AVAILABLE_ITEMS = {k:v for k,v in ITEMS.items() if k not in ALIASES}

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
    method: str = "Поработать"


class Adventure(WorldSystems, BattleRules, Game):
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
        self.init_world()

    @classmethod
    def create(cls,name,gender,race,background,item,region,human_branch='Дипломатия'):
        return super().create(name,gender,race,background,ALIASES.get(item,item),region,human_branch)

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
                cap=min(5,1+self.xp//100+2)
                penalty=min(1,distance//3)
                tier=1 if index==0 else rng.randint(1,max(1,cap-penalty))
                monster = monsters[tier-1]
                title, branch = f'Охота: {monster}', 'Мощь'
                description = f'{lore.capitalize()}: местным жителям угрожает {monster}. Найдите противника в регионе {target}. Земли: {biome}.'
                city = False
                base = tier
            elif index==2:
                title, branch, description = local_title+' · '+target, local_branch, local_description+' Место: '+lore+'.'
                city = self.in_city
                base = 1+int(self.in_city)
            else:
                if self.in_city:
                    title, branch, description = ('Поручение двора' if REGIONS[self.hero.region].capital else 'Заказ городской гильдии'), 'Дипломатия', 'Доставьте документы и согласуйте условия с представителем гильдии.'
                    city = True
                    base = 2
                else:
                    title, branch, description = 'Пропажа на тракте', 'Хитрость', 'Отыщите потерянные вещи каравана и верните их смотрителю стоянки.'
                    city = False
                    base = 1
                title += ' · '+target
                description += ' Место: '+lore+'.'
            cap=min(5,1+self.xp//100+2)
            difficulty=min(cap,base+min(1,distance//(3 if monster else 4)))
            loot=list(AVAILABLE_ITEMS)[(self.search_count*5+index)%len(AVAILABLE_ITEMS)] if monster else None
            xp=20*difficulty if monster else 8+4*difficulty
            gold=8*difficulty if monster else 3+2*difficulty+min(distance,3)
            progress=12*difficulty if monster else 4+2*difficulty
            method='Начать дуэль' if monster else 'Доставить документы' if index in (1,4) and city else 'Осмотреть следы' if branch=='Хитрость' else 'Изучить находки' if branch=='Знания' else 'Провести переговоры'
            self.offers.append(Quest(f'{self.search_count}-{index}',title,description,difficulty,branch,
                                     self.hero.region,target,city,monster,xp,gold,progress,loot,
                                     distance,tier,self.in_city,method))
        self.record(f'Поиск заданий: {self.hero.region}, '+('город' if self.in_city else 'регион')+'. Найдено пять поручений.')
        self.maybe_event('Поиск поручений')

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
        previous_level=self.xp//100
        self.xp+=quest.xp
        self.level_points+=self.xp//100-previous_level
        self.hero.gold+=quest.gold
        self.gain_branch(quest.branch,quest.progress)
        if quest.loot and quest.loot not in self.bag:self.bag.append(quest.loot)
        self.active.remove(quest)
        self.completed.append(quest.id)
        self.repute(REGIONS[quest.target].country,2 if quest.monster else 1,3 if quest.monster else 1)
        self.record(prefix+f'«{quest.title}»: +{quest.xp} опыта, +{quest.gold} золота, +{quest.progress} к ветви «{quest.branch}».'+(f' Предмет: {quest.loot}.' if quest.loot else ''))

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
        data = {'version': 4, 'hero': asdict(self.hero), 'turn': self.turn,
                'in_city': self.in_city, 'wars': sorted(self.wars), 'journal': self.journal,
                'xp': self.xp, 'branch_xp': self.branch_xp, 'bag': self.bag,
                'offers': [asdict(q) for q in self.offers], 'active': [asdict(q) for q in self.active],
                'completed': self.completed, 'search_count': self.search_count,
                'hp': self.hp, 'consumables': self.consumables, 'purchases': self.purchases,
                'battle': self.battle,
                'world': {k:getattr(self,k) for k in ('paths','selected_skills','level_points','reputation','fame','last_fame_event','event','event_serial','last_event_turn','last_event_check','preparation')}}
        path = Path(path)
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        temp.replace(path)

    @classmethod
    def load(cls,path=SAVE):
        try:
            data=json.loads(Path(path).read_text(encoding='utf-8'))
            version=data['version']
            if version not in (2,3,4):raise ValueError('Неизвестная версия сохранения.')
            h=data['hero']
            h['equipment']={k:ALIASES.get(v,v) for k,v in h['equipment'].items()}
            item=next((v for v in h['equipment'].values() if v),'Железный меч')
            game=cls.create(h['name'],h['gender'],h['race'],h['background'],item,h['region'])
            def natural(v):return type(v) is int and v>=0
            if (set(h['branches'])!=set(BRANCHES) or any(type(v) is not int or not 0<=v<=4 for v in h['branches'].values())
                or not natural(h['gold']) or set(h['equipment'])!={'Оружие','Доспех','Артефакт'}
                or not natural(data['xp']) or not natural(data['turn']) or data['turn']<1
                or not natural(data['search_count']) or type(data['in_city']) is not bool
                or set(data['branch_xp'])!=set(BRANCHES) or any(not natural(v) for v in data['branch_xp'].values())
                or not isinstance(data['bag'],list) or any(x not in ITEMS for x in data['bag'])
                or not isinstance(data['journal'],list) or not all(isinstance(x,str) for x in data['journal'])
                or not isinstance(data['completed'],list) or not all(isinstance(x,str) for x in data['completed'])):
                raise ValueError('Некорректное сохранение.')
            from eterion import Hero
            game.hero=Hero(**h)
            for key in ('turn','in_city','journal','xp','branch_xp','completed','search_count'):setattr(game,key,data[key])
            game.bag=list(dict.fromkeys(ALIASES.get(x,x) for x in data['bag']))
            if any(v is not None and (v not in game.bag or ITEMS[v][0]!=slot) for slot,v in h['equipment'].items()):
                raise ValueError('Некорректное снаряжение.')
            for key in ('offers','active'):
                quests=[Quest(**q) for q in data[key]]
                for q in quests:
                    q.loot=ALIASES.get(q.loot,q.loot)
                    if q.monster and q.monster_tier==0:
                        q.monster_tier=monster_tier(q.monster) or next((t for t,names in MONSTERS.items() if q.monster in [n for n,_ in names]),1)
                    if (type(q.difficulty) is not int or not 1<=q.difficulty<=5 or q.branch not in BRANCHES
                        or q.target not in REGIONS or REGIONS[q.target].blocked or q.origin not in REGIONS
                        or (q.loot is not None and q.loot not in AVAILABLE_ITEMS) or type(q.city) is not bool
                        or type(q.origin_city) is not bool or not natural(q.distance)
                        or any(not natural(v) for v in (q.xp,q.gold,q.progress,q.monster_tier))
                        or not all(isinstance(v,str) for v in (q.id,q.title,q.description,q.method))
                        or q.monster_tier>5 or (q.monster is not None and (q.monster_tier<1 or
                           (monster_tier(q.monster) is None and not any(q.monster==n for names in MONSTERS.values() for n,_ in names))))):
                        raise ValueError('Некорректное задание.')
                setattr(game,key,quests)
            ids=[q.id for q in game.offers+game.active]+game.completed
            if len(game.active)>3 or len(game.offers)>5 or len(ids)!=len(set(ids)):raise ValueError('Некорректное число заданий.')
            for a,b in data['wars']:game.set_relation(a,b,True)
            if version==4:
                world=data['world']
                if (set(world['paths'])!=set(BRANCHES) or any(v not in (None,'left','right') for v in world['paths'].values())
                    or not isinstance(world['selected_skills'],list) or len(world['selected_skills'])>3
                    or len(world['selected_skills'])!=len(set(world['selected_skills']))
                    or not natural(world['level_points']) or world['level_points']>game.xp//100):
                    raise ValueError('Некорректное дерево навыков.')
                for field,low,high in [('reputation',-100,100),('fame',0,1000),('last_fame_event',1,game.turn)]:
                    from eterion import COUNTRIES
                    if set(world[field])!=set(COUNTRIES) or any(type(v) is not int or not low<=v<=high for v in world[field].values()):
                        raise ValueError('Некорректная репутация или известность.')
                for key in ('paths','selected_skills','level_points','reputation','fame','last_fame_event','event','event_serial','last_event_turn','last_event_check','preparation'):
                    setattr(game,key,world[key])
                game.sync_skills()
                if any(s not in unlocked(game.hero) for s in game.selected_skills):raise ValueError('Выбран закрытый навык.')
                if any(game.hero.branches[k]>2 and not game.paths[k] for k in BRANCHES):raise ValueError('Не выбран путь ветви.')
            else:
                game.paths={k:'left' if v>2 else None for k,v in game.hero.branches.items()}
                game.sync_skills()
                game.selected_skills=unlocked(game.hero)[:3]
                game.sync_skills()
            game.hp=stats(game.hero)['hp']
            if version>=3:
                if (not natural(data['hp']) or data['hp']<1 or data['hp']>200
                    or not isinstance(data['consumables'],dict) or not isinstance(data['purchases'],dict)
                    or any(k not in CONSUMABLES or not natural(v) or v<1 for k,v in data['consumables'].items())
                    or sum(data['consumables'].values())>15
                    or any(not isinstance(k,str) or not natural(v) or v>3 for k,v in data['purchases'].items())):
                    raise ValueError('Некорректное здоровье или расходуемые карты.')
                game.hp=min(data['hp'],stats(game.hero)['hp'])
                game.consumables=data['consumables'];game.purchases=data['purchases'];game.battle=data['battle']
                if game.battle is not None:
                    if not isinstance(game.battle,dict):raise ValueError('Некорректная дуэль.')
                    if version<4:
                        game.battle['discard'].extend(game.battle['hand'][4:]);game.battle['hand']=game.battle['hand'][:4]
                    game.validate_battle()
            game.validate_world()
            return game
        except (KeyError,TypeError,AttributeError) as exc:
            raise ValueError('Повреждённое сохранение.') from exc
