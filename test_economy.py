import json,tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from adventure import Adventure
from economy import SUPPLIES,META
from trade import COUNTRY_SUPPLIES,GEAR_PRICES
from combat import CARDS,stats,card_heal
from eterion import REGIONS
from test_adventure import create

class EconomyTests(unittest.TestCase):
    def find(self,g,name):
        for _ in range(2000):
            if any(o['item']==name for o in g.shop()['gear']):return
            g.turn+=5
        self.fail(name)
    def roundtrip(self,g):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'save.json';g.save(p);return Adventure.load(p)

    def test_counts_locations_stability_and_stock(self):
        self.assertEqual(len(COUNTRY_SUPPLIES),8)
        for c,names in COUNTRY_SUPPLIES.items():self.assertEqual(len(names),6)
        for region in ('Глыба','Бреннор','Трущобы'):
            g=create();g.hero.region=region
            for city in (False,True):
                g.in_city=city;depth=2 if city and REGIONS[region].capital else int(city)
                s=g.shop();self.assertEqual(len(s['offers']),5+depth*2);self.assertEqual(len(s['gear']),1+depth)
                self.assertEqual(s,g.shop())
                self.assertEqual(len({o['card'] for o in s['offers']}),len(s['offers']))
                g.hero.gold=1000;key=s['offers'][0]['card']
                for _ in range(3):g.buy(key)
                with self.assertRaises(ValueError):g.buy(key)
                h=self.roundtrip(g);self.assertEqual(h.shop(),g.shop())
                g.turn+=5;self.assertTrue(all(o['left']==3 for o in g.shop()['offers']))

    def test_relation_modifies_counts_reputation_modifies_types(self):
        g=create();country=REGIONS[g.hero.region].country
        for attitude,counts in ((0,(5,1)),(40,(5,2)),(-10,(3,0))):
            g.attitudes[country]=attitude
            self.assertEqual((len(g.shop()['offers']),len(g.shop()['gear'])),counts)
        g.attitudes[country]=0;g.in_city=True
        for rep in (-70,0,70):
            g.reputation=rep
            for cycle in range(1,15):
                g.turn=cycle*5+1;s=g.shop()
                for o in s['offers']:
                    m=SUPPLIES[o['card']]
                    self.assertFalse(rep>0 and m['alignment']=='bad')
                    self.assertFalse(rep<0 and m['alignment']=='good')
                    self.assertFalse(rep==0 and m['alignment']!='neutral' and m['tier']>0)
                for o in s['gear']:
                    self.assertFalse(rep>0 and o['alignment']=='bad')
                    self.assertFalse(rep<0 and o['alignment']=='good')
                    self.assertFalse(rep==0 and o['rare'] and o['alignment']!='neutral')

    def test_actual_cost_sale_no_arbitrage_and_equipped_guard(self):
        g=create();g.hero.gold=1000;g.fame=250;g.attitudes['Княжество Бреннор']=20
        self.find(g,'Кольчуга');offer=next(o for o in g.shop()['gear'] if o['item']=='Кольчуга')
        g.buy('gear:Кольчуга');self.assertEqual(g.sale_price('gear:Кольчуга'),offer['price']*80//100)
        g.equip('Кольчуга')
        with self.assertRaises(ValueError):g.sell('gear:Кольчуга')
        g.unequip('Доспех');g=self.roundtrip(g);start=g.hero.gold;g.sell('gear:Кольчуга')
        self.assertEqual(g.hero.gold,start+offer['price']*80//100)
        with self.assertRaises(ValueError):g.buy('gear:Кольчуга')
        key=g.shop()['offers'][0]['card'];price=g.shop()['offers'][0]['price'];g.buy(key)
        g=self.roundtrip(g);self.assertEqual(g.sale_price(key),price*80//100)
        g.sell(key);self.assertNotIn(key,g.consumables)

    def test_heal_outside_battle_and_paid_rest(self):
        g=create();key='common:bandage';g.consumables[key]=2;g.hp=1;turn=g.turn
        g.use_item(key);self.assertEqual(g.hp,5);self.assertEqual(g.turn,turn)
        g.hp=14
        with self.assertRaises(ValueError):g.use_item(key)
        self.assertEqual(g.consumables[key],1)
        g.hp=1;gold=g.hero.gold
        with self.assertRaises(ValueError):g.wait()
        g.pass_turn();self.assertEqual(g.hp,1);self.assertEqual(g.hero.gold,gold)
        g.in_city=True;g.hp=1;g.wait();self.assertEqual(g.hp,6);self.assertEqual(g.hero.gold,gold-4)
        g.hero.region='Бреннор';g.hp=1;g.hero.gold=10;g.wait();self.assertEqual(g.hp,12);self.assertEqual(g.hero.gold,0)
        g.hp=1
        with self.assertRaises(ValueError):g.wait()
        self.assertEqual(g.hp,1)

    def test_passives_equipped_only_and_rare_loot_gates(self):
        g=create();g.bag.append('Меч верного слова');base=stats(g.hero)['hp']
        g.equip('Меч верного слова');self.assertEqual(stats(g.hero)['hp'],base+2)
        g.unequip('Оружие');self.assertEqual(stats(g.hero)['hp'],base)
        totals={}
        for tier in (1,2,3,4,5):
            ordinary=rare=0
            for seed in range(1500):
                h=create();name=h.roll_loot(tier,str(seed))
                if name:
                    if META[name]['rare']:rare+=1
                    else:ordinary+=1
            totals[tier]=(ordinary,rare)
            self.assertLess((ordinary+rare)/1500,.16)
            if tier<3:self.assertEqual(rare,0)
            else:self.assertGreater(rare,0)
        self.assertGreater(totals[5][1],totals[3][1])

if __name__=='__main__':unittest.main()
