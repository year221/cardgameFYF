"""
ZPY Card Game
"""
import math
import asyncio
import threading
import time
import zmq
from zmq import Context, Socket
import random
import arcade
import os
import argparse
import gameutil
from arcade import gui
import copy
import uuid

parser = argparse.ArgumentParser(description='Card client')

parser.add_argument('playerindex', type=int,
                    help='player index')

parser.add_argument('-p', dest='player_name', type=str, help='your name to be displayed', default='')
parser.add_argument('-n', dest='n_player', type=int, help='number of player', default=6)
parser.add_argument('-u', dest='server_ip', type=str, help='server ip', default='162.243.211.250')
# Network
UPDATE_TICK = 30
# Screen title and size
SCREEN_WIDTH = 1400
SCREEN_HEIGHT = 800
SCREEN_TITLE = "Zhao Peng You"

# Constants for sizing
CARD_SCALE = 0.5
NORMAL_MAT_SCALE = 0.5
SCORE_MAT_SCALE = 0.3
# How big are the cards?
CARD_WIDTH = 140
CARD_HEIGHT = 190

# If we fan out cards stacked on each other, how far apart to fan them?
CARD_OFFSET_PCT = 0.25
CARD_HORIZONTAL_OFFSET = int(CARD_WIDTH * 0.25)
CARD_VERICAL_OFFSET = int(CARD_WIDTH * 0.25)

# How much space do we leave as a gap between the mats?
# Done as a percent of the mat size.
VERTICAL_MARGIN_PERCENT = 0.10
HORIZONTAL_MARGIN_PERCENT = 0.10

# How big is the mat we'll place the card on?
MAT_PERCENT_OVERSIZE = 1.25
MAT_HEIGHT = int(CARD_HEIGHT * MAT_PERCENT_OVERSIZE)
MAT_WIDTH = int(CARD_WIDTH  * MAT_PERCENT_OVERSIZE * 3)
HAND_MAT_HEIGHT = int(CARD_HEIGHT*2 + MAT_HEIGHT * VERTICAL_MARGIN_PERCENT)
HAND_MAT_WIDTH = int(CARD_HORIZONTAL_OFFSET * 60 + CARD_WIDTH)

# The Y of the bottom row (2 piles)
HAND_MAT_Y = HAND_MAT_HEIGHT / 2  * CARD_SCALE + MAT_HEIGHT  * CARD_SCALE * VERTICAL_MARGIN_PERCENT
# The X of where to start putting things on the left side
HAND_MAT_X = HAND_MAT_WIDTH / 2  * CARD_SCALE + MAT_WIDTH  * CARD_SCALE * HORIZONTAL_MARGIN_PERCENT

STARTING_X = MAT_WIDTH * HORIZONTAL_MARGIN_PERCENT

TOP_OUTPUT_ROW_Y = (SCREEN_HEIGHT * 10.5) // 12
BOTTOM_OUTPUT_ROW_Y = (SCREEN_HEIGHT * 4.5) // 12
MID_CARD_Y = (SCREEN_HEIGHT * 7.5)//12
TOP_SCORE_ROW_Y = (SCREEN_HEIGHT * 9) // 12
BOTTOM_SCORE_ROW_Y = (SCREEN_HEIGHT * 6) // 12

PILE_SEPARATION_X =  CARD_WIDTH

# Face down image
FACE_DOWN_IMAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources/images/cards/cardBack_red2.png")

HAND_PILE = 0

# COLOR
COLOR_ACTIVE = (200,200,255)
COLOR_INACTIVE = (255,255,255)

# Card constants
CARD_VALUES = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
CARD_SUITS = ["Spades", "Hearts", "Clubs", "Diamonds", "Joker"]

CARD_VALUE2SYMBOL = {CARD_VALUES[index]:index for index in range(len(CARD_VALUES))}
CARD_SUITS2SYMBOL = {CARD_SUITS[index]:index for index in range(len(CARD_SUITS))}

class Mat(arcade.SpriteSolidColor):
    """ Mat for a card pile """

    def __init__(self, pile_position_in_card_pile_list, *args, **kwargs):
        """ Card constructor """

        # Attributes for suit and value
        super().__init__(*args, **kwargs)
        # Image to use for the sprite when face up
        self.pile_position_in_card_pile_list = pile_position_in_card_pile_list


