"""Правила графического прототипа: задания, развитие и снаряжение."""
from dataclasses import asdict, dataclass
from balance_rewards import hunt_reward
from origins import ORIGINS,RACE_GOLD
from pathlib import Path
import json
import random

from eterion import Game, ITEMS, REGIONS, BRANCHES
from battle_rules import BattleRules
from world_content import BIOMES, REGION_LORE, monster_tier, CONSUMABLES
from bestiary import hunting_pool,GUARDS
from social_rules import GEAR_PRICES
from combat import stats,selectable,SKILL_POWER,deck
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

ITEMS['Медный амулет']=('Артефакт','Простой медный амулет с тёплым камнем.')
ALIASES = {
 'Учебный меч':'Железный меч','Боевой топор':'Железный меч','Охотничье копьё':'Железный меч',
 'Посох ученика':'Железный меч','Арбалет':'Дорожный лук',
 'Стёганый доспех':'Кожаная куртка','Латный нагрудник':'Кольчуга',
 'Мантия учёного':'Кожаная куртка','Плащ следопыта':'Кожаная куртка',
 'Медный оберег':'Медный амулет','Компас морехода':'Медный амулет',
 'Лунный камень':'Медный амулет','Рунная монета':'Медный амулет','Печать посланника':'Кольцо янтаря',
}
AVAILABLE_ITEMS={k:ITEMS[k] for k in ('Железный меч','Короткий кинжал','Дорожный лук',
                                    'Кожаная куртка','Кольчуга','Кольцо янтаря','Медный амулет')}
