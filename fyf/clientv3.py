"""
ZPY Card Game
"""
import math
import asyncio
import threading
import time
import zmq
from zmq.asyncio import Context, Socket
import random
import arcade
import os
import argparse
parser = argparse.ArgumentParser(description='FYF client')

parser.add_argument('playerindex', type=int,
                    help='player index')

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

    def __init__(self, value, face_up=False, is_active=False, scale=1):
        """ Card constructor """

        # Attributes for suit and value
        self.value = 0

        # Image to use for the sprite when face up
        self.image_file_name = None
        self.is_face_up = None
        #self.clickable = True
        self.is_active = None
        self.update(value, face_up, is_active)

        super().__init__(self.image_file_name, scale)

    def update(self, value, face_up=True, is_active=False):
        self.value=value
        self.image_file_name = value2card(value)
        self.is_face_up = face_up
        #if face_up:
        #    self.face_up()
        #else:
        #    self.face_down()
        #
        self.is_active = is_active

    def face_down(self):
        """ Turn card face-down """
        self.texture = arcade.load_texture(FACE_DOWN_IMAGE)
        self.is_face_up = False

    def face_up(self):
        """ Turn card face-up """
        self.texture = arcade.load_texture(self.image_file_name)
        self.is_face_up = True

    def switch_activation_status(self):
        self.is_active = not self.is_active
        if self.is_active:
            self.color = COLOR_ACTIVE
        else:
            self.color = COLOR_INACTIVE


    def swtich_to_active(self):
        self.is_active = True
        self.color = COLOR_ACTIVE

    @property
    def is_face_down(self):
        """ Is this card face down? """
        return not self.is_face_up

    @property
    def active(self):
        return self.is_active



def sort_cards(value_list, exclude_values=None):
    return [w[0] for w in sorted([(w, (w % 54)) for w in value_list], key=lambda x: x[1])]

    #return sorted([w for w in int_list if w not in exclude_values]) + sorted([w for w in int_list if w in exclude_values])


def card_list_to_int_list(card_list):
    return [w.value for w in card_list]
    #return [card2int(card.suit, card.value) for card in card_list]

def update_cards_from_int(card_list, value_list, starting_x, starting_y, max_x, step_x, step_y, scale=CARD_SCALE):
    sorted_value_list = sort_cards(value_list)
    c_card_ints = card_list_to_int_list(card_list)
    if set(c_card_ints) == set(value_list):
        # if the cards are the same then there is no update
        return
    else:
        while card_list:
            card_list.pop()
        card_x = starting_x
        card_y = starting_y
        for w in sorted_value_list:
            card = Card(w, scale=scale)
            card.position = card_x, card_y
            card_x = card_x + step_x
            if card_x >= max_x:
                card_x = starting_x
                card_y = card_y -  step_y
            card_list.append(card)


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

COM_TO_SERVER_SYNC = 1
COM_TO_SERVER_NOUPDATE = 0
COM_FROM_SERVER_NOUPDATE = 0
COM_FROM_SERVER_UPDATE = 1
COM_FROM_SERVER_MERGE = 2



