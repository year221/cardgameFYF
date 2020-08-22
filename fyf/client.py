"""
ZPY Card Game
"""


import random
import arcade
import os
# Screen title and size
SCREEN_WIDTH = 1400
SCREEN_HEIGHT = 800
SCREEN_TITLE = "Zhao Peng You"

# Constants for sizing
CARD_SCALE = 0.6

# How big are the cards?
CARD_WIDTH = 140 * CARD_SCALE
CARD_HEIGHT = 190 * CARD_SCALE

# If we fan out cards stacked on each other, how far apart to fan them?
CARD_HORIZONTAL_OFFSET = int(CARD_WIDTH * 0.25)

# How much space do we leave as a gap between the mats?
# Done as a percent of the mat size.
VERTICAL_MARGIN_PERCENT = 0.10
HORIZONTAL_MARGIN_PERCENT = 0.10


# How big is the mat we'll place the card on?
MAT_PERCENT_OVERSIZE = 1.25
MAT_HEIGHT = int(CARD_HEIGHT * MAT_PERCENT_OVERSIZE)
MAT_WIDTH = int(CARD_WIDTH * MAT_PERCENT_OVERSIZE)
HAND_MAT_HEIGHT = int(CARD_HEIGHT*2 + MAT_HEIGHT * VERTICAL_MARGIN_PERCENT)
HAND_MAT_WIDTH = int(CARD_HORIZONTAL_OFFSET * 60 + CARD_WIDTH)

# The Y of the bottom row (2 piles)
HAND_MAT_Y = HAND_MAT_HEIGHT / 2 + MAT_HEIGHT * VERTICAL_MARGIN_PERCENT
# The X of where to start putting things on the left side
HAND_MAT_X = HAND_MAT_WIDTH / 2 + MAT_WIDTH * HORIZONTAL_MARGIN_PERCENT


# Card constants
CARD_VALUES = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
CARD_SUITS = ["Spades", "Hearts", "Clubs", "Diamonds", "Joker"]

CARD_VALUE2SYMBOL = {CARD_VALUES[index]:index for index in range(len(CARD_VALUES))}
CARD_SUITS2SYMBOL = {CARD_SUITS[index]:index for index in range(len(CARD_SUITS))}

def card2int(suit, value):
    return CARD_SUITS2SYMBOL[suit]*13+ CARD_VALUE2SYMBOL(value)

def int2card(x):
    return CARD_SUITS[x//13], CARD_VALUES[x%13]

# Face down image
FACE_DOWN_IMAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources/images/cards/cardBack_red2.png")



# COLOR
COLOR_ACTIVE = (200,200,255)
COLOR_INACTIVE = (255,255,255)

class Card(arcade.Sprite):
    """ Card sprite """

    def __init__(self, suit, value, scale=1):
        """ Card constructor """

        # Attributes for suit and value
        self.suit = suit
        self.value = value

        # Image to use for the sprite when face up
        self.image_file_name = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"resources/images/cards/card{self.suit}{self.value}.png")
        self.is_face_up = True
        self.clickable = True
        self.is_active = False
        super().__init__(self.image_file_name, scale)


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

    @property
    def is_face_down(self):
        """ Is this card face down? """
        return not self.is_face_up

    @property
    def active(self):
        return self.is_active

def sort_cards(int_list, exclude_values=None):
    if exclude_values is None:
        exclude_values = tuple(2+w*13 for w in range(4)) + (52, 53)
    return sorted([w for w in int_list if w not in exclude_values]) + sorted([w for w in int_list if w in exclude_values])


def card_list_to_int_list(card_list):
    return [card2int(card.suit, card.value) for card in card_list]

def update_cards(int_list, card_list, starting_x, starting_y, max_x):
    sorted_int_list = sort_cards(int_list)
    c_card_ints = card_list_to_int_list(card_list)
    if c_card_ints == int_list:
        # if the cards are the same then there is no update
        return
    else:
        while card_list:
            card_list.pop()
        card_x = starting_x
        card_y = starting_y
        for w in sorted_int_list:
            card = Card(*int2card(w), CARD_SCALE)
            card.position = card_x, card_y
            card_x = card_x + CARD_HORIZONTAL_OFFSET
            if card_x >= max_x:
                card_x = starting_x
                card_y = card_y +  CARD_HEIGHT + CARD_HEIGHT * VERTICAL_MARGIN_PERCENT
            card_list.append(card)

