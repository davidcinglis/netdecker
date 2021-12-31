import pytest
from netdecker import ocr

blank_uri = "https://raw.githubusercontent.com/davidcinglis/" \
            "netdecker/main/tests/images/blank.png"
lands_uri = "https://raw.githubusercontent.com/davidcinglis/" \
            "netdecker/main/tests/images/lands.png"

def test_ocr_errors():
    recognizer = ocr.GoogleOCR()
    assert recognizer.detect_text_uri("abcd").success == False
    assert recognizer.detect_text_uri("google.com").success == False
    assert recognizer.detect_text_uri(blank_uri).success == True
    assert recognizer.detect_text_uri(lands_uri).success == True