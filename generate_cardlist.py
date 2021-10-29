import requests
from decklist_ocr import formats

scryfall_url = "https://c2.scryfall.com/file/scryfall-bulk/oracle-cards/oracle-cards-20211029210454.json"
card_dict = requests.get(scryfall_url).json()
format_list = formats.supported_formats

for format in format_list:
    output_filename = "decklist_ocr/card-lists/%s.txt" % format
    output_file = open(output_filename, 'w')
    for card in card_dict:
        if card["legalities"][format] == "legal":
            # Double-faced cards are denoted by scryfall as "front // back".
            # On decklist screenshots only the front side of the card will
            # be visible, so we can truncate the backside from the string.
            output_file.write(card["name"].split(" // ")[0] + "\n")
    output_file.close()
