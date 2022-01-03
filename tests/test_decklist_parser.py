import pytest
from netdecker.decklist_parser import DecklistParser, Decklist

def test_truncation_check():
    d = DecklistParser([], "historic")
    str1 = "Teachings of the Archa... O"
    line, is_truncation = d.truncation_check(str1)
    assert line == "Teachings of the Archa"
    assert is_truncation == True
    

def test_line_matching():
    d = DecklistParser([], "historic")
    str1 = "Teachings of the Archa... O"
    str2 = "nonland..."
    assert d.match_to_card_name(str1) == "Teachings of the Archaics"
    assert not d.match_to_card_name(str2)
    