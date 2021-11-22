from os import name
import sqlite3 as sl

DATABASE_PATH = "netdecker/cardfile_data/cards.db"

def is_companion(card_name):
    con = sl.connect(DATABASE_PATH)
    cur = con.cursor()
    with con:
        cur.execute("SELECT COMPANION FROM CARD_OBJECT WHERE NAME = ?", [card_name])
        num = cur.fetchone()
    return num is not None and num[0] == 1

def name_from_alias(alias, format, is_truncated):
    """ Checks the alias table to find a match for the provided alias.

    Args:
        alias (str): The input alias string.
        format ([type]): The constructed format the alias is from.
        is_truncated (bool): Flag for whether the alias is truncated (...)

    Returns:
        The card name associated with that alias, or None if no such name exists.
    """
    con = sl.connect(DATABASE_PATH)
    cur = con.cursor()
    with con:
        if is_truncated:
            cur.execute("SELECT NAME FROM CARD_ALIAS NATURAL JOIN CARD_LEGALITIES WHERE FORMAT = ? AND SUBSTR(LOWER(ALIAS), 1, ?) = ?", [format, len(alias), alias.lower()])
        else:
            cur.execute("SELECT NAME FROM CARD_ALIAS NATURAL JOIN CARD_LEGALITIES WHERE FORMAT = ? AND LOWER(ALIAS) = ?", [format, alias.lower()])
        result = cur.fetchone()
    if not result:
        return None
    else:
        return result[0]

def add_alias(alias: str, card_name: str):
    con = sl.connect(DATABASE_PATH)
    with con:
        con.execute("INSERT OR IGNORE INTO CARD_ALIAS VALUES (?, ?)", (alias, card_name))

def names_in_range(min_length, max_length, format):
    """ Returns all the card names in a given length range.

    Args:
        min_length (int): Lower bound on card length, inclusive
        max_length (int): Upper bound on card length, inclusive
        format (str): The constructed format to pull cards from.

    Returns:
        List[str]: The card names that match the input criteria.
    """
    con = sl.connect(DATABASE_PATH)
    cur = con.cursor()
    with con:

        cur.execute("SELECT NAME FROM CARD_OBJECT NATURAL JOIN CARD_LEGALITIES WHERE FORMAT = ? AND LENGTH(NAME) BETWEEN ? AND ? ", (format, min_length, max_length))
        result = cur.fetchall()
    return [tup[0] for tup in result]
