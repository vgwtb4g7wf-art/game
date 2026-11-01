"""Проверки, что старт не сломан, а верхняя сложность остаётся опасной."""
import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('balance_sample',Path(__file__).parent/'tools'/'check_balance.py')
balance=importlib.util.module_from_spec(spec);spec.loader.exec_module(balance)


class BalanceTests(unittest.TestCase):
    def test_every_start_item_can_handle_first_monster(self):
        for item in ('Железный меч','Короткий кинжал','Дорожный лук','Кожаная куртка','Кольчуга','Кольцо янтаря','Медный амулет'):
            with self.subTest(item=item):
                runs=[balance.fight(item,1,1,day) for day in range(1,21)]
                self.assertGreaterEqual(sum(win for win,_ in runs),18)
                self.assertLess(sum(rounds for _,rounds in runs)/len(runs),6)

    def test_third_tier_is_risky_before_development(self):
        runs=[balance.fight('Железный меч',3,1,day) for day in range(1,41)]
        wins=sum(win for win,_ in runs)
        self.assertGreater(wins,5)
        self.assertLess(wins,38)


if __name__=='__main__':unittest.main()
