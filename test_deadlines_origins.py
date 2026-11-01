import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from adventure import Adventure
from origins import ORIGINS
from eterion import RACES
from test_adventure import create

class NewStartAndDeadlineTests(unittest.TestCase):
    def test_all_sixteen_native_starts_and_human_focus(self):
        for race in RACES:
            for bg,origin in ORIGINS.items():
                g=Adventure.create('Новый герой','Мужской',race,bg,'Железный меч','Глыба',origin['branch'])
                self.assertEqual(g.hero.gold,origin['gold']+(15 if race=='Высший эльф' else 0))
                self.assertEqual(g.consumables,{origin['consumable']:1})
                self.assertEqual(g.bag,['Железный меч'])
                self.assertEqual(sum(g.hero.branches.values()),1 if race=='Человек' else 0)
                self.assertEqual(g.branch_xp[origin['branch']],15 if race=='Человек' else 25)
                self.assertEqual(g.hp,17 if race=='Дварф' else 14)
                h=Adventure.create('Герой','Женский',race,bg,'Медный амулет','Глыба','Хитрость' if origin['branch']!='Хитрость' else 'Знания')
                self.assertEqual(sum(h.hero.branches.values()),0)

    def quest(self,g,distance=0):
        q=g.make_peace_quest('peace-006','Глыба','test');q.distance=distance;g.offers=[q];g.accept(q.id);return q

    def test_outside_wait_is_not_rest_and_no_hp_can_be_farmed(self):
        g=create();g.hp=1
        for _ in range(12):g.pass_turn()
        self.assertEqual(g.hp,1)
        with self.assertRaises(ValueError):g.wait()
        self.assertEqual(g.hp,1)
        g.in_city=True;g.hero.gold=4;g.wait();self.assertEqual(g.hp,6);self.assertEqual(g.hero.gold,0)

    def test_deadlines_8_9_10_and_expiry_without_fines(self):
        for distance,budget in ((0,8),(2,9),(6,10)):
            g=create();q=self.quest(g,distance);self.assertEqual(q.due_turn,g.turn+budget)
            gold=g.hero.gold
            for _ in range(budget-1):g.pass_turn()
            self.assertIn(q,g.active)
            g.pass_turn();self.assertNotIn(q,g.active);self.assertIn(q.id,g.failed)
            self.assertEqual(g.hero.gold,gold);self.assertEqual(g.xp,0)

    def test_cancel_reaccept_does_not_reset_clock(self):
        g=create();q=self.quest(g);deadline=q.due_turn;g.abandon(q.id);g.pass_turn();g.accept(q.id)
        self.assertEqual(q.due_turn,deadline)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'save.json';g.save(p);h=Adventure.load(p)
            self.assertEqual(h.active[0].due_turn,deadline)
            for _ in range(deadline-h.turn):h.pass_turn()
            self.assertEqual(h.active,[])

    def test_dialogue_can_finish_last_day_or_expire_during_listening(self):
        g=create();q=self.quest(g)
        for _ in range(6):g.pass_turn()
        g.complete(q.id);g.resolve_event('listen');g.resolve_event('good')
        self.assertIn(q.id,g.completed);self.assertNotIn(q.id,g.failed)
        g=create();q=self.quest(g)
        for _ in range(7):g.pass_turn()
        g.complete(q.id);g.resolve_event('listen')
        self.assertIsNone(g.event);self.assertIn(q.id,g.failed);self.assertEqual(g.xp,0)

    def test_native_save_no_repeated_gifts_and_legacy_deadline_migration(self):
        g=Adventure.create('Герой','Мужской','Высший эльф','Торговец','Железный меч','Глыба')
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'save.json';g.save(p);h=Adventure.load(p)
            self.assertEqual(h.hero.gold,g.hero.gold);self.assertEqual(h.consumables,g.consumables)
            import json
            q=self.quest(g);g.save(p);data=json.loads(p.read_text());data['version']=12
            for row in data['active']:row.pop('due_turn')
            p.write_text(json.dumps(data));h=Adventure.load(p)
            self.assertEqual(h.active[0].due_turn,h.turn+8)

if __name__=='__main__':unittest.main()
