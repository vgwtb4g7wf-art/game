"""Проверки веток, критов, лечения, брони и отложенной энергии."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from adventure import Adventure
from app import state
from combat import CARDS, SKILL_POWER, card_damage, card_heal, deck, stats
from progression import COSTS, TREES, PATH_NAMES
from test_adventure import create


def master(g,branch,side):
    g.gain_branch(branch,sum(COSTS))
    g.choose_path(branch,side)
    assert g.hero.branches[branch]==6


def start(g):
    g.search();g.accept(g.offers[0].id);g.complete(g.active[0].id);g.begin_battle({})
    return g.battle


def play(g,key,rolls=(50,50)):
    b=g.battle;b['hand']=[key];b['energy']=CARDS[key]['cost']
    with patch.object(g,'roll') as rng:
        rng.return_value.randint.side_effect=rolls
        g.play_card(0)


class SkillTests(unittest.TestCase):
    def test_power_common_and_two_different_strikes(self):
        g=create();g.gain_branch('Мощь',150)
        self.assertEqual(stats(g.hero)['hp'],20)
        self.assertEqual(card_damage(CARDS['strike:1'],g.hero),3)
        self.assertEqual(CARDS['skill:Натиск']['ratio'],150)
        g.gain_branch('Мощь',100);g.choose_path('Мощь','left')
        strikes=[CARDS[k] for k,source in deck(g.hero,{}) if source=='Основы' and k.startswith('strike')]
        self.assertEqual(len(strikes),2)
        self.assertTrue(all(c['ratio']==75 and c['block']==2 for c in strikes))
        self.assertEqual(CARDS['skill:Неприступный бастион']['block'],10)
        self.assertEqual(CARDS['skill:Неприступный бастион']['cost'],1)

    def test_defender_cancels_only_armor_accuracy_penalty(self):
        g=create();g.bag.append('Кольчуга');g.equip('Кольчуга')
        self.assertEqual(stats(g.hero)['hit'],85)
        master(g,'Мощь','left')
        self.assertEqual(stats(g.hero)['hit'],90)
        self.assertEqual(stats(g.hero)['armor'],10)
        g.gain_branch('Знания',150)
        self.assertEqual(stats(g.hero)['hit'],95)
        b=start(g);b['hand']=['strike:2'];b['enemy_hp']=100
        play(g,'strike:2',rolls=(100,))
        self.assertEqual(b['block'],2)
        play(g,'skill:Неприступный бастион',rolls=())
        self.assertEqual(b['block'],12)

    def test_berserker_bonus_is_additive_and_requires_no_equipped_armor(self):
        g=create();master(g,'Мощь','right')
        self.assertEqual(stats(g.hero)['damage'],4)
        for key,want in [('strike:3',6),('weapon:sword:cut',8),('weapon:bow:shot',14),('skill:Прорыв',16),('guard',0),('breath',0)]:
            self.assertEqual(card_damage(CARDS[key],g.hero),want,key)
        self.assertEqual(CARDS['skill:Прорыв']['cost'],2)
        for armor in ('Кожаная куртка','Кольчуга'):
            g.bag.append(armor);g.equip(armor)
            self.assertEqual(card_damage(CARDS['strike:3'],g.hero),4)
        # Даже истраченная броня не означает снятый доспех.
        b=start(g);b['armor']=0
        self.assertEqual(card_damage(CARDS['strike:3'],g.hero),4)

    def test_cunning_common_assassin_and_rogue_cards(self):
        self.assertEqual(PATH_NAMES['Хитрость'],['Ассасин','Плут'])
        g=create();master(g,'Хитрость','left')
        self.assertEqual(stats(g.hero)['crit_chance'],15)
        self.assertEqual(stats(g.hero)['crit_multiplier'],200)
        self.assertIn('guard:2',[k for k,_ in deck(g.hero,{})])
        self.assertEqual((CARDS['guard:2']['block'],CARDS['guard:2']['ratio']),(4,100))
        self.assertEqual((CARDS['skill:Смертельный выпад']['cost'],CARDS['skill:Смертельный выпад']['ratio']),(2,300))
        self.assertEqual((CARDS['skill:Манёвр']['ratio'],CARDS['skill:Манёвр']['block']),(50,4))
        other=create();master(other,'Хитрость','right')
        self.assertIn('guard:3',[k for k,_ in deck(other.hero,{})]);self.assertEqual(CARDS['guard:3']['block'],6)
        c=CARDS['skill:Ловкая передышка'];self.assertEqual((c['ratio'],c['block'],c['heal'],c['cost']),(50,3,3,1))

    def test_rogue_gold_bonus_changes_at_full_hundreds(self):
        g=create();master(g,'Хитрость','right')
        for gold,damage in ((0,4),(99,4),(100,5),(199,5),(200,6),(999,7),(100000,7)):
            g.hero.gold=gold;self.assertEqual(stats(g.hero)['damage'],damage)
        g.hero.gold=100;g.buy(g.shop()['offers'][0]['card'])
        self.assertEqual(stats(g.hero)['damage'],4)
        self.assertEqual(state(g)['card_values']['weapon:sword:cut']['damage'],6)

    def test_crit_roll_threshold_multiplier_and_mitigation_order(self):
        for assassin,chance,mult in ((False,3,150),(True,15,200)):
            for roll,critical in ((chance,True),(chance+1,False)):
                with self.subTest(assassin=assassin,roll=roll):
                    g=create()
                    if assassin:master(g,'Хитрость','left')
                    b=start(g);b['enemy_hp']=100;b['enemy_block']=2;b['enemy_armor']=1
                    play(g,'weapon:sword:cut',rolls=(50,roll))
                    total=6*mult//100 if critical else 6
                    self.assertEqual(b['enemy_hp'],100-(total-3))
                    self.assertEqual(b['enemy_block'],0);self.assertEqual(b['enemy_armor'],0)
                    self.assertEqual(any('Критический удар' in line for line in b['log']),critical)
        g=create();b=start(g);b['enemy_hp']=100
        play(g,'strike',rolls=(100,))
        self.assertEqual(b['enemy_hp'],100)  # Промах не проверяет крит.
        with patch('combat.effects',return_value={'crit_chance':99}):self.assertEqual(stats(g.hero)['crit_chance'],15)

    def test_fire_borrowed_energy_miss_ring_and_roundtrip(self):
        g=create();master(g,'Знания','left');g.select_skill('Огненный столб')
        self.assertEqual(PATH_NAMES['Знания'],['Маг огня','Водный целитель'])
        self.assertEqual(stats(g.hero)['damage'],5);self.assertEqual(stats(g.hero)['hit'],95)
        self.assertIn('breath:2',[k for k,_ in deck(g.hero,{})])
        self.assertEqual((CARDS['breath:2']['ratio'],CARDS['breath:2']['heal']),(125,0))
        g.bag.append('Кольцо янтаря');g.equip('Кольцо янтаря');b=start(g)
        key='skill:Огненный столб'
        # Оставляем настоящую колоду с долгом, чтобы проверить сохранение между раундами.
        for pile in ('draw','hand','discard'):
            b[pile]=[c for c in b[pile] if c!=key]
        b['hand'].append(key);index=b['hand'].index(key)
        with patch.object(g,'roll') as rng:
            rng.return_value.randint.return_value=100;g.play_card(index)
        self.assertEqual(b['next_energy'],-1)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'save.json';g.save(p);loaded=Adventure.load(p)
            self.assertEqual(loaded.battle,g.battle)
            for game in (g,loaded):game.end_round()
            self.assertEqual(g.battle,loaded.battle);self.assertEqual(b['energy'],1)
            for game in (g,loaded):game.end_round()
            self.assertEqual(g.battle,loaded.battle);self.assertEqual(b['energy'],2)
        b['enemy_hp']=100;b['enemy_armor']=0;play(g,key);self.assertEqual(b['enemy_hp'],87)
        play(g,'artifact:ring',rolls=());self.assertEqual(b['next_energy'],0)
        g.end_round();self.assertEqual(b['energy'],2)

    def test_healer_amplifies_all_healing_and_adds_persistent_battle_armor(self):
        g=create();master(g,'Знания','right');b=start(g)
        self.assertEqual(stats(g.hero)['hit'],95)
        self.assertEqual(card_heal(CARDS['breath:3'],g.hero),6)
        self.assertEqual(card_heal(CARDS['supply:heal'],g.hero),6)
        self.assertEqual(card_heal(CARDS['skill:Передышка'],g.hero),5)
        self.assertEqual(CARDS['skill:Передышка']['block'],3)
        g.hp=1;play(g,'skill:Восстановление',rolls=())
        self.assertEqual(g.hp,6);self.assertEqual(b['armor'],3)
        b['intent_value']=2;b['block']=0;g.end_round()
        self.assertEqual(g.hp,6);self.assertEqual(b['armor'],1)
        play(g,'breath:3',rolls=());self.assertEqual(g.hp,12)
        play(g,'skill:Восстановление',rolls=());self.assertEqual(g.hp,14);self.assertEqual(b['armor'],4)
        g.flee();start(g);self.assertEqual(g.battle['armor'],0)

    def test_combined_passives_and_api_card_numbers(self):
        g=create();master(g,'Мощь','right');master(g,'Хитрость','right');master(g,'Знания','right');g.hero.gold=200
        values=state(g)['card_values']
        self.assertEqual(stats(g.hero)['damage'],6)
        self.assertEqual(values['strike:3'],{'ratio':150,'damage':9,'heal':0})
        self.assertEqual(values['skill:Ловкая передышка'],{'ratio':100,'damage':6,'heal':5})
        self.assertEqual(values['breath:3']['heal'],6)
        self.assertEqual(values['guard:3']['damage'],0)

    def test_v7_renamed_selected_skills_and_old_battle_migrate(self):
        g=create();master(g,'Мощь','left');g.select_skill('Неприступный бастион');start(g)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'save.json';g.save(p);data=json.loads(p.read_text());data['version']=7
            data['world']['selected_skills']=['Ответный выпад']
            data['world']['skill_notices']=['Стальная стойкость','Сокрушающий удар']
            data['battle']['hand']=['strike:2','skill:Ответный выпад']
            p.write_text(json.dumps(data));loaded=Adventure.load(p)
            self.assertEqual(loaded.hero.branches['Мощь'],6)
            self.assertEqual(loaded.selected_skills,['Неприступный бастион'])
            self.assertEqual(loaded.skill_notices,['Мастер доспехов','Защитный удар'])
            self.assertIn('skill:Неприступный бастион',loaded.battle['draw']+loaded.battle['hand'])
            self.assertTrue(all(k in CARDS for k in loaded.battle['draw']+loaded.battle['hand']))
            loaded.save(p);again=Adventure.load(p);self.assertEqual(again.battle,loaded.battle)


if __name__=='__main__':unittest.main()
