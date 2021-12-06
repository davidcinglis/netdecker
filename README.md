# Netdecker: MTG Decklist OCR Bot

For Magic: The Gathering players it's a very common occurence to see a 
screenshot of a decklist on social media and want to build that deck for
themselves on the digital client. Traditionally this is a tedious process of
searching for the cards in the deckbuilder and adding them to the deck
one-by-one. Netdecker is a tool to automate that process. It performs all the
work needed to transform the screenshot into an importable text list, without
requiring any manual input from the end user. It can distinguish between
maindeck and sideboard, match card quantity labels to the correct card name,
and even detect companions. What used to be a tedious 5 minute process can
now be done in just a few clicks.

###  Example:

![Discord Decklist Example](/assets/discord-decklist-sample.PNG?raw=true "Discord Decklist Example")


## Usage

Post a decklist screenshot in Discord, then reply to that image with the
command `!decklist format`, substituting in the appropriate constructed format.
The bot will construct an importable text list of cards in the decklist,
then post it (in a thread so as not to clog up the channel). Currently the bot
is optimized for MTG Arena screenshots, and while it is functional for Magic
Online too there may some bugs there.

## Technical Details

Uses Google Cloud Vision OCR to extract all the text from the screenshot. These
raw text snippets are parsed with regexes to pull out the relevant bits
(card names, card quantity labels, etc.) and discard the noise. Cards
are identified by comparing against a SQLite database of all Magic cards using
Levenshtein fuzzy string matching.

All this information then gets organized and stored in a custom Decklist object.
The object can then be called to output its contents in a properly formatted
import string.

## Setup
Requires the following environment variables:
- `DISCORD_TOKEN`: Create a Discord application, create a bot for that
application, then set `DISCORD_TOKEN` to the bot's OAuth2 token. Here's a good
[reference](https://realpython.com/how-to-make-a-discord-bot-python/) for 
getting started Discord bots. 
- `GOOGLE_APPLICATION_CREDENTIALS`: Google Cloud Vision application credentials
are stored in a JSON file. After setting up your GCV account, download those
credentials and set the environment variable to the file path.

## Tests

Run tests with: `python3 -m pytest`

## Future Plans

- Better support for Magic Online screenshots in addition to MTG Arena.
- More ways to interface with the tool beyond the Discord bot (likely a web app
and a Twitter bot to start).

## LICENSE

GNU GPLv3