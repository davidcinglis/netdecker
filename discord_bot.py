import os
from dotenv import load_dotenv
from decklist_ocr import decklist, ocr, formats
import discord

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

client = discord.Client()

@client.event
async def on_message(message: discord.Message):
    """ Checks if a message is invoking the bot. If it is, 
        fetches the parsed decklist for an input image 
        and replies with the text decklist.

        Usage: Message must be a reply to a decklist image, 
        and of the form "!decklist format".
    Args:
        message (discord.Message): The discord message to be checked.
    """
    if message.author == client.user:
        return
    
    if message.content.startswith('!decklist'):
        tokens = message.content.split()
        if len(tokens) < 2:
            response = "Please specify a format for this decklist."
            await message.channel.send(response)
            return
        
        format = tokens[1].lower()
        if not formats.validate_format(format):
            response = 'Invalid format specified. Options are %s' % formats.serialize()
            await message.channel.send(response)
            return

        if not message.reference or not message.reference.resolved.attachments:
            response = 'Request must be a reply to a decklist image.'
            await message.channel.send(response)
            return
        
        url = message.reference.resolved.attachments[0].url
        deck = decklist.generate_decklist(url, ocr.GoogleOCR(), format)
        thread = await message.create_thread(name="Decklist")
        await thread.send(deck)

client.run(TOKEN)