class Card(arcade.Sprite):
    """ Card sprite """

    def __init__(self, value=None, face=False, is_active=False, scale=1):
        """ Card constructor """

        # Attributes for suit and value
        self._value = None
        # Image to use for the sprite when face up
        self.image_file_name = None
        self._is_face_up = None
        self._is_active = None
        super().__init__(self.image_file_name, scale)
        self.value = value
        self.face = face
        self._is_active = is_active

    @property
    def value(self):
        return self._value
    @value.setter
    def value(self, x):
        self._value = x
        #self.image_file_name = value2card(x)
        if x is None:
            self.image_file_name = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources/images/cards/cardBack_red2.png")
        else:
            self.image_file_name = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"resources/images/cards/card{CARD_SUITS[(x % 54)//13]}{CARD_VALUES[(x% 54)% 13]}.png")

    @property
    def face(self):
        return 'U' if self._is_face_up else 'D'
    @face.setter
    def face(self, x):
        if x == 'U':
            self.texture = arcade.load_texture(self.image_file_name)
            self._is_face_up = True
        else:
            self.texture = arcade.load_texture(FACE_DOWN_IMAGE)
            self._is_face_up = False

    def flip_face(self):
        if self._is_face_up:
            self.face = 'D'
        else:
            self.face = 'U'

    def face_flipped(self):
        return 'D' if self._is_face_up else 'U'

    @property
    def active(self):
        return self._is_active
    @active.setter
    def active(self, x):
        self._is_active = x
        if self._is_active:
            self.color = COLOR_ACTIVE
        else:
            self.color = COLOR_INACTIVE

    #def code_face_flipped(self):
    #    return self.value, 'D' if self._is_face_up else 'U'


def sort_cards(value_list, exclude_values=None):
    return [w[0] for w in sorted([(w, (w % 54)) for w in value_list], key=lambda x: x[1])]

def calculate_main_pile_positions(player_index, n_player, self_player_index=None):
    if self_player_index is None:
        self_player_index = 0
    mat_position_index = (player_index - self_player_index) % n_player
    if mat_position_index < math.ceil(n_player / 2):
        mat_x = STARTING_X + MAT_WIDTH * NORMAL_MAT_SCALE * ((1+HORIZONTAL_MARGIN_PERCENT)  * mat_position_index + 0.5)
        mat_y = BOTTOM_OUTPUT_ROW_Y
    else:
        mat_x = STARTING_X + MAT_WIDTH * NORMAL_MAT_SCALE * ((1+HORIZONTAL_MARGIN_PERCENT)  * (n_player-1-mat_position_index) + 0.5)
        mat_y = TOP_OUTPUT_ROW_Y
    return mat_x, mat_y

def calculate_score_pile_positions(player_index, n_player, self_player_index=None):
    if self_player_index is None:
        self_player_index = 0
    mat_position_index = (player_index - self_player_index) % n_player
    if mat_position_index < math.ceil(n_player / 2):
        mat_x = STARTING_X + MAT_WIDTH * NORMAL_MAT_SCALE * ((1+HORIZONTAL_MARGIN_PERCENT)  * mat_position_index + 0.5)
        mat_y = BOTTOM_SCORE_ROW_Y #- MAT_HEIGHT * NORMAL_MAT_SCALE
    else:
        mat_x = STARTING_X + MAT_WIDTH * NORMAL_MAT_SCALE * ((1+HORIZONTAL_MARGIN_PERCENT)  * (n_player-1-mat_position_index) + 0.5)
        mat_y = TOP_SCORE_ROW_Y #+ MAT_HEIGHT * NORMAL_MAT_SCALE
    return mat_x, mat_y

COM_TO_SERVER_UPDATE = 1
COM_TO_SERVER_NOUPDATE = 0
COM_FROM_SERVER_UPDATE = 1
COM_FROM_SERVER_NOUPDATE = 0

SORT_BY_SUIT=1

