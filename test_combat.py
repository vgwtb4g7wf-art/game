import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from adventure import Adventure, ITEMS
from combat import CARDS, ITEM_POWER, SKILL_POWER, deck, stats
from world_content import BIOMES, CONSUMABLES
from test_adventure import create, resolve


class CombatTests(unittest.TestCase):
    def start(self, game=None):
        game=game or create()
        game.search()
        game.accept(game.offers[0].id)
        game.complete(game.active[0].id)
        game.begin_battle(dict(list(game.consumables.items())[:1]))
        return game

    def test_every_item_and_skill_contributes_cards(self):
        game=create()
        base=len(deck(game.hero,{}))
        original=game.hero.equipment.copy()
        for item in ITEMS:
            with self.subTest(item=item):
                self.assertIn(item,ITEM_POWER)
                game.hero.equipment=dict.fromkeys(original)
                game.hero.equipment[ITEMS[item][0]]=item
                sources={source for _,source in deck(game.hero,{})}
                self.assertIn(item,sources)
                self.assertTrue(all(k in CARDS for k in ITEM_POWER[item]['cards']))
        game.hero.equipment=original
        game.hero.branches=dict.fromkeys(game.hero.branches,3)
        game.paths['Мощь']='left'
        game.sync_skills()
        game.select_skill('Мудрость')
        self.assertGreater(len(deck(game.hero,{})),base)
        self.assertEqual(len(SKILL_POWER),24)

    def test_passive_armor_dodge_damage_health_accuracy(self):
        game=create()
        plain=stats(game.hero)
        game.bag.extend(['Латный нагрудник','Плащ следопыта'])
        game.equip('Латный нагрудник')
        heavy=stats(game.hero)
        self.assertGreater(heavy['armor'],plain['armor'])
        self.assertGreater(heavy['hp'],plain['hp'])
        self.assertLess(heavy['hit'],plain['hit'])
        game.equip('Плащ следопыта')
        self.assertGreater(stats(game.hero)['dodge'],plain['dodge'])
        game.hero.branches['Мощь']=3
        game.paths['Мощь']='left';game.sync_skills()
        game.select_skill('Владение оружием')
        self.assertGreater(stats(game.hero)['damage'],plain['damage'])
        self.assertGreater(stats(game.hero)['hp'],0)

    def test_energy_hand_and_invalid_actions_are_atomic(self):
        game=self.start()
        b=game.battle
        self.assertEqual(len(b['hand']),4)
        self.assertEqual(b['energy'],3)
        before=json.dumps(b,sort_keys=True)
        for index in (-1,True,100):
            with self.assertRaises(ValueError):game.play_card(index)
        self.assertEqual(before,json.dumps(b,sort_keys=True))
        for operation in (lambda:game.move('Бреннор'),game.enter_city,game.wait,game.search,
                          lambda:game.equip('Железный меч'),lambda:game.buy('supply:heal'),
                          lambda:game.abandon(game.active[0].id),lambda:game.complete(game.active[0].id)):
            with self.assertRaises(ValueError):operation()
        b['energy']=0
        b['hand']=['strike']
        with self.assertRaises(ValueError):game.play_card(0)
        self.assertEqual(b['hand'],['strike'])
        game.end_round()
        self.assertEqual(b['energy'],3)
        self.assertLessEqual(len(b['hand']),4)
        self.assertEqual(b['round'],2)

    def test_shops_depend_on_country_region_city_capital(self):
        game=create()
        roadside=game.shop()
        game.enter_city()
        city=game.shop()
        self.assertNotEqual(roadside['id'],city['id'])
        self.assertGreater(len(city['offers']),len(roadside['offers']))
        self.assertNotIn('capital:seal',{o['card'] for o in city['offers']})
        game.move('Бреннор')
        game.enter_city()
        capital=game.shop()
        self.assertIn('capital:seal',{o['card'] for o in capital['offers']})
        self.assertNotEqual({o['card'] for o in roadside['offers']},{o['card'] for o in capital['offers']})
        game.hero.region='Эланиэль'
        self.assertNotEqual(game.shop()['offers'][1]['card'],roadside['offers'][1]['card'])

    def test_purchase_atomic_stock_gold_and_one_use(self):
        game=create()
        game.buy('supply:heal')
        self.assertEqual(game.hero.gold,35)
        self.assertEqual(game.turn,1)
        with self.assertRaises(ValueError):game.buy('capital:seal')
        self.start(game)
        game.hp-=10
        # Помещаем купленную карту в руку вместо ожидания случайного добора.
        b=game.battle
        b['draw']=[k for k in b['draw'] if k!='supply:heal']
        b['hand']=[k for k in b['hand'] if k!='supply:heal']
        b['hand'].insert(0,'supply:heal')
        game.play_card(0)
        self.assertNotIn('supply:heal',game.consumables)
        self.assertNotIn('supply:heal',b['discard'])
        self.assertEqual(game.hp,game.combat_stats()['hp'])
        game.flee()
        self.assertEqual(game.xp,0)
        self.assertEqual(game.turn,3)
        game.buy('supply:heal');game.buy('supply:heal')
        with self.assertRaises(ValueError):game.buy('supply:heal')

    def test_unplayed_consumable_survives_flee_and_rest_heals(self):
        game=create();game.buy('supply:heal');self.start(game)
        game.flee()
        self.assertEqual(game.consumables['supply:heal'],1)
        game.hp=1
        game.wait()
        self.assertEqual(game.hp,13)
        self.assertTrue(game.active)

    def test_defeat_is_not_a_reward_and_quest_remains(self):
        game=self.start()
        game.hp=1
        for _ in range(50):
            if game.battle is None:break
            game.end_round()
        self.assertIsNone(game.battle)
        self.assertEqual(game.last_battle['outcome'],'defeat')
        self.assertEqual(game.hp,1)
        self.assertEqual(game.hero.gold,30)
        self.assertEqual(game.xp,0)
        self.assertEqual(len(game.active),1)
        self.assertEqual(game.turn,3)

    def test_roundtrip_mid_duel_preserves_future_randomness(self):
        game=create();game.buy('supply:heal');self.start(game)
        game.play_card(0)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'save.json'
            game.save(path);loaded=Adventure.load(path)
            self.assertEqual(game.battle,loaded.battle)
            self.assertEqual(game.consumables,loaded.consumables)
            game.end_round();loaded.end_round()
            self.assertEqual(game.hp,loaded.hp)
            self.assertEqual(game.battle,loaded.battle)
            resolve(game);resolve(loaded)
            self.assertEqual(game.last_battle,loaded.last_battle)
            self.assertEqual(game.xp,loaded.xp)

    def test_miss_shield_armor_and_round_block_expiry(self):
        game=create()
        game.bag.append('Кольчуга');game.equip('Кольчуга')
        self.start(game)
        b=game.battle
        b['hand']=['strike']
        enemy_hp=b['enemy_hp']
        with patch.object(game,'roll') as rng:
            rng.return_value.randint.return_value=100
            game.play_card(0)
        self.assertEqual(b['enemy_hp'],enemy_hp)
        self.assertEqual(b['energy'],2)
        b['hand']=['strike'];b['enemy_block']=6
        with patch.object(game,'roll') as rng:
            rng.return_value.randint.return_value=1
            game.play_card(0)
        self.assertEqual(b['enemy_hp'],enemy_hp)
        self.assertEqual(b['enemy_block'],0)
        b['intent']='attack';b['intent_value']=10;b['block']=4
        hp=game.hp
        with patch.object(game,'roll') as rng:
            rng.return_value.randint.return_value=1
            game.end_round()
        self.assertEqual(game.hp,hp-3) # 10 − 3 брони − 4 блока.
        self.assertEqual(b['block'],0)

    def test_corrupt_duel_and_inventory_rejected_on_load(self):
        game=self.start()
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'save.json';game.save(path)
            original=json.loads(path.read_text())
            for field,value in [('energy',999),('hand',['unknown-card']),('enemy_hp',-1)]:
                data=json.loads(json.dumps(original));data['battle'][field]=value
                path.write_text(json.dumps(data))
                with self.assertRaises(ValueError):Adventure.load(path)

    def test_legacy_save_migration(self):
        game=create();game.search()
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'save.json';game.save(path)
            data=json.loads(path.read_text());data['version']=2
            for field in ('hp','consumables','purchases','battle'):data.pop(field)
            for q in data['offers']:
                for field in ('distance','monster_tier','origin_city'):q.pop(field)
            path.write_text(json.dumps(data))
            loaded=Adventure.load(path)
            self.assertEqual(loaded.hp,loaded.combat_stats()['hp'])
            self.assertGreater(loaded.offers[0].monster_tier,0)

    def test_local_ecology_and_source_venue(self):
        for region in ('Храм Камня','Глыба','Келебран','Эланиэль','Марктбург','Мерилион','Трущобы'):
            game=create();game.hero.region=region;game.search()
            q=game.offers[0]
            self.assertIn(q.monster,BIOMES[__import__('eterion').REGIONS[region].country][1])
            self.assertEqual(q.distance,0)
            self.assertEqual(q.monster_tier,1)
            game.enter_city()
            with self.assertRaises(ValueError):game.accept(q.id)
            game.search()
            self.assertTrue(any(q.city for q in game.offers))
            self.assertTrue(all(q.origin_city for q in game.offers))


if __name__=='__main__':unittest.main()