class CardPile(arcade.SpriteList):
    """ Card sprite """

    def __init__(self, card_pile_index=-1, card_start_x=CARD_WIDTH//2, card_start_y=CARD_HEIGHT//2, card_max_x=MAT_WIDTH-CARD_WIDTH//2, card_scale = 1, step_x = CARD_HORIZONTAL_OFFSET, step_y=CARD_VERICAL_OFFSET,
                 can_remove_card=None, can_add_card=None, to_server_type = COM_TO_SERVER_SYNC, from_server_type = COM_FROM_SERVER_NOUPDATE,
                 *args, **kwargs):
        """ Card constructor """

        super().__init__( *args, **kwargs)
        if can_remove_card is None:
            self.can_remove_card = False
        else:
            self.can_remove_card = can_remove_card

        if can_add_card is None:
            self.can_add_card = False
        else:
            self.can_add_card = can_add_card
        self.card_pile_index=card_pile_index
        self.card_start_x = card_start_x
        self.card_start_y = card_start_y
        self.card_max_x = card_max_x
        self.card_scale = card_scale
        self.to_server_type=to_server_type
        self.from_server_type=from_server_type
        self.step_x = int(step_x * self.card_scale)
        self.step_y = int(step_y * self.card_scale)


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

    def to_valuelist(self):
        return [w.value for w in self]

    def sort_cards(self):
        arrange_positions(self, self.card_start_x, self.card_start_y, self.card_max_x, self.step_x, self.step_y)

    def update_cards(self, int_list):
        update_cards_from_int(self, int_list, self.card_start_x, self.card_start_y, self.card_max_x, self.step_x, self.step_y, self.card_scale)


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

    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)

        arcade.set_background_color(arcade.color.AMAZON)
        self.n_player = None
        self.self_player_index = None


        # List of cards we are dragging with the mouse
        self.held_cards = None

        # Original location of cards we are dragging with the mouse in case
        # they have to go back.
        self.held_cards_original_position = None
        #self.held_cards_original_pile = None

        # Sprite list with all the mats tha cards lay on.
        self.pile_mat_list = None
        self.card_pile_list = None

        self.card_codes = dict(
            game_status = 0,
            card_in_hand = dict()
        )
        self.hand_pile_index = 0

    def setup(self, n_player = 6, player_index=1):
        """ Set up the game here. Call this function to restart the game. """
        self.n_player = n_player
        self.self_player_index = player_index
        # List of cards we are dragging with the mouse
        self.held_cards = []
        self.held_cards_original_position=[]
        self.card_pile_list = []
        #self.held_cards_original_pile = None

        # ---  Create the mats the cards go on.

        # Sprite list with all the mats tha cards lay on.
        self.pile_mat_list: arcade.SpriteList = arcade.SpriteList(is_static=True)

        # own pile

        COM_TO_SERVER_SYNC = 1
        COM_TO_SERVER_NOUPDATE = 0
        COM_FROM_SERVER_NOUPDATE = 0
        COM_FROM_SERVER_UPDATE = 1
        COM_FROM_SERVER_MERGE = 2

        self.hand_pile_index = len(self.card_pile_list)
        self.card_pile_list.append(CardPile(card_pile_index=self.self_player_index,
                                            card_start_x=HAND_MAT_X-HAND_MAT_WIDTH*CARD_SCALE//2+CARD_WIDTH*CARD_SCALE//2,
                                            card_start_y= HAND_MAT_Y+HAND_MAT_HEIGHT*CARD_SCALE//2-CARD_HEIGHT*CARD_SCALE/2,
                                            card_max_x=HAND_MAT_X+HAND_MAT_WIDTH*CARD_SCALE//2-CARD_WIDTH*CARD_SCALE//2,
                                            card_scale=CARD_SCALE,
                                            step_y = CARD_HEIGHT*(1+VERTICAL_MARGIN_PERCENT),
                                            can_remove_card=True,
                                            can_add_card=True,
                                            to_server_type=COM_TO_SERVER_SYNC,
                                            from_server_type=COM_FROM_SERVER_NOUPDATE
                                            )
                                   )
        hand_pile_mat = Mat(self.hand_pile_index, int(HAND_MAT_WIDTH*CARD_SCALE), int(HAND_MAT_HEIGHT*CARD_SCALE),
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
                CardPile(card_pile_index=player_index+starting_index_output_pile,
                         card_start_x = pile_position[0] - MAT_WIDTH*NORMAL_MAT_SCALE//2 + CARD_WIDTH*NORMAL_MAT_SCALE//2,
                         card_start_y = pile_position[1] + MAT_HEIGHT*NORMAL_MAT_SCALE // 2 - CARD_HEIGHT*NORMAL_MAT_SCALE // 2,
                         card_max_x = pile_position[0] + MAT_WIDTH*NORMAL_MAT_SCALE//2 -CARD_WIDTH*NORMAL_MAT_SCALE//2,
                         card_scale = NORMAL_MAT_SCALE,
                         can_remove_card=player_index==self.self_player_index,
                         can_add_card=player_index==self.self_player_index,
                         to_server_type=COM_TO_SERVER_SYNC if player_index==self.self_player_index else COM_TO_SERVER_NOUPDATE,
                         from_server_type=COM_FROM_SERVER_NOUPDATE if player_index==self.self_player_index else COM_FROM_SERVER_UPDATE,
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
                         card_start_x = pile_position[0] - MAT_WIDTH*0.5//2 + CARD_WIDTH*0.5//2,
                         card_start_y = pile_position[1] + MAT_HEIGHT*SCORE_MAT_SCALE // 2 - CARD_HEIGHT*SCORE_MAT_SCALE // 2,
                         card_max_x = pile_position[0] + MAT_WIDTH*0.5//2 -CARD_WIDTH*0.5//2,
                         card_scale =SCORE_MAT_SCALE,
                         can_remove_card=False,#player_index==self.self_player_index,
                         can_add_card=True,
                         to_server_type=COM_TO_SERVER_SYNC,
                         from_server_type=COM_FROM_SERVER_UPDATE
                         )
            )

        # Sprite list with all the cards, no matter what pile they are in.

        #self.out_card_list = arcade.SpriteList()
        # Create every card
        #update_cards(self.card_codes['card_in_hand'],
        #             self.card_pile_list[self.hand_pile_index],
        #             HAND_MAT_X-int(HAND_MAT_WIDTH/2)+int(CARD_WIDTH/2), HAND_MAT_Y-int(HAND_MAT_HEIGHT/2)+int(CARD_HEIGHT/2),
        #             HAND_MAT_X+int((HAND_MAT_WIDTH-CARD_WIDTH)/2))

        self.card_pile_list[self.hand_pile_index].update_cards(list(range(108)))

    @property
    def card_status(self):
        return dict(
            player_index = self.self_player_index,
            cards_in_pile = {pile.card_pile_index: pile.to_valuelist() for pile in self.card_pile_list if pile.to_server_type ==COM_TO_SERVER_SYNC}
            #card_in_hand = {self.self_player_index: self.card_pile_list[0].to_valuelist()},
            #output_pile = {pindex: self.card_pile_list[pindex+1].to_valuelist() for pindex in range(0, self.n_player) if self.card_pile_list[pindex+1].to_server_type ==COM_TO_SERVER_SYNC},
            #score_pile = {pindex:self.card_pile_list[pindex+1+self.n_player].to_valuelist() for pindex in range(0, self.n_player) if self.card_pile_list[pindex+1+self.n_player].to_server_type ==COM_TO_SERVER_SYNC},
        )

    def update_status(self, card_dict):
        for w in self.card_pile_list:
            if w.from_server_type==COM_FROM_SERVER_UPDATE:
                if str(w.card_pile_index) in card_dict:
                    w.update_cards(card_dict[str(w.card_pile_index)])


    def on_draw(self):
        """ Render the screen. """
        # Clear the screen
        arcade.start_render()

        # Draw the mats the cards go on to
        self.pile_mat_list.draw()

        # Draw the cards
        for card_pile in self.card_pile_list[::-1]:
            card_pile.draw()

    # def on_key_press(self, symbol: int, modifiers: int):
    #     """ User presses key """
    #     if symbol == arcade.key.R:
    #         # Restart
    #         self.setup()

    def get_pile_index_for_card(self, card):
        """ What pile is this card in? """
        for index, pile in enumerate(self.card_pile_list):
            if card in pile:
                return index

    # def pull_to_top(self, card):
    #     """ Pull card to top of rendering order (last to render, looks on-top) """
    #     # Find the index of the card
    #     index = self.card_list.index(card)
    #     # Loop and pull all the other cards down towards the zero end
    #     for i in range(index, len(self.card_list) - 1):
    #         self.card_list[i] = self.card_list[i + 1]
    #     # Put this card at the right-side/top/size of list
    #     self.card_list[len(self.card_list) - 1] = card

    def on_mouse_press(self, x, y, button, key_modifiers):
        """ Called when the user presses a mouse button. """
        c_mats = arcade.get_sprites_at_point((x, y), self.pile_mat_list)
        if len(c_mats)>0:
            pile_index = c_mats[0].index
            if self.card_pile_list[pile_index].can_remove_card:
                cards = arcade.get_sprites_at_point((x, y), self.card_pile_list[pile_index])
                if len(cards) > 0:
                    primary_card = cards[-1]

                    self.held_cards = [primary_card]
                    self.held_cards_original_position = [self.held_cards[0].position]

        elif button == arcade.MOUSE_BUTTON_RIGHT:
            pass

    def remove_card_from_pile(self, card):
        """ Remove card from whatever pile it was in. """
        for pile in self.piles:
            if card in pile:
                pile.remove(card)
                break

    def move_card_to_new_pile(self, card, pile_index):
        """ Move the card to a new pile """
        self.remove_card_from_pile(card)
        self.piles[pile_index].append(card)



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
            old_pile_index = self.get_pile_index_for_card(self.held_cards[0])
            if new_pile_index == old_pile_index:
                # If so, who cares. We'll just reset our position.
                pass
            elif not self.card_pile_list[new_pile_index].can_add_card:
                pass
            else:
                for i, dropped_card in enumerate(self.held_cards):
                    self.card_pile_list[new_pile_index].add_card(dropped_card)
                    self.card_pile_list[old_pile_index].remove(dropped_card)


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


