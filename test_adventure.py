import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from adventure import Adventure, ITEMS, MONSTERS
from app import make_server
from combat import CARDS


def create():
    return Adventure.create('Эрин', 'Женский', 'Человек', 'Торговец', 'Учебный меч', 'Глыба', 'Знания')


def resolve(game):
    for _ in range(100):
        if game.battle is None:
            return
        hand = game.battle['hand']
        options = [(i, CARDS[key]) for i,key in enumerate(hand) if CARDS[key]['cost']<=game.battle['energy']]
        if options:
            index,_ = max(options,key=lambda p:(p[1]['damage'],p[1]['heal'],p[1]['block']))
            game.play_card(index)
        else:
            game.end_round()
    raise AssertionError('Бой не завершился')


class AdventureTests(unittest.TestCase):
    def test_search_contains_local_remote_and_monster_distance_difficulty(self):
        game = create()
        game.search()
        self.assertEqual(game.turn, 2)
        self.assertTrue(all(1<=q.difficulty<=5 for q in game.offers))
        for q in game.offers:
            if q.monster:
                self.assertEqual(q.difficulty,min(5,q.monster_tier+(q.distance+1)//2))
        self.assertTrue(any(q.target == game.hero.region for q in game.offers))
        self.assertTrue(any(q.target != game.hero.region for q in game.offers))
        self.assertTrue(any(q.monster for q in game.offers))
        self.assertTrue(any(not q.monster for q in game.offers))
        self.assertTrue(all(q.target in game.reachable() for q in game.offers))

    def test_combat_rewards_only_once(self):
        game = create()
        game.search()
        q = game.offers[0]
        game.accept(q.id)
        self.assertEqual(game.turn, 2)
        game.complete(q.id)
        self.assertEqual(game.xp,0)
        self.assertIsNotNone(game.battle)
        resolve(game)
        self.assertEqual(game.turn, 3)
        self.assertEqual(game.xp, 30)
        self.assertEqual(game.hero.gold, 52)
        self.assertEqual(game.branch_xp['Мощь'], 20)
        self.assertIn(q.loot, game.bag)
        self.assertIn('Победа в карточной дуэли', game.journal[-1])
        with self.assertRaises(ValueError):
            game.complete(q.id)
        self.assertEqual(game.xp, 30)

    def test_remote_city_quest_and_branch_unlock(self):
        game = create()
        game.enter_city()
        game.search()
        q = next(q for q in game.offers if q.city)
        game.accept(q.id)
        before = game.turn
        with self.assertRaises(ValueError):
            game.complete(q.id)
        self.assertEqual(game.turn, before)
        # Передвижение протестировано в базовом наборе; здесь проверяем условия цели.
        game.hero.region = q.target
        game.in_city = False
        with self.assertRaises(ValueError):
            game.complete(q.id)
        game.enter_city()
        branch_before = game.hero.branches[q.branch]
        game.complete(q.id)
        self.assertEqual(game.hero.branches[q.branch], min(3, branch_before + q.progress // 60))
        self.assertGreater(game.xp, 0)

    def test_limit_abandon_and_refresh(self):
        game = create()
        game.search()
        ids = [q.id for q in game.offers]
        for id in ids[:3]:
            game.accept(id)
        with self.assertRaises(ValueError):
            game.accept(ids[3])
        game.abandon(ids[0])
        game.search()
        self.assertEqual(len(game.active), 2)
        self.assertFalse(set(ids) & {q.id for q in game.offers})
        with self.assertRaises(ValueError):
            game.accept(ids[0])

    def test_unreachable_destinations_not_offered(self):
        game = create()
        for country in ('Азалтир', 'Тротенфорская империя', 'Лесное царство Талласа', 'Дваллинхорг'):
            game.set_relation('Княжество Бреннор', country, True)
        game.search()
        self.assertTrue(all(q.target in ('Глыба', 'Бреннор') for q in game.offers))

    def test_equipment_ownership_and_slots(self):
        game = create()
        with self.assertRaises(ValueError):
            game.equip('Кольчуга')
        game.bag.extend(['Кольчуга', 'Боевой топор'])
        game.equip('Кольчуга')
        game.equip('Боевой топор')
        self.assertEqual(game.hero.equipment['Доспех'], 'Кольчуга')
        self.assertIn('Учебный меч', game.bag)
        self.assertEqual(game.hero.equipment['Оружие'], 'Боевой топор')
        game.unequip('Оружие')
        self.assertIsNone(game.hero.equipment['Оружие'])
        self.assertEqual(game.turn, 1)

    def test_roundtrip_including_empty_slots_and_corrupt_quests(self):
        game = create()
        game.search()
        game.accept(game.offers[0].id)
        game.complete(game.active[0].id)
        resolve(game)
        game.accept(game.offers[0].id)
        game.unequip('Оружие')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'save.json'
            game.save(path)
            loaded = Adventure.load(path)
            self.assertEqual(loaded.hero, game.hero)
            for attr in ('xp', 'bag', 'offers', 'active', 'completed', 'search_count', 'branch_xp', 'journal'):
                self.assertEqual(getattr(loaded, attr), getattr(game, attr))
            loaded.save(path)
            data = json.loads(path.read_text())
            data['active'][0]['target'] = 'Нархаз'
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                Adventure.load(path)

    def test_content_for_every_tier(self):
        self.assertEqual(set(MONSTERS), {1, 2, 3, 4, 5})
        self.assertTrue(all(len(v) == 3 for v in MONSTERS.values()))
        for slot in ('Оружие', 'Доспех', 'Артефакт'):
            self.assertGreaterEqual(sum(v[0] == slot for v in ITEMS.values()), 5)


class ServerTests(unittest.TestCase):
    def test_api_lifecycle_and_rejected_actions(self):
        with tempfile.TemporaryDirectory() as folder:
            server = make_server(0, Path(folder) / 'save.json')
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f'http://127.0.0.1:{server.server_port}'
            def post(action, **extra):
                req = Request(base + '/api/action', data=json.dumps(dict(action=action, **extra)).encode(),
                              headers={'Content-Type': 'application/json'})
                with urlopen(req) as response:
                    return json.load(response)['game']
            try:
                with urlopen(base) as response:
                    self.assertIn('Этерион', response.read().decode())
                with self.assertRaises(HTTPError):
                    post('search')
                h = dict(name='Эрин', gender='Женский', race='Человек', background='Торговец',
                         item='Учебный меч', region='Глыба', human_branch='Знания')
                post('create', hero=h)
                board = post('search')
                post('accept', id=board['offers'][0]['id'])
                done = post('complete', id=board['offers'][0]['id'])
                self.assertIsNotNone(done['battle'])
                for _ in range(100):
                    if done['battle'] is None:
                        break
                    b=done['battle']
                    options=[(i,CARDS[key]) for i,key in enumerate(b['hand']) if CARDS[key]['cost']<=b['energy']]
                    if options:
                        index,_=max(options,key=lambda pair:pair[1]['damage'])
                        done=post('play',index=index)
                    else:
                        done=post('end_round')
                self.assertEqual(done['xp'], 30)
                post('save')
                post('move', target='Бреннор')
                restored = post('load')
                self.assertEqual(restored['hero']['region'], 'Глыба')
                self.assertEqual(restored['completed'], 1)
                with self.assertRaises(HTTPError):
                    post('move', target='Нархаз')
                bad = Request(base + '/api/action', data=b'{"action":"wait"}',
                              headers={'Content-Type': 'application/json', 'Origin': 'http://foreign.invalid'})
                with self.assertRaises(HTTPError) as e:
                    urlopen(bad)
                self.assertEqual(e.exception.code, 403)
            finally:
                server.shutdown()
                server.server_close()
                thread.join()


if __name__ == '__main__':
    unittest.main()
