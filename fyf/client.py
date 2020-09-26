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
import gamestate, clientutil
from arcade import gui
from arcade.gui import UIEvent, TEXT_INPUT,UIInputBox
import copy
from dataclasses import asdict
import uuid

parser = argparse.ArgumentParser(description='Card client')

#parser.add_argument('playerindex', type=int,
#                    help='player index')

#parser.add_argument('-p', dest='player_name', type=str, help='your name to be displayed', default='')
#parser.add_argument('-n', dest='n_player', type=int, help='number of player', default=6)
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
MAT_WIDTH = int(CARD_WIDTH  * MAT_PERCENT_OVERSIZE * 3.2)
HAND_MAT_HEIGHT = int(CARD_HEIGHT*2 + MAT_HEIGHT * VERTICAL_MARGIN_PERCENT)
HAND_MAT_WIDTH = int(CARD_HORIZONTAL_OFFSET * 54 + CARD_WIDTH)

# The Y of the bottom row (2 piles)
HAND_MAT_Y = HAND_MAT_HEIGHT / 2  * CARD_SCALE + MAT_HEIGHT  * CARD_SCALE * VERTICAL_MARGIN_PERCENT
# The X of where to start putting things on the left side
HAND_MAT_X = HAND_MAT_WIDTH / 2  * CARD_SCALE + MAT_WIDTH  * CARD_SCALE * HORIZONTAL_MARGIN_PERCENT

STARTING_X = MAT_WIDTH * HORIZONTAL_MARGIN_PERCENT

TOP_OUTPUT_ROW_Y = (SCREEN_HEIGHT * 10.5) // 12
BOTTOM_OUTPUT_ROW_Y = (SCREEN_HEIGHT * 4.5) // 12
MID_CARD_Y = (SCREEN_HEIGHT * 7.5)//12
TOP_SCORE_ROW_Y = (SCREEN_HEIGHT * 8.8) // 12
BOTTOM_SCORE_ROW_Y = (SCREEN_HEIGHT * 6.2) // 12

PILE_SEPARATION_X =  CARD_WIDTH

HAND_PILE = 0


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




SCORE_RULE_510K = 0
SCORE_RULE_COUNT = 1
def calculate_score(value_list, score_rule):
    if score_rule == SCORE_RULE_510K:
        score_list = [(w % 54) % 13 for w in value_list]
        return score_list.count(3)*5 + score_list.count(8)*10 + score_list.count(11) *10
    elif score_rule == SCORE_RULE_COUNT:
        return len(value_list)







GAME_STATUS_RESET = -1
GAME_STATUS_ONGOING = 0

SORT_BUTTON_WIDTH=100
BUTTON_HEIGHT=20

class CardGame(arcade.Window):

    def __init__(self, *arg, **kargs):
        super().__init__(*arg, **kargs)
        self.game_state = None
        self.event_buffer = []

    def update_game_state(self, gs_dict):
        """ update game state from gs_dict """
        # no GUI change is allowed in this function
        self.game_state = gamestate.GameState(**gs_dict)




