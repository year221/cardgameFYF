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
import utils
import gamestate, clientelements
from cardpile import CardPile
from clientelements import Card, GameFlatButton,ResizableGameFlatButton,GameTextLabel
from utils import *
from arcade import gui
import cardpile
from cardpile import calculate_circular_pile_set_positions, Title_Type

from dataclasses import asdict
import uuid
import yaml

parser = argparse.ArgumentParser(description='Card client')

parser.add_argument('-u', dest='server_ip', type=str, help='server ip', default='162.243.211.250')
#parser.add_argument('-g', dest='game_config', type=str, help='game configuration file', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "../games/zhaopengyou.yaml"))


with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../games/zhaopengyou.yaml")) as file:
    # The FullLoader parameter handles the conversion from YAML
    # scalar values to Python the dictionary format
    DEFAULT_GAME_CONFIG = yaml.load(file, Loader=yaml.SafeLoader) # , Loader=yaml.SafeLoader)

# Network
UPDATE_TICK = 30

class CardGame(arcade.Window):

    def __init__(self, *arg, **kargs):
        super().__init__(*arg, **kargs)
        self.game_state = None
        self.event_buffer = []

    def update_game_state(self, gs_dict):
        """ update game state from gs_dict """
        # no GUI change is allowed in this function
        self.game_state = gamestate.GameState(**gs_dict)

    def on_resize(self, width: float, height: float):
        """
        Override this function to add custom code to be called any time the window
        is resized. The only responsibility here is to update the viewport.

        :param float width: New width
        :param float height: New height
        """
        super().on_resize(width, height)


        if self.current_view is not None:
            if hasattr(self.current_view, 'on_resize'):
                on_resize_op = getattr(self.current_view, "on_resize", None)
                if callable(on_resize_op):
                    self.current_view.on_resize(width, height)



