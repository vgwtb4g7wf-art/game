from test_adventure import complete_quest
import json
from pathlib import Path
import tempfile
import unittest

from adventure import Adventure, AVAILABLE_ITEMS, AVATARS
from app import state
from combat import CARDS
from eterion import REGIONS
from test_adventure import create


class RevisionTests(unittest.TestCase):
    def duel(self):
        game=create();game.search();game.accept(game.offers[0].id);game.complete(game.active[0].id);game.begin_battle({})
        return game

    def test_catalog_and_avatar(self):
        self.assertEqual(len(AVATARS),10)
        self.assertEqual(len(set(AVATARS)),10)
        self.assertEqual([sum(v[0]==slot for v in AVAILABLE_ITEMS.values()) for slot in ('Оружие','Доспех','Артефакт')],[3,2,2])
        for race in ('Человек','Дварф','Высший эльф','Лесной эльф'):
            game=Adventure.create('Руна','Мужской',race,'Торговец','Медный амулет','Глыба',avatar='⚓')
            self.assertEqual(game.avatar,'⚓')
        with self.assertRaises(ValueError):
            Adventure.create('Руна','Мужской','Человек','Торговец','Железный меч','Глыба',avatar='bad')

    def test_distance_is_only_a_small_gold_bonus(self):
        found_remote=False
        for city in (False,True):
            game=create();game.in_city=city
            for _ in range(5):
                game.search()
                for q in game.offers:
                    if q.distance:found_remote=True
                    self.assertEqual(q.difficulty,q.monster_tier if q.monster else 1 if __import__('narrative_content').PEACE_QUESTS[q.template]['delivery'] else 2)
                    base=__import__('balance_rewards').hunt_reward(q.difficulty)['gold'] if q.monster else __import__('balance_rewards').peace_reward(__import__('narrative_content').PEACE_QUESTS[q.template]['delivery'],0)['gold']
                    bonus=0 if q.distance==0 else 1 if q.distance<=2 else 2 if q.distance<=5 else 3
                    self.assertEqual(q.gold,base+bonus)
        self.assertTrue(found_remote)

    def test_renowned_hero_enters_town_and_capital_for_free(self):
        game=create();country=REGIONS['Глыба'].country
        game.reputation=20;game.attitudes[country]=10;game.fame=19
        self.assertEqual(game.entry_fee(),5)
        game.fame=20
        self.assertEqual(game.entry_fee(),0)
        game.hero.gold=0;turn=game.turn
        game.enter_city();self.assertEqual(game.hero.gold,0);self.assertEqual(game.turn,turn)
        game.move('Бреннор')
        self.assertEqual(game.entry_fee(),10)
        game.fame=50
        self.assertEqual(game.entry_fee(),0)
        game.enter_city();self.assertEqual(game.hero.gold,0)
        game.reputation=19;game.attitudes[country]=9
        self.assertEqual(game.entry_fee(),10)

    def test_war_toll_is_explicit_atomic_and_interior_stays_free(self):
        game=create();game.hero.gold=100
        game.set_relation('Княжество Бреннор','Азалтир',True)
        self.assertIsNotNone(game.travel_error('Келебран'))
        n=next(n for n in state(game)['neighbors'] if n['name']=='Келебран')
        self.assertIsNone(n['error']);self.assertEqual(n['war_gate']['fee'],60)
        with self.assertRaises(ValueError):game.move('Келебран')
        self.assertEqual(game.hero.gold,100);self.assertEqual(game.turn,1)
        game.move('Бреннор');game.move('Глыба');self.assertEqual(game.hero.gold,100)
        game.reputation=-30
        game.move('Келебран','pay')
        self.assertEqual(game.hero.gold,15) # 60 военный пропуск + 25 за репутацию.
        game.move('Азалтир');self.assertEqual(game.hero.gold,15)
        game.move('Келебран')
        before=game.turn
        with self.assertRaises(ValueError):game.move('Глыба','pay')
        self.assertEqual(game.hero.gold,15);self.assertEqual(game.turn,before)

    def test_choose_one_card_or_none_and_preserve_it_without_spending(self):
        game=self.duel();b=game.battle
        b['hand']=['strike','guard','breath','weapon:sword:parry']
        original=list(b['hand'])
        game.retain_card(1);self.assertEqual(b['retained'],1)
        game.retain_card(2);self.assertEqual(b['retained'],2)
        game.retain_card(2);self.assertIsNone(b['retained'])
        game.retain_card(1);game.end_round()
        self.assertEqual(b['hand'][0],'guard')
        self.assertEqual(b['energy'],2);self.assertIsNone(b['retained'])
        self.assertEqual(len(b['hand']),4)
        for bad in (-1,True,4,'1'):
            with self.assertRaises(ValueError):game.retain_card(bad)
        self.assertEqual(game.consumables,{})

    def test_playing_before_retained_card_updates_index_and_playing_it_clears(self):
        game=self.duel();b=game.battle
        b['hand']=['guard','breath','strike'];game.retain_card(2)
        game.play_card(0);self.assertEqual(b['retained'],1)
        game.play_card(1);self.assertIsNone(b['retained'])
        self.assertEqual(b['energy'],0)
        with self.assertRaises(ValueError):game.play_card(0)

    def test_notifications_and_cancelled_quest_can_be_retaken(self):
        game=create();self.assertFalse(game.skills_notice())
        game.gain_branch('Мощь',50)
        self.assertTrue(game.skills_notice());self.assertIn('Тяжёлый удар',game.skill_notices)
        game.search();q=next(q for q in game.offers if not q.monster and q.target==game.hero.region)
        game.accept(q.id);self.assertNotIn(q,game.offers)
        game.abandon(q.id);self.assertIn(q,game.offers);game.accept(q.id)
        game.xp=95;complete_quest(game,q.id)
        self.assertEqual(game.level_notice,2);self.assertTrue(state(game)['skills_notice'])
        self.assertEqual(game.level_points,1)

    def test_avatar_notices_and_retained_card_save_roundtrip(self):
        game=self.duel();game.avatar='☾';game.level_notice=1;game.retain_card(1)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'save.json';game.save(path);loaded=Adventure.load(path)
            self.assertEqual(loaded.avatar,'☾');self.assertEqual(loaded.level_notice,1)
            self.assertEqual(loaded.battle['retained'],1)
            game.end_round();loaded.end_round()
            self.assertEqual(game.battle,loaded.battle);self.assertEqual(game.hp,loaded.hp)
            data=json.loads(path.read_text());data['battle']['retained']=99
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):Adventure.load(path)

    def test_old_equipment_and_energy_migrate(self):
        game=self.duel()
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'save.json';game.save(path)
            data=json.loads(path.read_text());data['version']=4
            data['hero']['equipment']['Оружие']='Боевой топор';data['bag']=['Боевой топор']
            data['battle']['energy']=3;data['battle'].pop('retained')
            for k in ('avatar','level_notice','skill_notices'):data['world'].pop(k)
            path.write_text(json.dumps(data));loaded=Adventure.load(path)
            self.assertEqual(loaded.bag,['Железный меч']);self.assertEqual(loaded.battle['energy'],2)
            self.assertIsNone(loaded.battle['retained']);self.assertEqual(loaded.avatar,'✦')


if __name__=='__main__':unittest.main()
