from typing import List, Dict, Tuple
from dataclasses import dataclass, asdict, field
import json
import random
import copy
def json_obj_hook(d):
    if isinstance(d, dict):
        return {int(k) if k.lstrip('-').isdigit() else k: v for k, v in d.items()}
    else:
        return d

@dataclass
class GameState:
    n_pile: int
    #cards_in_pile: Dict[int, List[Tuple[int, str]]]
    cards_in_pile: Dict[int, List[int]]#Dict[int, List[Tuple[int, str]]]
    cards_status : Dict[int, str]
    n_player: int
    player_assignment: Dict[int, str]
    status: str

    def to_json(self):
        d = asdict(self)
        # dict(
        #     n_pile=self.n_pile,
        #     cards_in_pile=self.cards_in_pile,
        #     cards_status=self.cards_status,
        #     n_player=self.n_player,
        #     player_assignment=self.player_assignment,
        #     status=self.status
        # )
         #print(d)
        return json.dumps(d)

    def update_from_event(self, event):
        #print(event)
        #print(self.cards_in_pile.keys())
        if event.type == 'Move':
            if event.src_pile in self.cards_in_pile.keys() and event.dst_pile in self.cards_in_pile.keys():

                if not (set(event.cards) - set(self.cards_in_pile[event.src_pile])):
                    for card in event.cards:
                        self.cards_in_pile[event.src_pile].remove(card)
                        self.cards_in_pile[event.dst_pile].append(card)
            self.status = 'In Game'
            return [copy.deepcopy(self)]
        if event.type == 'Remove':
            if event.src_pile in self.cards_in_pile.keys():

                if not (set(event.cards) - set(self.cards_in_pile[event.src_pile])):
                    for card in event.cards:
                        self.cards_in_pile[event.src_pile].remove(card)
            self.status = 'In Game'
            return [copy.deepcopy(self)]
        elif event.type == 'Flip':
            self.cards_status.update(event.cards_status)
            self.status = 'In Game'
            return [copy.deepcopy(self)]

        elif event.type == 'StartNewGame':
            self.n_player = event.n_player
            self.n_pile = event.n_pile
            all_cards = list(range(sum(event.n_card_per_pile.values())))
            self.cards_status = {w: 'U' for w in all_cards}
            random.seed(a=None)
            random.shuffle(all_cards)
            n_cards_distributed = 0
            self.cards_in_pile = {w:[] for w in range(self.n_pile)}
            for key, val in event.n_card_per_pile.items():
                self.cards_in_pile[key] = all_cards[n_cards_distributed: n_cards_distributed+val]
                n_cards_distributed+=val
            self.status='New Game'


            return [copy.deepcopy(self)]




@dataclass
class Event:
    type: str
    player_index: int = -1
    src_pile: int = -1
    dst_pile: int = -1
    cards: List[int] = field(default_factory=list)#Tuple[int, str]] = []
    cards_status: Dict[int, str] = field(default_factory=dict)
    n_player : int = 6
    n_card_per_pile : Dict[int, int] = field(default_factory=dict)
    n_pile : int = 19




    def to_dict(self):
         return asdict(self)
    #     return dict(
    #         type=self.type,
    #         player_index=self.player_index,
    #         src_pile=self.src_pile,
    #         dst_pile=self.dst_pile,
    #         cards=self.cards,
    #         cards_status=self.cards_status
    #     )
