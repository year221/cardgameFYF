""" card piles"""
import math
import arcade
from clientelements import Card, ResizableGameTextLabel,ResizableGameFlatButton, ResizableUIInputBox,SyncedResizableUIInputBox
from utils import *
import gamestate
from gamestate import MAX_DECK_SIZE
import random
#from arcade.gui import UIEvent, TEXT_INPUT,UIInputBox
import copy
from enum import Enum
import PIL.Image
from arcade import Texture
from simpleeval import SimpleEval
#from arcade.arcade_types import RGB, Point, PointList
PILE_BUTTON_HEIGHT = 12
PILE_BUTTON_FONTSIZE = 8
PILE_BUTTON_WIDTH = 100
N_ELEMENT_PER_PILE = 4

def height_to_font_size(height):
    return height/1.6

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

    def __init__(self, card_pile, width,height, color, *args, **kwargs):
        """ Card constructor """

        # Attributes for suit and value
        super().__init__(width, height, color, *args, **kwargs)
        # Image to use for the sprite when face up
        self._card_pile = card_pile
        self.mat_color = color
    @property
    def cardpile(self):
        return self._card_pile

    # the following size setting is a temporary patch due to an arcade bug on resetting width and height
    @property
    def size(self):
        return self.width, self.height
    @size.setter
    def size(self, x):
        self.width = x[0]
        self.height = x[1]
        self._update_hit_box()
    def _update_hit_box(self):
        color = self.mat_color
        image = PIL.Image.new('RGBA', (self.width, self.height), color)
        self.texture = Texture(f"Solid-{color[0]}-{color[1]}-{color[2]}", image)
        self._points = self.texture.hit_box_points
        self._hit_box_shape = None

CARD_WIDTH = 140
CARD_HEIGHT = 190




