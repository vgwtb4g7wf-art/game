"""Этерион — пошаговая RPG. Python 3.10+, без внешних зависимостей."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

BRANCHES = {
    'Мощь': ('Закалка', 'Владение оружием', 'Несокрушимость'),
    'Знания': ('Грамотность', 'Тайные науки', 'Мудрость'),
    'Хитрость': ('Наблюдательность', 'Скрытность', 'Ловкость рук'),
    'Дипломатия': ('Этикет', 'Красноречие', 'Влияние'),
}
RACES = ('Человек', 'Дварф', 'Высший эльф', 'Лесной эльф')
RACE_BRANCH = {'Дварф': 'Мощь', 'Высший эльф': 'Знания', 'Лесной эльф': 'Хитрость'}
BACKGROUNDS = {
    'Прислуга': ('Знания', 25), 'Оруженосец': ('Мощь', 15),
    'Воришка': ('Хитрость', 20), 'Торговец': ('Дипломатия', 40),
}
ITEMS = {
    'Учебный меч': ('Оружие', 'Надёжное оружие начинающего путешественника.'),
    'Дорожный лук': ('Оружие', 'Лёгкий лук лесных следопытов.'),
    'Посох ученика': ('Оружие', 'Посох для изучения тайных искусств.'),
    'Кожаная куртка': ('Доспех', 'Лёгкая защита для дороги.'),
    'Стёганый доспех': ('Доспех', 'Прочная защита оруженосца.'),
    'Медный оберег': ('Артефакт', 'Памятный талисман странника.'),
    'Компас морехода': ('Артефакт', 'Старинный компас для морских путешествий.'),
}


@dataclass(frozen=True)
class Region:
    country: str
    capital: bool = False
    blocked: bool = False


REGIONS = {
    'Бронзовый Пик': Region('Дваллинхорг', True),
    'Храм Камня': Region('Дваллинхорг'),
    'Бреннор': Region('Княжество Бреннор', True),
    'Глыба': Region('Княжество Бреннор'),
    'Келебран': Region('Азалтир'),
    'Азалтир': Region('Азалтир', True),
    'Таллас': Region('Лесное царство Талласа', True),
    'Эланиэль': Region('Лесное царство Талласа'),
    'Тротенфор': Region('Тротенфорская империя', True),
    'Марктбург': Region('Тротенфорская империя'),
    'Штальбург': Region('Тротенфорская империя'),
    'Мерилион': Region('Королевство Алдория'),
    'Алдория': Region('Королевство Алдория', True),
    'Трущобы': Region('Аграмор'),
    'Аграмор': Region('Аграмор', True, True),
    'Нархаз': Region('Владычество Нархаз', True, True),
}
# Рёбра неориентированные. Тип маршрута описывает путь, а не отдельный ход.
ROUTES = (
    ('Бронзовый Пик', 'Храм Камня', 'суша'),
    ('Бронзовый Пик', 'Бреннор', 'суша'),
    ('Бронзовый Пик', 'Келебран', 'море'),
    ('Храм Камня', 'Азалтир', 'море'),
    ('Храм Камня', 'Мерилион', 'море'),
    ('Бреннор', 'Глыба', 'суша'),
    ('Глыба', 'Келебран', 'море'),
    ('Келебран', 'Азалтир', 'море'),
    ('Глыба', 'Азалтир', 'море'),
    ('Глыба', 'Таллас', 'суша'),
    ('Глыба', 'Тротенфор', 'суша'),
    ('Азалтир', 'Мерилион', 'море'),
    ('Азалтир', 'Марктбург', 'море'),
    ('Мерилион', 'Алдория', 'суша'),
    ('Алдория', 'Марктбург', 'суша'),
    ('Марктбург', 'Тротенфор', 'суша'),
    ('Марктбург', 'Штальбург', 'суша'),
    ('Тротенфор', 'Штальбург', 'суша'),
    ('Тротенфор', 'Таллас', 'суша'),
    ('Таллас', 'Эланиэль', 'суша'),
    ('Эланиэль', 'Штальбург', 'суша'),
    ('Эланиэль', 'Трущобы', 'суша'),
    ('Штальбург', 'Трущобы', 'суша'),
    ('Трущобы', 'Аграмор', 'суша'),
)
COUNTRIES = tuple(dict.fromkeys(r.country for r in REGIONS.values()))
SAVE_PATH = Path(__file__).parent / 'savegame.json'


@dataclass
class Hero:
    name: str
    gender: str
    race: str
    background: str
    branches: dict[str, int]
    equipment: dict[str, str | None]
    gold: int
    region: str


class Game:
    def __init__(self, hero: Hero):
        self.hero = hero
        self.turn = 1
        self.in_city = False
        self.wars: set[tuple[str, str]] = set()
        self.journal: list[str] = ['Путешествие начинается.']

    @classmethod
    def create(cls, name, gender, race, background, item, region, human_branch='Дипломатия'):
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 40:
            raise ValueError('Имя должно содержать от 1 до 40 символов.')
        if not isinstance(gender, str) or not gender.strip():
            raise ValueError('Укажите пол героя.')
        if race not in RACES or background not in BACKGROUNDS or item not in ITEMS:
            raise ValueError('Неизвестная раса, предыстория или предмет.')
        if region not in REGIONS or REGIONS[region].blocked:
            raise ValueError('Этот стартовый регион недоступен.')
        if human_branch not in BRANCHES:
            raise ValueError('Неизвестная ветвь.')
        branches = dict.fromkeys(BRANCHES, 0)
        branches[human_branch if race == 'Человек' else RACE_BRANCH[race]] += 1
        branch, gold = BACKGROUNDS[background]
        branches[branch] += 1
        equipment = dict.fromkeys(('Оружие', 'Доспех', 'Артефакт'))
        equipment[ITEMS[item][0]] = item
        return cls(Hero(name.strip(), gender.strip(), race, background, branches, equipment, gold, region))

    def record(self, message):
        self.journal.append(f'Ход {self.turn}: {message}')
        self.turn += 1

    def neighbors(self):
        return [(b if a == self.hero.region else a, kind)
                for a, b, kind in ROUTES if self.hero.region in (a, b)]

    def travel_error(self, destination):
        if destination not in dict(self.neighbors()):
            return 'За ход можно перейти только в соседний регион.'
        if REGIONS[destination].blocked:
            return 'Регион закрыт для путешественников.'
        countries = tuple(sorted((REGIONS[self.hero.region].country, REGIONS[destination].country)))
        if countries in self.wars:
            return 'Граница закрыта: страны находятся в состоянии войны.'
        return None

    def move(self, destination):
        error = self.travel_error(destination)
        if error:
            raise ValueError(error)
        source = self.hero.region
        self.hero.region = destination
        self.in_city = False
        self.record(f'Переход: {source} → {destination}. Вы находитесь за городскими воротами.')

    def entry_fee(self):
        return 10 if REGIONS[self.hero.region].capital else 5

    def enter_city(self):
        if self.in_city:
            raise ValueError('Вы уже в городе.')
        fee = self.entry_fee()
        if self.hero.gold < fee:
            raise ValueError(f'Недостаточно золота. Вход стоит {fee}.')
        self.hero.gold -= fee
        self.in_city = True
        self.record(f'Вход в город {self.hero.region}: уплачено {fee} золота.')

    def leave_city(self):
        if not self.in_city:
            raise ValueError('Вы уже за городом.')
        self.in_city = False
        self.record('Выход за городские ворота.')

    def wait(self):
        self.record('Отдых. В мире проходит ещё один ход.')

    def set_relation(self, first, second, war):
        if first not in COUNTRIES or second not in COUNTRIES or first == second:
            raise ValueError('Выберите две разные страны.')
        pair = tuple(sorted((first, second)))
        if war:
            self.wars.add(pair)
        else:
            self.wars.discard(pair)

    def save(self, path=SAVE_PATH):
        path = Path(path)
        data = {'version': 1, 'hero': asdict(self.hero), 'turn': self.turn,
                'in_city': self.in_city, 'wars': sorted(self.wars), 'journal': self.journal}
        temporary = path.with_suffix(path.suffix + '.tmp')
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        temporary.replace(path)

    @classmethod
    def load(cls, path=SAVE_PATH):
        try:
            data = json.loads(Path(path).read_text(encoding='utf-8'))
            if data['version'] != 1:
                raise ValueError('Неизвестная версия сохранения.')
            h = data['hero']
            game = cls.create(h['name'], h['gender'], h['race'], h['background'],
                              next(item for item in h['equipment'].values() if item), h['region'])
            if (set(h['branches']) != set(BRANCHES)
                    or any(type(v) is not int or not 0 <= v <= 3 for v in h['branches'].values())
                    or type(h['gold']) is not int or h['gold'] < 0
                    or set(h['equipment']) != {'Оружие', 'Доспех', 'Артефакт'}
                    or any(v is not None and (v not in ITEMS or ITEMS[v][0] != k)
                           for k, v in h['equipment'].items())
                    or type(data['turn']) is not int or data['turn'] < 1
                    or type(data['in_city']) is not bool
                    or not isinstance(data['journal'], list)
                    or not all(isinstance(x, str) for x in data['journal'])):
                raise ValueError('Некорректные данные героя.')
            game.hero = Hero(**h)
            game.turn, game.in_city, game.journal = data['turn'], data['in_city'], data['journal']
            for a, b in data['wars']:
                game.set_relation(a, b, True)
            return game
        except (KeyError, TypeError, StopIteration, json.JSONDecodeError) as exc:
            raise ValueError('Повреждённый файл сохранения.') from exc


def choose(title, options):
    options = list(options)
    print('\n' + title)
    for i, option in enumerate(options, 1):
        print(f'  {i}. {option}')
    while True:
        answer = input('> ').strip()
        if answer.isdecimal() and 1 <= int(answer) <= len(options):
            return options[int(answer) - 1]
        print('Введите номер варианта.')


def new_game():
    name = input('Имя героя: ').strip()
    while not name or len(name) > 40:
        name = input('Введите имя (1–40 символов): ').strip()
    gender = choose('Пол героя', ['Мужской', 'Женский', 'Другой'])
    race = choose('Раса: человек — любая ветвь; дварф — мощь; высший эльф — знания; лесной — хитрость', RACES)
    branch = choose('Расовый бонус: выберите ветвь', BRANCHES) if race == 'Человек' else 'Дипломатия'
    descriptions = {f'{k} (+{v[0]}, {v[1]} золота)': k for k, v in BACKGROUNDS.items()}
    background = descriptions[choose('Предыстория', descriptions)]
    descriptions = {f'{k} [{v[0]}] — {v[1]}': k for k, v in ITEMS.items()}
    item = descriptions[choose('Один стартовый предмет; остальные слоты пусты', descriptions)]
    region = choose('Стартовый регион (снаружи города)', [r for r, v in REGIONS.items() if not v.blocked])
    return Game.create(name, gender, race, background, item, region, branch)


def show_hero(game):
    h = game.hero
    print(f'\n{h.name} • {h.gender} • {h.race} • {h.background}')
    print(f'Золото: {h.gold}. Класса нет; открытые ступени ветвей:')
    for branch, level in h.branches.items():
        print(f'  {branch}: ' + (' → '.join(BRANCHES[branch][:level]) or 'не открыта'))
    for slot, item in h.equipment.items():
        print(f'  {slot}: {item or "пусто"}')


def main():
    print('\nЭ Т Е Р И О Н\nПервое путешествие • прототип 0.1')
    game = None
    while game is None:
        action = choose('Начать', ['Новый герой', 'Загрузить', 'Выход'])
        if action == 'Выход':
            return
        try:
            game = new_game() if action == 'Новый герой' else Game.load()
        except (OSError, ValueError) as exc:
            print(f'Не удалось загрузить: {exc}')
    while True:
        h = game.hero
        print(f'\n── Ход {game.turn} • {h.region} • {REGIONS[h.region].country} ──')
        print(f'{"В городе" if game.in_city else "За городом"} | Золото: {h.gold}')
        action = choose('Действие', ['Путешествовать', 'Войти в город', 'Выйти из города',
                                    'Отдыхать', 'Герой', 'Карта и пути', 'Отношения стран',
                                    'Журнал', 'Сохранить', 'Сохранить и выйти'])
        try:
            if action == 'Путешествовать':
                routes = {f'{r} ({kind})' + (f' — {game.travel_error(r)}' if game.travel_error(r) else ''): r
                          for r, kind in game.neighbors()}
                selected = choose('Соседние регионы', [*routes, 'Отмена'])
                if selected != 'Отмена':
                    game.move(routes[selected])
            elif action == 'Войти в город':
                print(f'Плата за вход: {game.entry_fee()} золота.')
                if choose('Оплатить вход?', ['Да', 'Отмена']) == 'Да':
                    game.enter_city()
            elif action == 'Выйти из города':
                game.leave_city()
            elif action == 'Отдыхать':
                game.wait()
            elif action == 'Герой':
                show_hero(game)
            elif action == 'Карта и пути':
                for a, b, kind in ROUTES:
                    print(f'{a} ↔ {b} [{kind}]')
                print('Аграмор и Нархаз закрыты. Нархаз не имеет доступных маршрутов.')
            elif action == 'Отношения стран':
                print('Все страны в мире, кроме перечисленных пар:')
                for a, b in sorted(game.wars):
                    print(f'  {a} ⚔ {b}')
                if choose('Настройка сценария (бесплатно, не способность героя)', ['Назад', 'Изменить отношения']) != 'Назад':
                    a = choose('Первая страна', COUNTRIES)
                    b = choose('Вторая страна', [c for c in COUNTRIES if c != a])
                    game.set_relation(a, b, choose('Отношения', ['Мир', 'Война']) == 'Война')
            elif action == 'Журнал':
                print('\n'.join(game.journal[-20:]))
            elif action in ('Сохранить', 'Сохранить и выйти'):
                game.save()
                print('Игра сохранена.')
                if action == 'Сохранить и выйти':
                    return
        except (ValueError, OSError) as exc:
            print(f'Действие не выполнено: {exc}')


if __name__ == '__main__':
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        print('\nИгра закрыта. Сохранение выполняется через меню.')
