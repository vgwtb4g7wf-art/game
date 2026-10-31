import json
import tempfile
import unittest
from pathlib import Path

from eterion import BACKGROUNDS, BRANCHES, REGIONS, ROUTES, Game


class GameTests(unittest.TestCase):
    def make(self, region='Глыба', **kwargs):
        args = dict(name='Эрин', gender='Женский', race='Человек', background='Торговец',
                    item='Учебный меч', region=region, human_branch='Знания')
        args.update(kwargs)
        return Game.create(**args)

    def test_creation_bonuses_and_equipment(self):
        game = self.make()
        self.assertEqual(game.hero.branches, dict(zip(BRANCHES, [0, 1, 0, 1])))
        self.assertEqual(game.hero.gold, 40)
        self.assertEqual(sum(v is not None for v in game.hero.equipment.values()), 1)
        self.assertFalse(game.in_city)

    def test_all_races_and_backgrounds(self):
        for race, branch in [('Дварф', 'Мощь'), ('Высший эльф', 'Знания'), ('Лесной эльф', 'Хитрость')]:
            for background, (bonus, gold) in BACKGROUNDS.items():
                with self.subTest(race=race, background=background):
                    hero = self.make(race=race, background=background).hero
                    self.assertGreaterEqual(hero.branches[branch], 1)
                    self.assertEqual(hero.branches[bonus], 2 if branch == bonus else 1)
                    self.assertEqual(hero.gold, gold)

    def test_land_and_sea_movement(self):
        game = self.make()
        game.move('Бреннор')
        self.assertEqual(game.turn, 2)
        game.move('Глыба')
        game.move('Келебран')
        self.assertEqual(game.hero.region, 'Келебран')
        self.assertEqual(game.turn, 4)

    def test_rejected_movement_does_not_consume_turn(self):
        game = self.make()
        with self.assertRaises(ValueError):
            game.move('Алдория')
        self.assertEqual(game.turn, 1)
        self.assertEqual(game.hero.region, 'Глыба')

    def test_closed_capital_and_demons(self):
        game = self.make('Трущобы')
        with self.assertRaises(ValueError):
            game.move('Аграмор')
        for region in ['Аграмор', 'Нархаз']:
            with self.assertRaises(ValueError):
                self.make(region)

    def test_war_is_symmetric_and_peace_restores_access(self):
        game = self.make()
        a, b = REGIONS['Глыба'].country, REGIONS['Келебран'].country
        game.set_relation(b, a, True)
        with self.assertRaises(ValueError):
            game.move('Келебран')
        game.move('Бреннор')  # Внутренний путь остаётся открыт.
        game.move('Глыба')
        game.set_relation(a, b, False)
        game.move('Келебран')

    def test_city_entry_exit_and_travel(self):
        game = self.make()
        game.enter_city()
        self.assertTrue(game.in_city)
        self.assertEqual(game.hero.gold, 35)
        with self.assertRaises(ValueError):
            game.enter_city()
        self.assertEqual(game.turn, 2)
        game.move('Бреннор')
        self.assertFalse(game.in_city)
        game.enter_city()
        self.assertEqual(game.hero.gold, 25)
        game.leave_city()
        self.assertFalse(game.in_city)

    def test_insufficient_gold_is_atomic(self):
        game = self.make()
        game.hero.gold = 0
        with self.assertRaises(ValueError):
            game.enter_city()
        self.assertEqual(game.turn, 1)
        self.assertFalse(game.in_city)
        self.assertEqual(game.hero.gold, 0)

    def test_save_load_preserves_state(self):
        game = self.make()
        game.enter_city()
        game.set_relation('Азалтир', 'Аграмор', True)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'save.json'
            game.save(path)
            loaded = Game.load(path)
            self.assertEqual(loaded.hero, game.hero)
            self.assertEqual(loaded.turn, game.turn)
            self.assertEqual(loaded.in_city, game.in_city)
            self.assertEqual(loaded.wars, game.wars)
            self.assertEqual(loaded.journal, game.journal)
            game.save(path)  # Повторное сохранение поддерживается.

    def test_corrupt_save(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'save.json'
            path.write_text('{}')
            with self.assertRaises(ValueError):
                Game.load(path)

    def test_map_is_consistent(self):
        pairs = set()
        for a, b, kind in ROUTES:
            self.assertIn(a, REGIONS)
            self.assertIn(b, REGIONS)
            self.assertIn(kind, ('суша', 'море'))
            pair = tuple(sorted((a, b)))
            self.assertNotIn(pair, pairs)
            pairs.add(pair)


if __name__ == '__main__':
    unittest.main()
