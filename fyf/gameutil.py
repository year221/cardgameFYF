from typing import List, Dict, Tuple
from dataclasses import dataclass, asdict, field
import json

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
     # def __init__(self, n_pile=None, cards_in_pile=None, n_player=None, player_assignment=None, status=None):
     #      if n_pile is None:
     #           self.n_pile=0
     #      else:
     #           self.n_pile=n_pile
     #      if cards_in_pile is None:
     #           self.cards_in_pile = []
     #      else:
     #           self.cards_in_pile = {key: [tuple(w) for w in val] for key, val in cards_in_pile.items()}
     #      if n_player is None:
     #           self.n_player = 4
     #      else:
     #           self.n_player = n_player
     #      if player_assignment is None:
     #           self.player_assignment = {}
     #      else:
     #           self.player_assignment = player_assignment
     #      if status is None:
     #           self.status = "NewGame"
     #      else:
     #           self.status = status
     def to_json(self):
         d = dict(
              n_pile=self.n_pile,
              cards_in_pile=self.cards_in_pile,
              cards_status=self.cards_status,
              n_player=self.n_player,
              player_assignment=self.player_assignment,
              status=self.status
         )
         #print(d)
         return json.dumps(d)

     def update_from_event(self, event):
          #print(event)
          #print(self.cards_in_pile.keys())
          if event.type == 'Move':
               if event.src_pile in self.cards_in_pile.keys() and event.dst_pile in self.cards_in_pile.keys():
                    #rint(event.cards)
                    #print(event.cards)
                    #print(self.cards_in_pile[event.src_pile])
                    #event.cards = [tuple(w) for w in event.cards]
                    #print(set(event.cards) - set(self.cards_in_pile[event.src_pile]))
                    if not (set(event.cards) - set(self.cards_in_pile[event.src_pile])):

                         for card in event.cards:
                              #print(card_code)
                              self.cards_in_pile[event.src_pile].remove(card)
                              self.cards_in_pile[event.dst_pile].append(card)
          print("finish update")


@dataclass
class Event:
     type: str
     player_index: int
     src_pile: int
     dst_pile: int
     cards: List[int]#Tuple[int, str]]
     cards_status: Dict[int, str]


     # def __init__(self, type, player_index, src_pile, dst_pile, cards):
     #      self.type=type
     #      self.player_index=player_index
     #      self.src_pile=src_pile
     #      self.dst_pile = dst_pile
     #      self.cards=[tuple(w) for w in cards]
     #      self.cards_status


     def to_dict(self):
          return dict(
               type=self.type,
               player_index=self.player_index,
               src_pile=self.src_pile,
               dst_pile=self.dst_pile,
               cards=self.cards,
               cards_status=self.cards_status
          )
