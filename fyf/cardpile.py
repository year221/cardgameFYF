""" card piles"""
import math
import arcade
from clientelements import Card, GameFlatButton,GameTextLabel
from utils import *
import gamestate
from arcade.gui import UIEvent, TEXT_INPUT,UIInputBox
import copy
from enum import Enum

PILE_BUTTON_HEIGHT = 12
PILE_BUTTON_FONTSIZE = 8
N_ELEMENT_PER_PILE = 4

def calculate_circular_pile_set_positions(starting_mat_center, pile_offset, piles_per_side,
                                          player_index, n_player, pile_position_offset, starting_index_type=None,
                                          self_player_index=None, counterclockwise=True):
    """ calculate posiitons of indidvidual piles  in a circule pile set

    :param starting_mat_center:
    :param pile_offset:
    :param piles_per_side:
    :param player_index:
    :param n_player:
    :param pile_position_offset:
    :param self_player_index:
    :param counterclockwise:
    :return:
    """
    if self_player_index is None:
        self_player_index = 0
    if starting_index_type is None:
        starting_index_type=Pile_Position_Offset.NO_OFFSET

    if piles_per_side[0]==-1:
        nrow = piles_per_side[1]
        ncol = math.ceil((n_player - 2 * (nrow-2))/2)
    elif piles_per_side[1]==-1:
        ncol = piles_per_side[0]
        nrow = math.ceil((n_player - 2 * (ncol-2))/2)
    else:
        ncol = piles_per_side[0]
        nrow = piles_per_side[1]

    mat_position_index = (player_index - self_player_index + pile_position_offset) % n_player
    if counterclockwise:
        if 0<=mat_position_index <= ncol-1:
            grid_position = mat_position_index, 0
        elif ncol <= mat_position_index <= (ncol-1+nrow-1):
            grid_position = ncol-1, mat_position_index-(ncol-1)
        elif (ncol-1+nrow) <=mat_position_index<= (ncol-1+nrow-1 + ncol-1):
            grid_position = (ncol-1)-(mat_position_index-(ncol-1+nrow-1)), nrow-1
        else:
            grid_position = 0, (nrow-1)-(mat_position_index - (ncol-1+nrow-1 + ncol-1))
    else:
        if 0<=mat_position_index < nrow:
            grid_position = 0, mat_position_index
        elif nrow<= mat_position_index < (nrow-1)+ncol:
            grid_position = mat_position_index-(nrow-1), nrow-1
        elif (nrow-1)+ncol<=mat_position_index< (nrow-1)+(ncol-1) + nrow:
            grid_position = ncol-1, (nrow-1)-(mat_position_index-((nrow-1)+ncol))
        else:
            grid_position =(ncol-1)-(mat_position_index - (nrow-1)+(ncol-1) + nrow), 0
    mat_x = starting_mat_center[0] + grid_position[0] * pile_offset[0]
    mat_y = starting_mat_center[1] + grid_position[1] * pile_offset[1]

    return mat_x, mat_y



class Title_Type(Enum):
    NONE = 0
    FIXED_TEXT = 1
    PLAYER_NAME = 2
    SCORE = 3



class PileMat(arcade.SpriteSolidColor):
    """ Mat for a card pile """

    def __init__(self, card_pile, *args, **kwargs):
        """ Card constructor """

        # Attributes for suit and value
        super().__init__(*args, **kwargs)
        # Image to use for the sprite when face up
        self._card_pile = card_pile
    @property
    def cardpile(self):
        return self._card_pile

import cProfile

CARD_WIDTH = 140
CARD_HEIGHT = 190