import trade  # Регистрирует товары чёрного рынка.
AVATARS=('✦','♜','⚒','❧','☾','☀','♞','⚓','✺','♠')

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
    tracking: int = 0
    template: str = ""
    stage: int = 0
    due_turn: int = 0


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
    def create(cls,name,gender,race,background,item,region,human_branch='Дипломатия',avatar='✦'):
        if avatar not in AVATARS:raise ValueError('Выберите один из десяти значков героя.')
        if gender not in ('Мужской','Женский'):raise ValueError('Выберите мужской или женский пол.')
        from eterion import RACE_BRANCH
        hero=Game.create(name,gender,race,background,ALIASES.get(item,item),region,human_branch).hero
        hero.branches=dict.fromkeys(BRANCHES,0)
        origin=ORIGINS[background]
        hero.gold=origin['gold']+(RACE_GOLD if race=='Высший эльф' else 0)
        game=cls(hero);game.avatar=avatar
        game.gain_branch(origin['branch'],origin['xp'])
        game.consumables[origin['consumable']]=1
        game.consumable_costs[origin['consumable']]=[CONSUMABLES[origin['consumable']]['price']]
        if race=='Человек':game.gain_branch(human_branch,40)
        game.hp=game.combat_stats()['hp']
        return game

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
        for index in range(self.offer_limit()):
            target = self.hero.region if index in (0,1) or not other else rng.choice(other)
            distance = distances[target]
            country = REGIONS[target].country
            biome, monsters, local_title, local_branch, local_description = BIOMES[country]
            lore = REGION_LORE[target]
            monster = None
            tier = 0
            if index==0 or (index==2 and self.search_count%2==0) or (index>=3 and index==self.offer_limit()-1):
                cap=min(5,1+self.xp//100+2,self.combat_rating()['tier'])
                penalty=0
                tier=1 if index==0 and self.xp<100 else rng.randint(1,max(1,cap-penalty))
                monster = rng.choice(hunting_pool(country,tier))
                tracking = self.search_count%3==0 if index==0 else rng.choice((True,False))
                title, branch = f'{"Выслеживание" if tracking else "Охота"}: {monster}', 'Хитрость' if tracking else 'Мощь'
                description = f'{lore.capitalize()}: местным жителям угрожает {monster}. Найдите противника в регионе {target}. Земли: {biome}.'
                city = False
                base = tier
            elif index==1:
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
            difficulty=min(cap,base)
            loot=None
            reward=hunt_reward(difficulty)
            xp=reward['xp'] if monster else 8+4*difficulty
            travel_bonus=0 if distance==0 else 1 if distance<=2 else 2 if distance<=5 else 3
            gold=(reward['gold'] if monster else 3+2*difficulty)+travel_bonus
            progress=reward['progress'] if monster else 4+2*difficulty
            method='Начать дуэль' if monster else 'Доставить документы' if index in (1,4) and city else 'Осмотреть следы' if branch=='Хитрость' else 'Изучить находки' if branch=='Знания' else 'Провести переговоры'
            self.offers.append(Quest(f'{self.search_count}-{index}',title,description,difficulty,branch,
                                     self.hero.region,target,city,monster,xp,gold,progress,loot,
                                     distance,tier,self.in_city,'Выследить противника' if monster and tracking else method,1 if monster and tracking else 0))
        from narrative_content import PEACE_QUESTS
        pool=list(PEACE_QUESTS)
        for i,q in enumerate(self.offers):
            if not q.monster:
                key=pool[(self.search_count*7+i*19)%len(pool)]
                t=PEACE_QUESTS[key]
                target=rng.choice(other) if t['delivery'] and other else q.target
                self.offers[i]=self.make_peace_quest(key,target,q.id)
        self.record(f'Поиск заданий: {self.hero.region}, '+('город' if self.in_city else 'регион')+f'. Найдено {self.offer_limit()} поручений.')
        self.maybe_event('Поиск поручений')

    def accept(self, quest_id):
        self.ensure_free()
        if len(self.active) >= self.quest_limit():
            raise ValueError(f'Можно принять не больше {self.quest_limit()} заданий.')
        quest = next((q for q in self.offers if q.id == quest_id), None)
        if quest is None or quest.origin != self.hero.region or quest.origin_city != self.in_city:
            raise ValueError('Задание недоступно. Найдите поручения в текущем регионе.')
        if quest.due_turn and self.turn>=quest.due_turn:raise ValueError('Срок этого предложения уже истёк.')
        if not quest.due_turn:quest.due_turn=self.turn+8+min(2,quest.distance//2)
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
            if quest.tracking:
                quest.tracking-=1
                quest.method='Начать дуэль'
                self.record(f'След найден: {quest.monster}. Теперь можно начать дуэль.')
                return
            self.start_battle(quest)
            return
        if quest.template:
            self.open_dialogue(quest);return
        self.reward(quest, 'Мирное поручение выполнено. ')

    def reward(self, quest, prefix):
        previous_level=self.xp//100
        self.xp+=quest.xp
        self.level_points+=self.xp//100-previous_level
        self.stat_points+=(self.xp//100)//2-previous_level//2
        if self.xp//100>previous_level:self.level_notice=1+self.xp//100
        self.hero.gold+=quest.gold
        self.gain_branch(quest.branch,quest.progress)
        # Снаряжение приобретается только в магазине; старые награды предметами тоже не выдаются.
        self.active.remove(quest)
        self.completed.append(quest.id)
        self.repute(REGIONS[quest.target].country,2 if quest.monster else 1,3 if quest.monster else 1)
        self.record(prefix+f'«{quest.title}»: +{quest.xp} опыта, +{quest.gold} золота, +{quest.progress} к ветви «{quest.branch}».')

    def abandon(self, quest_id):
        self.ensure_free()
        quest = next((q for q in self.active if q.id == quest_id), None)
        if not quest:
            raise ValueError('Задание не найдено.')
        self.active.remove(quest)
        if quest.origin==self.hero.region and quest.origin_city==self.in_city and len(self.offers)<self.offer_limit():
            self.offers.append(quest)
        self.journal.append(f'Отказ от задания «{quest.title}».')

    def equip(self, item):
        self.ensure_free()
        if item not in self.bag or item not in GEAR_PRICES:
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
        data = {'version': 13, 'hero': asdict(self.hero), 'turn': self.turn,
                'in_city': self.in_city, 'wars': sorted(self.wars), 'journal': self.journal,
                'xp': self.xp, 'branch_xp': self.branch_xp, 'bag': self.bag,
                'offers': [asdict(q) for q in self.offers], 'active': [asdict(q) for q in self.active],
                'completed': self.completed, 'search_count': self.search_count,
                'hp': self.hp, 'consumables': self.consumables, 'purchases': self.purchases,
                'battle': self.battle,
                'world': {k:getattr(self,k) for k in ('paths','selected_skills','level_points','reputation','fame','last_fame_event','event','event_serial','last_event_turn','last_event_check','preparation','avatar','level_notice','skill_notices','dead','failed','applied_grants','stat_points','stat_hp','stat_damage','relations','auto_diplomacy','diplomacy_step','border_checks','attitudes','seen_events','item_costs','consumable_costs')}}
        path = Path(path)
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        temp.replace(path)

    @classmethod
    def load(cls,path=SAVE):
        try:
            data=json.loads(Path(path).read_text(encoding='utf-8'))
            version=data['version']
            if version not in (2,3,4,5,6,7,8,9,10,11,12,13):raise ValueError('Неизвестная версия сохранения.')
            h=data['hero']
            if version<7 and h['gender'] not in ('Мужской','Женский'):h['gender']='Мужской'
            h['equipment']={k:ALIASES.get(v,v) for k,v in h['equipment'].items()}
            item=next((v for v in h['equipment'].values() if v),'Железный меч')
            game=cls.create(h['name'],h['gender'],h['race'],h['background'],item,h['region'])
            def natural(v):return type(v) is int and v>=0
            if (set(h['branches'])!=set(BRANCHES) or any(type(v) is not int or not 0<=v<=6 for v in h['branches'].values())
                or not natural(h['gold']) or set(h['equipment'])!={'Оружие','Доспех','Артефакт'}
                or not natural(data['xp']) or not natural(data['turn']) or data['turn']<1
                or not natural(data['search_count']) or type(data['in_city']) is not bool
                or set(data['branch_xp'])!=set(BRANCHES) or any(not natural(v) for v in data['branch_xp'].values())
                or not isinstance(data['bag'],list) or any(x not in ITEMS for x in data['bag'])
                or not isinstance(data['journal'],list) or not all(isinstance(x,str) for x in data['journal'])
                or not isinstance(data['completed'],list) or not all(isinstance(x,str) for x in data['completed'])):
                raise ValueError('Некорректное сохранение.')
            if version<6:h['branches']={k:(v+1 if v>=3 else v) for k,v in h['branches'].items()}
            from eterion import Hero
            game.hero=Hero(**h)
            game.skill_notices=[]
            game.consumables={};game.consumable_costs={}
            for key in ('turn','in_city','journal','xp','branch_xp','completed','search_count'):setattr(game,key,data[key])
            game.bag=list(dict.fromkeys(ALIASES.get(x,x) for x in data['bag']))
            if any(v is not None and (v not in game.bag or ITEMS[v][0]!=slot) for slot,v in h['equipment'].items()):
                raise ValueError('Некорректное снаряжение.')
            for key in ('offers','active'):
                quests=[Quest(**q) for q in data[key]]
                for q in quests:
                    q.loot=None
                    if version<9 and q.monster and monster_tier(q.monster):
                        q.monster_tier=monster_tier(q.monster);q.difficulty=q.monster_tier
                    if q.monster and q.monster_tier==0:
                        q.monster_tier=monster_tier(q.monster) or next((t for t,names in MONSTERS.items() if q.monster in [n for n,_ in names]),1)
                    if (type(q.difficulty) is not int or not 1<=q.difficulty<=5 or q.branch not in BRANCHES
                        or q.target not in REGIONS or REGIONS[q.target].blocked or q.origin not in REGIONS
                        or (q.loot is not None and q.loot not in AVAILABLE_ITEMS) or type(q.city) is not bool
                        or type(q.origin_city) is not bool or not natural(q.distance)
                        or any(not natural(v) for v in (q.xp,q.gold,q.progress,q.monster_tier))
                        or not all(isinstance(v,str) for v in (q.id,q.title,q.description,q.method))
                        or type(q.tracking) is not int or not 0<=q.tracking<=1 or (q.tracking and not q.monster)
                        or type(q.due_turn) is not int or q.due_turn<0
                        or type(q.stage) is not int or q.stage not in (0,1) or (q.template and q.template not in __import__('narrative_content').PEACE_QUESTS)
                        or (q.monster and monster_tier(q.monster) is not None and q.monster_tier!=monster_tier(q.monster))
                        or q.monster_tier>5 or (q.monster is not None and (q.monster_tier<1 or
                           (monster_tier(q.monster) is None and not any(q.monster==n for names in MONSTERS.values() for n,_ in names))))):
                        raise ValueError('Некорректное задание.')
                setattr(game,key,quests)
            ids=[q.id for q in game.offers+game.active]+game.completed
            if len(game.active)>3 or len(game.offers)>6 or len(ids)!=len(set(ids)):raise ValueError('Некорректное число заданий.')
            from diplomacy import NEIGHBOR_PAIRS
            for a,b in data['wars']:
                pair=tuple(sorted((a,b)))
                if version<7 and (pair not in NEIGHBOR_PAIRS or any(game.war_count(c)>=2 for c in pair)):continue
                game.set_relation(a,b,True)
            if version>=4:
                world=data['world']
                if version<8:
                    from progression import LEGACY_SKILLS
                    world=dict(world)
                    for key in ('selected_skills','skill_notices'):
                        if key in world:world[key]=[LEGACY_SKILLS.get(n,n) for n in world[key]]
                if (set(world['paths'])!=set(BRANCHES) or any(v not in (None,'left','right') for v in world['paths'].values())
                    or not isinstance(world['selected_skills'],list) or len(world['selected_skills'])>3
                    or len(world['selected_skills'])!=len(set(world['selected_skills']))
                    or not natural(world['level_points']) or world['level_points']>game.xp//100):
                    raise ValueError('Некорректное дерево навыков.')
                if version<7:
                    world=dict(world)
                    if isinstance(world['reputation'],dict):world['reputation']=round(sum(world['reputation'].values())/len(world['reputation']))
                    if isinstance(world['fame'],dict):world['fame']=max(world['fame'].values(),default=0)
                    if isinstance(world['last_fame_event'],dict):world['last_fame_event']=max(world['last_fame_event'].values(),default=game.turn)
                for key in ('paths','selected_skills','level_points','reputation','fame','last_fame_event','event','event_serial','last_event_turn','last_event_check','preparation'):
                    setattr(game,key,world[key])
                if version>=5:
                    game.avatar=world['avatar'];game.level_notice=world['level_notice'];game.skill_notices=world['skill_notices']
                game.sync_skills()
                if version<6:
                    game.selected_skills=selectable(game.hero)[:3]
                    game.skill_notices=[]
                    game.sync_skills()
                if any(s not in selectable(game.hero) for s in game.selected_skills):raise ValueError('Выбран закрытый навык-карта.')
                if any(game.hero.branches[k]>3 and not game.paths[k] for k in BRANCHES):raise ValueError('Не выбран путь ветви.')
            else:
                game.paths={k:'left' if v>2 else None for k,v in game.hero.branches.items()}
                game.sync_skills()
                game.selected_skills=selectable(game.hero)[:3]
                game.sync_skills()
            if version>=6:
                for field in ('dead','failed','applied_grants'):setattr(game,field,data['world'][field])
            else:
                game.applied_grants=[n for n in unlocked(game.hero) if SKILL_POWER[n]['grant']]
            if version>=7:
                for key in ('stat_points','stat_hp','stat_damage','relations','auto_diplomacy','diplomacy_step'):setattr(game,key,data['world'][key])
            else:game.stat_points=(game.xp//100)//2
            if version>=9:game.border_checks=data['world']['border_checks']
            if version>=11:
                game.attitudes=data['world']['attitudes'];game.seen_events=data['world']['seen_events']
            else:game.attitudes={c:max(-100,min(100,game.reputation)) for c in game.attitudes}
            game.sync_skills()
            game.hp=stats(game.hero)['hp']
            if version>=3:
                if (not natural(data['hp']) or data['hp']<(0 if version>=6 and game.dead else 1) or data['hp']>200
                    or not isinstance(data['consumables'],dict) or not isinstance(data['purchases'],dict)
                    or any(k not in CONSUMABLES or not natural(v) or v<1 for k,v in data['consumables'].items())
                    or sum(data['consumables'].values())>15
                    or any(not isinstance(k,str) or not natural(v) or v>3 for k,v in data['purchases'].items())):
                    raise ValueError('Некорректное здоровье или расходуемые карты.')
                game.hp=min(data['hp'],stats(game.hero)['hp'])
                game.consumables=data['consumables'];game.purchases=data['purchases'];game.battle=data['battle']
                if game.battle is not None:
                    if not isinstance(game.battle,dict):raise ValueError('Некорректная дуэль.')
                    if version<10:
                        old=game.battle
                        game.battle=None
                        game.preparation={k:old.get(k) for k in ('kind','target','quest_id')}
                        game.preparation['kind']=old.get('kind','quest')
                        enemy=old['enemy']
                        if game.preparation['kind']=='border':
                            enemy=GUARDS[REGIONS[old['target']].country][0]
                        game.preparation.update(enemy=enemy,tier=monster_tier(enemy) or old['tier'])
                        game.begin_battle({})
                    game.validate_battle()
            if version<9 and game.preparation:
                p=game.preparation
                if p['kind']=='border':p.update(enemy=GUARDS[REGIONS[p['target']].country][0],tier=3)
                else:p['tier']=monster_tier(p['enemy']) or p['tier']
            if version>=12:
                game.item_costs=data['world']['item_costs'];game.consumable_costs=data['world']['consumable_costs']
            else:
                game.item_costs={n:GEAR_PRICES[n] for n in game.bag}
                game.consumable_costs={k:[CONSUMABLES[k]['price']]*v for k,v in game.consumables.items()}
            if version<13:
                for q in game.active:q.due_turn=game.turn+8+min(2,q.distance//2)
            game.expire_quests()
            game.validate_world()
            return game
        except (KeyError,TypeError,AttributeError) as exc:
            raise ValueError('Повреждённое сохранение.') from exc