class LoadingView(arcade.View):
    """ Screen loading the GUI   """
    def __init__(self, player_id=None):
        super().__init__()
        if player_id is None:
            self.player_id = str(uuid.uuid4())
        else:
            self.player_id = player_id

    @property
    def game_state(self):
        return self.window.game_state

    def on_draw(self):
        arcade.start_render()
        arcade.draw_text('Loading. PLease Wait...', 10, 10, arcade.color.GOLD, 30)

    def on_update(self, deltatime):
        if self.game_state:
            player_index = self.game_state.player_index_per_id[self.player_id]
            n_player = self.game_state.n_player
            game_view = GameView(player_id=self.player_id)
            game_view.setup(game_config=DEFAULT_GAME_CONFIG, n_player=n_player, player_index=player_index)
            self.window.show_view(game_view)

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

    def on_resize(self, width: float, height: float):
        pass
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
                    player_index = self.game_state.player_index_per_id[self.player_id]
                    self.ui_manager.purge_ui_elements()
                    loading_view = LoadingView(player_id = self.player_id)
                    self.window.show_view(loading_view)
                    # #print(self.game_state.player_index_per_id)
                    # player_index = self.game_state.player_index_per_id[self.player_id]
                    # player_name =  self.game_state.player_name_per_id[self.player_id]
                    # n_player = self.game_state.n_player
                    # self.ui_manager.purge_ui_elements()
                    # game_view = GameView(player_id=self.player_id)
                    # game_view.setup(game_config =DEFAULT_GAME_CONFIG,  n_player=n_player, player_index=player_index)
                    # self.window.show_view(game_view)

            elif self.game_state.status == 'In Game':
                if self.player_id in self.game_state.player_index_per_id:
                    #player_index = self.game_state.player_index_per_id[self.player_id]
                    #player_name =  self.game_state.player_name_per_id[self.player_id]
                    player_index = self.game_state.player_index_per_id[self.player_id]
                    if player_index <= -1:
                        self.ui_manager.purge_ui_elements()
                        loading_view = LoadingView(player_id = self.player_id)
                        self.window.show_view(loading_view)
                    # if player_index <=-1: # we are an observer
                    #     n_player = self.game_state.n_player
                    #     self.ui_manager.purge_ui_elements()
                    #     game_view = GameView(player_id=self.player_id)
                    #     game_view.setup(n_player=n_player, player_index=player_index)
                    #     self.window.show_view(game_view)

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
            starting_y = 650
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
        self.n_player = None
        self.self_player_index = None

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
        self.card_pile_list = None
        self.resize_list = []
        self.game_config = None
        self._size_scaler = 1

    @property
    def game_state(self):
        return self.window.game_state
    @game_state.setter
    def game_state(self, x):
        self.window.game_state = x

    @property
    def event_buffer(self):
        return self.window.event_buffer

    def on_resize(self, width, height):

        # calculate new scaling factor
        if self.game_config is not None:
            new_size_scaler = self.calculate_size_scaler(width, height)
            if new_size_scaler is not None:
                if new_size_scaler !=self._size_scaler:
                    self._size_scaler = new_size_scaler
                    for resizable_obj in self.resize_list:
                        resizable_obj.size_scaler = self._size_scaler

    def calculate_size_scaler(self, width, height):
        """ calculate size scaler

        :param width:
        :param height:
        :return:
        """
        scaler_x = width/self.game_config['default_screen_size'][0]
        scaler_y = height/self.game_config['default_screen_size'][1]
        if self.game_config['scale_by']=='HEIGHT':
            new_size_scaler=scaler_y
        elif self.game_config['scale_by']=='WIDTH':
            new_size_scaler = scaler_x
        elif self.game_config['scale_by']=='BOTH':
            new_size_scaler = min(scaler_x, scaler_y)
        else:
            new_size_scaler= None
        return new_size_scaler
        #print(f'scaler: {self._size_scaler}')

    def clear_all_piles(self):
        """ clear all piles """
        for card_pile in self.card_pile_list:
            card_pile.clear(cache_cleared_values=False)
        self.held_cards = []
        self.held_cards_original_position=[]
        self.active_cards = []
        self.card_on_press = None

    @property
    def n_pile(self):
        return max([w.card_pile_id for w in self.card_pile_list])+1

    def setup(self, game_config, n_player = None, player_index=0):
        """ Set up the game here. Call this function to restart the game. """

        self.ui_manager.purge_ui_elements()
        self.n_player = n_player
        self.self_player_index = player_index


        # List of cards we are dragging with the mouse
        self.game_config = game_config
        self.held_cards = []
        self.held_cards_original_position=[]
        self.active_cards = []
        self.card_pile_list = []
        self.resize_list = []
        self.card_on_press = None
        # ---  Create the mats the cards go on.
        # calculate propriate size
        width, height = self.window.get_size()
        new_size_scaler = self.calculate_size_scaler(width, height)
        if new_size_scaler is not None:
            self._size_scaler = new_size_scaler


        # Sprite list with all the mats tha cards lay on.
        self.pile_mat_list: arcade.SpriteList = arcade.SpriteList()

        # calculate pile id
        starting_pile_id = 0
        starting_pile_id = 0
        pile_tag_to_pile_id = {}
        for pile_set in game_config['cardpiles']:


            if pile_set['piletype'] == 'PlayerPile':
                pile_tag_to_pile_id.update({pile_set['pile_set_tag']: list(range(starting_pile_id, starting_pile_id+ self.n_player))})
                starting_pile_id += self.n_player
            elif pile_set['piletype'] == 'PublicPile':
                pile_tag_to_pile_id.update(
                    {pile_set['pile_set_tag']: [starting_pile_id]})
                starting_pile_id+=1
            elif pile_set['piletype'] == 'CardDeck':
                pile_tag_to_pile_id.update(
                    {pile_set['pile_set_tag']: [starting_pile_id]})
                starting_pile_id+=1

        # adding piles based on game_config
        starting_pile_id = 0
        for pile_set in game_config['cardpiles']:
            if pile_set['piletype'] == 'PlayerPile':
                if pile_set['display'] == 'SELF':
                    if self.self_player_index>=0:
                        card_pile = cardpile.CardPile(
                            card_pile_id=starting_pile_id+self.self_player_index,
                            mat_center=tuple(pile_set['mat_center']),
                            mat_size=tuple(pile_set['mat_size']),
                            mat_boundary=tuple(pile_set['mat_boundary']),
                            card_size=tuple(pile_set['card_size']),
                            card_offset=tuple(pile_set['card_offset']),
                            mat_color=tuple(pile_set['mat_color']),
                            button_height=pile_set['button_height'] if 'button_height' in pile_set else None,
                            size_scaler=self._size_scaler,
                            sorting_rule=Sorting_Rule[pile_set['sorting_rule']],
                            auto_sort_setting=Auto_Sort[pile_set['auto_sort_setting']],
                            enable_sort_button=pile_set['enable_sort_button'],
                            enable_clear_button=pile_set['enable_clear_button'],
                            enable_recover_last_removed_cards=pile_set['enable_recover_last_removed_cards'],
                            enable_flip_all=pile_set['enable_flip_all'],
                            title_property=pile_set['title'],
                            update_event_handle=self.add_event,
                            other_properties={'player_index': player_index}
                        )
                        self.card_pile_list.append(card_pile)
                        self.pile_mat_list.append(card_pile.mat)
                        self.resize_list.append(card_pile)
                elif pile_set['display'] == 'ALL_PLAYER_CIRCLE':
                    for player_index in range(self.n_player):
                        pile_position = calculate_circular_pile_set_positions(
                            starting_mat_center=tuple(pile_set['starting_mat_center']),
                            pile_offset=tuple(pile_set['pile_offset']),
                            piles_per_side=tuple(pile_set['piles_per_side']),
                            player_index=player_index,
                            n_player=self.n_player,
                            pile_position_offset=pile_set['pile_position_offset'],
                            starting_index_type = Pile_Position_Offset[pile_set['pile_position_offset_type']],
                            self_player_index=self.self_player_index,
                            counterclockwise=pile_set['direction'] == 'COUNTERCLOCKWISE'
                        )
                        card_pile = cardpile.CardPile(
                            card_pile_id=player_index + starting_pile_id,
                            mat_center=(pile_position[0], pile_position[1]),
                            mat_size=tuple(pile_set['mat_size']),
                            mat_boundary=tuple(pile_set['mat_boundary']),
                            card_size=tuple(pile_set['card_size']),
                            card_offset=tuple(pile_set['card_offset']),
                            mat_color=tuple(pile_set['self_mat_color']) if (player_index==self.self_player_index and 'self_mat_color' in pile_set) else tuple(pile_set['mat_color']),
                            button_height=pile_set['button_height'] if 'button_height' in pile_set else None,
                            size_scaler=self._size_scaler,
                            sorting_rule=Sorting_Rule[pile_set['sorting_rule']],
                            auto_sort_setting=Auto_Sort[pile_set['auto_sort_setting']],
                            enable_sort_button=pile_set['enable_sort_button'],
                            enable_clear_button=pile_set['enable_clear_button'],
                            enable_recover_last_removed_cards=pile_set['enable_recover_last_removed_cards'],
                            enable_flip_all=pile_set['enable_flip_all'],
                            #enable_title=pile_set['enable_title'],
                            title_property=pile_set['title'],
                            #title=pile_set['default_title'],
                            update_event_handle=self.add_event,
                            other_properties={'player_index': player_index}
                        )
                        self.card_pile_list.append(card_pile)
                        self.pile_mat_list.append(card_pile.mat)
                        self.resize_list.append(card_pile)
                # add starting pile id
                starting_pile_id += self.n_player

            elif pile_set['piletype'] == 'PublicPile':
                #if pile_set['display'] == 'ALL':
                card_pile = cardpile.CardPile(
                    card_pile_id=starting_pile_id,
                    mat_center=tuple(pile_set['mat_center']),
                    mat_size=tuple(pile_set['mat_size']),
                    mat_boundary=tuple(pile_set['mat_boundary']),
                    card_size=tuple(pile_set['card_size']),
                    card_offset=tuple(pile_set['card_offset']),
                    mat_color=tuple(pile_set['mat_color']),
                    button_height=pile_set['button_height'] if 'button_height' in pile_set else None,
                    size_scaler=self._size_scaler,
                    sorting_rule=Sorting_Rule[pile_set['sorting_rule']],
                    auto_sort_setting=Auto_Sort[pile_set['auto_sort_setting']],
                    enable_sort_button=pile_set['enable_sort_button'],
                    enable_clear_button=pile_set['enable_clear_button'],
                    enable_recover_last_removed_cards=pile_set['enable_recover_last_removed_cards'],
                    enable_flip_all=pile_set['enable_flip_all'],
                    title_property=pile_set['title'],
                    update_event_handle=self.add_event
                )
                self.card_pile_list.append(card_pile)
                self.pile_mat_list.append(card_pile.mat)
                self.resize_list.append(card_pile)
                starting_pile_id+=1
            elif pile_set['piletype'] == 'CardDeck':
                #if pile_set['display'] == 'ALL':
                card_pile = cardpile.CardDeck(
                    card_pile_id=starting_pile_id,
                    mat_center=tuple(pile_set['mat_center']),
                    mat_size=tuple(pile_set['mat_size']),
                    mat_boundary=tuple(pile_set['mat_boundary']),
                    card_size=tuple(pile_set['card_size']),
                    card_offset=tuple(pile_set['card_offset']),
                    mat_color=tuple(pile_set['mat_color']),
                    button_height=pile_set['button_height'] if 'button_height' in pile_set else None,
                    vertical_button_width=pile_set['vertical_button_width'],
                    vertical_button_height=pile_set['vertical_button_height'],
                    size_scaler=self._size_scaler,
                    per_deck_cards=pile_set['per_deck_cards'],
                    face_down=pile_set['face_down'],
                    initial_num_of_decks=pile_set['initial_num_of_decks'],
                    enable_generation=pile_set['enable_generation'],
                    num_of_decks_per_generation=pile_set['num_of_decks_per_generation'],
                    enable_auto_distribution=pile_set['enable_auto_distribution'],
                    destination_piles_and_cards=pile_set['destination_piles_and_cards'],
                    title_property=pile_set['title'],
                    update_event_handle=self.add_event,
                    other_properties={'player_index': player_index,
                                      'constants': {'CONST_NPLAYER': self.n_player},
                                      'pile_tag_to_pile_id': pile_tag_to_pile_id
                                      },
                )
                self.card_pile_list.append(card_pile)
                self.pile_mat_list.append(card_pile.mat)
                self.resize_list.append(card_pile)
                starting_pile_id+=1
        # add ui element
        for card_pile in self.card_pile_list:
            new_ui_elments = card_pile.get_ui_elements()
            for element in new_ui_elments:
                self.ui_manager.add_ui_element(element)

        for game_button in game_config['gamebuttons']:
            new_game_button = ResizableGameFlatButton(
                click_event=self.initiate_game_restart if game_button['action']=='initiate_game_restart' else (
                    self.reset_player_and_game if game_button['action']=='reset_player_and_game' else None),
                width = game_button['size'][0],
                height=game_button['size'][1],
                center_x=game_button['center'][0],
                center_y=game_button['center'][1],
                size_scaler=self._size_scaler,
                font_size=game_button['font_size'],
                bg_color=tuple(game_button['bg_color']),
                text=game_button['text']
                )
            self.ui_manager.add_ui_element(new_game_button)
            self.resize_list.append(new_game_button)

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

                self.game_state.status='In Game'
                self.clear_all_piles()
            held_cards_value = [w.value for w in self.held_cards]
            active_cards_value = [w.value for w in self.active_cards]
            # update piles
            for w in self.card_pile_list:
                if w.card_pile_id in self.game_state.cards_in_pile:
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

                if w.title_type == Title_Type.PLAYER_NAME:
                    if 'player_index' in w.other_properties:
                        if w.other_properties['player_index'] in self.game_state.player_name:
                            if w.title!=self.game_state.player_name[w.other_properties['player_index']]:
                                w.title = self.game_state.player_name[w.other_properties['player_index']]
                elif w.title_type == Title_Type.SCORE:
                    if 'score_type' in w._title_property:
                        scores = utils.calculate_score(w.to_valuelist(), utils.Score_Rule[w._title_property['score_type']])
                        if w.title != str(scores):
                            if w.title.isdigit() or scores>0:
                                w.title=str(scores)

    def on_draw(self):
        """ Render the screen. """
        arcade.start_render()

        # Draw the mats the cards go on to
        self.pile_mat_list.draw()
        for card_pile in self.card_pile_list[::-1]:
            card_pile.draw()

    def get_pile_for_card(self, card):
        for index, pile in enumerate(self.card_pile_list):
            if card in pile:
                return pile

    def on_mouse_press(self, x, y, button, key_modifiers):
        """ Called when the user presses a mouse button. """
        self.card_on_press = None
        c_mats = arcade.get_sprites_at_point((x, y), self.pile_mat_list)
        if len(c_mats)>0:
            #pile_index = c_mats[0].pile_position_in_card_pile_list
            c_card_pile =  c_mats[0].cardpile

            if button == arcade.MOUSE_BUTTON_RIGHT and (key_modifiers & arcade.key.MOD_ALT):
                # with control, sort current piles
                c_card_pile.resort_cards()
                #self.card_pile_list[pile_index].resort_cards()
            elif button == arcade.MOUSE_BUTTON_RIGHT and (key_modifiers & arcade.key.MOD_CTRL):
                self.clear_a_pile(c_card_pile)
            else:
                cards = arcade.get_sprites_at_point((x, y), c_card_pile)
                if len(cards) > 0:

                    primary_card = cards[-1]
                    if button == arcade.MOUSE_BUTTON_LEFT:
                        self.card_on_press = primary_card

                        if not primary_card.active:

                            if len(self.active_cards)>=1:
                                # check if the pile being clicked on is the same as the active cards
                                #current_pile_index = self.get_pile_index_for_card(self.card_on_press)
                                current_pile = self.get_pile_for_card(self.card_on_press)
                                #active_card_pile = self.get_pile_index_for_card(self.active_cards[0])
                                active_card_pile = self.get_pile_for_card(self.active_cards[0])

                                if current_pile != active_card_pile:
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
        mat_of_new_pile, distance = clientelements.get_minimum_distance_mat(self.card_on_press, self.pile_mat_list)
        reset_position = True

        # See if we are in contact with the closest pile
        if arcade.check_for_collision(self.card_on_press, mat_of_new_pile):

            # What pile is it?
            new_pile = mat_of_new_pile.cardpile#self.pile_mat_list.index(pile)

            #  Is it the same pile we came from?
            old_pile = self.get_pile_for_card(self.card_on_press)
            if new_pile == old_pile:
                cards = arcade.get_sprites_at_point((x, y), new_pile)
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
                self.move_cards(self.held_cards, new_pile)
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

    def move_cards(self, cards, new_pile):
        old_pile = self.get_pile_for_card(cards[0])

        for i, dropped_card in enumerate(cards):
            new_pile.add_card(dropped_card)
            old_pile.remove_card(dropped_card)
        new_event = gamestate.Event(
            type='Move',
            player_index=self.self_player_index,
            src_pile = old_pile.card_pile_id,
            dst_pile = new_pile.card_pile_id,
            cards = [card.value for card in cards]
        )
        self.event_buffer.append(new_event)
        self.game_state.update_from_event(new_event)

    def flip_card(self, card):
        new_face=card.face_flipped()

        new_event = gamestate.Event(
            type='Flip',
            player_index=self.self_player_index,
            cards = [card.value],
            cards_status = {card.value:new_face}
        )

        self.event_buffer.append(new_event)
        self.game_state.update_from_event(new_event)
        card.face= new_face

    def add_event(self, new_event, local_fast_update=True):
        self.event_buffer.append(new_event)
        if local_fast_update:
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
        n_card_per_pile = {w+1: n_card_per_player for w in range(self.n_player)}
        n_card_per_pile[0]=n_residual_card
        new_event = gamestate.Event(type='StartNewGame',
                                   #player_index=self.self_player_index,
                                   n_player = self.n_player,
                                   n_pile = self.n_pile,
                                   n_card_per_pile = n_card_per_pile,
                                   face_down_pile = [0],
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

    window = CardGame(DEFAULT_GAME_CONFIG['default_screen_size'][0], DEFAULT_GAME_CONFIG['default_screen_size'][1], DEFAULT_GAME_CONFIG['name'], resizable=True)


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