class CardPile(arcade.SpriteList):
    """ Card sprite """

    def __init__(self, card_pile_id, mat_center, mat_size, mat_boundary, card_scale, card_offset,  other_properties=None, *args, **kwargs):
        """ Card constructor """

        super().__init__( *args, **kwargs)
        self.card_pile_id=card_pile_id
        self.mat_center = mat_center
        self.card_start_x, self.card_start_y= mat_center[0] - mat_size[0]//2 + mat_boundary[0], mat_center[1] + mat_size[1]//2 - mat_boundary[1]
        self.card_max_x = mat_center[0] + mat_size[0]//2 - mat_boundary[0]
        self.step_x, self.step_y = int(card_offset[0]), int(card_offset[1])
        self.card_scale = card_scale
        self._cached_values = []
        self._cached_face_status = {}
        self.other_properties = copy.deepcopy(other_properties)

    def clear(self):
        """ clear entire pile"""
        self._cached_values = []
        self._cached_face_status = {}
        while self.__len__() > 0:
            self.pop()

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
        card.scale=self.card_scale
        #card.y = card_y
        self.append(card)

        #self._cached_codes.append(card.code)
        self._cached_values.append(card.value)
        self._cached_face_status[card.value]=card.face

    def to_valuelist(self):
        """ export as value list"""
        return [w.value for w in self]

    def to_face_staus(self):
        """ export as dictionary"""
        return {w.value:w.face for w in self}



    def remove_card(self, card):
        self.remove(card)
        self._cached_values.remove(card.value)
        self._cached_face_status.pop(card.value)
        #self._cached_codes.remove(card.code)

    def sort_cards(self, sorting_rule=SORT_BY_SUIT):
        """ sort cards based on certain order

        :param sorting_rule:
        :return: None
        """
        if sorting_rule == SORT_BY_SUIT:
            sorted_cards = sorted([(w, w.value % 54) for w in self], key = lambda x:x[1])
            self.clear()
            for card, _ in sorted_cards:
                self.add_card(card)

    def from_value_face(self, value_list, face_status_dict):
        """ update pile based on value list and face status dictionary"""
        # update pile based on new value list and face status dict
        cards_to_remove = set(self._cached_values) - set(value_list)
        cards_to_add = set(value_list) - set(self._cached_values)
        cards_to_flip = dict(set(self._cached_face_status.items())-set(face_status_dict.items()))

        if cards_to_remove or cards_to_flip or cards_to_add:
            self._cached_values = value_list
            self._cached_face_status = {key: value for key, value in face_status_dict.items() if key in self._cached_values}

            if cards_to_remove:
                cards_to_remove_ls = [card for card in self if card.value in cards_to_remove]
                for card in cards_to_remove_ls:
                    self.remove(card)

            if cards_to_flip:
                cards_to_flip = [card for card in self if card.value in cards_to_flip.keys()]
                for card in cards_to_flip:
                    card.face = face_status_dict[card.value]

            if cards_to_add:
                for value in cards_to_add:
                    self.add_card(Card(value=value, face=face_status_dict[value]))

        card_added_removed = set.union(cards_to_remove, cards_to_add)
        return card_added_removed

# suporting fuction to localize mouse click
def get_distance_to_mat(card, mat):
    return math.sqrt(
        max((abs(card.center_x - mat.center_x) - mat.width/2),0) **2 +
        max((abs(card.center_y - mat.center_y) - mat.height / 2), 0) ** 2)

def get_minimum_distance_mat(card, mat_list):
    if len(mat_list)==0:
        return None, None
    else:
        min_dist = get_distance_to_mat(card, mat_list[0])
        min_index = 0
        #print(f"mi: {0} di: {min_dist}")
        for index, mat in enumerate(mat_list[1:], 1):
            dist = get_distance_to_mat(card, mat)
            #print(f"mi: {index} di: {dist}")
            if dist < min_dist:
                min_dist = dist
                min_index = index
    return mat_list[min_index], min_dist


GAME_STATUS_RESET = -1
GAME_STATUS_ONGOING = 0

SORT_BUTTON_WIDTH=100
BUTTON_HEIGHT=20

