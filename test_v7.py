from test_adventure import complete_quest
from collections import Counter
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from adventure import Adventure
from combat import stats,ITEM_POWER,SKILL_POWER
from diplomacy import ACTIVE_COUNTRIES,ALL_PAIRS,NEIGHBOR_PAIRS,DEMONS,pair_key
from eterion import REGIONS
from progression import COSTS
from test_adventure import create
from world_systems import calendar


class RevisionTests(unittest.TestCase):
    def test_new_racial_bonuses_do_not_add_a_skill_rank(self):
        for race in ('Человек','Дварф','Лесной эльф','Высший эльф'):
            with self.subTest(race=race):
                g=Adventure.create('Руна','Женский',race,'Оруженосец','Железный меч','Глыба','Знания')
                self.assertEqual(sum(g.hero.branches.values()),0)
                self.assertEqual(g.hero.branches['Мощь'],0)
                self.assertEqual(g.branch_xp['Знания'],40 if race=='Человек' else 0)
                self.assertEqual(g.hp,17 if race=='Дварф' else 14)
                self.assertEqual(g.combat_stats()['damage'],5 if race=='Лесной эльф' else 4)
                self.assertEqual(g.hero.gold,35 if race=='Высший эльф' else 20)
        with self.assertRaises(ValueError):Adventure.create('Руна','Другой','Человек','Оруженосец','Железный меч','Глыба')

    def test_fifty_then_hundred_and_class_requires_experience(self):
        g=create();self.assertEqual(COSTS,(50,50,50,100,100,100))
        g.gain_branch('Мощь',149);self.assertEqual(g.hero.branches['Мощь'],2)
        g.gain_branch('Мощь',1);self.assertEqual(g.hero.branches['Мощь'],3)
        with self.assertRaises(ValueError):g.choose_path('Мощь','left')
        self.assertFalse(g.skills_notice() and g.paths['Мощь'])
        g.gain_branch('Мощь',99)
        with self.assertRaises(ValueError):g.choose_path('Мощь','left')
        g.gain_branch('Мощь',1);g.choose_path('Мощь','left')
        self.assertEqual(g.hero.branches['Мощь'],4);self.assertEqual(g.branch_xp['Мощь'],0)
        g.gain_branch('Мощь',99);self.assertEqual(g.hero.branches['Мощь'],4)
        g.gain_branch('Мощь',1);self.assertEqual(g.hero.branches['Мощь'],5)

    def test_odd_level_choice_and_no_automatic_stat_growth(self):
        g=create();initial=g.combat_stats().copy();g.xp=100;g.sync_skills()
        self.assertEqual(g.combat_stats(),initial)
        for xp,choice in ((195,'damage'),(395,'hp')):
            g.xp=xp;g.search();q=next(q for q in g.offers if not q.monster and q.target==g.hero.region)
            g.accept(q.id);complete_quest(g,q.id)
            self.assertEqual(g.stat_points,1);g.choose_growth(choice);self.assertEqual(g.stat_points,0)
        self.assertEqual(g.combat_stats()['damage'],initial['damage']+1)
        self.assertEqual(g.combat_stats()['hp'],initial['hp']+3)
        with self.assertRaises(ValueError):g.choose_growth('hp')
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'save.json';g.save(p);loaded=Adventure.load(p)
            self.assertEqual(loaded.stat_hp,3);self.assertEqual(loaded.stat_damage,1)
            data=json.loads(p.read_text());data['world']['stat_points']=1;p.write_text(json.dumps(data))
            with self.assertRaises(ValueError):Adventure.load(p)

    def test_global_reputation_is_separate_from_country_relations(self):
        g=create();relations=dict(g.relations);initial=g.fame
        g.repute('Азалтир',5,3);g.repute('Княжество Бреннор',-3,2)
        self.assertEqual(g.reputation,2);self.assertGreater(g.fame,initial)
        self.assertEqual(g.relations,relations)
        g.reputation=20;g.fame=50;g.attitudes['Княжество Бреннор']=10
        self.assertEqual(g.entry_fee(),0);g.move('Бреннор');self.assertEqual(g.entry_fee(),0)

    def test_automatic_wars_neighbors_caps_and_demon_idle(self):
        g=create();g.auto_diplomacy=True;seen=False
        for turn in range(1,3001):
            g.turn=turn;g.tick_diplomacy()
            self.assertTrue(all(p in NEIGHBOR_PAIRS for p in g.wars))
            self.assertTrue(all(g.war_count(c)<=2 for c in ACTIVE_COUNTRIES))
            self.assertEqual(g.war_count(DEMONS),0)
            self.assertTrue(all(g.relations[pair_key(DEMONS,c)]==0 for c in ACTIVE_COUNTRIES))
            seen=seen or bool(g.wars)
        self.assertTrue(seen)
        self.assertTrue(any('объявили войну' in text for text in g.journal))
        self.assertTrue(any('заключили мир' in text for text in g.journal))

    def test_long_run_distribution_close_to_requested_target(self):
        g=create();g.auto_diplomacy=True;counts=Counter()
        for turn in range(1,18001):
            g.turn=turn;g.tick_diplomacy()
            if turn>2000:counts.update(g.war_count(c) for c in ACTIVE_COUNTRIES)
        total=sum(counts.values())
        for degree,target in ((0,.30),(1,.50),(2,.20)):
            self.assertAlmostEqual(counts[degree]/total,target,delta=.035)

    def test_manual_wars_cannot_break_constraints(self):
        g=create()
        with self.assertRaises(ValueError):g.set_relation('Дваллинхорг','Лесное царство Талласа',True)
        with self.assertRaises(ValueError):g.set_relation(DEMONS,'Азалтир',True)
        g.set_relation('Княжество Бреннор','Дваллинхорг',True)
        g.set_relation('Княжество Бреннор','Азалтир',True)
        with self.assertRaises(ValueError):g.set_relation('Княжество Бреннор','Тротенфорская империя',True)
        self.assertEqual(g.relations[pair_key('Княжество Бреннор','Азалтир')],-50)
        g.set_relation('Княжество Бреннор','Азалтир',False)
        self.assertEqual(g.relations[pair_key('Княжество Бреннор','Азалтир')],10)
        g.set_relation('Княжество Бреннор','Тротенфорская империя',True)

    def test_no_dodge_enemy_attack_guaranteed_chain_penalizes_hit(self):
        g=create();g.bag.append('Кольчуга');g.equip('Кольчуга')
        self.assertEqual(g.combat_stats()['hit'],85);self.assertNotIn('dodge',g.combat_stats())
        self.assertTrue(all('dodge' not in p for p in ITEM_POWER.values()))
        self.assertTrue(all('dodge' not in p['effects'] for p in SKILL_POWER.values()))
        g.search();g.accept(g.offers[0].id);g.complete(g.active[0].id);g.begin_battle({})
        b=g.battle;b['armor']=0;b['block']=0;b['hand']=[];b['draw']=['guard']*10
        hp=g.hp
        with patch.object(g,'roll',side_effect=AssertionError('Враг не должен проверять попадание')):g.end_round()
        self.assertEqual(g.hp,hp-b['profile']['attack'])

    def test_diplomacy_and_new_state_roundtrip(self):
        g=create();g.auto_diplomacy=True
        for _ in range(20):g.pass_turn()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'save.json';g.save(p);loaded=Adventure.load(p)
            self.assertEqual(loaded.relations,g.relations);self.assertEqual(loaded.wars,g.wars)
            for _ in range(10):g.pass_turn();loaded.pass_turn()
            self.assertEqual(loaded.relations,g.relations);self.assertEqual(loaded.wars,g.wars)
            self.assertEqual(loaded.journal,g.journal)
            loaded.save(p);data=json.loads(p.read_text());data['world']['relations'][pair_key(DEMONS,'Азалтир')]=5
            p.write_text(json.dumps(data))
            with self.assertRaises(ValueError):Adventure.load(p)

    def test_migrate_old_local_reputation(self):
        g=create()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'save.json';g.save(p);data=json.loads(p.read_text());data['version']=6
            data['hero']['gender']='Другой'
            data['world']['reputation']={c:(16 if c=='Азалтир' else 0) for c in __import__('eterion').COUNTRIES}
            data['world']['fame']={c:(40 if c=='Азалтир' else 0) for c in __import__('eterion').COUNTRIES}
            data['world']['last_fame_event']={c:1 for c in __import__('eterion').COUNTRIES}
            p.write_text(json.dumps(data));loaded=Adventure.load(p)
            self.assertEqual(loaded.reputation,2);self.assertEqual(loaded.fame,40)
            self.assertEqual(loaded.hero.gender,'Мужской')

    def test_calendar_and_concrete_final_passives(self):
        self.assertEqual(calendar(6)['week'],'Лунная')
        g=create();g.gain_branch('Хитрость',sum(COSTS[:4]));g.choose_path('Хитрость','left');g.gain_branch('Хитрость',sum(COSTS[4:]))
        self.assertEqual(g.hero.branches['Хитрость'],6)
        self.assertIn('200%',SKILL_POWER['Смертельная точность']['description'])
        g.search();g.accept(g.offers[0].id);g.complete(g.active[0].id);g.begin_battle({})
        self.assertEqual(g.battle['block'],0)
        self.assertEqual(g.combat_stats()['crit_multiplier'],200)
        for name,power in SKILL_POWER.items():
            if power['kind']=='passive':self.assertNotEqual(power['description'],'Постоянный бонус после открытия.')


if __name__=='__main__':unittest.main()
