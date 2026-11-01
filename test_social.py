import copy,json,tempfile
from pathlib import Path
import unittest
from narrative_content import EVENTS,PEACE_QUESTS
from social_rules import fame_stage,reputation_stage,GEAR_PRICES
from adventure import Adventure,AVAILABLE_ITEMS
from eterion import COUNTRIES
from app import state
from test_adventure import create
from test_skills import master

class SocialTests(unittest.TestCase):
    def save_roundtrip(self,g):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'save.json';g.save(p);return Adventure.load(p)

    def test_content_counts(self):
        self.assertEqual(len(EVENTS),100);self.assertEqual(len(PEACE_QUESTS),100)
        self.assertEqual(sum(v['mode']=='море' for v in EVENTS.values()),33)
        self.assertEqual(sum(v['effect']=='fight' for v in EVENTS.values()),4)
        self.assertEqual(len({v['title'] for v in EVENTS.values()}),100)
        self.assertEqual(len({v['title'] for v in PEACE_QUESTS.values()}),100)
        self.assertEqual(sum(v['combat'] for v in PEACE_QUESTS.values()),5)

    def test_all_fame_and_reputation_thresholds_and_country_access(self):
        self.assertEqual([fame_stage(n) for n in (0,19,20,49,50,119,120,249,250)],[0,0,1,1,2,2,3,3,4])
        self.assertEqual([reputation_stage(n) for n in (-100,-35,-10,-9,0,9,10,35,70)],[-3,-2,-1,0,0,0,1,2,3])
        g=create();g.fame=20;g.reputation=100
        self.assertEqual(g.entry_fee(),5)
        g.attitudes['Княжество Бреннор']=10;self.assertEqual(g.entry_fee(),0)
        g.hero.region='Бреннор';self.assertEqual(g.entry_fee(),10)
        g.fame=50;self.assertEqual(g.entry_fee(),0)
        g.repute(None,0,-99999);self.assertEqual(g.fame,0)
        g.fame=250;self.assertEqual(g.offer_limit(),4);self.assertEqual(g.shop()['discount'],10)

    def test_shops_equipment_black_market_and_no_quest_equipment(self):
        g=create();g.hero.gold=1000
        def find(key):
            for _ in range(2000):
                if any(o['item']==key for o in g.shop()['gear']):return
                g.turn+=5
            self.fail('Товар не встречается в ассортименте')
        self.assertEqual(len(AVAILABLE_ITEMS),7)
        find('Кольчуга');g.buy('gear:Кольчуга');g.equip('Кольчуга')
        self.assertEqual(g.hero.gold,950)
        with self.assertRaises(ValueError):g.buy('gear:Кольчуга')
        g.search();self.assertTrue(all(q.loot is None for q in g.offers))
        for rep,allowed in ((10,False),(9,True),(0,True),(-20,True)):
            g.hero.region='Трущобы';g.reputation=rep
            self.assertEqual(g.shop()['accessible'],allowed)
        g.reputation=-1;find('Амулет теневого договора');g.buy('gear:Амулет теневого договора');g.equip('Амулет теневого договора')
        key=g.shop()['offers'][0]['card'];g.buy(key)
        h=self.save_roundtrip(g);self.assertEqual(h.bag,g.bag);self.assertEqual(h.consumables,g.consumables)
        g.hero.region='Глыба'
        with self.assertRaises(ValueError):g.buy('black:blade')

    def test_all_events_complete_without_leaking_state(self):
        for key,t in EVENTS.items():
            with self.subTest(scene=key):
                g=create();g.hero.gold=100;g.social_event('travel',template=key)
                h=self.save_roundtrip(g);self.assertEqual(h.narrative_view(),g.narrative_view())
                g.resolve_event('good');self.assertIsNone(g.event)
                if t['effect']=='fight':
                    self.assertEqual(g.preparation['kind'],'event')
                    g.begin_battle({});h=self.save_roundtrip(g);self.assertEqual(g.battle,h.battle)
                    g.flee();self.assertEqual(g.active,[])
                elif t['effect']=='quest':self.assertEqual(len(g.active),1)
                self.assertTrue(g.hero.gold>=0)

    def test_all_peace_quests_dialogue_success_and_no_double_reward(self):
        for key,t in PEACE_QUESTS.items():
            with self.subTest(quest=key):
                g=create();q=g.make_peace_quest(key,'Глыба','test');g.active=[q]
                gold=g.hero.gold;g.complete(q.id)
                self.assertEqual(g.xp,0)
                if not t['delivery']:
                    g.resolve_event('listen');self.assertEqual(q.stage,1)
                    h=self.save_roundtrip(g);self.assertEqual(h.narrative_view(),g.narrative_view())
                g.resolve_event('good');self.assertEqual(g.xp,q.xp);self.assertEqual(g.active,[])
                self.assertEqual(g.hero.gold,gold+q.gold-t['fee'])
                with self.assertRaises(ValueError):g.complete(q.id)

    def test_dialogue_neutral_wrong_and_rare_fight(self):
        for key in ('peace-006','peace-096'):
            g=create();q=g.make_peace_quest(key,'Глыба','test');g.active=[q]
            g.complete(q.id);g.resolve_event('ignore');self.assertEqual(g.xp,0);self.assertIn(q,g.active)
            g.complete(q.id);g.resolve_event('listen');g.resolve_event('bad')
            if PEACE_QUESTS[key]['combat']:
                self.assertTrue(q.monster);g.begin_battle({});h=self.save_roundtrip(g)
                self.assertEqual(g.battle,h.battle)
            else:self.assertIsNone(g.preparation)

    def test_event_followup_obeys_limit_and_payment_is_atomic(self):
        g=create();g.active=[g.make_peace_quest('peace-001','Глыба',str(i)) for i in range(2)]
        g.social_event('travel',template='travel-005')
        with self.assertRaises(ValueError):g.resolve_event('good')
        self.assertIsNotNone(g.event);g.resolve_event('ignore');self.assertEqual(len(g.active),2)
        g.hero.gold=0;g.social_event('travel',template='travel-002')
        with self.assertRaises(ValueError):g.resolve_event('good')
        self.assertEqual(g.hero.gold,0);self.assertIsNotNone(g.event)

    def test_dead_hero_state_and_fame_require_local_trust(self):
        g=create();g.fame=250
        self.assertEqual(g.shop()['discount'],0);self.assertEqual(g.offer_limit(),3)
        g.hp=0;g.dead=True
        self.assertEqual(state(g)['combat_rating']['tier'],0)

    def test_combat_assessment_uses_build_and_has_no_real_effects(self):
        g=create();before=copy.deepcopy((g.hero,g.xp,g.hp,g.active,g.journal,g.fame,g.reputation))
        low=g.combat_rating()['tier'];self.assertEqual(before,(g.hero,g.xp,g.hp,g.active,g.journal,g.fame,g.reputation))
        master(g,'Мощь','right');g.hp=g.combat_stats()['hp']
        self.assertGreaterEqual(g.combat_rating()['tier'],low)
        self.assertEqual(g.combat_rating(),g.combat_rating())
        g.hp=1;self.assertLessEqual(g.combat_rating()['tier'],low)

if __name__=='__main__':unittest.main()