class CardPile(arcade.SpriteList):
    """ Card sprite """

    def __init__(self, card_pile_id, mat_center, mat_size, mat_boundary, card_size, card_offset, mat_color, size_scaler=1,
                 sorting_rule=None,
                 auto_sort_setting=None,
                 enable_sort_button=True, enable_clear_button=False, enable_recover_last_removed_cards=False,
                 update_event_handle = None,
                 title_property = None,
                 other_properties=None, *args, **kwargs):
        """ Card constructor """

        super().__init__(*args, **kwargs)
        self.card_pile_id = card_pile_id
        self._size_scaler = size_scaler

        self._mat_center = mat_center
        self._mat_size = mat_size
        self._mat_boundary = mat_boundary
        self._card_start = mat_center[0] - mat_size[0] / 2 + mat_boundary[0], \
                           mat_center[1] + mat_size[1] / 2 - mat_boundary[1]

        self._card_offset = card_offset
        self._card_size = card_size
        self._card_scale = min(self._card_size[0]/CARD_WIDTH, self._card_size[1]/CARD_HEIGHT)

        # update
        self.mat_center = int_scale_tuple(self._mat_center, self._size_scaler)
        self.mat_size = int_scale_tuple(self._mat_size, self._size_scaler)
        self.mat_boundary = int_scale_tuple(self._mat_boundary, self._size_scaler)
        self.card_start = int_scale_tuple(self._card_start, self._size_scaler)
        self.card_max_x =  self.mat_center[0] + self.mat_size[0] // 2 - self.mat_boundary[0]
        self.step_x = round(self._card_offset[0] * self._size_scaler)
        self.step_y = round(self._card_offset[1] * self._size_scaler)
        self.card_scale = self._card_scale*self._size_scaler

        self._pile_mat = PileMat(self, self.mat_size[0], self.mat_size[1], mat_color)
        self._pile_mat.position = self.mat_center
        #self._card_scale_calculated = min(self._card_size[0]*self._normalizing_length/CARD_WIDTH, self._card_size[1]*self._normalizing_length/CARD_HEIGHT)
        #self.card_scale = card_scale
        #self.card_size = card_size
        self.sorting_rule = sorting_rule
        self.auto_sort_setting = auto_sort_setting
        self._cached_values = []
        self._cached_face_status = {}
        self.enable_sort_button = enable_sort_button
        self.sort_button = None
        self.enable_clear_button = enable_clear_button
        self.clear_button = None
        #self.clear_action = clear_action
        self.enable_recover_last_removed_cards = enable_recover_last_removed_cards
        self.recover_button = None
        #self.recover_action = recover_action
        self._title_label = None
        if title_property is None:
            self._title_property = dict(type = Title_Type.NONE, default='')
        else:
            self._title_property =copy.deepcopy(title_property)
        self._title_property['type'] = Title_Type[self._title_property['type']]
        #self.enable_title = title_property['type']
        self._title = self._title_property['default']
        #self._title = '' if title is None else title
        self._update_event_handle = update_event_handle if update_event_handle is not None else lambda x: None
        self._last_removed_card_values = []
        self._last_removed_face_status = {}
        self.other_properties = copy.deepcopy(other_properties)

    @property
    def size_scaler(self):
        return self._size_scaler
    @size_scaler.setter
    def size_scaler(self, x):
        self._size_scaler = x
        self.mat_center = int_scale_tuple(self._mat_center, self._size_scaler)
        self.mat_size = int_scale_tuple(self._mat_size, self._size_scaler)
        self.mat_boundary = int_scale_tuple(self._mat_boundary, self._size_scaler)
        self.card_start = int_scale_tuple(self._card_start, self._size_scaler)
        self.card_max_x =  self.mat_center[0] + self.mat_size[0] // 2 - self.mat_boundary[0]
        self.step_x = round(self._card_offset[0] * self._size_scaler)
        self.step_y = round(self._card_offset[1] * self._size_scaler)
        self.card_scale = self._card_scale*self._size_scaler
        self._pile_mat.position = self.mat_center
        self._pile_mat.width = self.mat_size[0]
        self._pile_mat.height = self.mat_size[1]

    def clear(self):
        """ clear entire pile"""
        self._last_removed_card_values = self._cached_values
        self._last_removed_face_status = self._cached_face_status
        self._cached_values = []
        self._cached_face_status = {}
        while self.__len__() > 0:
            self.pop()

    def _clear_card(self):

        #if 'Clearable' in pile.other_properties:
        #    if pile.other_properties['Clearable']:
        new_event = gamestate.Event(
            type='Remove',
            src_pile = self.card_pile_id,
            cards = self.to_valuelist()
        )
        self.clear()
        #pile.clear()  # remove_card(dropped_card)
        self._update_event_handle(new_event)

        # self.event_buffer.append(new_event)
        # self.game_state.update_from_event(new_event)

    def _recover_removed_card(self):
        """ recover previously cleared cards"""
        card_recovered = self._last_removed_card_values
        face_status = self._last_removed_face_status
        for value in card_recovered:
            self.add_card(Card(value=value, face=self._last_removed_face_status[value]))

        self._last_removed_card_values = []
        self._last_removed_face_status = {}
        new_event = gamestate.Event(
            type='Add',
            dst_pile = self.card_pile_id,
            cards = card_recovered,
            cards_status = face_status
        )
        self._update_event_handle(new_event)

    @property
    def mat(self):
        return self._pile_mat


    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, x):
        if x is None:
            self._title = ''
        else:
            self._title = x
        if self._title_label is not None:
            self._title_label.text = self._title

    @property
    def title_type(self):
        return self._title_property['type']
    def get_ui_elements(self):
        all_elements = []
        if self._title_property['type'] != Title_Type.NONE:
            if self._title_label is None:
                self._title_label = GameTextLabel(
                    text=self._title,
                    font_size=PILE_BUTTON_FONTSIZE,
                    center_x=self.mat_center[0] - self.mat_size[0] // 2 + int(
                        self.mat_size[0] / N_ELEMENT_PER_PILE / 2),
                    center_y=self.mat_center[1] + self.mat_size[1] // 2 + PILE_BUTTON_HEIGHT // 2,
                )
            all_elements.append(self._title_label)

        if self.enable_sort_button:
            if self.sort_button is None:
                self.sort_button = GameFlatButton(
                    self.resort_cards,
                    font_size=PILE_BUTTON_FONTSIZE,
                    text='SORT',
                    center_x=self.mat_center[0] - self.mat_size[0] // 2 + int(
                        self.mat_size[0] / N_ELEMENT_PER_PILE / 2 * 3),
                    center_y=self.mat_center[1] + self.mat_size[1] // 2 + PILE_BUTTON_HEIGHT // 2,
                    width=int(self.mat_size[0] / N_ELEMENT_PER_PILE),
                    height=PILE_BUTTON_HEIGHT
                )
            all_elements.append(self.sort_button)
        if self.enable_clear_button:

            if self.clear_button is None:

                self.clear_button = GameFlatButton(
                    self._clear_card,
                    font_size=PILE_BUTTON_FONTSIZE,
                    text='CLEAR',
                    center_x=self.mat_center[0] - self.mat_size[0] // 2 + int(
                        self.mat_size[0] / N_ELEMENT_PER_PILE / 2 * 5),
                    center_y=self.mat_center[1] + self.mat_size[1] // 2 + PILE_BUTTON_HEIGHT // 2,
                    width=int(self.mat_size[0] / N_ELEMENT_PER_PILE),
                    height=PILE_BUTTON_HEIGHT
                )
            all_elements.append(self.clear_button)
        if self.enable_recover_last_removed_cards:
            if self.recover_button is None:
                self.recover_button = GameFlatButton(
                    self._recover_removed_card,
                    font_size=PILE_BUTTON_FONTSIZE,
                    text='UNDO CLEAR',
                    center_x=self.mat_center[0] - self.mat_size[0] // 2 + int(
                        self.mat_size[0] / N_ELEMENT_PER_PILE / 2 * 7),
                    center_y=self.mat_center[1] + self.mat_size[1] // 2 + PILE_BUTTON_HEIGHT // 2,
                    width=int(self.mat_size[0] / N_ELEMENT_PER_PILE),
                    height=PILE_BUTTON_HEIGHT
                )
            all_elements.append(self.recover_button)
        return all_elements

    def add_card(self, card):
        """ add card """
        if self.__len__() > 0:
            card_x, card_y = (self.__getitem__(-1)).position
            card_x = card_x + self.step_x
            if card_x >= self.card_max_x:
                card_x = self.card_start[0]
                card_y = card_y - self.step_y
        else:
            card_x = self.card_start[0]
            card_y = self.card_start[1]
        card.position = card_x, card_y
        card.scale = self.card_scale

        self.append(card)

        self._cached_values.append(card.value)
        self._cached_face_status[card.value] = card.face

    def to_valuelist(self):
        """ export as value list"""
        return [w.value for w in self]

    def to_face_staus(self):
        """ export as dictionary"""
        return {w.value: w.face for w in self}



    def remove_card(self, card):
        self.remove(card)
        self._cached_values.remove(card.value)
        self._cached_face_status.pop(card.value)
        # self._cached_codes.remove(card.code)

    def resort_cards(self, sorting_rule=None):
        """ sort cards based on certain order

        :param sorting_rule:
        :return: None
        """
        if sorting_rule is None:
            sorting_rule = self.sorting_rule
        sorted_cards = sort_cards(self, sorting_rule)  # [(w, w.value % 54) for w in self], key=lambda x: x[1])
        # if sorting_rule == SORT_BY_SUIT_THEN_NUMBER:
        #    sorted_cards = sorted([(w, w.value % 54) for w in self], key = lambda x:x[1])
        if self.to_valuelist() != [w.value for w in sorted_cards]:
            self.clear()
            for card in sorted_cards:
                self.add_card(card)

    def from_value_face(self, value_list, face_status_dict):
        """ update pile based on value list and face status dictionary"""
        # update pile based on new value list and face status dict
        card_values_to_remove = set(self._cached_values) - set(value_list)
        card_values_to_add = set(value_list) - set(self._cached_values)
        card_values_to_flip = dict(set(self._cached_face_status.items()) - set(face_status_dict.items()))

        if card_values_to_remove or card_values_to_flip or card_values_to_add:
            self._cached_values = value_list
            self._cached_face_status = {key: value for key, value in face_status_dict.items() if
                                        key in self._cached_values}

            if card_values_to_remove:
                cards_to_remove_ls = [card for card in self if card.value in card_values_to_remove]
                for card in cards_to_remove_ls:
                    self.remove(card)

            if card_values_to_flip:
                cards_to_flip = [card for card in self if card.value in card_values_to_flip.keys()]
                for card in cards_to_flip:
                    card.face = face_status_dict[card.value]

            if card_values_to_add:
                # NO_AUTO_SORT = 0
                # AUTO_SORT_NEW_CARD_ONLY = 1
                # AUTO_SORT_ALL_CARDS = 2
                if self.auto_sort_setting is None or self.auto_sort_setting == Auto_Sort.NO_AUTO_SORT:
                    for value in card_values_to_add:
                        self.add_card(Card(value=value, face=face_status_dict[value]))
                elif self.auto_sort_setting == Auto_Sort.AUTO_SORT_NEW_CARD_ONLY:
                    sorted_card_values = sort_card_value(card_values_to_add, self.sorting_rule)
                    for value in sorted_card_values:
                        self.add_card(Card(value=value, face=face_status_dict[value]))
                else:
                    for value in card_values_to_add:
                        self.add_card(Card(value=value, face=face_status_dict[value]))

        card_added_removed = set.union(card_values_to_remove, card_values_to_add)
        if self.auto_sort_setting == Auto_Sort.AUTO_SORT_ALL_CARDS:
            self.resort_cards()
        return card_added_removed