async def thread_main(window: FYFGame, loop):
    ctx = Context()

    sub_sock: Socket = ctx.socket(zmq.SUB)
    sub_sock.connect('tcp://localhost:25000')
    sub_sock.subscribe('')

    push_sock: Socket = ctx.socket(zmq.PUSH)
    push_sock.connect('tcp://localhost:25001')

    async def pusher():
        """Push the player's INPUT state 60 times per second"""
        while True:
            d = window.card_status
            msg = dict(counter=1, event=d)
            await push_sock.send_json(msg)
            await asyncio.sleep(1 / UPDATE_TICK)


    async def receive_game_state():
        while True:
            #print("*")
            gs_dict = await sub_sock.recv_json()
            #print(gs_dict)
            # logger.debug('.', end='', flush=True)
            window.update_status(gs_dict['cards_in_pile'])

            #window.game_state.from_json(gs_string)
            #ps = window.game_state.player_states[0]
            #t = time.time()
            #window.position_buffer.append(
            #    (Vec2d(ps.x, ps.y), t)
            #)
            #window.t = 0
            #window.player_position_snapshot = copy.copy(window.player.position)

    try:
        await asyncio.gather(pusher(), receive_game_state())
    finally:
        sub_sock.close(1)
        push_sock.close(1)
        ctx.destroy(linger=1)

def thread_worker(window: FYFGame):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(thread_main(window, loop))
    loop.run_forever()

def main(player_index=None):
    """ Main method """
    window = FYFGame()
    window.setup(n_player=6, player_index=player_index)
    thread = threading.Thread(
        target=thread_worker, args=(window,), daemon=True)
    thread.start()
    arcade.run()


if __name__ == "__main__":
    args = parser.parse_args()
    main(args.playerindex)