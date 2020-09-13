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
#import GameState, Event


parser = argparse.ArgumentParser(description='Card client')

parser.add_argument('playerindex', type=int,
                    help='player index')

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

#def card2int(suit, value):
#    return CARD_SUITS2SYMBOL[suit]*13+ CARD_VALUE2SYMBOL[value]

def value2card(x):
    if x is None:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources/images/cards/cardBack_red2.png")
    else:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), f"resources/images/cards/card{CARD_SUITS[(x % 54)//13]}{CARD_VALUES[(x% 54)% 13]}.png")
#def int2card(x):
#    return CARD_SUITS[(x % 54)//13], CARD_VALUES[x%13]

class Mat(arcade.SpriteSolidColor):
    """ Card sprite """

    def __init__(self, index,  *args, **kwargs):
        """ Card constructor """

        # Attributes for suit and value
        super().__init__(*args, **kwargs)
        # Image to use for the sprite when face up
        self.index = index



class Card(arcade.Sprite):
    """ Card sprite """

    def __init__(self, code = None, value=None, face=False, is_active=False, scale=1):
        """ Card constructor """

        # Attributes for suit and value
        self.value = None
        # Image to use for the sprite when face up
        self.image_file_name = None
        self._is_face_up = None
        self.is_active = is_active
        super().__init__(self.image_file_name, scale)
        if code is not None:
            self.code = code
        else:
            self._change_value(value, face=='U')



    def _change_value(self, value=None, face_up=True):
        self.value=value
        self.image_file_name = value2card(value)
        if face_up:
            self.face_up()
        else:
            self.face_down()

    def flip_face(self):
        if self._is_face_up:
            self.face_down()
        else:
            self.face_up()

    def face_down(self):
        """ Turn card face-down """
        self.texture = arcade.load_texture(FACE_DOWN_IMAGE)
        self._is_face_up = False

    def face_up(self):
        """ Turn card face-up """
        self.texture = arcade.load_texture(self.image_file_name)
        self._is_face_up = True

    def switch_activation_status(self):
        self.is_active = not self.is_active
        if self.is_active:
            self.color = COLOR_ACTIVE
        else:
            self.color = COLOR_INACTIVE


    def swtich_to_active(self):
        self.is_active = True
        self.color = COLOR_ACTIVE

    def to_code(self):
        return self.value, 'U' if self._is_face_up else 'D'

    def update_from_code(self, code):
        if code[1]=='U':
            self.face_up()
        else:
            self.face_down()
        self.value = code[0]
        self.image_file_name = value2card(self.value)

    @property
    def face(self):
        return 'U' if self._is_face_up else 'D'
    @face.setter
    def face(self, x):
        if x == 'U':
            self.face_up()
        else:
            self.face_down()

    @property
    def code(self):
        return self.value, 'U' if self._is_face_up else 'D'
    @code.setter
    def code(self, x):
        self.value = x[0]
        self.image_file_name = value2card(self.value)
        #print((self.value, self.image_file_name))
        if x[1]=='U':
            self.face_up()
        else:
            self.face_down()


    #def code_face_flipped(self):
    #    return self.value, 'D' if self._is_face_up else 'U'
    def face_flipped(self):
        return 'D' if self._is_face_up else 'U'

    @property
    def active(self):
        return self.is_active

    @active.setter
    def active(self, value):
        self.is_active=value
        if self.is_active:
            self.color = COLOR_ACTIVE
        else:
            self.color = COLOR_INACTIVE


def sort_cards(value_list, exclude_values=None):
    return [w[0] for w in sorted([(w, (w % 54)) for w in value_list], key=lambda x: x[1])]

    #return sorted([w for w in int_list if w not in exclude_values]) + sorted([w for w in int_list if w in exclude_values])

def sort_card_codes(code_list):
    return [s[0] for s in sorted([((w, card_attr), (w % 54)) for w, card_attr in code_list], key=lambda x: x[1])]

#def card_list_to_attr_value_list():
#    return [(w.value, 'U' if w.is_face_up else 'D') for w in card_list]


def card_list_to_int_list(card_list):
    return [w.value for w in card_list]
    #return [card2int(card.suit, card.value) for card in card_list]

