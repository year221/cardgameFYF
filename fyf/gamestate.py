from typing import List, Dict, Tuple
from dataclasses import dataclass, asdict, field
import json
import random
import copy
import math
def json_obj_hook(d):
    if isinstance(d, dict):
        return {int(k) if k.lstrip('-').isdigit() else k: v for k, v in d.items()}
    else:
        return d

MAX_DECK_SIZE=54

@dataclass
class GameState:
    n_pile: int = 0
    cards_in_pile: Dict[int, List[int]] = field(default_factory=dict)
    cards_status : Dict[int, str] = field(default_factory=dict)
    pile_property: Dict[int, Dict] = field(default_factory=dict)
    n_player: int = 0
    player_index_per_id: Dict[str, int] = field(default_factory=dict)
    player_name: Dict[str, str] = field(default_factory=dict)
    player_name_per_id: Dict[str, str] = field(default_factory=dict)
    status: str = 'Wait for Player to Join'

    def to_json(self):
        d = asdict(self)
        return json.dumps(d)

    def start_new_game(self):
        all_non_zero_ids = [w for key, w in self.player_index_per_id.items() if w >= 0]
        sorted_index = sorted(all_non_zero_ids)
        self.player_index_per_id = {key: (sorted_index.index(val) if val >= 0 else val) for key, val in
                                    self.player_index_per_id.items()}
        self.player_name = {index_val: self.player_name_per_id[player_id] for player_id, index_val in
                            self.player_index_per_id.items() if index_val >= 0}
        self.n_player = len(all_non_zero_ids)
        self.status = 'Starting New Game'


    def update_from_event(self, event):
        #print(event)
        #print(self.cards_in_pile.keys())
        if event.type == 'GetGameState':
            return [copy.deepcopy(self)]
        elif event.type == 'Move':
            if event.src_pile not in self.cards_in_pile.keys():
                self.cards_in_pile.update({event.src_pile:[]})
            if event.dst_pile not in self.cards_in_pile.keys():
                self.cards_in_pile.update({event.dst_pile:[]})

            if not (set(event.cards) - set(self.cards_in_pile[event.src_pile])):
                for card in event.cards:
                    self.cards_in_pile[event.src_pile].remove(card)
                    self.cards_in_pile[event.dst_pile].append(card)
            self.status = 'In Game'
            return [copy.deepcopy(self)]

        elif event.type == 'Add':

            if event.dst_pile not in self.cards_in_pile.keys():
                self.cards_in_pile.update({event.dst_pile:[]})
            for card in event.cards:
                if card not in self.cards_in_pile[event.dst_pile]:
                    self.cards_in_pile[event.dst_pile].append(card)
            self.cards_status.update(event.cards_status)
            self.status = 'In Game'
            return [copy.deepcopy(self)]
        elif event.type == 'Remove':
            if event.src_pile not in self.cards_in_pile.keys():
                self.cards_in_pile.update({event.src_pile:[]})
            if not (set(event.cards) - set(self.cards_in_pile[event.src_pile])):
                for card in event.cards:
                    self.cards_in_pile[event.src_pile].remove(card)
            self.status = 'In Game'
            return [copy.deepcopy(self)]
        elif event.type == 'Flip':
            self.cards_status.update(event.cards_status)
            self.status = 'In Game'
            return [copy.deepcopy(self)]
        elif event.type == 'AddNewCards':
            max_value_card = max([max(val, default=-1) for _, val in self.cards_in_pile.items()], default=-1)
            value_offset = math.ceil((max_value_card+1)/MAX_DECK_SIZE) * MAX_DECK_SIZE
            if event.dst_pile not in self.cards_in_pile.keys():
                self.cards_in_pile.update({event.dst_pile:[]})
            for card in event.cards:
                if card+value_offset not in self.cards_in_pile[event.dst_pile]:
                    self.cards_in_pile[event.dst_pile].append(card+value_offset)
            self.cards_status.update({key+value_offset:val for key, val in event.cards_status.items()})
            self.status = 'In Game'
            return [copy.deepcopy(self)]

        elif event.type == 'StartNewGame':
            self.cards_in_pile = {}
            self.cards_status = {}
            self.status='New Game'
            return [copy.deepcopy(self)]
        elif event.type == 'UpdatePlayerInfo':
            self.player_name_per_id.update({event.player_id: event.player_name})
            return [copy.deepcopy(self)]
        elif event.type == 'PlayerDisconnect':
            if event.player_id in self.player_index_per_id:
                index = self.player_index_per_id.pop(event.player_id)
                self.player_name.pop(index)
            if event.player_id in self.player_name_per_id:
                self.player_name_per_id.pop(event.player_id)

            return [copy.deepcopy(self)]
        elif event.type == 'ResetPlayerAndGame':
            self.player_name_per_id = {}
            self.player_index_per_id = {}
            self.player_name = {}
            self.cards_status = {}
            n_cards_distributed = 0
            self.cards_in_pile = {}
            self.pile_property = {}
            self.status = 'Wait for Player to Join'
            return [copy.deepcopy(self)]
        elif event.type == 'PlayerReady':
            if self.status == 'Wait for Player to Join':
                self.player_name_per_id.update({event.player_id: event.player_name})
                if event.player_id not in self.player_index_per_id:
                    assigned_index = min(set(range(len(self.player_name_per_id))) - set(self.player_index_per_id.values()))
                    self.player_index_per_id.update({event.player_id:assigned_index})

                if sorted(self.player_index_per_id.keys()) == sorted(self.player_name_per_id.keys()) and (any([w>=0 for key, w in self.player_index_per_id.items()])):
                    self.start_new_game()
                return [copy.deepcopy(self)]
            else:
                return []
        elif event.type == 'Observe':
            self.player_name_per_id.update({event.player_id: event.player_name})
            self.player_index_per_id.update({event.player_id: -1})
            if self.status == 'Wait for Player to Join':
                if sorted(self.player_index_per_id.keys()) == sorted(self.player_name_per_id.keys()) and (any([w>=0 for key, w in self.player_index_per_id.items()])):
                    # all player recognized. Start game
                    self.start_new_game()
            return [copy.deepcopy(self)]
        elif event.type =='UIElementChange':
            if event.dst_pile not in self.pile_property:
                self.pile_property.update({event.dst_pile:{}})
            self.pile_property[event.dst_pile].update(event.property)
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
    n_player : int = 0
    # : Dict[int, int] = field(default_factory=dict)
    #n_pile : int = 0
    #face_down_pile : List[int] = field(default_factory=list)
    player_id: str = ''

@dataclass
class EventConnect:
    type: str
    player_name : str = ''
    player_id : str = ''

@dataclass
class EventAddNewCards:
    type: str
    dst_pile: int = -1
    cards: List[int] = field(default_factory=list)
    cards_status: Dict[int, str] = field(default_factory=dict)



@dataclass
class Event:
    type: str
    player_index: int = -1
    src_pile: int = -1
    dst_pile: int = -1
    cards: List[int] = field(default_factory=list)
    cards_status: Dict[int, str] = field(default_factory=dict)
    n_player : int = 6
    #n_card_per_pile : Dict[int, int] = field(default_factory=dict)
    #n_pile : int = 19
    #face_down_pile : List[int] = field(default_factory=list)
    player_name : str = ''
    player_id : str = ''
    property: Dict = field(default_factory=dict)