def arrange_positions(card_list, starting_x, starting_y, max_x):
    card_x = starting_x
    card_y = starting_y
    for card in card_list:
        card.position = card_x, card_y
        card_x = card_x + CARD_HORIZONTAL_OFFSET
        if card_x >= max_x:
            card_x = starting_x
            card_y = card_y + CARD_HEIGHT + CARD_HEIGHT * VERTICAL_MARGIN_PERCENT


class ZPYGame(arcade.Window):
    """ Main application class. """

    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)

        arcade.set_background_color(arcade.color.AMAZON)

        # Sprite list with all the cards, no matter what pile they are in.
        self.card_list = None
        self.out_card_list = None


        # Sprite list with all the mats tha cards lay on.
        self.pile_mat_list = None

        # Create a list of lists, each holds a pile of cards.
        self.piles = None

        # Create a list of cards that are activated
        self.active_cards = None
        # message encoding the cards
        self.card_codes = dict(
            card_in_hand = list(range(54)) + list(range(54))
        )






    def setup(self):
        """ Set up the game here. Call this function to restart the game. """

        # ---  Create the mats the cards go on.

        # Sprite list with all the mats tha cards lay on.
        self.pile_mat_list: arcade.SpriteList = arcade.SpriteList()

        hand_pile = arcade.SpriteSolidColor(HAND_MAT_WIDTH, HAND_MAT_HEIGHT, arcade.csscolor.DARK_OLIVE_GREEN)
        hand_pile.position = HAND_MAT_X, HAND_MAT_Y
        self.pile_mat_list.append(hand_pile)

        output_card_pile = arcade.SpriteSolidColor(MAT_WIDTH, MAT_HEIGHT, arcade.csscolor.DARK_OLIVE_GREEN)
        output_card_pile.position = int(SCREEN_WIDTH/2), int(HAND_MAT_Y+HAND_MAT_HEIGHT/2+MAT_HEIGHT)
        self.pile_mat_list.append(output_card_pile)

        # Sprite list with all the cards, no matter what pile they are in.
        self.card_list = arcade.SpriteList()
        self.out_card_list = arcade.SpriteList()
        # Create every card
        update_cards(self.card_codes['card_in_hand'], self.card_list, HAND_MAT_X-int(HAND_MAT_WIDTH/2)+int(CARD_WIDTH/2), HAND_MAT_Y-int(HAND_MAT_HEIGHT/2)+int(CARD_HEIGHT/2), HAND_MAT_X+int((HAND_MAT_WIDTH-CARD_WIDTH)/2))

        self.active_cards = []
    def on_draw(self):
        """ Render the screen. """
        # Clear the screen
        arcade.start_render()

        # Draw the mats the cards go on to
        self.pile_mat_list.draw()

        # Draw the cards
        self.card_list.draw()
        self.out_card_list.draw()

    def on_mouse_press(self, x, y, button, key_modifiers):
        """ Called when the user presses a mouse button. """

        if button == arcade.MOUSE_BUTTON_LEFT:
            # Get list of cards we've clicked on

            cards = arcade.get_sprites_at_point((x, y), self.card_list)

            # Have we clicked on a card?
            if len(cards) > 0:

                primary_card = cards[-1]

                primary_card.switch_activation_status()
                if primary_card.active:
                    self.active_cards.append(primary_card)
                else:
                    self.active_cards.remove(primary_card)

        elif button == arcade.MOUSE_BUTTON_RIGHT:

            for card in self.active_cards:
                card.switch_activation_status()
                self.card_list.remove(card)
                self.out_card_list.append(card)
            self.active_cards = []
            # send cards to the other pile
            arrange_positions(self.out_card_list,
                              int(SCREEN_WIDTH/2), int(HAND_MAT_Y+HAND_MAT_HEIGHT/2+MAT_HEIGHT),
                              SCREEN_WIDTH)

def main():
    """ Main method """
    window = ZPYGame()
    window.setup()
    arcade.run()


if __name__ == "__main__":
    main()