"""Недельный ассортимент, цены приобретения, продажа, трофеи и отдых."""
from random import Random
from math import ceil
from eterion import REGIONS,ITEMS
from combat import CARDS,card_heal,effects
from world_content import CONSUMABLES
from social_rules import GEAR_PRICES,fame_stage,reputation_stage
from trade import META,SUPPLIES

class EconomyRules:
    def shop(self):
        country=REGIONS[self.hero.region].country;cycle=(self.turn-1)//5
        black=self.hero.region=='Трущобы';allowed=(reputation_stage(self.reputation)<=0) if black else self.attitudes[country]>-40
        depth=2 if self.in_city and REGIONS[self.hero.region].capital else 1 if self.in_city else 0
        attitude=self.attitudes[country];stage=fame_stage(self.fame) if attitude>=10 else 0
        discount=min(40,effects(self.hero).get('discount',0)+(10 if stage>=4 else 5 if stage>=3 else 0))
        def eligible(meta):
            side=meta['alignment'];rep=reputation_stage(self.reputation)
            return side=='neutral' or (side=='good' and (rep>0 or (rep==0 and not meta.get('rare',False)))) or (side=='bad' and (rep<0 or (rep==0 and not meta.get('rare',False))))
        def available_supply(meta,level):
            if meta.get('guild') and not effects(self.hero).get('stock'):return False
            if black:return meta['black'] or (not meta['black'] and meta['country'] in (None,country) and eligible(meta) and meta['tier']<=level)
            if meta['black'] or meta['country'] not in (None,country) or not eligible(meta):return False
            if meta['alignment']!='neutral' and meta['tier']>0 and reputation_stage(self.reputation)==0:return False
            return meta['tier']<=level
        keys=[];equipment=[]
        for level in range(depth+1):
            rng=Random(f'store:{self.hero.region}:{cycle}:{level}:{reputation_stage(self.reputation)}')
            pool=[k for k,m in SUPPLIES.items() if available_supply(m,level) and k not in keys]
            # Более глубокие помещения в первую очередь открывают новые городские/столичные товары.
            rng.shuffle(pool);pool.sort(key=lambda k:SUPPLIES[k]['tier']!=level)
            keys+=pool[:5 if level==0 else 2]
            gp=[n for n,m in META.items() if (black or not m['black']) and eligible(m) and n not in equipment]
            # Пассивные вещи реже попадают в продажу; в городах вероятность выше.
            ordinary=[n for n in gp if not META[n]['rare']];rare=[n for n in gp if META[n]['rare']]
            candidates=rare if rare and rng.random()<(.08,.18,.30)[level] else ordinary or rare
            if candidates:equipment.append(rng.choice(candidates))
        if attitude>=40:
            rng=Random(f'favored:{self.hero.region}:{cycle}:{depth}')
            extra=[n for n,m in META.items() if n not in equipment and (black or not m['black']) and eligible(m)]
            if extra:equipment.append(rng.choice(extra))
        elif attitude<=-10:
            rng=Random(f'hostile:{self.hero.region}:{cycle}:{depth}')
            if equipment:equipment.pop(rng.randrange(len(equipment)))
            for _ in range(min(2,len(keys))):keys.pop(rng.randrange(len(keys)))
        store_id=f'{self.hero.region}:market:{cycle}'
        def left(key,stock):return max(0,stock-self.purchases.get(store_id+'|'+key,0))
        name=('Чёрный рынок' if black else ('Столичный магазин' if depth==2 else 'Городской магазин' if depth else 'Дорожный магазин'))+' · '+self.hero.region
        return dict(id=store_id,name=name,access_reason=('Чёрный рынок закрыт при хорошей репутации.' if black else 'Отношение страны ≤ −40: торговцы отказываются обслуживать героя.'),description='Недельная поставка; 80% цены приобретения при продаже.',accessible=allowed,
            discount=discount,refresh_in=5-(self.turn-1)%5,
            gear=[dict(item=n,price=max(1,GEAR_PRICES[n]*(100-discount)//100),owned=n in self.bag,left=left('gear:'+n,1),**META[n]) for n in equipment] if allowed else [],
            offers=[dict(card=k,price=max(1,CONSUMABLES[k]['price']*(100-discount)//100),left=left(k,3)) for k in keys] if allowed else [])

    def sale_price(self,key):
        if not isinstance(key,str):raise ValueError('Выберите предмет.')
        if key.startswith('gear:'):
            name=key[5:]
            if name not in self.bag:raise ValueError('Нет такого предмета.')
            basis=self.item_costs.get(name,GEAR_PRICES[name])
        else:
            if self.consumables.get(key,0)<1:raise ValueError('Нет такого расходника.')
            basis=self.consumable_costs.get(key,[CONSUMABLES[key]['price']])[0]
        return max(1,basis*80//100)

    def buy(self,key):
        self.ensure_free()
        if not isinstance(key,str):raise ValueError('Выберите товар.')
        shop=self.shop()
        if not shop['accessible']:raise ValueError('Магазин недоступен.')
        gear=key.startswith('gear:');name=key[5:] if gear else key
        offer=next((o for o in (shop['gear'] if gear else shop['offers']) if o['item' if gear else 'card']==name),None)
        if not offer or offer['left']<1:raise ValueError('Товар отсутствует в текущем ассортименте.')
        if gear and name in self.bag:raise ValueError('Этот предмет уже есть.')
        if not gear and sum(self.consumables.values())>=15:raise ValueError('Можно нести не больше 15 расходников.')
        if self.hero.gold<offer['price']:raise ValueError('Недостаточно золота.')
        self.hero.gold-=offer['price'];purchase=shop['id']+'|'+key;self.purchases[purchase]=self.purchases.get(purchase,0)+1
        if gear:self.bag.append(name);self.item_costs[name]=offer['price']
        else:
            count=self.consumables.get(key,0)
            self.consumable_costs.setdefault(key,[CONSUMABLES[key]['price']]*count).append(offer['price'])
            self.consumables[key]=count+1
        self.journal.append(f'Куплено: {CARDS[key]["name"] if not gear else name} · {offer["price"]} монет.')

    def sell(self,key):
        self.ensure_free()
        if not self.shop()['accessible']:raise ValueError('Торговец не обслуживает героя.')
        price=self.sale_price(key)
        if key.startswith('gear:'):
            name=key[5:]
            if name in self.hero.equipment.values():raise ValueError('Сначала снимите предмет.')
            self.bag.remove(name);self.item_costs.pop(name,None)
        else:self.consume(key)
        self.hero.gold+=price;self.journal.append(f'Продажа: +{price} монет (80% цены приобретения).')

    def consume(self,key):
        self.consumables[key]-=1
        costs=self.consumable_costs.get(key)
        if costs:
            costs.pop(0)
            if not costs:self.consumable_costs.pop(key,None)
        if self.consumables[key]==0:del self.consumables[key]

    def use_item(self,key):
        self.ensure_free()
        if self.consumables.get(key,0)<1 or key not in CONSUMABLES or not CARDS[key]['heal']:raise ValueError('Нужен имеющийся лечебный расходник.')
        maximum=self.combat_stats()['hp']
        if self.hp>=maximum:raise ValueError('Здоровье уже полное; предмет не потрачен.')
        amount=min(maximum-self.hp,card_heal(CARDS[key],self.hero))
        self.consume(key);self.hp+=amount
        self.journal.append(f'Лечение вне боя: +{amount} HP. Остальные боевые эффекты не применяются.')

    def rest_offer(self):
        maximum=self.combat_stats()['hp']
        if not self.in_city:return dict(cost=0,heal=0,label='Отдых недоступен вне города')
        capital=REGIONS[self.hero.region].capital
        return dict(cost=10 if capital else 4,heal=ceil(maximum*(.75 if capital else .30)),label='Отдых в столице' if capital else 'Отдых в городе')

    def wait(self):
        self.ensure_free()
        if not self.in_city:raise ValueError('Бесплатных привалов больше нет. Восстановитесь предметом или оплатите отдых в городе.')
        offer=self.rest_offer()
        if self.in_city and self.hp>=self.combat_stats()['hp']:raise ValueError('Здоровье полное; отдых не требуется.')
        if self.hero.gold<offer['cost']:raise ValueError('Недостаточно монет на отдых.')
        amount=min(offer['heal'],self.combat_stats()['hp']-self.hp)
        self.hero.gold-=offer['cost'];self.hp+=amount
        self.record(f'{offer["label"]}: +{amount} HP, плата {offer["cost"]} монет.')

    def roll_loot(self,tier,seed):
        rng=Random('loot:'+seed)
        chance=.07 if tier<3 else .12
        if rng.random()>=chance:return None
        rare=tier>=3 and rng.random()<(.18 if tier==3 else .25 if tier==4 else .35)
        pool=[n for n,m in META.items() if n not in self.bag and m['rare']==rare and not m['black']]
        if not pool:return None
        name=rng.choice(pool);self.bag.append(name);self.item_costs[name]=GEAR_PRICES[name]
        self.journal.append(f'Находка после боя: {name}'+(' · пассивное свойство.' if rare else '.'))
        return name
