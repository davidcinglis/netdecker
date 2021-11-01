import string
import re
from thefuzz import fuzz
from thefuzz import process
from decklist_ocr.ocr import GoogleOCR
from decklist_ocr.text_storage import BoundingBox, Vertex
from typing import List
from decklist_ocr import formats
import logging

FUZZY_MATCHING_THRESHOLD = 91


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

    def serialize(self):
        output = ""
        if self.companion is not None:
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


def parse_line(line, bounding_box, card_dataset, decklist, quantities):
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

    if decklist.sideboard_position is None and \
       fuzz.partial_ratio(line, "Sideboard") > 95:
            decklist.sideboard_position = bounding_box.upper_left_vertex
            return
    
    match = re.search("[xX][1-9][0-9]*", line)
    if match:
        quantity = int(match.group(0)[1:])
        quantities.append(CardQuantity(quantity, bounding_box))
        return

    # Each card name is at least 3 characters.
    elif len(line) < 3:
        return
    
    else:
        # TODO something more efficient than iterating through the entire cardset
        choice, ratio = process.extractOne(line, card_dataset)
        if ratio > FUZZY_MATCHING_THRESHOLD:
            card = CardTuple(choice, bounding_box)
            decklist.add_card(card)


def match_quantities(decklist: Decklist, quantities: List[CardQuantity]):
    """ Matches each quantity object to the closest card.
    """
    for quantity in quantities:
        position = quantity.bounding_box.upper_left_vertex
        closest_card = None
        closest_distance = None
        for card in decklist.maindeck:
            card_left_corner = card.bounding_box.upper_left_vertex
            card_right_corner = card.bounding_box.lower_right_vertex

            # The card has to be above and to the left of the quantity.
            if card_left_corner.x > position.x or card_left_corner.y > position.y:
                continue
            current_distance = position.distance(card_right_corner)
            if not closest_distance or closest_distance > current_distance:
                closest_distance = current_distance
                closest_card = card
        if closest_card is not None:
            closest_card.quantity = quantity.quantity


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
    reference_card_file = formats.get_cardlist(format)
    if not reference_card_file:
        return "Invalid format specified. Formats are %s." % formats.serialize()
    textboxes = recognizer.detect_text_uri(uri)
    logging.info("Recognizer detected %d textboxes" % len(textboxes))

    with open(reference_card_file) as f:
        reference_cardset = [line.strip() for line in f]
        decklist = Decklist()
        quantities = []

        for textbox in textboxes:
            line = preprocess_line_text(textbox.text)
            parse_line(line, textbox.bounding_box, reference_cardset, decklist, quantities)

    logging.info("Detected %d maindeck cards." % len(decklist.maindeck))
    logging.info("Deteced %d sideboard cards." % len(decklist.sideboard))
    logging.info("Detected %d quantities" % len(quantities))            
    match_quantities(decklist, quantities)
    return decklist.serialize()
