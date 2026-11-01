import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from collections import Counter
from adventure import Adventure
from bestiary import BESTIARY,LOCAL_POOLS,COMMON_POOLS,GUARDS,hunting_pool,intent
from world_content import enemy_profile
from test_adventure import create
from test_skills import start


class BestiaryTests(unittest.TestCase):
    def test_exact_counts_unique_names_and_tiers(self):
        self.assertEqual(len(BESTIARY),231)
        self.assertEqual([len(COMMON_POOLS[t]) for t in range(1,6)],[5,4,3,2,1])
        for country,pools in LOCAL_POOLS.items():
            self.assertEqual([len(pools[t]) for t in range(1,6)],[7,6,5,4,3])
            self.assertEqual(len(GUARDS[country]),2)
            for name in GUARDS[country]:self.assertEqual(BESTIARY[name]['tier'],3)
            for t,names in pools.items():
                for name in names:self.assertEqual(BESTIARY[name]['tier'],t)
                self.assertFalse(set(GUARDS[country]) & set(hunting_pool(country,t)))
        for name,m in BESTIARY.items():
            p=enemy_profile(name,m['tier']);self.assertGreater(p['hp'],0)
            self.assertTrue(m['description']);self.assertNotIn('dodge',p)
            with self.assertRaises(ValueError):enemy_profile(name,1 if m['tier']!=1 else 2)

    def test_pools_are_local_and_common_and_tracking_has_no_early_rewards(self):
        g=create();seen=set()
        for _ in range(30):
            g.search()
            for q in g.offers:
                if q.monster:
                    country=__import__('eterion').REGIONS[q.target].country
                    self.assertIn(q.monster,hunting_pool(country,q.monster_tier));seen.add(q.monster)
                    self.assertLessEqual(q.difficulty,3)
            if g.offers[0].tracking:
                q=g.offers[0];g.accept(q.id);before=(g.xp,g.hero.gold);turn=g.turn
                g.complete(q.id);self.assertIsNone(g.preparation);self.assertEqual(q.tracking,0)
                self.assertEqual(g.turn,turn+1);self.assertEqual((g.xp,g.hero.gold),before)
                g.complete(q.id);self.assertEqual(g.preparation['enemy'],q.monster)
                g.cancel_preparation();g.abandon(q.id)
        self.assertGreater(len(seen),8)

    def test_enemy_heals_instead_of_attack_and_intents_survive_save(self):
        g=create();g.search();q=g.offers[0]
        q.monster=next(n for n,m in BESTIARY.items() if m['tier']==1 and m['kind']=='восстановитель')
        g.accept(q.id);g.complete(q.id);g.begin_battle({});b=g.battle
        b['round']=3;b['enemy_hp']=2;g.draw_round();hp=g.hp
        self.assertEqual(b['intent'],'heal');g.end_round()
        self.assertEqual(g.hp,hp);self.assertEqual(b['enemy_hp'],4)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'save.json';g.save(p);loaded=Adventure.load(p)
            self.assertEqual(loaded.battle,g.battle)
        for name,m in BESTIARY.items():
            profile=enemy_profile(name,m['tier'])
            for r in range(1,10):
                kind,value=intent(profile,r);self.assertIn(kind,('attack','heal','guard'));self.assertGreater(value,0)

    def test_border_pay_risk_both_outcomes_and_unique_tier_three_guard(self):
        for chance,stopped in ((0.,True),(.99,False)):
            g=create();g.reputation=-30;gold=g.hero.gold
            with patch('battle_rules.random.Random') as rng:
                rng.return_value.random.return_value=chance;g.move('Келебран','risk')
            self.assertEqual(g.hero.gold,gold)
            if stopped:
                self.assertEqual(g.hero.region,'Глыба');self.assertIn(g.preparation['enemy'],GUARDS['Азалтир'])
                self.assertEqual(g.preparation['tier'],3)
                with tempfile.TemporaryDirectory() as d:
                    p=Path(d)/'save.json';g.save(p);loaded=Adventure.load(p)
                    self.assertEqual(g.preparation,loaded.preparation);self.assertEqual(loaded.border_checks,1)
                turn=g.turn;g.cancel_preparation();self.assertEqual(g.turn,turn+1)
            else:self.assertEqual(g.hero.region,'Келебран')
        g=create();g.reputation=-30;g.hero.gold=100;g.move('Келебран','pay')
        self.assertEqual(g.hero.gold,75);self.assertEqual(g.border_checks,0)

    def test_border_frequency_and_reload_is_not_a_reroll(self):
        stopped=0
        for i in range(600):
            g=create();g.hero.name=str(i);g.reputation=-30;g.move('Келебран','risk')
            stopped+=g.preparation is not None
        self.assertTrue(260<stopped<340)
        g=create();g.reputation=-30
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'save.json';g.save(p);h=Adventure.load(p)
            for game in (g,h):game.move('Келебран','risk')
            self.assertEqual(g.hero.region,h.hero.region);self.assertEqual(g.preparation,h.preparation)

    def test_guard_flee_keeps_original_side_and_has_no_quest_reward(self):
        g=create();g.reputation=-30
        with patch('battle_rules.random.Random') as rng:
            rng.return_value.random.return_value=0;g.move('Келебран','risk')
        g.begin_battle({});g.flee()
        self.assertEqual(g.hero.region,'Глыба');self.assertEqual(g.xp,0)
        self.assertEqual(g.active,[])


if __name__=='__main__':unittest.main()
