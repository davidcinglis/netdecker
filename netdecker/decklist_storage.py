from netdecker.text_storage import BoundingBox, Vertex
from typing import List
from netdecker.cardfile_data import cardfile

# The minimum height needed to be classified as a card, as a fraction of
# the average height among all potential cards.
MIN_HEIGHT_FRACTION = .55


class CardQuantity:
    """Represents a card quantity (e.g. "x2") on the decklist image."""
    def __init__(self, quantity: int, bounding_box: BoundingBox):
        self.quantity = quantity
        self.bounding_box = bounding_box


class CardTuple:
    """Represents a card name on the decklist image."""
    def __init__(self, name: str, bounding_box: BoundingBox, quantity: int = 1):
        self.name = name
        self.bounding_box = bounding_box
        self.quantity = quantity

    def serialize(self) -> str:
        return "%d %s\n" % (self.quantity, self.name)


class Decklist:
    """ Class for storing a parsed decklist. Stores cards in the maindeck,
        sideboard, and a potential companion. Also keeps track of the sideboard
        position to use as a delimiter when determining if a card is in the
        maindeck or the sideboard.
    """
    def __init__(self):
        self.maindeck : List[CardTuple] = []
        self.sideboard : List[CardTuple] = []
        self.sideboard_position : Vertex = None
        self.companion : CardTuple = None

    def add_card(self, card: CardTuple):
        def add_or_increment(card_list: List[CardTuple], card: CardTuple):
            # Combine quantities if card is already in the list.
            for candidate in card_list:
                if candidate.name == card.name:
                    candidate.quantity += card.quantity
                    return
            # If the card wasn't already in the list, add it.
            card_list.append(card)

        # TODO: Better positional check. This could potentially fail for
        #       very short sideboard card names.
        if self.sideboard_position is not None and \
           card.bounding_box.lower_right_vertex.x > self.sideboard_position.x:
                add_or_increment(self.sideboard, card)
        else:
            add_or_increment(self.maindeck, card)

    def companion_check(self):
        """ In Arena screenshots the companion shows up in both the maindeck
            and sideboard (as the first card in both). This function checks
            if the first maindeck/sideboard card is the same companion, and if
            so puts that card in the companion slot instead.
        """
        if len(self.maindeck) == 0 or len(self.sideboard) == 0:
            return
        
        maindeck_first = self.maindeck[0]
        sideboard_first = self.sideboard[0]

        if maindeck_first.name != sideboard_first.name:
            return
        
        if maindeck_first.quantity != 1 or sideboard_first.quantity != 1:
            return
        
        if cardfile.is_companion(maindeck_first.name):
            self.companion = CardTuple(maindeck_first.name, None, 1)
            self.maindeck = self.maindeck[1:]
            self.sideboard = self.sideboard[1:]
    
    def match_quantities(self, quantities: List[CardQuantity]):
        """ Matches each quantity object to the closest card.
        """
        for quantity in quantities:
            position = quantity.bounding_box.upper_left_vertex
            closest_card = None
            closest_distance = None
            for card in self.maindeck:
                if card.quantity > 1:
                    continue
                card_left_corner = card.bounding_box.upper_left_vertex
                card_right_corner = card.bounding_box.lower_right_vertex

                # The card has to be above and to the left of the quantity.
                if card_left_corner.x > position.x or card_left_corner.y > position.y:
                    continue
                
                # The card name should be just a little bit above the quantity.
                # The height of the quantity is a good way to judge this
                if quantity.bounding_box.get_height() * 2 < position.y_delta(card_left_corner):
                    continue
                current_distance = position.distance(card_right_corner)
                if not closest_distance or closest_distance > current_distance:
                    closest_distance = current_distance
                    closest_card = card
            if closest_card is not None:
                closest_card.quantity = quantity.quantity
    
    def cull_outliers(self):
        """ Removes detected card names that are abnormally small compared to
            to the average card name. This helps the text on the body of the
            card from being misinterpreted as a card name.Only operates on the 
            maindeck for now because Arena sideboard cards do not have any 
            body text on them, and the body text on MTGO cards is too similar 
            in size to the title text for this process to distinguish the two.
        """
        if len(self.maindeck) > 0:
            heights = [card.bounding_box.get_height() for card in self.maindeck]
            mean_height = sum(heights) / len(heights)
            height_threshold = mean_height * MIN_HEIGHT_FRACTION
            self.maindeck = [card for card in self.maindeck if \
                             card.bounding_box.get_height() > height_threshold]
    
    def serialize(self):
        output = ""
        if self.companion is not None:
            output += "Companion\n"
            output += self.companion.serialize() + "\n"
        
        output += "Deck\n"
        for card_tuple in self.maindeck:
            output += card_tuple.serialize()
        
        if len(self.sideboard) > 0:
            output += "\nSideboard\n"
            for card_tuple in self.sideboard:
                output += card_tuple.serialize()
        
        return output

    def deck_size(self):
        maindeck_count = sum([card.quantity for card in self.maindeck])
        sideboard_count = sum([card.quantity for card in self.sideboard])
        return maindeck_count, sideboard_count

class DecklistResponse:
    def __init__(self, success: bool = False, decklist: Decklist = None):
        self.success = success
        self.decklist = decklist