class ConnectView(arcade.View):
    """ Screen waiting for people to connect   """
    def __init__(self, player_id=None, player_name=None):
        super().__init__()
        if player_id is None:
            self.player_id = str(uuid.uuid4())
        else:
            self.player_id = player_id
        self.player_name = player_name
        self.ui_manager = gui.UIManager()
        self.ui_input_box=None
        self.label = None

    @property
    def game_state(self):
        return self.window.game_state
    @property
    def event_buffer(self):
        return self.window.event_buffer
    def connect(self, text):
        self.player_name = text
        new_event = gamestate.EventConnect(type='UpdatePlayerInfo',
                                          player_name = self.player_name,
                                          player_id = self.player_id
                                          )
        self.event_buffer.append(new_event)

    def get_game_state(self):
        new_event = gamestate.EventConnect(type='GetGameState')
        self.event_buffer.append(new_event)

    def send_ready(self, text):
        new_event = gamestate.EventConnect(type='PlayerReady',
                                          player_name = self.player_name,
                                          player_id = self.player_id
                                          )
        self.event_buffer.append(new_event)

    def reset_player_and_game(self):
        new_event = gamestate.EventConnect(type='ResetPlayerAndGame')
        self.event_buffer.append(new_event)

    def observe_a_game(self):
        new_event = gamestate.EventConnect(type='Observe',
                                          player_name = self.player_name,
                                          player_id = self.player_id
                                          )
        self.event_buffer.append(new_event)
    def on_update(self, deltatime):
        if self.game_state:
            if self.game_state.status=='Starting New Game':
                if self.player_id in self.game_state.player_index_per_id:
                    print(self.game_state.player_index_per_id)
                    player_index = self.game_state.player_index_per_id[self.player_id]
                    player_name =  self.game_state.player_name_per_id[self.player_id]
                    n_player = self.game_state.n_player
                    self.ui_manager.purge_ui_elements()
                    game_view = GameView(player_id=self.player_id)
                    game_view.setup(n_player=n_player, player_index=player_index)
                    self.window.show_view(game_view)

            elif self.game_state.status == 'In Game':
                if self.player_id in self.game_state.player_index_per_id:
                    player_index = self.game_state.player_index_per_id[self.player_id]
                    player_name =  self.game_state.player_name_per_id[self.player_id]
                    if player_index <=-1: # we are an observer
                        n_player = self.game_state.n_player
                        self.ui_manager.purge_ui_elements()
                        game_view = GameView(player_id=self.player_id)
                        game_view.setup(n_player=n_player, player_index=player_index)
                        self.window.show_view(game_view)

    def setup(self):
        self.ui_input_box = gui.UIInputBox(
            center_x=200,
            center_y=300,
            width=300
        )
        self.ui_manager.add_ui_element(self.ui_input_box )
        connect_button = GameFlatButton(
            lambda : self.connect(self.ui_input_box.text),
            text='Connect',
            center_x=200,
            center_y=250,
            width=200
        )
        self.ui_manager.add_ui_element(connect_button)

        submit_button = GameFlatButton(
            lambda : self.send_ready(self.ui_input_box.text),
            text='READY (Game starts when all players are ready',
            center_x=450,
            center_y=200,
            width=700
        )
        self.ui_manager.add_ui_element(submit_button)
        observe_button = GameFlatButton(
            self.observe_a_game,
            text='OBSERVE (In Game)',
            center_x=450,
            center_y=150,
            width=700
        )
        self.ui_manager.add_ui_element(observe_button)
        clear_button = GameFlatButton(
            self.reset_player_and_game,
            text='Reset Player (and Game if being played)',
            center_x=450,
            center_y=100,
            width=700
        )
        self.ui_manager.add_ui_element(clear_button)
        self.get_game_state()
    def on_show_view(self):
        """ Called once when view is activated. """
        self.setup()
        arcade.set_background_color(arcade.color.AMAZON)
    def on_draw(self):
        arcade.start_render()
        if self.game_state:
            starting_y = SCREEN_HEIGHT-150
            arcade.draw_text(f'Game Status: {self.game_state.status}', 200, starting_y, arcade.color.GOLD, 14)
            starting_y -= 25
            arcade.draw_text('players name | index', 200, starting_y, arcade.color.GOLD, 14)
            for player_id, player_name in self.game_state.player_name_per_id.items():
                starting_y -= 25
                arcade.draw_text(f'{player_name} | {str(self.game_state.player_index_per_id[player_id]) if player_id in self.game_state.player_index_per_id else "not ready"}',
                                 200, starting_y, arcade.color.GOLD, 14)


