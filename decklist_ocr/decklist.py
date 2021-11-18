import string
import re
import Levenshtein
from decklist_ocr.text_storage import BoundingBox, Vertex
from typing import List
import logging
from decklist_ocr.cardfile_data import cardfile

# a value of N allows 1 mistake for every N characters
DISTANCE_THRESHOLD = 6

# The approximate number of characters in a name before Arena truncates it
TRUNCATION_THRESHOLD = 20

MAX_CARD_LENGTH = 34

# The minimum height needed to be classified as a card, as a fraction of
# the average height among all potential cards.
MIN_HEIGHT_FRACTION = .65


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
            card from being misinterpreted as a card name.
        """
        heights = [card.bounding_box.get_height() for card in self.maindeck]
        mean_height = sum(heights) / len(heights)
        height_threshold = mean_height * MIN_HEIGHT_FRACTION
        self.maindeck = [card for card in self.maindeck if card.bounding_box.get_height() > height_threshold]
    
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

def preprocess_line_text(line):
    """ Some preprocessing on the raw line to strip whitespace and any
        garbage characters the OCR might have picked up.

    Args:
        line (str): The raw line of text from the OCR.

    Returns:
        str: The processed line
    """
    # looking for the "x4" style quantity strings
    match = re.search("[xX][1-9][0-9]*", line)
    if match:
        return match.group(0)

    # TODO Eventually support the few cards with numbers in their name.
    # Right now this is more trouble than it's worth since the OCR has such
    # a high false positive rate on numbers (usually from mana costs).
    allowed_chars = string.ascii_letters + ' ' + ',' + '\'' + '-' + '.'
    line = ''.join([c for c in line if c in allowed_chars])
    line = line.strip()
    return line


def parse_line(line, bounding_box, format, decklist, quantities):
    """ The actual parsing logic for each line of input text. Decides if the
        line is a card name, a card quantity, or noise, and handles each case
        accordingly.

    Args:
        line (string): The input line of text, already preprocessed.
        bounding_box (BoundingBox): The position of the text in the image.
        card_dataset (List[str]): The cardset to match card names to.
        decklist (Decklist): The output Decklist object to be populated.
        quantities (List[CardQuantity]): The decklist's card quantities.
    
    Returns:
        No return, all the data is added directly to the input decklist and
        quantity objects.
    """

    # Check for the sideboard label
    if decklist.sideboard_position is None and \
       Levenshtein.distance(line, "Sideboard") < 4:
            decklist.sideboard_position = bounding_box.upper_left_vertex
            return
    
    # Check for a card quantity (x4)
    match = re.search("[xX][1-9][0-9]*", line)
    if match:
        logging.info("Found quantity match %s for line %s at position %s" % (match, line, bounding_box.serialize()))
        quantity = int(match.group(0)[1:])
        quantities.append(CardQuantity(quantity, bounding_box))
        return

    elif len(line) < 3:
        # Card names are >= 3 characters, and we already checked for quantities
        return
    
    # TODO Consider refactoring this part of the function
    else:
        choice = ""

        is_truncated = False
        if len(line) > TRUNCATION_THRESHOLD and "..." in line:
            line = line.split("...")[0]
            is_truncated = True
        match_length = len(line)

        # first try to get an exact match with the card name
        exact_match = cardfile.name_from_alias(line, format, is_truncated)
        if exact_match is not None:
            choice = exact_match
        
        # if that fails, iterate through all cards with a similar length name
        # and try to find a strong partial match.
        else:
            if is_truncated:
                candidates = cardfile.names_in_range(match_length + 3, MAX_CARD_LENGTH, format)
            else:
                # The OCR-generated names are rarely any shorter
                # than the actual name. But sometimes it thinks the mana cost
                # is part of the card name and adds a few extra characters at
                # the end, so we need to look at slightly shorter card names.
                candidates = cardfile.names_in_range(match_length - 3, match_length + 1, format)
            for candidate in candidates:
                if is_truncated:
                    dist = Levenshtein.distance(candidate[:len(line)], line)
                else:
                    dist = Levenshtein.distance(candidate, line)
                max_distance = max(len(candidate), len(line)) // DISTANCE_THRESHOLD
                if dist <= max_distance:
                    choice = candidate
                    cardfile.add_alias(line, candidate)
                    break
        
        if choice != "":
            logging.info("Matching input %s with choice %s at position %s" % (line, choice, bounding_box.serialize()))
            card = CardTuple(choice, bounding_box)
            decklist.add_card(card)
        else:
            logging.info("Discarding input %s at position %s" % (line, bounding_box.serialize()))


def generate_decklist(uri, recognizer, format):
    """ The actual payoff function to be called externally. High-level logic to
        get from an input image to a decklist, calling helper functions
        along the way.

    Args:
        uri (str): The location of the input image.
        recognizer (OCR): The instantiated recognizer object.
        format (str): The constructed MTG format of the decklist.

    Returns:
        str: The serialized decklist.
    """
    
    textboxes = recognizer.detect_text_uri(uri)
    decklist = Decklist()
    quantities = []
    logging.info("Recognizer detected %d textboxes" % len(textboxes))
    for textbox in textboxes:
        line = preprocess_line_text(textbox.text)
        parse_line(line, textbox.bounding_box, format, decklist, quantities)        
    
    logging.info("Detected %d maindeck cards." % len(decklist.maindeck))
    logging.info("Deteced %d sideboard cards." % len(decklist.sideboard))
    logging.info("Detected %d quantities" % len(quantities))
    decklist.cull_outliers()  
    decklist.match_quantities(quantities)
    decklist.companion_check()
    return decklist.serialize()
