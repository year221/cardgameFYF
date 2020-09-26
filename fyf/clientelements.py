import os
import math
import arcade
from arcade import gui
from typing import List, Dict, Tuple
from dataclasses import dataclass, asdict, field

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


# class Mat(arcade.SpriteSolidColor):
#     """ Mat for a card pile """
#
#     def __init__(self, pile_position_in_card_pile_list, *args, **kwargs):
#         """ Card constructor """
#
#         # Attributes for suit and value
#         super().__init__(*args, **kwargs)
#         # Image to use for the sprite when face up
#         self.pile_position_in_card_pile_list = pile_position_in_card_pile_list

# Face down image
FACE_DOWN_IMAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources/images/cards/cardBack_red2.png")
# COLOR
COLOR_ACTIVE = (200,200,255)
COLOR_INACTIVE = (255,255,255)
# Card constants
CARD_VALUES = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
CARD_SUITS = ["Spades", "Hearts", "Clubs", "Diamonds", "Joker"]

class Card(arcade.Sprite):
    """ Enhanced Card sprite boject"""

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

class GameFlatButton(gui.UIFlatButton):
    """
    To capture a button click, subclass the button and override on_click.
    """
    def __init__(self, click_event, font_size=None, bg_color=None, *arg, **kargs):
        super().__init__(*arg, **kargs)
        self.click_event = click_event
        if font_size is not None:
            self.set_style_attrs(font_size=font_size)
        self.set_style_attrs(border_color=arcade.color.BLACK,
                             font_color=arcade.color.GOLD,
                             #border_color_hover=arcade.color.BLUE,
                             #border_color_press=arcade.color.ORANGE,
                             bg_color=bg_color if bg_color is not None else arcade.color.DARK_SLATE_GRAY,
                             bg_color_hover=arcade.color.DARK_ORANGE,
                             bg_color_press=arcade.color.ORANGE,
                             )

    def on_click(self):
        """ Called when user lets off button """
        self.click_event()



class GameTextLabel(gui.UILabel):
    """
    To capture a button click, subclass the button and override on_click.
    """
    def __init__(self, font_size=None, *arg, **kargs):
        super().__init__(*arg, **kargs)
        if font_size is not None:
            self.set_style_attrs(font_size=font_size)
        self.set_style_attrs(font_color=arcade.color.GOLD)