class GameView(arcade.View):
    """ Main Game View class. """

    def __init__(self, player_id=None):
        super().__init__()
        self.ui_manager = gui.UIManager()
        arcade.set_background_color(arcade.color.AMAZON)
        if player_id is None:
            self.player_id = str(uuid.uuid4())
        else:
            self.player_id = player_id
        #self.player_name = player_name
        #self.player_name_display_list = None
        self.n_player = None
        self.self_player_index = None
        self.n_decks = None
        self.n_residual_card = None
        self.n_pile= None

        # List of cards we are dragging with the mouse
        self.held_cards = None
        # Original location of cards we are dragging with the mouse in case they have to go back.
        self.held_cards_original_position = None
        # active cards
        self.active_cards = None
        # card that was pressed on
        self.card_on_press = None

        # Sprite list with all the mats tha cards lay on.
        self.pile_mat_list = None
        #self.pile_text_list = None
        self.card_pile_list = None

    @property
    def game_state(self):
        return self.window.game_state
    @game_state.setter
    def game_state(self, x):
        self.window.game_state = x

    @property
    def event_buffer(self):
        return self.window.event_buffer

    def clear_all_piles(self):
        """ clear all piles """
        for card_pile in self.card_pile_list:
            card_pile.clear()

        self.held_cards = []
        self.held_cards_original_position=[]
        self.active_cards = []
        self.card_on_press = None

    def setup(self, n_player = None, player_index=0):
        """ Set up the game here. Call this function to restart the game. """
        self.ui_manager.purge_ui_elements()
        self.n_player = n_player
        self.n_pile = self.n_player *4+2
        self.self_player_index = player_index

        # List of cards we are dragging with the mouse
        self.held_cards = []
        self.held_cards_original_position=[]
        self.active_cards = []
        self.card_pile_list = []
        #self.held_cards_original_pile = None

        # ---  Create the mats the cards go on.

        # Sprite list with all the mats tha cards lay on.
        self.pile_mat_list: arcade.SpriteList = arcade.SpriteList(is_static=True)
        #self.pile_text_list = []
        #self.player_name_display_list = []

        # own pile

        #self.hand_pile_index = len(self.card_pile_list)
        if self.self_player_index >=0:
            hand_pile_mat = Mat(len(self.card_pile_list), int(HAND_MAT_WIDTH*CARD_SCALE), int(HAND_MAT_HEIGHT*CARD_SCALE),
                                       arcade.csscolor.LIGHT_SLATE_GREY)
            self.card_pile_list.append(CardPile(
                card_pile_id=self.self_player_index,
                mat_center=(HAND_MAT_X, HAND_MAT_Y),
                mat_size = (HAND_MAT_WIDTH*CARD_SCALE, HAND_MAT_HEIGHT*CARD_SCALE),
                mat_boundary=(int(CARD_WIDTH*CARD_SCALE/2), int(CARD_HEIGHT*CARD_SCALE/2)),
                card_scale = CARD_SCALE,
                card_offset = (int(CARD_WIDTH*CARD_SCALE*CARD_OFFSET_PCT),int(CARD_HEIGHT*CARD_SCALE)),
                sorting_rule=SORT_BY_SUIT_THEN_NUMBER,
                auto_sort_setting=AUTO_SORT_ALL_CARDS,
                enable_sort_button=True,
                enable_clear_button=False,
                enable_recover_last_removed_cards=False,
                enable_title=True,
                title='Your Private Pile',
                other_properties={'Clearable': False, 'score_to_display': SCORE_RULE_COUNT}
            ))
            hand_pile_mat.position = HAND_MAT_X, HAND_MAT_Y
            self.pile_mat_list.append(hand_pile_mat)

            temp_pile_mat = Mat(len(self.card_pile_list), int(MAT_WIDTH*NORMAL_MAT_SCALE), int(HAND_MAT_HEIGHT*CARD_SCALE),
                                       arcade.csscolor.LIGHT_SLATE_GREY)
            self.card_pile_list.append(CardPile(
                card_pile_id=self.self_player_index + self.n_player,
                mat_center=(int(HAND_MAT_X + HAND_MAT_WIDTH*CARD_SCALE/2 + MAT_WIDTH*NORMAL_MAT_SCALE*0.6), HAND_MAT_Y),
                mat_size =  (int(MAT_WIDTH*NORMAL_MAT_SCALE), HAND_MAT_HEIGHT*CARD_SCALE),
                mat_boundary = (int(CARD_WIDTH*NORMAL_MAT_SCALE/2), int(CARD_HEIGHT*CARD_SCALE/2)),
                card_scale=CARD_SCALE,
                card_offset=(int(CARD_WIDTH*CARD_SCALE*CARD_OFFSET_PCT),int(CARD_HEIGHT*CARD_SCALE)),
                sorting_rule=SORT_BY_SUIT_THEN_NUMBER,
                auto_sort_setting=NO_AUTO_SORT,
                enable_sort_button=True,
                enable_clear_button=False,
                enable_recover_last_removed_cards=False,
                enable_title=True,
                title='Private Pile 2',
                other_properties={'Clearable': False, 'score_to_display': SCORE_RULE_COUNT}
            ))
            temp_pile_mat.position = int(HAND_MAT_X + HAND_MAT_WIDTH*CARD_SCALE/2 + MAT_WIDTH*NORMAL_MAT_SCALE*0.6), HAND_MAT_Y
            self.pile_mat_list.append(temp_pile_mat)

        # main output piles for each player
        starting_index_output_pile = 2* self.n_player
        for player_index in range(self.n_player):
            pile_ls_index = len(self.card_pile_list)
            pile_position = calculate_main_pile_positions(player_index, self.n_player, self.self_player_index)
            pile = Mat(pile_ls_index, int(MAT_WIDTH*NORMAL_MAT_SCALE), int(MAT_HEIGHT*NORMAL_MAT_SCALE),
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
                    sorting_rule= SORT_BY_SUIT_THEN_NUMBER,
                    auto_sort_setting = AUTO_SORT_NEW_CARD_ONLY,
                    enable_sort_button=True,
                    enable_clear_button=True,
                    clear_action=lambda: self.clear_a_pile(pile_index=pile_ls_index),
                    enable_recover_last_removed_cards=True,
                    recover_action=lambda: self.recover_card_to_a_pile(pile_index=pile_ls_index),
                    enable_title=True,
                    other_properties = {'Clearable':True, 'player_index_to_display': player_index}
                )
            )

        # score piles for each player
        starting_index_score_pile = self.n_player*3
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
                    sorting_rule=SORT_BY_NUMBER_THEN_SUIT,
                    auto_sort_setting=NO_AUTO_SORT,
                    enable_sort_button=True,
                    enable_clear_button=False,
                    enable_recover_last_removed_cards=False,
                    enable_title=True,
                    title='Cards won',
                    other_properties={'Clearable':False, 'score_to_display':SCORE_RULE_510K}
                )
            )

        pile = Mat(len(self.card_pile_list), int(MAT_WIDTH*0.5), int(MAT_HEIGHT*0.3), arcade.csscolor.DARK_SLATE_BLUE)
        pile.position = int(MAT_WIDTH * 0.35), MID_CARD_Y
        self.pile_mat_list.append(pile)
        self.card_pile_list.append(
            CardPile(
                card_pile_id=self.n_player*4,
                mat_center=pile.position,
                mat_size=(int(MAT_WIDTH * 0.5), int(MAT_HEIGHT * SCORE_MAT_SCALE)),
                mat_boundary=(int(CARD_WIDTH * SCORE_MAT_SCALE/2), int(CARD_HEIGHT * SCORE_MAT_SCALE/2)),
                card_scale =SCORE_MAT_SCALE,
                card_offset=(int(CARD_WIDTH * SCORE_MAT_SCALE * CARD_OFFSET_PCT),
                             int(CARD_HEIGHT * SCORE_MAT_SCALE * CARD_OFFSET_PCT)),
                sorting_rule=DO_NOT_SORT,
                auto_sort_setting=NO_AUTO_SORT,
                enable_sort_button=False,
                enable_clear_button=False,
                enable_recover_last_removed_cards=False,
                enable_title=True,
                title='Hidden Pile',
                other_properties={'Clearable': False, 'score_to_display': SCORE_RULE_COUNT}
            )
        )

        # PUBLIC POLE
        pile = Mat(len(self.card_pile_list),
                     MAT_WIDTH, int(MAT_HEIGHT*0.3), arcade.csscolor.DARK_SLATE_GRAY)
        pile.position = int(MAT_WIDTH * 1.2), MID_CARD_Y
        self.pile_mat_list.append(pile)
        self.card_pile_list.append(
            CardPile(
                card_pile_id=self.n_player*4+1,
                mat_center=pile.position,
                mat_size=(int(MAT_WIDTH), int(MAT_HEIGHT * SCORE_MAT_SCALE)),
                mat_boundary=(int(CARD_WIDTH * SCORE_MAT_SCALE/2), int(CARD_HEIGHT * SCORE_MAT_SCALE/2)),
                card_scale =SCORE_MAT_SCALE,
                card_offset=(int(CARD_WIDTH * SCORE_MAT_SCALE * CARD_OFFSET_PCT),
                             int(CARD_HEIGHT * SCORE_MAT_SCALE * CARD_OFFSET_PCT)),
                sorting_rule=SORT_BY_NUMBER_THEN_SUIT,
                auto_sort_setting=NO_AUTO_SORT,
                enable_sort_button=True,
                enable_clear_button=False,
                enable_recover_last_removed_cards=False,
                enable_title=True,
                title='Aggregate Cards Won',
                other_properties={'Clearable': False, 'score_to_display':SCORE_RULE_510K}
            )
        )

        for card_pile in self.card_pile_list:
            new_ui_elments = card_pile.get_ui_elements()
            for element in new_ui_elments:
                self.ui_manager.add_ui_element(element)

        new_game_button = GameFlatButton(
                        self.initiate_game_restart,
                        font_size=12,
                        bg_color=arcade.color.DARK_RED,
                        text='New Game Round',
                        center_x=int(MAT_WIDTH * 2),
                        center_y=MID_CARD_Y+20,
                        width=200,
                        height=30)
        self.ui_manager.add_ui_element(new_game_button)

        quit_game_button = GameFlatButton(
                        self.reset_player_and_game,
                        font_size=12,
                        bg_color=arcade.color.DARK_RED,
                        text='Leave and Reset Game',
                        center_x=int(MAT_WIDTH * 2),
                        center_y= MID_CARD_Y-20,
                        width=200,
                        height=30)
        self.ui_manager.add_ui_element(quit_game_button)


    def on_update(self, delta_time):
        """ on update, which is called in the event loop."""
        if self.game_state:
            if self.game_state.status=='Wait for Player to Join':
                self.ui_manager.purge_ui_elements()
                connect_view = ConnectView(player_id=self.player_id)
                connect_view.setup()
                self.window.show_view(connect_view)
                return
            elif self.game_state.status=='New Game':

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
                            held_cards_value.remove(held_cards_value[index])

                        if card_value in active_cards_value:
                            index = active_cards_value.index(card_value)
                            self.active_cards[index].active = False
                            self.active_cards.remove(self.active_cards[index])
                            active_cards_value.remove(active_cards_value[index])

                if w.enable_title:
                    if 'player_index_to_display' in w.other_properties:
                        if w.other_properties['player_index_to_display'] in self.game_state.player_name:
                            if w.title!=self.game_state.player_name[w.other_properties['player_index_to_display']]:
                                w.title = self.game_state.player_name[w.other_properties['player_index_to_display']]
                    elif 'score_to_display' in w.other_properties:
                        scores = calculate_score(w.to_valuelist(), w.other_properties['score_to_display'])
                        if w.title!=str(scores):
                            if w.title.isdigit() or scores>0:
                                w.title=str(scores)


    def on_draw(self):
        """ Render the screen. """
        arcade.start_render()

        # Draw the mats the cards go on to
        self.pile_mat_list.draw()

        # draw text
        #for text, x, y, color, size in self.pile_text_list:
        #    arcade.draw_text(text, x, y, color, size)
        #if self.game_state:
        #    for player_index, x, y, color, size in self.player_name_display_list:
        #        if player_index in self.game_state.player_name:
        #            arcade.draw_text(self.game_state.player_name[player_index], x, y, color, size)
        # Draw the cards
        for card_pile in self.card_pile_list[::-1]:
            card_pile.draw()

    def on_key_press(self, symbol: int, modifiers: int):
         """ User presses key """
         pass
         # if symbol == arcade.key.R:
         #     if modifiers & arcade.key.MOD_CTRL:
         #        self.initiate_game_restart()
         # if symbol == arcade.key.Q:
         #     if modifiers & arcade.key.MOD_CTRL:
         #        self.reset_player_and_game()
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
                self.card_pile_list[pile_index].resort_cards()
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
        new_pile, distance = clientutil.get_minimum_distance_mat(self.card_on_press, self.pile_mat_list)
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

    def move_cards(self, cards, new_pile_index):
        old_pile_index = self.get_pile_index_for_card(cards[0])

        for i, dropped_card in enumerate(cards):
            self.card_pile_list[new_pile_index].add_card(dropped_card)
            self.card_pile_list[old_pile_index].remove_card(dropped_card)
        new_event = gamestate.Event(type='Move',
                                   player_index=self.self_player_index,
                                   src_pile = self.card_pile_list[old_pile_index].card_pile_id,
                                   dst_pile = self.card_pile_list[new_pile_index].card_pile_id,
                                   cards = [card.value for card in cards]
                                   )
        self.event_buffer.append(new_event)
        self.game_state.update_from_event(new_event)

    def flip_card(self, card):
        new_face=card.face_flipped()

        new_event = gamestate.Event(type='Flip',
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
                new_event = gamestate.Event(type='Remove',
                                           player_index=self.self_player_index,
                                           src_pile = self.card_pile_list[pile_index].card_pile_id,
                                           cards = self.card_pile_list[pile_index].to_valuelist()
                                           )
                self.card_pile_list[pile_index].clear()  # remove_card(dropped_card)
                self.event_buffer.append(new_event)
                self.game_state.update_from_event(new_event)

    def recover_card_to_a_pile(self, pile_index):
        card_values, face_dict = self.card_pile_list[pile_index].recover_removed_card()

        new_event = gamestate.Event(type='Add',
                                   player_index=self.self_player_index,
                                   dst_pile = self.card_pile_list[pile_index].card_pile_id,
                                   cards = card_values,
                                   cards_status = face_dict
                                   )
        self.event_buffer.append(new_event)
        self.game_state.update_from_event(new_event)



    def reset_player_and_game(self):
        #print('reset')
        new_event = gamestate.EventConnect(type='ResetPlayerAndGame')
        self.event_buffer.append(new_event)


    def initiate_game_restart(self):
        n_decks= self.n_player
        n_residual_card =  self.n_player*2
        n_card_per_player = (n_decks * 54 - n_residual_card) // self.n_player
        n_residual_card = n_decks * 54 - n_card_per_player*self.n_player
        n_card_per_pile = {w: n_card_per_player for w in range(self.n_player)}
        n_card_per_pile[self.n_player*4]=n_residual_card
        new_event = gamestate.Event(type='StartNewGame',
                                   player_index=self.self_player_index,
                                   n_player = self.n_player,
                                   n_pile = self.n_pile,
                                   n_card_per_pile = n_card_per_pile,
                                   face_down_pile = [self.n_player*4],
                                   )
        self.event_buffer.append(new_event)

def thread_pusher(window: CardGame, server_ip:str):
    ctx = Context()
    push_sock: Socket = ctx.socket(zmq.PUSH)
    push_sock.connect(f'tcp://{server_ip}:25001')
    try:
        while True:
            if window.event_buffer:
                d = window.event_buffer.pop()
                msg = dict(counter=1, event=asdict(d))
                print(msg)
                push_sock.send_json(msg)
            time.sleep(1 / UPDATE_TICK)

    finally:
        push_sock.close(1)
        ctx.destroy(linger=1)

def thread_receiver(window: CardGame, server_ip: str):
    ctx = Context()
    sub_sock: Socket = ctx.socket(zmq.SUB)
    sub_sock.connect(f'tcp://{server_ip}:25000')
    sub_sock.subscribe('')
    try:
        while True:
            gs_dict = sub_sock.recv_json(object_hook=gamestate.json_obj_hook)
            window.update_game_state(gs_dict)
            time.sleep(1 / UPDATE_TICK)

    finally:
        sub_sock.close(1)
        ctx.destroy(linger=1)

def main(args):
    """ Main method """

    window = CardGame(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE, resizable=True)
    connect_view = ConnectView()
    connect_view.setup()
    #game_view = GameView(args.player_name if args.player_name!='' else f'PLAYER {args.playerindex}')
    #game_view.setup(n_player=args.n_player, player_index=args.playerindex)
    window.show_view(connect_view)
    thread1 = threading.Thread(
        target=thread_pusher, args=(window, args.server_ip,), daemon=True)
    thread2 = threading.Thread(
        target=thread_receiver, args=(window, args.server_ip,), daemon=True)
    thread1.start()
    thread2.start()
    arcade.run()


if __name__ == "__main__":
    args = parser.parse_args()
    main(args)