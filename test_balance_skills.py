"""Регрессии баланса: эффективность тяжёлых карт, пределы и полноценные дуэли."""
import unittest

from combat import CARDS,card_damage,card_heal,stats
from test_adventure import create
from test_skills import master
from tools.audit_balance import BUILDS,WEAPONS,duel


class SkillBalanceTests(unittest.TestCase):
    def test_two_energy_berserker_attack_is_worth_two_actions(self):
        g=create();master(g,'Мощь','right')
        for bonus in range(7):
            g.stat_damage=bonus;g.sync_skills()
            heavy=card_damage(CARDS['skill:Прорыв'],g.hero)
            ordinary=card_damage(CARDS['skill:Натиск'],g.hero)
            self.assertGreaterEqual(heavy,2*ordinary)

    def test_final_defender_passive_has_survival_value_and_removes_penalty(self):
        g=create();g.bag.append('Кольчуга');g.equip('Кольчуга')
        g.gain_branch('Мощь',350);g.choose_path('Мощь','left')
        before=stats(g.hero)
        g.gain_branch('Мощь',100);after=stats(g.hero)
        self.assertGreater(after['armor'],before['armor'])
        self.assertGreater(after['hit'],before['hit'])

    def test_specialist_healing_card_does_not_dominate_pure_block(self):
        g=create();master(g,'Знания','right')
        c=CARDS['skill:Восстановление']
        effective=c['armor']+card_heal(c,g.hero)
        self.assertLessEqual(effective,CARDS['skill:Неприступный бастион']['block'])

    def test_diplomacy_bonus_applies_to_deeds_not_grants_or_bad_actions(self):
        g=create();start=g.hero.gold;master(g,'Дипломатия','left')
        self.assertEqual(g.hero.gold,start+40)
        self.assertEqual(g.reputation,5)
        g.repute(None,2,3);self.assertEqual(g.reputation,8)
        g.repute(None,-6,4);self.assertEqual(g.reputation,2)
        g.repute(None,5,0);self.assertEqual(g.reputation,7)
        g.gain_branch('Дипломатия',0);self.assertEqual(g.hero.gold,start+40)
        other=create();master(other,'Дипломатия','right')
        left={o['card']:o['price'] for o in g.shop()['offers']}
        right={o['card']:o['price'] for o in other.shop()['offers']}
        self.assertTrue(all(right[k]<=p for k,p in left.items() if k in right))
        self.assertGreater(other.shop()['discount'],g.shop()['discount'])

    def test_every_complete_path_handles_top_tier_without_stalling(self):
        for name in BUILDS:
            with self.subTest(path=name):
                results=[duel(name,w,5,seed) for w in WEAPONS for seed in range(1,9)]
                self.assertGreaterEqual(sum(o['win'] for o in results)/len(results),.70)
                self.assertTrue(all(not o['timeout'] for o in results))
                self.assertLess(sum(o['rounds'] for o in results)/len(results),14)


if __name__=='__main__':unittest.main()
