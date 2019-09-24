#!/usr/bin/env python3

from dotenv import load_dotenv, find_dotenv
import os
import telebot
import requests
import subprocess

load_dotenv(find_dotenv())
bot = telebot.TeleBot(os.getenv("TELEGRAM_BOT_TOKEN"))
print(bot.get_me())

# content types: document, photo, sticker
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Howdy, how are you doing?")

@bot.message_handler(content_types=['sticker'])
def process_sticker(message):
    process_file(bot.get_file(message.sticker.file_id), message, message.sticker)

@bot.message_handler(content_types=['photo'])
def process_photo(message):
    original = None
    tmp = 0
    l = {}
    # find the largest photo in the PhotoSize array
    for x in message.photo:
        if x.width > tmp:
            original = x.file_id
            tmp = x.width
            l = x
    process_file(bot.get_file(original), message, l)

def process_file(file_info, message, dim):
    print(f'Processing file: {file_info.file_id}')
    # Download the file
    file = requests.get(f'https://api.telegram.org/file/bot{os.getenv("TELEGRAM_BOT_TOKEN")}/{file_info.file_path}')
    # extract the file extension from the string (https://stackoverflow.com/a/541394)
    _, ext = os.path.splitext(file_info.file_path)
    # write the download to a file
    open(f'{file_info.file_id}{ext}', 'wb').write(file.content)
    print(f'\tDownloaded: {file_info.file_id}{ext}')
	
    method = ''
    if dim.width < dim.height:
        method = 'x512'
    else:
        method = '512x'
    subprocess.run(['convert', f'{file_info.file_id}{ext}', '-resize', method, f'{file_info.file_id}_new.png'])
    subprocess.run(['pngcrush', f'{file_info.file_id}_new.png'])

    # Send the new PNG document
    doc = open(f'{file_info.file_id}_new.png', 'rb')
    bot.send_document(message.chat.id, doc, reply_to_message_id=message.message_id)
	
    # Clean up generated files
    os.remove(f'{file_info.file_id}{ext}')
    os.remove(f'{file_info.file_id}_new.png')

bot.polling()