class FYFGame(arcade.View):
    """ Main application class. """

    def __init__(self, player_name=None):
        super().__init__()
        self.ui_manager = gui.UIManager()
        arcade.set_background_color(arcade.color.AMAZON)
        self.event_buffer = []
        self.game_state = None
        self.player_id = str(uuid.uuid4())
        self.player_name = player_name
        self.player_name_display_list = None
        self.n_player = None
        self.self_player_index = None
        self.n_decks = None
        self.n_residual_card = None
        self.n_pile= None

        ## list used to control moving cards

        # List of cards we are dragging with the mouse
        self.held_cards = None
        # Original location of cards we are dragging with the mouse in case
        # they have to go back.
        self.held_cards_original_position = None
        # active cards
        self.active_cards = None
        # card that was pressed on
        self.card_on_press = None

        # Sprite list with all the mats tha cards lay on.
        self.pile_mat_list = None
        self.pile_text_list = None
        self.card_pile_list = None


    def clear_all_piles(self):
        """ clear all piles """
        for card_pile in self.card_pile_list:
            card_pile.clear()

        self.held_cards = []
        self.held_cards_original_position=[]
        self.active_cards = []
        self.card_on_press = None

    def setup(self, n_player = 6, player_index=1, n_decks=6, n_residual_card=6):
        """ Set up the game here. Call this function to restart the game. """
        self.ui_manager.purge_ui_elements()
        self.n_player = n_player
        self.n_pile = self.n_player *3+2
        self.self_player_index = player_index
        self.n_decks=n_decks
        self.n_residual_card=n_residual_card
        # List of cards we are dragging with the mouse
        self.held_cards = []
        self.held_cards_original_position=[]
        self.active_cards = []
        self.card_pile_list = []
        #self.held_cards_original_pile = None

        # ---  Create the mats the cards go on.

        # Sprite list with all the mats tha cards lay on.
        self.pile_mat_list: arcade.SpriteList = arcade.SpriteList(is_static=True)
        self.pile_text_list = []
        self.player_name_display_list = []

        # own pile

        #self.hand_pile_index = len(self.card_pile_list)
        hand_pile_mat = Mat(len(self.card_pile_list), int(HAND_MAT_WIDTH*CARD_SCALE), int(HAND_MAT_HEIGHT*CARD_SCALE),
                                   arcade.csscolor.LIGHT_SLATE_GREY)
        self.card_pile_list.append(CardPile(
            card_pile_id=self.self_player_index,
            mat_center=(HAND_MAT_X, HAND_MAT_Y),
            mat_size = (HAND_MAT_WIDTH*CARD_SCALE, HAND_MAT_HEIGHT*CARD_SCALE),
            mat_boundary=(int(CARD_WIDTH*CARD_SCALE/2), int(CARD_HEIGHT*CARD_SCALE/2)),
            card_scale = CARD_SCALE,
            card_offset = (int(CARD_WIDTH*CARD_SCALE*CARD_OFFSET_PCT),int(CARD_HEIGHT*CARD_SCALE)),
            other_properties={'Clearable': False}
        ))

        hand_pile_mat.position = HAND_MAT_X, HAND_MAT_Y
        self.pile_mat_list.append(hand_pile_mat)
        self.pile_text_list.append(('Your Private Pile', hand_pile_mat.center_x-50, hand_pile_mat.center_y, arcade.color.GOLD, 15))
        starting_x = hand_pile_mat.right+20
        starting_y = hand_pile_mat.top - 20
        step_y = 20
        self.pile_text_list.append(
            ("Left press/release to drag", starting_x, starting_y, arcade.csscolor.GOLD, 15))
        self.pile_text_list.append(
            ("Right click to flip a card", starting_x, starting_y-step_y, arcade.csscolor.GOLD, 15))
        self.pile_text_list.append(
            ("CTRL + right click to clear a pile", starting_x, starting_y-step_y*2, arcade.csscolor.GOLD,
             15))
        self.pile_text_list.append(
            ("ALT + right click to sort a pile", starting_x, starting_y-step_y*3, arcade.csscolor.GOLD,
             15))
        self.pile_text_list.append(
            ("CLRT + R to reset the game", starting_x, starting_y-step_y*4, arcade.csscolor.GOLD,
             15))

        # button = gui.UIFlatButton(
        #     'sort',
        #     center_x=int(hand_pile_mat.right-SORT_BUTTON_WIDTH//2),
        #     center_y=int(hand_pile_mat.bottom+BUTTON_HEIGHT//2),
        #     width=SORT_BUTTON_WIDTH,
        #     height=BUTTON_HEIGHT
        # )
        #self.ui_manager.add_ui_element(button)

        # main output piles for each player
        starting_index_output_pile = self.n_player
        for player_index in range(self.n_player):

            pile_position = calculate_main_pile_positions(player_index, self.n_player, self.self_player_index)
            pile = Mat(len(self.card_pile_list), int(MAT_WIDTH*NORMAL_MAT_SCALE), int(MAT_HEIGHT*NORMAL_MAT_SCALE),
                                           arcade.csscolor.FOREST_GREEN if player_index==self.self_player_index else arcade.csscolor.DARK_OLIVE_GREEN)
            pile.position = pile_position
            self.pile_mat_list.append(pile)
            self.card_pile_list.append(
                CardPile(
                    card_pile_id=player_index+starting_index_output_pile,
                    mat_center = (pile_position[0], pile_position[1]),
                    mat_size = (int(MAT_WIDTH*NORMAL_MAT_SCALE), int(MAT_HEIGHT*NORMAL_MAT_SCALE)),
                    mat_boundary = (int(CARD_WIDTH*NORMAL_MAT_SCALE/2), int(CARD_HEIGHT*NORMAL_MAT_SCALE/2)),
                    card_scale = NORMAL_MAT_SCALE,
                    card_offset = (int(CARD_WIDTH*NORMAL_MAT_SCALE*CARD_OFFSET_PCT),int(CARD_HEIGHT*NORMAL_MAT_SCALE*CARD_OFFSET_PCT)),
                    other_properties = {'Clearable':True}
                )
            )
            if player_index == self.self_player_index:
                self.pile_text_list.append(
                    ('Lay your card here', pile.center_x-50, pile.center_y, arcade.color.DARK_GRAY, 10))

            self.player_name_display_list.append(
                (player_index, pile.center_x - 50, pile.center_y-20, arcade.color.DARK_GRAY, 10)
            )
        # score piles for each player
        starting_index_score_pile = self.n_player*2
        for player_index in range(self.n_player):

            pile_position = calculate_score_pile_positions(player_index, self.n_player, self.self_player_index)
            pile = Mat(len(self.card_pile_list), int(MAT_WIDTH*0.5), int(MAT_HEIGHT*0.3),
                                           arcade.csscolor.DARK_SLATE_GRAY)
            pile.position = pile_position
            self.pile_mat_list.append(pile)
            self.card_pile_list.append(
                CardPile(
                    card_pile_id=player_index + starting_index_score_pile,
                    mat_center=(pile_position[0], pile_position[1]),
                    mat_size=(int(MAT_WIDTH * 0.5), int(MAT_HEIGHT * SCORE_MAT_SCALE)),
                    mat_boundary=(int(CARD_WIDTH * SCORE_MAT_SCALE/2), int(CARD_HEIGHT * SCORE_MAT_SCALE/2)),
                    card_scale =SCORE_MAT_SCALE,
                    card_offset=(int(CARD_WIDTH * SCORE_MAT_SCALE * CARD_OFFSET_PCT),
                                 int(CARD_HEIGHT * SCORE_MAT_SCALE * CARD_OFFSET_PCT)),
                    other_properties={'Clearable': False}
                )
            )
            if player_index == self.self_player_index:
               self.pile_text_list.append(
                    ('Cards you scored', pile.center_x-50, pile.center_y, arcade.csscolor.DARK_GRAY, 10))
            #else:
            #    self.pile_text_list.append(
            #        ("Public: other's scored cards", pile.center_x-50, pile.center_y, arcade.csscolor.DARK_GRAY, 10))

        pile = Mat(len(self.card_pile_list), int(MAT_WIDTH*0.5), int(MAT_HEIGHT*0.3), arcade.csscolor.DARK_SLATE_BLUE)
        pile.position = int(MAT_WIDTH * 0.35), MID_CARD_Y
        self.pile_mat_list.append(pile)
        self.card_pile_list.append(
            CardPile(
                card_pile_id=self.n_player*3,
                mat_center=pile.position,
                mat_size=(int(MAT_WIDTH * 0.5), int(MAT_HEIGHT * SCORE_MAT_SCALE)),
                mat_boundary=(int(CARD_WIDTH * SCORE_MAT_SCALE/2), int(CARD_HEIGHT * SCORE_MAT_SCALE/2)),
                card_scale =SCORE_MAT_SCALE,
                card_offset=(int(CARD_WIDTH * SCORE_MAT_SCALE * CARD_OFFSET_PCT),
                             int(CARD_HEIGHT * SCORE_MAT_SCALE * CARD_OFFSET_PCT)),
                other_properties={'Clearable': False}
            )
        )
        self.pile_text_list.append(
            ("Hidden pile", pile.center_x - 50, pile.center_y, arcade.csscolor.DARK_GRAY, 10))

        pile = Mat(len(self.card_pile_list),
                     MAT_WIDTH, int(MAT_HEIGHT*0.3), arcade.csscolor.DARK_SLATE_GRAY)
        pile.position = int(MAT_WIDTH * 1.2), MID_CARD_Y
        self.pile_mat_list.append(pile)
        self.card_pile_list.append(
            CardPile(
                card_pile_id=self.n_player*3+1,
                mat_center=pile.position,
                mat_size=(int(MAT_WIDTH), int(MAT_HEIGHT * SCORE_MAT_SCALE)),
                mat_boundary=(int(CARD_WIDTH * SCORE_MAT_SCALE/2), int(CARD_HEIGHT * SCORE_MAT_SCALE/2)),
                card_scale =SCORE_MAT_SCALE,
                card_offset=(int(CARD_WIDTH * SCORE_MAT_SCALE * CARD_OFFSET_PCT),
                             int(CARD_HEIGHT * SCORE_MAT_SCALE * CARD_OFFSET_PCT)),
                other_properties={'Clearable': False}
            )
        )
        self.pile_text_list.append(
            ("Public: all scored cards", pile.center_x - 50, pile.center_y, arcade.csscolor.DARK_GRAY, 10))

    def update_game_state(self, gs_dict):
        """ update game state from gs_dict """
        # no GUI change is allowed in this function
        self.game_state = gameutil.GameState(**gs_dict)

    def on_update(self, delta_time):
        """ on update, which is called in the event loop."""
        if self.game_state:
            if self.game_state.status=='New Game':

                self.game_state.status='Game'
                self.clear_all_piles()
            held_cards_value = [w.value for w in self.held_cards]
            active_cards_value = [w.value for w in self.active_cards]
            # update piles
            for w in self.card_pile_list:
                if (w.card_pile_id) in self.game_state.cards_in_pile:
                    # update card
                    card_changed_removed = w.from_value_face(self.game_state.cards_in_pile[w.card_pile_id], self.game_state.cards_status)

                    # check whether hand-held cards affected

                    for card_value in card_changed_removed:
                        if card_value in held_cards_value:
                            index = held_cards_value.index(card_value)
                            if self.held_cards[index] == self.card_on_press:
                                self.card_on_press = None
                            self.held_cards.remove(self.held_cards[index])
                            self.held_cards_original_position.remove(self.held_cards_original_position[index])
                            self.held_cards_value.remove(self.held_cards_value[index])

                        if card_value in active_cards_value:
                            index = active_cards_value.index(card_value)
                            self.active_cards[index].active = False
                            self.active_cards.remove(self.active_cards[index])
                            self.active_cards_value.remove(self.active_cards_value[index])

    def on_draw(self):
        """ Render the screen. """
        arcade.start_render()

        # Draw the mats the cards go on to
        self.pile_mat_list.draw()

        # draw text
        for text, x, y, color, size in self.pile_text_list:
            arcade.draw_text(text, x, y, color, size)
        if self.game_state:
            for player_index, x, y, color, size in self.player_name_display_list:
                if player_index in self.game_state.player_name:
                    arcade.draw_text(self.game_state.player_name[player_index], x, y, color, size)
        # Draw the cards
        for card_pile in self.card_pile_list[::-1]:
            card_pile.draw()

    def on_key_press(self, symbol: int, modifiers: int):
         """ User presses key """
         if symbol == arcade.key.R:
             if modifiers & arcade.key.MOD_CTRL:
                self.initiate_game_restart()
         if symbol == arcade.key.C:
                self.connect()
    def get_pile_index_for_card(self, card):
        """ What pile is this card in? """

        for index, pile in enumerate(self.card_pile_list):
            if card in pile:
                return index


    def on_mouse_press(self, x, y, button, key_modifiers):
        """ Called when the user presses a mouse button. """
        self.card_on_press = None
        c_mats = arcade.get_sprites_at_point((x, y), self.pile_mat_list)
        if len(c_mats)>0:
            pile_index = c_mats[0].pile_position_in_card_pile_list

            if button == arcade.MOUSE_BUTTON_RIGHT and (key_modifiers & arcade.key.MOD_ALT):
                # with control, sort current piles
                self.card_pile_list[pile_index].sort_cards()
            elif button == arcade.MOUSE_BUTTON_RIGHT and (key_modifiers & arcade.key.MOD_CTRL):
                self.clear_a_pile(pile_index)
            else:
                cards = arcade.get_sprites_at_point((x, y), self.card_pile_list[pile_index])
                if len(cards) > 0:

                    primary_card = cards[-1]
                    if button == arcade.MOUSE_BUTTON_LEFT:
                        self.card_on_press = primary_card

                        if not primary_card.active:

                            if len(self.active_cards)>=1:
                                # check if the pile being clicked on is the same as the active cards
                                current_pile_index = self.get_pile_index_for_card(self.card_on_press)
                                active_card_pile = self.get_pile_index_for_card(self.active_cards[0])

                                if current_pile_index != active_card_pile:
                                    # if the card being clicked on belongs to a different pile than those active cards. deactive other cards
                                    for card in self.active_cards:
                                        card.active = False
                                    self.active_cards = []
                            # will held this regardless whether its active
                            self.held_cards.append(primary_card)
                            self.held_cards_original_position.append(primary_card.position)

                        # all active card will move together
                        for card in self.active_cards:
                             self.held_cards.append(card)
                             self.held_cards_original_position.append(card.position)

                    elif button == arcade.MOUSE_BUTTON_RIGHT:
                        self.flip_card(primary_card)


    def on_mouse_release(self, x: float, y: float, button: int,
                         modifiers: int):
        """ Called when the user presses a mouse button. """

        # If we don't have any cards, who cares
        if self.card_on_press is None:
            return
        if button == arcade.MOUSE_BUTTON_RIGHT:
            return

        # Find the closest pile, in case we are in contact with more than one
        new_pile, distance = get_minimum_distance_mat(self.card_on_press, self.pile_mat_list)
        reset_position = True

        # See if we are in contact with the closest pile
        if arcade.check_for_collision(self.card_on_press, new_pile):

            # What pile is it?
            new_pile_index = new_pile.pile_position_in_card_pile_list#self.pile_mat_list.index(pile)

            #  Is it the same pile we came from?
            old_pile_index = self.get_pile_index_for_card(self.card_on_press)
            if new_pile_index == old_pile_index:
                cards = arcade.get_sprites_at_point((x, y), self.card_pile_list[new_pile_index])
                if len(cards) >= 1:
                    primary_card = cards[-1]
                    if primary_card is not None:
                        if primary_card == self.card_on_press:
                            # did not move position
                            if self.card_on_press.active:
                                # if it were active
                                self.card_on_press.active = False
                                self.active_cards.remove(self.card_on_press)
                            else:
                                self.card_on_press.active = True
                                self.active_cards.append(self.card_on_press)
                            self.card_on_press = None
            else:
                self.move_cards(self.held_cards, new_pile_index)
                for card in self.active_cards:
                    card.active = False
                self.active_cards = []
                # Success, don't reset position of cards
                reset_position = False
        if reset_position:
            # Where-ever we were dropped, it wasn't valid. Reset the each card's position
            # to its original spot.
            for card_index, card in enumerate(self.held_cards):
                card.position = self.held_cards_original_position[card_index]

        # We are no longer holding cards
        self.held_cards = []
        self.held_cards_original_position = []

    def on_mouse_motion(self, x: float, y: float, dx: float, dy: float):
        """ User moves mouse """

        # If we are holding cards, move them with the mouse
        for card in self.held_cards:
            card.center_x += dx
            card.center_y += dy

    ## supporting functions to send out events
    def connect(self):
        new_event = gameutil.Event(type='Connect',
                                   player_index=self.self_player_index,
                                   player_name = self.player_name,
                                   player_id = self.player_id
                                   )
        self.event_buffer.append(new_event)

    def move_cards(self, cards, new_pile_index):
        old_pile_index = self.get_pile_index_for_card(cards[0])

        for i, dropped_card in enumerate(cards):
            self.card_pile_list[new_pile_index].add_card(dropped_card)
            self.card_pile_list[old_pile_index].remove_card(dropped_card)
        new_event = gameutil.Event(type='Move',
                                   player_index=self.self_player_index,
                                   src_pile = self.card_pile_list[old_pile_index].card_pile_id,
                                   dst_pile = self.card_pile_list[new_pile_index].card_pile_id,
                                   cards = [card.value for card in cards]
                                   )
        self.event_buffer.append(new_event)
        self.game_state.update_from_event(new_event)

    def flip_card(self, card):
        new_face=card.face_flipped()

        new_event = gameutil.Event(type='Flip',
                                   player_index=self.self_player_index,
                                   cards = [card.value],
                                   cards_status = {card.value:new_face}
                                   )

        self.event_buffer.append(new_event)
        self.game_state.update_from_event(new_event)
        card.face= new_face

    def clear_a_pile(self, pile_index):
        if 'Clearable' in self.card_pile_list[pile_index].other_properties:
            if self.card_pile_list[pile_index].other_properties['Clearable']:
                new_event = gameutil.Event(type='Remove',
                                           player_index=self.self_player_index,
                                           src_pile = self.card_pile_list[pile_index].card_pile_id,
                                           cards = self.card_pile_list[pile_index].to_valuelist()
                                           )
                self.card_pile_list[pile_index].clear()  # remove_card(dropped_card)
                self.event_buffer.append(new_event)
                self.game_state.update_from_event(new_event)


    def initiate_game_restart(self):
        n_card_per_player = (self.n_decks * 64 - self.n_residual_card) // self.n_player
        n_residual_card = self.n_decks * 64 - n_card_per_player*self.n_player
        n_card_per_pile = {w: n_card_per_player for w in range(self.n_player)}
        n_card_per_pile[self.n_player*3]=n_residual_card
        new_event = gameutil.Event(type='StartNewGame',
                                   player_index=self.self_player_index,
                                   n_player = self.n_player,
                                   n_pile = self.n_pile,
                                   n_card_per_pile = n_card_per_pile,
                                   face_down_pile = [self.n_player*3],
                                   )
        self.event_buffer.append(new_event)


