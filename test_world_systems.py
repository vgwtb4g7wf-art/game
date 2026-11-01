import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from adventure import Adventure, AVAILABLE_ITEMS
from combat import deck, stats
from eterion import REGIONS, COUNTRIES
from progression import COSTS, unlocked
from test_adventure import create, resolve
from world_systems import calendar


class WorldTests(unittest.TestCase):
    def test_calendar_rollovers(self):
        self.assertEqual(calendar(1),dict(year=1,month='Капель',season='Весна',week='Солнечная',day='Искра',date=1))
        self.assertEqual(calendar(6)['week'],'Ночная')
        self.assertEqual(calendar(11)['month'],'Цветень')
        self.assertEqual(calendar(21)['season'],'Лето')
        self.assertEqual(calendar(81)['year'],2)
        self.assertEqual(calendar(81)['month'],'Капель')

    def test_city_is_instant_and_war_only_closes_border(self):
        game=create();gold=game.hero.gold;turn=game.turn
        game.enter_city();game.leave_city();game.enter_city()
        self.assertEqual(game.turn,turn)
        self.assertEqual(game.hero.gold,gold-10)
        game.set_relation('Княжество Бреннор','Азалтир',True)
        game.move('Бреннор');game.move('Глыба')
        with self.assertRaises(ValueError):game.move('Келебран')
        self.assertEqual(game.hero.region,'Глыба')

    def test_quest_cap_and_lower_peace_rewards(self):
        for xp in (0,100,300):
            for region in ('Глыба','Мерилион','Храм Камня'):
                game=create();game.hero.region=region;game.xp=xp
                for _ in range(4):
                    game.search()
                    self.assertTrue(all(q.difficulty<=min(5,xp//100+3) for q in game.offers))
                    for q in game.offers:
                        if q.monster:
                            self.assertLessEqual(q.monster_tier,q.difficulty)
                        else:
                            self.assertIsNone(q.loot)
                            self.assertLess(q.xp,20*q.difficulty)
                            self.assertLess(q.progress,12*q.difficulty)
                ids=[q.id for q in game.offers]
                for id in ids[:2]:game.accept(id)
                with self.assertRaises(ValueError):game.accept(ids[2])

    def test_tree_fork_increasing_cost_active_skills_and_level_reward(self):
        game=create();self.assertEqual(sorted(COSTS),list(COSTS))
        game.gain_branch('Мощь',sum(COSTS[:4]));self.assertEqual(game.hero.branches['Мощь'],3)
        self.assertEqual(game.branch_xp['Мощь'],COSTS[3]);game.choose_path('Мощь','right')
        self.assertEqual(game.hero.branches['Мощь'],4);self.assertIn('Разящий удар',unlocked(game.hero))
        self.assertNotIn('Сокрушающий удар',unlocked(game.hero))
        with self.assertRaises(ValueError):game.choose_path('Мощь','left')
        game.select_skill('Натиск');self.assertIn('Натиск',game.selected_skills)
        with self.assertRaises(ValueError):game.select_skill('Закалка')
        game.select_skill('Натиск');self.assertNotIn('skill:Натиск',[k for k,_ in __import__('combat').deck(game.hero,{})])
        game.xp=95;game.search();q=next(q for q in game.offers if not q.monster and q.target==game.hero.region)
        game.accept(q.id);game.complete(q.id);self.assertEqual(game.level_points,1)
        before=game.branch_xp['Хитрость'];game.spend_level('Хитрость')
        self.assertEqual(game.branch_xp['Хитрость'],before+20);self.assertEqual(game.level_points,0)
        with self.assertRaises(ValueError):game.spend_level('Хитрость')

    def test_preparation_four_card_limit_and_only_selected_cards(self):
        game=create();game.consumables={'supply:heal':3,'supply:smoke':3}
        game.search();game.accept(game.offers[0].id);game.complete(game.active[0].id)
        self.assertIsNotNone(game.preparation);self.assertIsNone(game.battle)
        before=game.turn
        with self.assertRaises(ValueError):game.begin_battle({'supply:heal':3,'supply:smoke':2})
        self.assertEqual(game.turn,before)
        game.begin_battle({'supply:smoke':2})
        pool=game.battle['hand']+game.battle['draw']
        self.assertEqual(pool.count('supply:smoke'),2)
        self.assertNotIn('supply:heal',pool)
        self.assertEqual(len(game.battle['hand']),4)
        game.flee()
        self.assertEqual(game.consumables,{'supply:heal':3,'supply:smoke':3})

    def test_tavern_restocks_and_changes_after_five_days(self):
        game=create();game.hero.gold=100
        original={o['card'] for o in game.shop()['offers']}
        for _ in range(3):game.buy('supply:heal')
        with self.assertRaises(ValueError):game.buy('supply:heal')
        for _ in range(5):game.wait()
        self.assertEqual(next(o['left'] for o in game.shop()['offers'] if o['card']=='supply:heal'),3)
        self.assertNotEqual(original,{o['card'] for o in game.shop()['offers']})
        game.buy('supply:heal')
        self.assertEqual(game.consumables['supply:heal'],4)

    def test_reputation_toll_guard_fight_and_war_priority(self):
        game=create();country=REGIONS['Келебран'].country
        game.repute(country,-30,25)
        gate=game.reputation_gate('Келебран')
        self.assertEqual(gate['fee'],25)
        with self.assertRaises(ValueError):game.move('Келебран')
        game.move('Келебран','pay')
        self.assertEqual(game.hero.gold,15)
        self.assertEqual(game.hero.region,'Келебран')
        game.move('Азалтир') # Внутри страны плата не нужна.
        game.move('Келебран');game.move('Глыба')
        game.set_relation('Княжество Бреннор',country,True)
        before=game.hero.gold
        with self.assertRaises(ValueError):game.move('Келебран','pay')
        self.assertEqual(game.hero.gold,before)
        game.set_relation('Княжество Бреннор',country,False)
        game.move('Келебран','fight')
        self.assertEqual(game.hero.region,'Глыба')
        self.assertEqual(game.preparation['kind'],'border')
        game.begin_battle({});resolve(game)
        self.assertEqual(game.last_battle['outcome'],'victory')
        self.assertEqual(game.hero.region,'Келебран')
        self.assertEqual(game.xp,0) # За стражу нет награды охоты.
        self.assertEqual(game.reputation[country],-35)

    def test_fame_spreads_but_reputation_does_not_and_slowly_fades(self):
        game=create();country='Княжество Бреннор'
        game.repute(country,-5,25)
        self.assertEqual(game.reputation[country],-5)
        self.assertGreater(game.fame['Азалтир'],0)
        self.assertEqual(game.reputation['Азалтир'],0)
        before=game.fame[country]
        for _ in range(40):game.wait()
        self.assertLess(game.fame[country],before)

    def test_events_good_bad_cooldown_and_no_repeated_free_entry_roll(self):
        game=Adventure.create('Нора','Женский','Человек','Торговец','Железный меч','Глыба')
        with patch('world_systems.Random') as rng:
            rng.return_value.random.return_value=0
            rng.return_value.choice.return_value='purse'
            game.enter_city()
            self.assertIsNotNone(game.event)
            with self.assertRaises(ValueError):game.search()
            game.resolve_event('bad')
            self.assertEqual(game.hero.gold,39) # 40 − 5 вход + 4 кошель.
            country=REGIONS[game.hero.region].country
            self.assertEqual(game.reputation[country],-6)
            self.assertEqual(game.fame[country],9)
            game.leave_city();game.enter_city()
            self.assertIsNone(game.event)
            for _ in range(5):game.wait()
            game.search();self.assertIsNotNone(game.event)
            game.resolve_event('good')
            self.assertEqual(game.reputation[country],-3)
            self.assertEqual(game.fame[country],12)

    def test_three_weapon_families_and_persistent_new_state(self):
        weapons=[k for k,v in AVAILABLE_ITEMS.items() if v[0]=='Оружие']
        self.assertEqual(len(weapons),3)
        game=create();game.repute('Азалтир',-30,24);game.consumables={'supply:heal':2}
        game.search();game.accept(game.offers[0].id);game.complete(game.active[0].id)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'save.json';game.save(path)
            restored=Adventure.load(path)
            self.assertEqual(restored.preparation,game.preparation)
            self.assertEqual(restored.reputation,game.reputation)
            self.assertEqual(restored.fame,game.fame)
            self.assertEqual(restored.selected_skills,game.selected_skills)
            restored.begin_battle({'supply:heal':1});restored.save(path)
            self.assertEqual(Adventure.load(path).battle,restored.battle)
            data=json.loads(path.read_text());data['world']['selected_skills']=['fake']
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):Adventure.load(path)

    def test_version_three_save_migrates_weapon_and_five_card_hand(self):
        game=create();game.search();game.accept(game.offers[0].id);game.complete(game.active[0].id);game.begin_battle({})
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'save.json';game.save(path)
            data=json.loads(path.read_text());data['version']=3;data.pop('world')
            data['hero']['equipment']['Оружие']='Учебный меч'
            data['bag']=['Учебный меч']
            data['battle']['hand'].append('guard')
            path.write_text(json.dumps(data))
            loaded=Adventure.load(path)
            self.assertEqual(loaded.hero.equipment['Оружие'],'Железный меч')
            self.assertEqual(loaded.bag,['Железный меч'])
            self.assertEqual(len(loaded.battle['hand']),4)
            self.assertEqual(loaded.battle['round'],1)
            self.assertTrue(all(__import__('combat').SKILL_POWER[n]['kind']=='card' for n in loaded.selected_skills))


if __name__=='__main__':unittest.main()
