import string
import re
import Levenshtein
from netdecker.text_storage import Textbox
from netdecker.decklist_storage import Decklist, DecklistResponse, CardQuantity, CardTuple
from netdecker.ocr import OCR
from typing import List
import logging
from netdecker.cardfile_data import cardfile

# The threshold for determining the maximum allowed distance when matching
# an input string to a card name. A value of N represents a tolerance of one
# mistake for every N characters in the card name.
DISTANCE_THRESHOLD = 6

# The approximate number of characters in a name before Arena truncates it.
# It's complicated to provide an absolute number since the mana cost effects
# the available space for the card. So a card like Emergent Ultimatum gets
# truncated to 13 characters because of the BBGGGUU mana cost. The name font
# doesn't have a fixed width either.
TRUNCATION_THRESHOLD = 13

# An upper bound on the length of a card name.
MAX_CARD_LENGTH = 34

class DecklistParser:
    """ Class for storing and generating decklist parsing information. Starts
        with an input set of textboxes from the OCR, then parses the card names
        and card quantities from those input strings and packages them into
        a Decklist object.
    """
    def __init__(self, textboxes: List[Textbox], format: str):
        self.textboxes = textboxes
        self.decklist = Decklist()
        self.quantities = []
        self.format = format
    
    def preprocess_line_text(self, line):
        """ Some preprocessing on a raw text line to strip whitespace and any
            garbage characters the OCR might have picked up.
        """

        # looking for the "x4" style quantity strings
        match = re.search("[xX][1-9][0-9]*", line)
        if match:
            return match.group(0)

        # strip out all characters that can't appear in a card nae.
        allowed_chars = string.ascii_letters + ' ' + ',' + '\'' + '-' + '.'
        line = ''.join([c for c in line if c in allowed_chars])

        # TODO Eventually support the few cards with numbers in their name.
        # Right now this is more trouble than it's worth since the OCR has such
        # a high false positive rate on numbers (usually from mana costs).

        line = line.strip()
        return line
    
    def truncation_check(self, line: str):
        """ Checks if a line is truncated by an ellipsis.
        """
        if len(line) < TRUNCATION_THRESHOLD:
            return line, False

        # The regular expression checks for two or more consecutive periods.
        match = re.search(r"\.{2,}", line)
        if match:
            return line[:match.start()], True
        else:
            return line, False

    def match_to_card_name(self, line: str):
        """ Matches an input text line to a card name from the database.
        """

        line, is_truncated = self.truncation_check(line)

        # try to get an exact match with the card name
        exact_match = cardfile.name_from_alias(line, self.format, is_truncated)
        if exact_match is not None:
            return exact_match
        
        # if that fails, iterate through all cards with a similar length name
        # and try to find a strong partial match.
        if is_truncated:
            # The truncated line will be at least 3 characters shorter
            # than the non-truncated card name.
            candidates = cardfile.names_in_range(len(line) + 3, MAX_CARD_LENGTH, self.format)
        else:
            # The OCR will almost never produce a name shorter than the
            # length of the actual card name, but it often produces a longer
            # one by incorrectly interpreting the mana cost.
            candidates = cardfile.names_in_range(len(line) - 3, len(line) + 1, self.format)
        
        # Iterate through all the candidates and try to find one within
        # the distance threshold.
        for candidate in candidates:
            if is_truncated:
                dist = Levenshtein.distance(candidate[:len(line)], line)
            else:
                dist = Levenshtein.distance(candidate, line)
            # The maximum acceptable distance between the line and a candidate.
            max_distance = min(len(candidate), len(line)) // DISTANCE_THRESHOLD
            if dist <= max_distance:
                cardfile.add_alias(line, candidate)
                return candidate
        
        # This point is only reached when no match exists.
        return None
    
    def parse_line(self, line, bounding_box):
        """ High-level method to parse an input line from the recognizer.
        """
        # Check for a sideboard label
        if self.decklist.sideboard_position is None and \
           Levenshtein.distance(line, "Sideboard") <= 3:
                self.decklist.sideboard_position = bounding_box.upper_left_vertex
                return
        
        # Check for a card quantity
        match = re.search("[xX][1-9][0-9]*", line)
        if match:
            logging.info("Found quantity match %s for line %s at position %s" \
                         % (match, line, bounding_box.serialize()))
            quantity = int(match.group(0)[1:])
            self.quantities.append(CardQuantity(quantity, bounding_box))
            return

        # Rule out lines that couldn't be a card name
        elif len(line) < 3:
            return

        # Now check for a card name
        card_name = self.match_to_card_name(line)
        if card_name:
            logging.info("Matching input %s to card name %s" % (line, card_name))
            self.decklist.add_card(CardTuple(card_name, bounding_box))
        else:
            logging.info("Discarding input %s" % line)
    
    def create_decklist(self):
        """ Top-level method for the parser class. Starts with the input
            textboxes and calls all the helper methods needed to fully populate
            the decklist object."""
        for textbox in self.textboxes:
            line = self.preprocess_line_text(textbox.text)
            self.parse_line(line, textbox.bounding_box)        

        self.decklist.cull_outliers()  
        self.decklist.match_quantities(self.quantities)
        self.decklist.companion_check()
    
def generate_decklist(img_b64, recognizer: OCR, format: str):
    """ The actual payoff function to be called externally. Invokes the
        recognizer, creates a decklist parser to handle the payoff, then creates
        and returns a decklist response.
    """
    ocr_response = recognizer.detect_text_uri(img_b64)
    decklist_response = DecklistResponse(ocr_response.success)

    # If the OCR was unsuccessful we can skip straight to the response.
    if not decklist_response.success:
        return decklist_response
    else:
        parser = DecklistParser(ocr_response.textboxes, format)
        parser.create_decklist()
        decklist_response.decklist = parser.decklist
        return decklist_response