class CardPile(arcade.SpriteList):
    """ Card sprite """

    def __init__(self, card_pile_id, mat_center, mat_size, mat_boundary, card_size, card_offset, mat_color, size_scaler=1,
                 sorting_rule=None,
                 auto_sort_setting=None,
                 enable_sort_button=True, enable_clear_button=False, enable_recover_last_removed_cards=False, enable_flip_all=False,
                 button_width=None, button_height=None,
                 vertical_button_width=None, vertical_button_height=None,
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
        if button_width is None:
            self._button_width = self._mat_size[0] / N_ELEMENT_PER_PILE
        else:
            self._button_width = button_width
        if button_height is None:
            self._button_height = PILE_BUTTON_HEIGHT
        else:
            self._button_height = button_height
        if vertical_button_height is None:
            self._vertical_button_height = PILE_BUTTON_HEIGHT
        else:
            self._vertical_button_height = vertical_button_height
        if vertical_button_width is None:
            self._vertical_button_width = PILE_BUTTON_WIDTH
        else:
            self._vertical_button_width = vertical_button_width

        # update
        self.mat_center = scale_tuple(self._mat_center, self._size_scaler)
        self.mat_size = scale_tuple(self._mat_size, self._size_scaler)
        self.mat_boundary = scale_tuple(self._mat_boundary, self._size_scaler)
        self.card_start = scale_tuple(self._card_start, self._size_scaler)
        self.card_max_x =  self.mat_center[0] + self.mat_size[0] // 2 - self.mat_boundary[0]
        self.step_x = round(self._card_offset[0] * self._size_scaler)
        self.step_y = round(self._card_offset[1] * self._size_scaler)
        self.card_scale = self._card_scale*self._size_scaler
        #self.button_height = self._button_height*self._size_scaler

        self._pile_mat = PileMat(self, round(self.mat_size[0]), round(self.mat_size[1]), mat_color)
        self._pile_mat.position = self.mat_center
        if sorting_rule is None:
            self.sorting_rule=Sorting_Rule.DO_NOT_SORT
        else:
            self.sorting_rule = sorting_rule
        if auto_sort_setting is None:
            self.auto_sort_setting=Auto_Sort.NO_AUTO_SORT
        else:
            self.auto_sort_setting = auto_sort_setting
        self._cached_values = []
        self._cached_face_status = {}
        self.enable_sort_button = enable_sort_button
        self.sort_button = None
        self.enable_clear_button = enable_clear_button
        self.clear_button = None
        self.enable_recover_last_removed_cards = enable_recover_last_removed_cards
        self.recover_button = None
        self.enable_flip_all = enable_flip_all
        self.flip_all_button = None
        self._title_label = None
        if title_property is None:
            self._title_property = dict(type = Title_Type.NONE, default='')
        else:
            self._title_property =copy.deepcopy(title_property)
        self._title_property['type'] = Title_Type[self._title_property['type']]
        self._title = self._title_property['default']
        self._update_event_handle = update_event_handle if update_event_handle is not None else lambda x: None
        self._last_removed_card_values = []
        self._last_removed_face_status = {}
        self.other_properties = copy.deepcopy(other_properties)
        self._ui_elements = None
        self._button_count = 0
        self._vertical_button_count = 0
        self.setup_ui_elements()


    @property
    def size_scaler(self):
        return self._size_scaler
    @size_scaler.setter
    def size_scaler(self, x):
        factor = x/self._size_scaler
        old_card_start = self._card_start
        self._size_scaler = x
        self.mat_center = scale_tuple(self._mat_center, self._size_scaler)
        self.mat_size = scale_tuple(self._mat_size, self._size_scaler)
        self.mat_boundary = scale_tuple(self._mat_boundary, self._size_scaler)
        self.card_start = scale_tuple(self._card_start, self._size_scaler)
        self.card_max_x =  self.mat_center[0] + self.mat_size[0] // 2 - self.mat_boundary[0]
        self.step_x = round(self._card_offset[0] * self._size_scaler)
        self.step_y = round(self._card_offset[1] * self._size_scaler)
        self.card_scale = self._card_scale*self._size_scaler
        #self.button_height = self._button_height*self._size_scaler


        #self._pile_mat.width = round(self.mat_size[0])
        #self._pile_mat.height = round(self.mat_size[1])
        self._pile_mat.size = round(self.mat_size[0]), round(self.mat_size[1])
        self._pile_mat.position = self.mat_center
        for ui_element in self._ui_elements:
            ui_element.size_scaler = self._size_scaler

        for cardsprite in self.sprite_list:
            cardsprite.center_x = cardsprite.center_x * factor
            cardsprite.center_y = cardsprite.center_y * factor
            cardsprite.scale = self.card_scale

    def clear(self, cache_cleared_values=True):
        """ clear entire pile"""
        if cache_cleared_values:
            self._last_removed_card_values = self._cached_values
            self._last_removed_face_status = self._cached_face_status
        else:
            self._last_removed_card_values=[]
            self._last_removed_face_status={}

        self._cached_values = []
        self._cached_face_status = {}
        while self.__len__() > 0:
            self.pop()

    def _clear_card(self):

        new_event = gamestate.Event(
            type='Remove',
            src_pile = self.card_pile_id,
            cards = self.to_valuelist()
        )
        self.clear()
        self._update_event_handle(new_event)

    def _flip_all_card(self):

        card_update_dict = {}
        for card in self:
            new_face = card.face_flipped()
            card_update_dict[card.value]=new_face#.update({card.value: new_face})
            card.face = new_face
        new_event = gamestate.Event(
            type='Flip',
            cards=list(card_update_dict.keys()),
            cards_status=card_update_dict,
        )
        self._update_event_handle(new_event)

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

    def _add_horizontal_buttons(self, click_event, text):
        c_button = ResizableGameFlatButton(
            click_event=click_event,
            width=self._button_width,
            height=self._button_height,
            center_x=self._mat_center[0] - self._mat_size[0] / 2 + (
                    self._button_width * (self._button_count * 2 + 1) / 2),
            center_y=self._mat_center[1] + self._mat_size[1] / 2 + self._button_height / 2,
            size_scaler=self._size_scaler,
            font_size=height_to_font_size(self._button_height),
            text=text
        )
        self._ui_elements.append(c_button)
        self._button_count += 1
        return c_button

    def _add_vertical_buttons(self, click_event, text):
        c_button = ResizableGameFlatButton(
            click_event=click_event,
            width=self._vertical_button_width,
            height=self._vertical_button_height,
            center_x=self._mat_center[0] + self._mat_size[0] / 2 + self._vertical_button_width / 2,
            center_y=self._mat_center[1] + self._mat_size[1] / 2 - (
                        self._vertical_button_count * 2 + 1) / 2 * self._vertical_button_height,
            size_scaler=self._size_scaler,
            font_size=height_to_font_size(self._vertical_button_height),
            text=text
        )

        self._ui_elements.append(c_button)
        self._vertical_button_count += 1
        return c_button

    def setup_ui_elements(self):
        self._ui_elements = []
        #button_count = 0
        if self._title_property['type'] != Title_Type.NONE:
            if self._title_label is None:
                self._title_label = ResizableGameTextLabel(
                    width=self._button_width,
                    height=self._button_height,
                    center_x=self._mat_center[0] - self._mat_size[0] / 2 + (
                            self._button_width * (self._button_count * 2 + 1) / 2),
                    center_y=self._mat_center[1] + self._mat_size[1] / 2 + self._button_height / 2,
                    text=self._title,
                    size_scaler=self._size_scaler,
                    font_size=height_to_font_size(self._button_height),
                )
                self._ui_elements.append(self._title_label)
                self._button_count+=1

        if self.enable_sort_button:
            if self.sort_button is None:
                self.sort_button= self._add_horizontal_buttons(self.resort_cards, 'SORT')

        if self.enable_clear_button:

            if self.clear_button is None:
                self.clear_button = self._add_horizontal_buttons(self._clear_card, 'CLEAR')

        if self.enable_recover_last_removed_cards:
            if self.recover_button is None:
                self.recover_button = self._add_horizontal_buttons(self._recover_removed_card, 'UNDO CLR')

        if self.enable_flip_all:
            if self.flip_all_button is None:
                self.flip_all_button = self._add_horizontal_buttons(self._flip_all_card, 'FLIP ALL')

    def get_ui_elements(self):
        return self._ui_elements

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
                    for value in [w for w in value_list if w in card_values_to_add]:
                        self.add_card(Card(value=value, face=face_status_dict[value]))
                elif self.auto_sort_setting == Auto_Sort.AUTO_SORT_NEW_CARD_ONLY:
                    sorted_card_values = sort_card_value(card_values_to_add, self.sorting_rule)
                    for value in sorted_card_values:
                        self.add_card(Card(value=value, face=face_status_dict[value]))
                else:
                    #for value in card_values_to_add:
                    #    self.add_card(Card(value=value, face=face_status_dict[value]))
                    for value in [w for w in value_list if w in card_values_to_add]:
                        self.add_card(Card(value=value, face=face_status_dict[value]))
        card_added_removed = set.union(card_values_to_remove, card_values_to_add)
        if self.auto_sort_setting == Auto_Sort.AUTO_SORT_ALL_CARDS:
            self.resort_cards()
        return card_added_removed

class CardDeck(CardPile):
    def __init__(self, card_pile_id, mat_center, mat_size, mat_boundary, card_size, card_offset, mat_color, size_scaler,
                 update_event_handle,
                 per_deck_cards, #initial_num_of_decks=None,
                 face_down=True,
                 enable_generation=None, num_of_decks_per_generation=1,
                 enable_auto_distribution=None, destination_piles_and_cards=None, title_property=None,other_properties=None,
                 *args, **kwargs
                 ):
        super().__init__(card_pile_id, mat_center, mat_size, mat_boundary, card_size, card_offset, mat_color, size_scaler,
                         sorting_rule=None, auto_sort_setting=None, enable_sort_button=False,
                         enable_recover_last_removed_cards=False,
                         update_event_handle=update_event_handle,
                         title_property=title_property,
                         other_properties=other_properties,
                         *args, **kwargs)
        self._simple_eval = SimpleEval()
        self.enable_auto_distribution = enable_auto_distribution
        self._destination_piles_and_cards=destination_piles_and_cards
        self._ui_destination_piles_and_cards = {}
        self.per_deck_cards=per_deck_cards
        #self.initial_num_of_decks=initial_num_of_decks
        self._enable_generation = enable_generation
        self._num_of_decks_per_generation = num_of_decks_per_generation
        self._ui_num_of_decks_per_generation = None
        self._enable_auto_distribution = enable_auto_distribution
        self._per_deck_cards = per_deck_cards
        self.face_down=face_down
        self._generation_button = None
        self._auto_distribution_button = None
        self.setup_vertical_ui_elements()

    @property
    def num_of_decks_per_generation(self):
        if self._ui_num_of_decks_per_generation is None:
            return None
        else:
            c_value = self._ui_num_of_decks_per_generation.text
            if not c_value.isdigit():
                return None
            else:
                return int(c_value)
    @num_of_decks_per_generation.setter
    def num_of_decks_per_generation(self, value):
        if value is not None:
            #if self._ui_num_of_decks_per_generation.text!=str(value):
            self._ui_num_of_decks_per_generation.sync_text(str(value))

    @property
    def destination_piles_and_cards(self):
        output_dict = {}
        for key, ui_input in self._ui_destination_piles_and_cards.items():
            c_value = ui_input.text
            if not c_value.isdigit():
                return None
            else:
                output_dict[key]=int(c_value)
        return output_dict
    @destination_piles_and_cards.setter
    def destination_piles_and_cards(self, value: dict):
        for key, val in value.items():
            #c_value =self._ui_destination_piles_and_cards[key].text
            #if c_value != str(val):
            self._ui_destination_piles_and_cards[key].sync_text(str(val))

    def update_ui_property(self, ui_property):
        if 'num_of_decks_per_generation' in ui_property:
            self.num_of_decks_per_generation = ui_property['num_of_decks_per_generation']
        if 'destination_piles_and_cards' in ui_property:
            self.destination_piles_and_cards = ui_property['destination_piles_and_cards']

    def deal_cards(self):
        if 'pile_tag_to_pile_id' in self.other_properties:
            card_values = self.to_valuelist()
            destination_piles_and_cards = self.destination_piles_and_cards
            if destination_piles_and_cards is not None:
                all_cards_to_distribute_count = sum([len(self.other_properties['pile_tag_to_pile_id'][key])*self._eval_expression(val) for key, val in destination_piles_and_cards.items()])
                if all_cards_to_distribute_count<=len(card_values):
                    starting_index = 0
                    for key, val in destination_piles_and_cards.items():
                        n_cards = self._eval_expression(val)
                        for card_pile_id in self.other_properties['pile_tag_to_pile_id'][key]:
                            new_event = gamestate.Event(
                                type='Move',
                                src_pile=self.card_pile_id,
                                dst_pile=card_pile_id,
                                cards=card_values[starting_index:starting_index+n_cards]
                            )
                            self._update_event_handle(new_event, local_fast_update=False)
                            starting_index+=n_cards

    def _eval_expression(self, x):
        if isinstance(x, str):
            temp_str = x
            for key, val in self.other_properties['constants'].items():
                temp_str = temp_str.replace(key, str(val))
            return self._simple_eval.eval(temp_str)
        else:
            return x
    def generate_cards(self):
        """ Send gnerate new cards event

        :return:
        """

        random.seed(a=None)
        n_deck_per_generation = self.num_of_decks_per_generation
        if n_deck_per_generation is not None:
            new_cards = [j*MAX_DECK_SIZE + w for j in range(n_deck_per_generation) for w in self.per_deck_cards]
            face_value = 'D' if self.face_down else 'U'
            card_status = {w: face_value for w in new_cards}
            random.shuffle(new_cards)
            new_event = gamestate.EventAddNewCards(
                type='AddNewCards',
                dst_pile = self.card_pile_id,
                cards= new_cards,
                cards_status= card_status
            )
            self._update_event_handle(new_event, local_fast_update=False)



    def _on_change_num_of_decks_per_generation(self, value):
        num_of_decks_per_generation = self.num_of_decks_per_generation
        if num_of_decks_per_generation is not None:
            new_event = gamestate.Event(
                type='UIElementChange',
                dst_pile=self.card_pile_id,
                property={'num_of_decks_per_generation':num_of_decks_per_generation}
            )
            self._update_event_handle(new_event, local_fast_update=False)

    def _on_change_destination_piles_and_cards(self, value):
        destination_piles_and_cards = self.destination_piles_and_cards
        if destination_piles_and_cards is not None:
            new_event = gamestate.Event(
                type='UIElementChange',
                dst_pile=self.card_pile_id,
                property={'destination_piles_and_cards':destination_piles_and_cards}
            )
            self._update_event_handle(new_event, local_fast_update=False)

    def setup_vertical_ui_elements(self):
        #num_vertical_button = 0
        if self._enable_generation:
            if self._generation_button is None:
                text_label = ResizableGameTextLabel(
                    width=self._vertical_button_width / 2,
                    height=self._vertical_button_height,
                    center_x=self._mat_center[0] + self._mat_size[0] / 2 + self._vertical_button_width / 4,
                    center_y=self._mat_center[1] + self._mat_size[1] / 2 - (
                            self._vertical_button_count * 2 + 1) / 2 * self._vertical_button_height,
                    size_scaler=self._size_scaler,
                    font_size=height_to_font_size(self._vertical_button_height),
                    text=str('#decks')
                )
                c_text_input = SyncedResizableUIInputBox(
                    width=self._vertical_button_width / 2,
                    height=self._vertical_button_height,
                    center_x=self._mat_center[0] + self._mat_size[0] / 2 + self._vertical_button_width / 4 * 3,
                    center_y=self._mat_center[1] + self._mat_size[1] / 2 - (
                            self._vertical_button_count * 2 + 1) / 2 * self._vertical_button_height,
                    size_scaler=self._size_scaler,
                    font_size=height_to_font_size(self._vertical_button_height),
                    text=str(self._eval_expression(self._num_of_decks_per_generation)),
                    on_text_update_hanlder=self._on_change_num_of_decks_per_generation
                )
                self._ui_num_of_decks_per_generation = c_text_input
                self._vertical_button_count += 1
                self._ui_elements.append(text_label)
                self._ui_elements.append(c_text_input)

                self._generation_button = self._add_vertical_buttons(self.generate_cards, 'GENERATE')



        if self._enable_auto_distribution:
            if self._auto_distribution_button is None:
                for key, val in self._destination_piles_and_cards.items():
                    text_label = ResizableGameTextLabel(
                        width=self._vertical_button_width/2,
                        height=self._vertical_button_height,
                        center_x=self._mat_center[0] + self._mat_size[0] / 2 + self._vertical_button_width / 4,
                        center_y=self._mat_center[1] + self._mat_size[1] / 2 - (
                                self._vertical_button_count * 2 + 1) / 2 * self._vertical_button_height,
                        size_scaler=self._size_scaler,
                        font_size=height_to_font_size(self._vertical_button_height),
                        text=str(key)
                    )

                    c_text_input = SyncedResizableUIInputBox(
                        width=self._vertical_button_width/2,
                        height=self._vertical_button_height,
                        center_x=self._mat_center[0] + self._mat_size[0] / 2 + self._vertical_button_width / 4 * 3,
                        center_y=self._mat_center[1] + self._mat_size[1] / 2 - (
                                self._vertical_button_count * 2 + 1) / 2 * self._vertical_button_height,
                        size_scaler=self._size_scaler,
                        font_size=height_to_font_size(self._vertical_button_height),
                        text=str(self._eval_expression(val)),
                        on_text_update_hanlder=self._on_change_destination_piles_and_cards
                    )
                    self._ui_destination_piles_and_cards[key]=c_text_input
                    self._vertical_button_count+=1
                    self._ui_elements.append(text_label)
                    self._ui_elements.append(c_text_input)
                self._auto_distribution_button = self._add_vertical_buttons(self.deal_cards, 'DEAL')