# def update_cards_from_int(card_list, value_list, starting_x, starting_y, max_x, step_x, step_y, scale=CARD_SCALE):
#     sorted_value_list = sort_cards(value_list)
#     c_card_ints = card_list_to_int_list(card_list)
#     if set(c_card_ints) == set(value_list):
#         # if the cards are the same then there is no update
#         return
#     else:
#         while card_list:
#             card_list.pop()
#         card_x = starting_x
#         card_y = starting_y
#         for w in sorted_value_list:
#             card = Card(w, scale=scale)
#             card.position = card_x, card_y
#             card_x = card_x + step_x
#             if card_x >= max_x:
#                 card_x = starting_x
#                 card_y = card_y -  step_y
#             card_list.append(card)


def arrange_positions(card_list, starting_x, starting_y, max_x, step_x, step_y):
    card_x = starting_x
    card_y = starting_y
    for card in card_list:
        card.position = card_x, card_y
        card_x = card_x + step_x
        if card_x >= max_x:
            card_x = starting_x
            card_y = card_y - step_y


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



class CardPile(arcade.SpriteList):
    """ Card sprite """

    def __init__(self, card_pile_index, mat_center, mat_size, mat_boundary, card_scale, card_offset,  *args, **kwargs):
        """ Card constructor """

        super().__init__( *args, **kwargs)
        #if can_remove_card is None:
        #    self.can_remove_card = False
        #else:
        #    self.can_remove_card = can_remove_card

        #if can_add_card is None:
        #    self.can_add_card = False
        #else:
        #    self.can_add_card = can_add_card
        self.card_pile_index=card_pile_index
        self.card_start_x, self.card_start_y= mat_center[0] - mat_size[0]//2 + mat_boundary[0], mat_center[1] + mat_size[1]//2 - mat_boundary[1]
        self.card_max_x = mat_center[0] + mat_size[0]//2 - mat_boundary[0]
        self.step_x, self.step_y = int(card_offset[0]), int(card_offset[1])
        self.card_scale = card_scale
        #self.to_server_type=to_server_type
        #self.from_server_type=from_server_type
        #self._cached_codes = []
        self._cached_values = []
        self._cached_face_status = {}
    def reset(self):
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
        return [w.value for w in self]

    def to_face_staus(self):
        return {w.value:w.face for w in self}

    #def to_code(self):
    #    return [w.to_code() for w in self]

    def remove_card(self, card):
        self.remove(card)
        self._cached_values.remove(card.value)
        self._cached_face_status.pop(card.value)
        #self._cached_codes.remove(card.code)


    def from_value_face(self, value_list, face_status_dict):
        # update pile based on new value list and face status dict
        #code_list = [tuple(w) for w in code_list]
        cards_to_remove = set(self._cached_values) - set(value_list)
        cards_to_add = set(value_list) - set(self._cached_values)

        cards_to_flip = dict(set(self._cached_face_status.items())-set(face_status_dict.items()))#[key for key, val in self._cached_face_status if (key in face_status_dict) and face_status_dict[key]!=val]

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



    # def from_code(self, code_list):
    #     code_list = [tuple(w) for w in code_list]
    #     card_to_change = set(self._cached_codes) - set(code_list)
    #     card_to_add = [w for w in code_list if w not in self._cached_codes]
    #
    #     if (not card_to_change) and (not card_to_add):
    #         return
    #     else:
    #         if card_to_change:
    #             cards_to_remove = []
    #             for card in self:
    #                 if card.code in card_to_change:
    #                     code_if_flipped = card.code_face_flipped()
    #                     if code_if_flipped in card_to_add:
    #                         # flip the card
    #                         card_to_add.remove(code_if_flipped)
    #                         card.flip_face()
    #                     else:
    #                         # add card to be removed
    #                         self.remove_card(card)
    #             for card in cards_to_remove:
    #                 self.remove(card)
    #         for code in card_to_add:
    #             self.add_card(Card(code=code))


    #def sort_cards(self):
    #    arrange_positions(self, self.card_start_x, self.card_start_y, self.card_max_x, self.step_x, self.step_y)

    #def update_cards(self, int_list):
    #    update_cards_from_int(self, int_list, self.card_start_x, self.card_start_y, self.card_max_x, self.step_x, self.step_y, self.card_scale)


