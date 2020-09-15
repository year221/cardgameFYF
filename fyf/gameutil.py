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
    n_pile: int = 0
    cards_in_pile: Dict[int, List[int]] = field(default_factory=dict)
    cards_status : Dict[int, str] = field(default_factory=dict)
    n_player: int = 0
    player_id: Dict[int, str] = field(default_factory=dict)
    player_name : Dict[int, str] = field(default_factory=dict)
    status: str = 'Initialization'

    def to_json(self):
        d = asdict(self)
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
                if key in event.face_down_pile:
                    self.cards_status.update({w:'D' for w in all_cards[n_cards_distributed: n_cards_distributed+val]})
                self.cards_in_pile[key] = all_cards[n_cards_distributed: n_cards_distributed+val]
                # send some card facedown
                n_cards_distributed+=val
            self.status='New Game'
            return [copy.deepcopy(self)]
        elif event.type == 'Connect':
            self.player_name.update({event.player_index: event.player_name})
            self.player_id.update({event.player_index: event.player_id})
            print(self)
            return []




@dataclass
class EventCardChange:
    type: str
    player_index: int = -1
    src_pile: int = -1
    dst_pile: int = -1
    cards: List[int] = field(default_factory=list)
    cards_status: Dict[int, str] = field(default_factory=dict)
    player_id : str = ''

@dataclass
class EventGameControl:
    type: str
    n_player : int = 6
    n_card_per_pile : Dict[int, int] = field(default_factory=dict)
    n_pile : int = 19
    face_down_pile : List[int] = field(default_factory=list)
    player_id: str = ''

@dataclass
class EventConnect:
    type: str
    player_name : str = ''
    player_id : str = ''


@dataclass
class Event:
    type: str
    player_index: int = -1
    src_pile: int = -1
    dst_pile: int = -1
    cards: List[int] = field(default_factory=list)
    cards_status: Dict[int, str] = field(default_factory=dict)
    n_player : int = 6
    n_card_per_pile : Dict[int, int] = field(default_factory=dict)
    n_pile : int = 19
    face_down_pile : List[int] = field(default_factory=list)
    player_name : str = ''
    player_id : str = ''

