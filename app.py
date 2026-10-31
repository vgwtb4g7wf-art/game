"""Локальный графический интерфейс Этериона. Запуск: python3 app.py."""
import argparse
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
from urllib.parse import urlsplit

from adventure import Adventure, ITEMS, MONSTERS, SAVE
from combat import CARDS, ITEM_POWER, SKILL_POWER, deck
from world_content import BIOMES, REGION_LORE
from eterion import BACKGROUNDS, BRANCHES, COUNTRIES, RACES, REGIONS, ROUTES

ROOT = Path(__file__).parent / 'web'


def state(game):
    return None if game is None else {
        'hero': asdict(game.hero), 'turn': game.turn, 'in_city': game.in_city,
        'hp': game.hp, 'combat_stats': game.combat_stats(), 'battle': game.battle,
        'last_battle': game.last_battle, 'consumables': game.consumables, 'shop': game.shop(),
        'deck': [dict(card=key, source=source) for key, source in deck(game.hero, game.consumables)],
        'fee': game.entry_fee(), 'xp': game.xp, 'level': 1 + game.xp // 100,
        'branch_xp': game.branch_xp, 'bag': game.bag,
        'offers': [asdict(q) for q in game.offers if q.origin == game.hero.region and q.origin_city == game.in_city],
        'active': [asdict(q) for q in game.active], 'completed': len(game.completed),
        'journal': game.journal[-60:], 'wars': sorted(game.wars),
        'neighbors': [{'name': r, 'kind': k, 'error': game.travel_error(r)} for r, k in game.neighbors()]}


class Handler(BaseHTTPRequestHandler):
    def respond(self, body, status=200, mime='application/json; charset=utf-8'):
        raw = body.encode('utf-8') if isinstance(body, str) else body
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(raw)

    def json(self, data, status=200):
        self.respond(json.dumps(data, ensure_ascii=False), status)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == '/api/state':
            self.json({'game': state(self.server.game)})
        elif path == '/api/catalog':
            self.json({'races': RACES, 'backgrounds': BACKGROUNDS, 'branches': BRANCHES,
                       'items': ITEMS, 'regions': {n: asdict(r) for n, r in REGIONS.items()},
                       'routes': ROUTES, 'monsters': MONSTERS, 'countries': COUNTRIES,
                       'cards': CARDS, 'item_power': ITEM_POWER, 'skill_power': SKILL_POWER,
                       'biomes': BIOMES, 'region_lore': REGION_LORE})
        elif path in ('/', '/style.css', '/game.js'):
            name = 'index.html' if path == '/' else path[1:]
            mime = {'index.html': 'text/html', 'style.css': 'text/css', 'game.js': 'text/javascript'}[name]
            self.respond((ROOT / name).read_bytes(), mime=mime + '; charset=utf-8')
        else:
            self.json({'error': 'Страница не найдена.'}, 404)

    def do_POST(self):
        origin = self.headers.get('Origin')
        if origin and origin != 'http://' + self.headers.get('Host', ''):
            self.json({'error': 'Запрос должен исходить из окна игры.'}, 403)
            return
        try:
            if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                raise ValueError('Ожидается JSON.')
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 16384:
                raise ValueError('Некорректный размер запроса.')
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError('Ожидается объект запроса.')
            action = data.get('action')
            game = self.server.game
            if game is not None and game.battle is not None and action not in ('play','end_round','flee','save','load'):
                raise ValueError('Сначала завершите дуэль или отступите.')
            if action == 'create':
                self.server.game = Adventure.create(**data['hero'])
            elif action == 'load':
                self.server.game = Adventure.load(self.server.save_path)
            elif game is None:
                raise ValueError('Сначала создайте или загрузите героя.')
            elif action == 'save':
                game.save(self.server.save_path)
            elif action == 'move':
                game.move(data['target'])
            elif action == 'enter':
                game.enter_city()
            elif action == 'leave':
                game.leave_city()
            elif action == 'wait':
                game.wait()
            elif action == 'search':
                game.search()
            elif action in ('accept', 'complete', 'abandon'):
                getattr(game, action)(data['id'])
            elif action == 'buy':
                game.buy(data['card'])
            elif action == 'play':
                game.play_card(data['index'])
            elif action == 'end_round':
                game.end_round()
            elif action == 'flee':
                game.flee()
            elif action == 'equip':
                game.equip(data['item'])
            elif action == 'unequip':
                game.unequip(data['slot'])
            elif action == 'relation':
                if type(data['war']) is not bool:
                    raise ValueError('Некорректное отношение.')
                game.set_relation(data['first'], data['second'], data['war'])
            else:
                raise ValueError('Неизвестное действие.')
            self.json({'game': state(self.server.game)})
        except (ValueError, TypeError, KeyError, OSError) as exc:
            self.json({'error': 'Сохранение не найдено.' if isinstance(exc, FileNotFoundError) else str(exc)}, 400)


def make_server(port=8000, save_path=SAVE):
    server = HTTPServer(('127.0.0.1', port), Handler)
    server.game = None
    server.save_path = Path(save_path)
    return server


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Этерион — локальная игра в браузере')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    with make_server(args.port) as server:
        print(f'Этерион запущен. Откройте в браузере http://127.0.0.1:{server.server_port}')
        print('Для остановки нажмите Ctrl+C. Сохраняйте игру кнопкой в интерфейсе.')
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print('\nИгра остановлена.')
