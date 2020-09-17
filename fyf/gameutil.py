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
    player_index_per_id: Dict[str, int] = field(default_factory=dict)
    player_name: Dict[str, str] = field(default_factory=dict)
    player_name_per_id: Dict[str, str] = field(default_factory=dict)
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
            #self.n_player = event.n_player
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
        elif event.type == 'UpdatePlayerInfo':
            self.player_name_per_id.update({event.player_id: event.player_name})
            print(self)
            return [copy.deepcopy(self)]
        elif event.type == 'PlayerDisconnect':
            if event.player_id in self.player_index_per_id:
                index = self.player_index_per_id.pop(event.player_id)
                self.player_name.pop(index)
            if event.player_id in self.player_name_per_id:
                self.player_name_per_id.pop(event.player_id)

            print(self)
            return [copy.deepcopy(self)]
        elif event.type == 'ResetPlayerAndGame':
            self.player_name_per_id = {}
            self.player_index_per_id = {}
            self.player_name = {}
            self.cards_status = {}
            n_cards_distributed = 0
            self.cards_in_pile = {}
            self.status = 'Wait for Player to Join'
            return [copy.deepcopy(self)]
        elif event.type == 'PlayerReady':
            if self.status == 'Wait for Player to Join':
                self.player_name_per_id.update({event.player_id: event.player_name})


                if event.player_id not in self.player_index_per_id:
                    assigned_index = min(set(range(len(self.player_name_per_id))) - set(self.player_index_per_id.values()))
                    self.player_index_per_id.update({event.player_id:assigned_index})

                if (len(self.player_index_per_id) == len(self.player_name_per_id)) and (len(self.player_index_per_id) >=3):
                    # all player recognized. Start game
                    sorted_index = sorted(self.player_index_per_id.values())
                    self.player_index_per_id = {key:sorted_index.index(val) for key, val in self.player_index_per_id.items()}
                    self.player_name = {index_val: self.player_name_per_id[player_id] for player_id, index_val in self.player_index_per_id.items()}
                    self.n_player = len(self.player_index_per_id)
                    self.status = 'Start Game View'
                return [copy.deepcopy(self)]




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

