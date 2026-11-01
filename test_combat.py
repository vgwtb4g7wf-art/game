import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from adventure import Adventure,AVAILABLE_ITEMS
from combat import CARDS,ITEM_POWER,SKILL_POWER,deck,stats,card_damage,selectable
from world_content import BIOMES,enemy_profile
from progression import TREES,COSTS,unlocked
from test_adventure import create,resolve


class CombatTests(unittest.TestCase):
    def start(self,game=None,chosen=None):
        game=game or create();game.search();game.accept(game.offers[0].id)
        game.complete(game.active[0].id);game.begin_battle(chosen or {})
        return game

    def force_hit(self,game,operation):
        with patch.object(game,'roll') as rng:
            rng.return_value.randint.return_value=50
            operation()

    def test_base_damage_and_cards(self):
        game=create()
        self.assertEqual(stats(game.hero)['damage'],4)
        self.assertEqual(stats(game.hero)['hp'],14)
        self.assertEqual(card_damage(CARDS['strike'],game.hero),2)
        self.assertEqual(CARDS['guard']['block'],2)
        self.assertEqual(CARDS['breath']['heal'],2)
        self.assertEqual(CARDS['guard']['name'],'Уворот')
        self.assertEqual(CARDS['breath']['name'],'Поддержка')

    def test_exact_weapon_properties(self):
        game=create()
        for name,ratios,blocks,costs in [
            ('Короткий кинжал',[150,150],[0,0],[1,1]),
            ('Железный меч',[150,100],[0,2],[1,1]),
            ('Дорожный лук',[300,0],[0,4],[2,1])]:
            cards=[CARDS[k] for k in ITEM_POWER[name]['cards']]
            self.assertEqual([c['ratio'] for c in cards],ratios)
            self.assertEqual([c['block'] for c in cards],blocks)
            self.assertEqual([c['cost'] for c in cards],costs)
        self.assertEqual(ITEM_POWER['Короткий кинжал']['cards'][0],ITEM_POWER['Короткий кинжал']['cards'][1])
        self.assertEqual(card_damage(CARDS['weapon:bow:shot'],game.hero),12)
        self.assertEqual(card_damage(CARDS['weapon:dagger'],game.hero),6)

    def test_armor_only_gives_refillable_pool_and_chain_accuracy_penalty(self):
        game=create();game.bag+=['Кольчуга','Кожаная куртка']
        self.assertEqual(ITEM_POWER['Кожаная куртка']['cards'],[])
        game.equip('Кожаная куртка');self.assertEqual(stats(game.hero)['armor'],4)
        game.equip('Кольчуга');self.assertEqual(stats(game.hero)['armor'],8)
        self.assertNotIn('dodge',stats(game.hero));self.assertEqual(stats(game.hero)['hit'],85)
        self.assertEqual(stats(game.hero)['hp'],14)
        self.start(game);b=game.battle
        hp=game.hp;b['intent']='attack';b['intent_value']=10;b['block']=4
        self.force_hit(game,game.end_round)
        self.assertEqual(game.hp,hp);self.assertEqual(b['armor'],2);self.assertEqual(b['block'],0)
        b['intent']='attack';b['intent_value']=5
        self.force_hit(game,game.end_round)
        self.assertEqual(game.hp,hp-3);self.assertEqual(b['armor'],0)
        game.flee();self.assertFalse(game.dead)
        self.start(game);self.assertEqual(game.battle['armor'],8)

    def test_passives_always_work_and_only_cards_are_selected(self):
        game=create();before=stats(game.hero)['hp']
        game.gain_branch('Мощь',sum(COSTS[:3]))
        self.assertEqual(stats(game.hero)['hp'],before+6)
        self.assertEqual(game.hero.branches['Мощь'],3)
        with self.assertRaises(ValueError):game.select_skill('Закалка')
        with self.assertRaises(ValueError):game.select_skill('Тяжёлый удар')
        game.select_skill('Натиск')
        self.assertIn('skill:Натиск',[k for k,_ in deck(game.hero,{})])
        game.select_skill('Натиск');self.assertEqual(stats(game.hero)['hp'],before+6)
        self.assertIn('strike:1',[k for k,_ in deck(game.hero,{})])
        game.gain_branch('Мощь',COSTS[3]);game.choose_path('Мощь','right');game.gain_branch('Мощь',sum(COSTS[4:]))
        self.assertEqual(stats(game.hero)['damage'],4)
        self.assertEqual(card_damage(CARDS['strike:3'],game.hero),6)
        self.assertIn('strike:3',[k for k,_ in deck(game.hero,{})])

    def test_combat_tree_shape_and_diplomacy_has_no_cards(self):
        for branch,t in TREES.items():
            for side in ('common','left','right'):
                self.assertEqual([SKILL_POWER[n]['kind'] for n in t[side]],['passive']*3 if branch=='Дипломатия' else ['upgrade','card','passive'])
        self.assertTrue(all(SKILL_POWER[n]['card'] is None for seq in TREES['Дипломатия'].values() for n in seq))

    def test_energy_hand_and_invalid_actions_are_atomic(self):
        game=self.start();b=game.battle
        self.assertEqual(len(b['hand']),4);self.assertEqual(b['energy'],2)
        before=json.dumps(b,sort_keys=True)
        for index in (-1,True,100):
            with self.assertRaises(ValueError):game.play_card(index)
        self.assertEqual(before,json.dumps(b,sort_keys=True))
        for op in (lambda:game.move('Бреннор'),game.enter_city,game.wait,game.search,
                   lambda:game.equip('Железный меч'),lambda:game.buy('supply:heal'),lambda:game.abandon(game.active[0].id)):
            with self.assertRaises(ValueError):op()
        b['energy']=0;b['hand']=['strike']
        with self.assertRaises(ValueError):game.play_card(0)
        game.end_round();self.assertEqual(b['energy'],2);self.assertLessEqual(len(b['hand']),4)

    def test_miss_block_and_enemy_armor_are_consumed(self):
        game=self.start();b=game.battle;b['hand']=['strike'];enemy_hp=b['enemy_hp']
        with patch.object(game,'roll') as rng:
            rng.return_value.randint.return_value=5000;game.play_card(0)
        self.assertEqual(b['enemy_hp'],enemy_hp)
        b['hand']=['weapon:sword:cut'];b['enemy_block']=2;b['enemy_armor']=3
        self.force_hit(game,lambda:game.play_card(0))
        self.assertEqual(b['enemy_hp'],enemy_hp-1);self.assertEqual(b['enemy_armor'],0);self.assertEqual(b['enemy_block'],0)

    def test_ring_is_once_per_battle_and_banks_exactly_one_energy(self):
        game=create();game.bag.append('Кольцо янтаря');game.equip('Кольцо янтаря');self.start(game)
        b=game.battle;key='artifact:ring'
        b['draw']=[k for k in b['draw'] if k!=key];b['hand']=[key]
        game.play_card(0);self.assertEqual(b['energy'],1);self.assertEqual(b['next_energy'],1)
        self.assertIn(key,b['exhausted']);self.assertNotIn(key,b['discard'])
        game.end_round();self.assertEqual(b['energy'],3);self.assertEqual(b['next_energy'],0)
        game.end_round();self.assertEqual(b['energy'],2)
        self.assertNotIn(key,b['hand']+b['draw']+b['discard'])
        game.flee();self.start(game)
        self.assertEqual((game.battle['hand']+game.battle['draw']).count(key),1)

    def test_amulet_once_block_eight_and_consumable_separate(self):
        game=create();game.bag.append('Медный амулет');game.equip('Медный амулет')
        game.consumables.update({'supply:heal':1});self.start(game,{'supply:heal':1});b=game.battle
        for key in ('artifact:amulet','supply:heal'):
            b['draw']=[k for k in b['draw'] if k!=key];b['hand']=[k for k in b['hand'] if k!=key]
        b['hand']=['artifact:amulet','supply:heal'];game.hp-=4
        game.play_card(0);self.assertEqual(b['block'],8)
        game.play_card(0);self.assertEqual(game.hp,game.combat_stats()['hp'])
        self.assertNotIn('supply:heal',game.consumables)
        self.assertIn('artifact:amulet',b['exhausted'])

    def test_flee_fails_quest_loses_fame_and_can_kill(self):
        game=self.start();b=game.battle;quest=game.active[0];country=__import__('eterion').REGIONS[quest.target].country
        before=game.fame;damage=b['profile']['escape'];hp=game.hp
        game.flee();self.assertEqual(game.hp,hp-damage)
        self.assertIn(quest.id,game.failed);self.assertEqual(game.active,[])
        self.assertEqual(game.fame,max(0,before-b['profile']['fame_loss']))
        self.assertEqual(game.xp,0);self.assertEqual(game.turn,3)
        self.start(game);game.hp=1;game.battle['armor']=8;game.battle['block']=99
        game.flee();self.assertTrue(game.dead);self.assertEqual(game.hp,0)
        with self.assertRaises(ValueError):game.wait()
        with self.assertRaises(ValueError):game.search()
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'dead.json';game.save(path);loaded=Adventure.load(path)
            self.assertTrue(loaded.dead);self.assertEqual(loaded.hp,0)

    def test_unplayed_consumable_survives_flee_and_rest_heals(self):
        game=create();game.consumables.update({'supply:heal':1});self.start(game,{'supply:heal':1});game.flee()
        self.assertEqual(game.consumables['supply:heal'],1);game.hp=1
        with self.assertRaises(ValueError):game.wait()
        game.pass_turn();self.assertEqual(game.hp,1)
        self.assertEqual(game.active,[]);self.assertEqual(len(game.failed),1)

    def test_defeat_is_death_and_does_not_give_reward(self):
        game=self.start();game.hp=1
        for _ in range(50):
            if not game.battle:break
            game.end_round()
        self.assertTrue(game.dead);self.assertEqual(game.hp,0);self.assertEqual(game.xp,0)
        self.assertEqual(len(game.failed),1);self.assertEqual(game.active,[])

    def test_roundtrip_mid_duel_preserves_randomness_armor_and_artifact(self):
        game=create();game.bag+=['Кольчуга','Кольцо янтаря'];game.equip('Кольчуга');game.equip('Кольцо янтаря');self.start(game)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'save.json';game.save(path);loaded=Adventure.load(path)
            self.assertEqual(game.battle,loaded.battle)
            game.end_round();loaded.end_round();self.assertEqual(game.hp,loaded.hp);self.assertEqual(game.battle,loaded.battle)
            resolve(game);resolve(loaded);self.assertEqual(game.last_battle,loaded.last_battle)

    def test_corrupt_duel_rejected(self):
        game=self.start()
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'save.json';game.save(path);original=json.loads(path.read_text())
            for field,value in [('energy',99),('armor',99),('hand',['bad']),('exhausted',['strike'])]:
                data=json.loads(json.dumps(original));data['battle'][field]=value;path.write_text(json.dumps(data))
                with self.assertRaises(ValueError):Adventure.load(path)

    def test_diplomacy_grants_once_discounts_and_limits(self):
        game=create();start=game.hero.gold
        # Initial diplomacy rank 1, then health, gold, reputation, extra quest, discount/stock.
        game.gain_branch('Дипломатия',sum(COSTS[1:3]));self.assertEqual(game.hero.gold,start+40)
        game.gain_branch('Дипломатия',0);self.assertEqual(game.hero.gold,start+40)
        game.gain_branch('Дипломатия',COSTS[3]);game.choose_path('Дипломатия','left');game.gain_branch('Дипломатия',sum(COSTS[4:]))
        self.assertEqual(game.quest_limit(),3);self.assertEqual(game.offer_limit(),3)
        self.assertTrue(game.reputation>=5)
        self.assertEqual(game.shop()['discount'],15)
        self.assertTrue(__import__('combat').effects(game.hero).get('stock'))
        self.assertTrue(all(o['price']>=1 for o in game.shop()['offers']))
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'s.json';game.save(path);loaded=Adventure.load(path)
            loaded.gain_branch('Дипломатия',0);self.assertEqual(loaded.hero.gold,game.hero.gold)
        other=create();other.gain_branch('Дипломатия',sum(COSTS[1:3]));other.gain_branch('Дипломатия',COSTS[3]);other.choose_path('Дипломатия','right');other.gain_branch('Дипломатия',sum(COSTS[4:]))
        self.assertEqual(other.offer_limit(),5);self.assertEqual(other.quest_limit(),2)
        other.search();self.assertEqual(len(other.offers),5)

    def test_chances_all_multiples_of_five_and_monster_scaling(self):
        self.assertTrue(all(c['accuracy']%5==0 for c in CARDS.values()))
        for name in AVAILABLE_ITEMS:
            game=create();game.bag.append(name);game.equip(name)
            self.assertEqual(game.combat_stats()['hit']%5,0);self.assertNotIn('dodge',game.combat_stats())
        for _,names,*_ in BIOMES.values():
            previous=0
            for tier,name in enumerate(names,1):
                profile=enemy_profile(name,tier);self.assertGreater(profile['hp'],previous);previous=profile['hp']
                self.assertNotIn('hit',profile);self.assertGreater(profile['escape'],0)

    def test_shop_locality_and_city_sources(self):
        game=create();road=game.shop();game.enter_city();city=game.shop()
        self.assertGreater(len(city['offers']),len(road['offers']))
        self.assertNotIn('capital:seal',[o['card'] for o in city['offers']])
        game.move('Бреннор');game.enter_city()
        self.assertIn('capital:seal',[o['card'] for o in game.shop()['offers']])


if __name__=='__main__':unittest.main()
