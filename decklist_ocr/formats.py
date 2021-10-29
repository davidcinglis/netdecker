from typing import List, Optional

supported_formats = [
    "standard", "historic", "pioneer", "modern", "legacy", "vintage", "pauper"
]

def get_cardlist(input: str) -> Optional[str]:
    format = input.lower().strip()
    if format not in supported_formats:
        return None
    else:
        return "decklist_ocr/card-lists/%s.txt" % format

def parse_format(input: str) -> str:
    return input.lower().strip()

def validate_format(input: str) -> bool:
    return parse_format(input) in supported_formats

def serialize() -> List[str]:
    return ", ".join(supported_formats)
