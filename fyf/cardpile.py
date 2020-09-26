""" card piles"""
import arcade
from clientelements import Card, GameFlatButton,GameTextLabel
from utils import *
import gamestate
from arcade.gui import UIEvent, TEXT_INPUT,UIInputBox
import copy

PILE_BUTTON_HEIGHT = 12
PILE_BUTTON_FONTSIZE = 8
N_ELEMENT_PER_PILE = 4

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


class CardPile(arcade.SpriteList):
    """ Card sprite """

    def __init__(self, card_pile_id, mat_center, mat_size, mat_boundary, card_scale, card_offset, mat_color, sorting_rule=None,
                 auto_sort_setting=None,
                 enable_sort_button=True, enable_clear_button=False, enable_recover_last_removed_cards=False,
                 update_event_handle = None,
                 enable_title=False, title=None, other_properties=None, *args, **kwargs):
        """ Card constructor """

        super().__init__(*args, **kwargs)
        self.card_pile_id = card_pile_id
        self.mat_center = mat_center
        self.mat_size = mat_size
        self.card_start_x, self.card_start_y = mat_center[0] - mat_size[0] // 2 + mat_boundary[0], mat_center[1] + \
                                               mat_size[1] // 2 - mat_boundary[1]
        self._pile_mat = PileMat(self, int(self.mat_size[0]), int(self.mat_size[1]), mat_color)
                                 #arcade.csscolor.LIGHT_SLATE_GREY if mat_color is None else mat_color)
        self._pile_mat.position = mat_center

        self.card_max_x = mat_center[0] + mat_size[0] // 2 - mat_boundary[0]
        self.step_x, self.step_y = int(card_offset[0]), int(card_offset[1])
        self.card_scale = card_scale
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
        self.enable_title = enable_title
        self._title = '' if title is None else title
        self._update_event_handle = update_event_handle if update_event_handle is not None else lambda x: None
        self._last_removed_card_values = []
        self._last_removed_face_status = {}
        self.other_properties = copy.deepcopy(other_properties)




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
        #return card_recovered, face_status
        new_event = gamestate.Event(
            type='Add',
            dst_pile = self.card_pile_id,
            cards = card_recovered,
            cards_status = face_status
        )
        self._update_event_handle(new_event)

    # def recover_removed_card(self):
    #
    #     card_values, face_dict = self._recover_removed_card()
    #
    #     new_event = gamestate.Event(
    #         type='Add',
    #         dst_pile = pile.card_pile_id,
    #         cards = card_values,
    #         cards_status = face_dict
    #     )
    #     self._update_event_handle(new_event)


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

    def get_ui_elements(self):
        all_elements = []
        if self.enable_title:
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
                card_x = self.card_start_x
                card_y = card_y - self.step_y
        else:
            card_x = self.card_start_x
            card_y = self.card_start_y
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
                if self.auto_sort_setting is None or self.auto_sort_setting == NO_AUTO_SORT:
                    for value in card_values_to_add:
                        self.add_card(Card(value=value, face=face_status_dict[value]))
                elif self.auto_sort_setting == AUTO_SORT_NEW_CARD_ONLY:
                    sorted_card_values = sort_card_value(card_values_to_add, self.sorting_rule)
                    for value in sorted_card_values:
                        self.add_card(Card(value=value, face=face_status_dict[value]))
                else:
                    for value in card_values_to_add:
                        self.add_card(Card(value=value, face=face_status_dict[value]))

        card_added_removed = set.union(card_values_to_remove, card_values_to_add)
        if self.auto_sort_setting == AUTO_SORT_ALL_CARDS:
            self.resort_cards()
        return card_added_removed