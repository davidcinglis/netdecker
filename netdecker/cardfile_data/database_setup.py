import requests
import sqlite3 as sl
import formats

def generate_card_records():
    scryfall_url = "https://data.scryfall.io/oracle-cards/oracle-cards-20241028090152.json"
    card_dict = requests.get(scryfall_url).json()
    card_objects = []
    card_legalities = []
    for card in card_dict:
        # Scryfall represents double-faced card names as "front // back"
        # But for image parsing we only care about the front half of the card
        name = card["name"].split(" // ")[0]
        legal_formats = []
        for f in formats.supported_formats:
            if card["legalities"][f] in ("legal", "restricted"):
                legal_formats.append((name, f))
        if len(legal_formats) == 0:
            continue
        
        is_companion = "Companion" in card["keywords"]
        card_objects.append((card["id"], name, is_companion))
        card_legalities.extend(legal_formats)
    
    return card_objects, card_legalities


con = sl.connect("netdecker/cardfile_data/cards.db")
card_objects, card_legalities = generate_card_records()

with con:
    con.execute("DROP TABLE IF EXISTS CARD_OBJECT;")
    con.execute("""
        CREATE TABLE CARD_OBJECT (
            scryfall_id TEXT PRIMARY KEY,
            name TEXT,
            companion INTEGER
        );
    """)

    con.execute("DROP TABLE IF EXISTS CARD_ALIAS;")
    con.execute("""        
        CREATE TABLE IF NOT EXISTS CARD_ALIAS (
            alias TEXT PRIMARY KEY,
            name TEXT NOT NULL
        );
    """)

    con.execute("DROP TABLE IF EXISTS CARD_LEGALITIES;")

    con.execute("""
        CREATE TABLE IF NOT EXISTS CARD_LEGALITIES (
            name TEXT NOT NULL,
            format TEXT NOT NULL,
            UNIQUE(name, format)
        );
    """)

    con.executemany("INSERT INTO CARD_OBJECT VALUES (?, ?, ?)", card_objects)

    con.executemany("INSERT INTO CARD_LEGALITIES VALUES (?, ?)", card_legalities)

    con.execute("""INSERT INTO CARD_ALIAS SELECT name, name FROM CARD_OBJECT""")





