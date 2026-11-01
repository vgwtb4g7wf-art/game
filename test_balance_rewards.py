import unittest
from math import ceil
from balance_rewards import hunt_reward,peace_reward,event_reward
from social_rules import GEAR_PRICES
from world_content import CONSUMABLES
from trade import META
from test_adventure import create

class RewardBalanceTests(unittest.TestCase):
    def test_reward_curve_is_monotone_and_no_single_boss_level(self):
        rows=[hunt_reward(t) for t in range(1,6)]
        for key in ('xp','gold','progress'):
            self.assertEqual([r[key] for r in rows],sorted(r[key] for r in rows))
        self.assertEqual(rows[0],dict(xp=16,gold=13,progress=8))
        self.assertEqual(rows[-1],dict(xp=56,gold=29,progress=24))
        self.assertTrue(all(r['xp']<100 and r['progress']<50 for r in rows))
        for t in range(1,6):
            self.assertLess(event_reward(t)['xp'],hunt_reward(t)['xp'])
            self.assertLess(event_reward(t)['gold'],hunt_reward(t)['gold'])

    def test_basic_gear_needs_saving_and_low_hunt_cannot_buy_two_bandages(self):
        reward=hunt_reward(1)['gold'];price=CONSUMABLES['common:bandage']['price']
        self.assertLessEqual(price,reward);self.assertLess(reward,price*2)
        initial=15
        self.assertGreater(GEAR_PRICES['Железный меч'],initial+reward)
        self.assertLessEqual(GEAR_PRICES['Железный меч'],initial+reward*2)
        self.assertTrue(all(GEAR_PRICES[n]>=80 for n,m in META.items() if m['rare'] and n!='Мантия лекаря'))

    def test_generated_tasks_use_new_rewards_and_small_travel_bonus(self):
        g=create()
        for _ in range(10):
            g.search()
            for q in g.offers:
                r=hunt_reward(q.monster_tier) if q.monster else peace_reward(__import__('narrative_content').PEACE_QUESTS[q.template]['delivery'],0)
                self.assertEqual(q.xp,r['xp']);self.assertEqual(q.progress,r['progress'])
                self.assertTrue(0<=q.gold-r['gold']<=3)

if __name__=='__main__':unittest.main()
