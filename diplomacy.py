"""Отношения стран и медленная автоматическая дипломатия по соседнему графу."""
from itertools import combinations
from random import Random
from eterion import COUNTRIES,REGIONS,ROUTES

DEMONS='Владычество Нархаз'
ACTIVE_COUNTRIES=tuple(c for c in COUNTRIES if c!=DEMONS)
ALL_PAIRS=tuple(combinations(sorted(COUNTRIES),2))
NEIGHBOR_PAIRS=tuple(sorted({tuple(sorted((REGIONS[a].country,REGIONS[b].country)))
    for a,b,_ in ROUTES if REGIONS[a].country!=REGIONS[b].country
    and DEMONS not in (REGIONS[a].country,REGIONS[b].country)}))
# Эти веса откалиброваны на данном графе: около 30% / 50% / 20% стран с 0 / 1 / 2 войнами.
DEGREE_WEIGHT=(1.0,.8933373317806049,.4859339595368374)


def pair_key(a,b):return '|'.join(sorted((a,b)))


class DiplomacyRules:
    def init_diplomacy(self):
        self.relations={pair_key(a,b):0 for a,b in ALL_PAIRS}
        self.auto_diplomacy=True
        self.diplomacy_step=0

    def war_count(self,country):return sum(country in pair for pair in self.wars)

    def set_relation(self,first,second,war):
        self.ensure_free()
        if first not in COUNTRIES or second not in COUNTRIES or first==second or type(war) is not bool:
            raise ValueError('Выберите две разные страны и состояние войны.')
        pair=tuple(sorted((first,second)))
        if DEMONS in pair:raise ValueError('Нархаз бездействует и не участвует в дипломатии.')
        if war:
            if pair not in NEIGHBOR_PAIRS:raise ValueError('Война возможна только между соседями с прямым маршрутом.')
            if pair not in self.wars and any(self.war_count(c)>=2 for c in pair):
                raise ValueError('Страна не может воевать более чем с двумя соседями.')
            self.wars.add(pair);self.relations[pair_key(*pair)]=-50
        else:
            self.wars.discard(pair);self.relations[pair_key(*pair)]=10

    def tick_diplomacy(self):
        if not self.auto_diplomacy or self.turn%3:return
        self.diplomacy_step+=1
        rng=Random(f'diplomacy:{self.turn}:{self.diplomacy_step}')
        for a,b in ALL_PAIRS:
            if DEMONS in (a,b):continue
            key=pair_key(a,b);old=self.relations[key]
            value=old+rng.choice((-2,-1,0,1,2))
            self.relations[key]=max(-100,min(-10 if (a,b) in self.wars else 100,value))
        for pair in rng.sample(NEIGHBOR_PAIRS,2):
            a,b=pair
            old_a,old_b=self.war_count(a),self.war_count(b)
            peace=pair in self.wars
            new_a,new_b=(old_a-1,old_b-1) if peace else (old_a+1,old_b+1)
            if max(new_a,new_b)>2:continue
            ratio=DEGREE_WEIGHT[new_a]*DEGREE_WEIGHT[new_b]/(DEGREE_WEIGHT[old_a]*DEGREE_WEIGHT[old_b])
            if rng.random()>min(1,ratio):continue
            if peace:
                self.wars.remove(pair);self.relations[pair_key(a,b)]=10
                self.journal.append(f'День {self.turn}: {a} и {b} заключили мир.')
            else:
                self.wars.add(pair);self.relations[pair_key(a,b)]=-50
                self.journal.append(f'День {self.turn}: {a} и {b} объявили войну.')

    def validate_diplomacy(self):
        if (type(self.auto_diplomacy) is not bool or type(self.diplomacy_step) is not int or self.diplomacy_step<0
            or not isinstance(self.relations,dict) or set(self.relations)!={pair_key(a,b) for a,b in ALL_PAIRS}
            or any(type(v) is not int or not -100<=v<=100 for v in self.relations.values())
            or any(p not in NEIGHBOR_PAIRS for p in self.wars)
            or any(self.war_count(c)>2 for c in COUNTRIES)
            or any(self.relations[pair_key(DEMONS,c)]!=0 for c in ACTIVE_COUNTRIES)):
            raise ValueError('Некорректная дипломатия государств.')