def thread_pusher(window: FYFGame, server_ip:str):
    ctx = Context()
    push_sock: Socket = ctx.socket(zmq.PUSH)
    push_sock.connect(f'tcp://{server_ip}:25001')
    try:
        while True:
            if window.event_buffer:
                d = window.event_buffer.pop()
                msg = dict(counter=1, event=d.asdict())
                print(msg)
                push_sock.send_json(msg)
            time.sleep(1 / UPDATE_TICK)

    finally:
        push_sock.close(1)
        ctx.destroy(linger=1)


def thread_receiver(window: FYFGame, server_ip: str):
    ctx = Context()
    sub_sock: Socket = ctx.socket(zmq.SUB)
    sub_sock.connect(f'tcp://{server_ip}:25000')
    sub_sock.subscribe('')
    try:
        while True:
            gs_dict = sub_sock.recv_json(object_hook=gameutil.json_obj_hook)
            window.update_game_state(gs_dict)
            time.sleep(1 / UPDATE_TICK)

    finally:
        sub_sock.close(1)
        ctx.destroy(linger=1)

def main(args):
    """ Main method """

    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE, resizable=True)

    game_view = FYFGame(args.player_name if args.player_name!='' else f'PLAYER {args.playerindex}')
    game_view.setup(n_player=args.n_player, player_index=args.playerindex)
    window.show_view(game_view)
    thread1 = threading.Thread(
        target=thread_pusher, args=(game_view, args.server_ip,), daemon=True)
    thread2 = threading.Thread(
        target=thread_receiver, args=(game_view, args.server_ip,), daemon=True)
    thread1.start()
    thread2.start()
    arcade.run()


if __name__ == "__main__":
    args = parser.parse_args()
    main(args)