import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from adventure import Adventure
from test_adventure import create
from test_skills import start,play

class DamageLedgerTests(unittest.TestCase):
    def test_healing_does_not_erase_damage_and_save_retains_it(self):
        g=create();b=start(g);b['armor']=2;b['armor_max']=2;b['block']=1;b['intent']='attack';b['intent_value']=5
        hp=g.hp;g.end_round()
        self.assertEqual(g.hp,hp-2);self.assertEqual(b['damage_taken'],2)
        play(g,'breath',rolls=());self.assertEqual(g.hp,hp);self.assertEqual(b['damage_taken'],2)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'save.json';g.save(p);h=Adventure.load(p)
            self.assertEqual(h.battle['damage_taken'],2)
            data=json.loads(p.read_text());data['battle']['damage_taken']=-1;p.write_text(json.dumps(data))
            with self.assertRaises(ValueError):Adventure.load(p)
        b['enemy_hp']=1;b['enemy_armor']=0;b['enemy_block']=0
        play(g,'weapon:sword:cut');self.assertEqual(g.last_battle['damage_taken'],2)

    def test_block_and_armor_do_not_count_as_hp_damage(self):
        g=create();b=start(g);b['armor']=8;b['armor_max']=8;b['block']=3;b['intent']='attack';b['intent_value']=5
        hp=g.hp;g.end_round();self.assertEqual(g.hp,hp);self.assertEqual(b['damage_taken'],0)
        self.assertEqual(b['armor'],6)

    def test_lethal_damage_is_actual_hp_loss(self):
        g=create();b=start(g);g.hp=3;b['armor']=0;b['block']=0;b['intent']='attack';b['intent_value']=99
        g.end_round();self.assertEqual(g.last_battle['damage_taken'],3)
        self.assertTrue(g.dead)

    def test_flee_damage_is_included(self):
        g=create();b=start(g);damage=b['profile']['escape'];g.flee()
        self.assertEqual(g.last_battle['damage_taken'],damage)

if __name__=='__main__':unittest.main()