def get_distance_to_mat(card, mat):
    #print(f"mx: {mat.cente_x} my {mat.center_y}")
    #print(f"x: {mat.center_x}, y:{mat.center_y}")
    return math.sqrt(
        max((abs(card.center_x - mat.center_x) - mat.width/2),0) **2 +
        max((abs(card.center_y - mat.center_y) - mat.height / 2), 0) ** 2)
        #(0 if abs(card.center_x-mat.center_x) <= mat.width else min((card.center_x - mat.center_x - mat.width/2) ** 2, (card.center_x - mat.center_x + mat.width/2) ** 2))+
        #(0 if abs(card.center_y - mat.center_y) <= mat.width else min(
        #    (card.center_y - mat.center_y - mat.width / 2) ** 2, (card.center_y - mat.center_y + mat.width / 2) ** 2)) )


def get_minimum_distance_mat(card, mat_list):
    #print(f"cx: {card.center_x} cy {card.center_y}")
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


class FYFGame(arcade.Window):
    """ Main application class. """

    def __init__(self, n_player=6, n_decks=6, n_residual_card=6):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)

        arcade.set_background_color(arcade.color.AMAZON)
        self.n_player = None
        self.self_player_index = None
        self.n_decks = None
        self.n_residual_card = None
        self.n_pile= None
        #self._lock = threading.Lock()

        # List of cards we are dragging with the mouse
        self.held_cards = None

        # Original location of cards we are dragging with the mouse in case
        # they have to go back.
        self.held_cards_original_position = None
        #self.held_cards_original_pile = None

        # Sprite list with all the mats tha cards lay on.
        self.pile_mat_list = None
        self.card_pile_list = None
        self.event_buffer = []
        self.game_state = None

    def reset_all_piles(self):
        for card_pile in self.card_pile_list:
            card_pile.reset()

    def setup(self, n_player = 6, player_index=1, n_decks=6, n_residual_card=6):
        """ Set up the game here. Call this function to restart the game. """

        self.n_player = n_player
        self.n_pile = self.n_player *3+1
        self.self_player_index = player_index
        self.n_decks=n_decks
        self.n_residual_card=n_residual_card
        # List of cards we are dragging with the mouse
        self.held_cards = []
        self.held_cards_original_position=[]
        self.card_pile_list = []
        #self.held_cards_original_pile = None

        # ---  Create the mats the cards go on.

        # Sprite list with all the mats tha cards lay on.
        self.pile_mat_list: arcade.SpriteList = arcade.SpriteList(is_static=True)

        # own pile

        #self.hand_pile_index = len(self.card_pile_list)
        self.card_pile_list.append(CardPile(
            card_pile_index=self.self_player_index,
            mat_center=(HAND_MAT_X, HAND_MAT_Y),
            mat_size = (HAND_MAT_WIDTH*CARD_SCALE, HAND_MAT_HEIGHT*CARD_SCALE),
            mat_boundary=(int(CARD_WIDTH*CARD_SCALE/2), int(CARD_HEIGHT*CARD_SCALE/2)),
            card_scale = CARD_SCALE,
            card_offset = (int(CARD_WIDTH*CARD_SCALE*CARD_OFFSET_PCT),int(CARD_HEIGHT*CARD_SCALE))
        ))
        hand_pile_mat = Mat(self.self_player_index, int(HAND_MAT_WIDTH*CARD_SCALE), int(HAND_MAT_HEIGHT*CARD_SCALE),
                                   arcade.csscolor.DARK_OLIVE_GREEN)
        hand_pile_mat.position = HAND_MAT_X, HAND_MAT_Y
        self.pile_mat_list.append(hand_pile_mat)

        #output_card_pile = arcade.SpriteSolidColor(MAT_WIDTH, MAT_HEIGHT, arcade.csscolor.DARK_OLIVE_GREEN)
        #output_card_pile.position = int(SCREEN_WIDTH/2), int(HAND_MAT_Y+HAND_MAT_HEIGHT/2+MAT_HEIGHT)
        #self.pile_mat_list.append(output_card_pile)
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
                    card_pile_index=player_index+starting_index_output_pile,
                    mat_center = (pile_position[0], pile_position[1]),
                    mat_size = (int(MAT_WIDTH*NORMAL_MAT_SCALE), int(MAT_HEIGHT*NORMAL_MAT_SCALE)),
                    mat_boundary = (int(CARD_WIDTH*NORMAL_MAT_SCALE/2), int(CARD_HEIGHT*NORMAL_MAT_SCALE/2)),
                    card_scale = NORMAL_MAT_SCALE,
                    card_offset = (int(CARD_WIDTH*NORMAL_MAT_SCALE*CARD_OFFSET_PCT),int(CARD_HEIGHT*NORMAL_MAT_SCALE*CARD_OFFSET_PCT))
                )
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
                    card_pile_index=player_index + starting_index_score_pile,
                    mat_center=(pile_position[0], pile_position[1]),
                    mat_size=(int(MAT_WIDTH * 0.5), int(MAT_HEIGHT * SCORE_MAT_SCALE)),
                    mat_boundary=(int(CARD_WIDTH * SCORE_MAT_SCALE/2), int(CARD_HEIGHT * SCORE_MAT_SCALE/2)),
                    card_scale =SCORE_MAT_SCALE,
                    card_offset=(int(CARD_WIDTH * SCORE_MAT_SCALE * CARD_OFFSET_PCT),
                                 int(CARD_HEIGHT * SCORE_MAT_SCALE * CARD_OFFSET_PCT))
                )
            )

        pile = Mat(len(self.card_pile_list), int(MAT_WIDTH*0.5), int(MAT_HEIGHT*0.3), arcade.csscolor.DARK_SLATE_BLUE)
        pile.position = MAT_WIDTH//2, MID_CARD_Y
        self.pile_mat_list.append(pile)
        self.card_pile_list.append(
            CardPile(
                card_pile_index=self.n_player*3,
                mat_center=(MAT_WIDTH//2, MID_CARD_Y),
                mat_size=(int(MAT_WIDTH * 0.5), int(MAT_HEIGHT * SCORE_MAT_SCALE)),
                mat_boundary=(int(CARD_WIDTH * SCORE_MAT_SCALE/2), int(CARD_HEIGHT * SCORE_MAT_SCALE/2)),
                card_scale =SCORE_MAT_SCALE,
                card_offset=(int(CARD_WIDTH * SCORE_MAT_SCALE * CARD_OFFSET_PCT),
                             int(CARD_HEIGHT * SCORE_MAT_SCALE * CARD_OFFSET_PCT))
            )
        )
        #self.card_pile_list[0].from_code(sort_card_codes(list(zip(list(range(108)), ['U']*108))))

        #print(self.card_pile_list[0].to_code())

    def update_game_state(self, gs_dict):
        self.game_state = gameutil.GameState(**gs_dict)

    #def update_status(self, card_dict):
        #print("us")
        #with self._lock:



    def on_update(self, delta_time):
        #print(self.game_state)
        if self.game_state:
            #print(self.game_state.cards_in_pile.keys())
            if self.game_state.status=='New Game':

                self.game_state.status='Game'
                self.reset_all_piles()
            #print(self.game_state.status)

            for w in self.card_pile_list:
                #if w.from_server_type==COM_FROM_SERVER_UPDATE:
                if (w.card_pile_index) in self.game_state.cards_in_pile:
                    #print(self.game_state.cards_in_pile[(w.card_pile_index)])
                    w.from_value_face(self.game_state.cards_in_pile[w.card_pile_index], self.game_state.cards_status)

                    #w.from_code(self.game_state.cards_in_pile[(w.card_pile_index)])

    def on_draw(self):
        """ Render the screen. """
        #(".")
        # Clear the screen
        #with self._lock:
        arcade.start_render()

        # Draw the mats the cards go on to
        self.pile_mat_list.draw()

        # Draw the cards

        for card_pile in self.card_pile_list[::-1]:
            card_pile.draw()

    def on_key_press(self, symbol: int, modifiers: int):
         """ User presses key """
         if symbol == arcade.key.R:
             if modifiers & arcade.key.MOD_CTRL:
                self.initiate_game_restart()

    def get_pile_index_for_card(self, card):
        """ What pile is this card in? """

        for index, pile in enumerate(self.card_pile_list):
            if card in pile:
                return index


    def on_mouse_press(self, x, y, button, key_modifiers):
        """ Called when the user presses a mouse button. """

        c_mats = arcade.get_sprites_at_point((x, y), self.pile_mat_list)
        if len(c_mats)>0:
            pile_index = c_mats[0].index
            #if self.card_pile_list[pile_index].can_remove_card:
            cards = arcade.get_sprites_at_point((x, y), self.card_pile_list[pile_index])
            if len(cards) > 0:

                primary_card = cards[-1]
                if button == arcade.MOUSE_BUTTON_LEFT:
                    self.held_cards = [primary_card]
                    self.held_cards_original_position = [self.held_cards[0].position]

                elif button == arcade.MOUSE_BUTTON_RIGHT:
                    self.flip_card(primary_card)

    #def remove_card_from_pile(self, card):
    #    """ Remove card from whatever pile it was in. """
    #    for pile in self.piles:
    #        if card in pile:
    #            pile.remove(card)
    #            break

    #def move_card_to_new_pile(self, card, pile_index):
    #    """ Move the card to a new pile """
    #    self.remove_card_from_pile(card)
    #    self.piles[pile_index].append(card)

    def move_cards(self, cards, new_pile_index):
        old_pile_index = self.get_pile_index_for_card(cards[0])

        for i, dropped_card in enumerate(cards):
            self.card_pile_list[new_pile_index].add_card(dropped_card)
            self.card_pile_list[old_pile_index].remove_card(dropped_card)
        new_event = gameutil.Event(type='Move',
                                   player_index=self.self_player_index,
                                   src_pile = self.card_pile_list[old_pile_index].card_pile_index,
                                   dst_pile = self.card_pile_list[new_pile_index].card_pile_index,
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
                                   )
        self.event_buffer.append(new_event)
    def on_mouse_release(self, x: float, y: float, button: int,
                         modifiers: int):
        """ Called when the user presses a mouse button. """

        # If we don't have any cards, who cares
        if len(self.held_cards) == 0:
            return

        # Find the closest pile, in case we are in contact with more than one
        new_pile, distance = get_minimum_distance_mat(self.held_cards[0], self.pile_mat_list)
        #print(new_pile.index)
        #print(distance)

        reset_position = True

        # See if we are in contact with the closest pile
        if arcade.check_for_collision(self.held_cards[0], new_pile):

            # What pile is it?
            new_pile_index = new_pile.index#self.pile_mat_list.index(pile)

            #  Is it the same pile we came from?
            #print("rl")
            #with self._lock:
            old_pile_index = self.get_pile_index_for_card(self.held_cards[0])
            if new_pile_index == old_pile_index:
                # If so, who cares. We'll just reset our position.
                pass
            else:
                self.move_cards(self.held_cards, new_pile_index)
                # Success, don't reset position of cards
                reset_position = False



        if reset_position:
            # Where-ever we were dropped, it wasn't valid. Reset the each card's position
            # to its original spot.
            #with self._lock:
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

def thread_pusher(window: FYFGame, server_ip:str):
    ctx = Context()
    push_sock: Socket = ctx.socket(zmq.PUSH)
    push_sock.connect(f'tcp://{server_ip}:25001')
    try:
        while True:
            if window.event_buffer:
                d = window.event_buffer.pop()
                msg = dict(counter=1, event=d.to_dict())
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




def main(player_index=None, server_ip=None):
    """ Main method """
    window = FYFGame()
    window.setup(n_player=6, player_index=player_index)
    thread1 = threading.Thread(
        target=thread_pusher, args=(window,server_ip,), daemon=True)
    thread2 = threading.Thread(
        target=thread_receiver, args=(window,server_ip,), daemon=True)
    thread1.start()
    thread2.start()
    arcade.run()


if __name__ == "__main__":
    args = parser.parse_args()
    main(args.playerindex,args.server_ip)