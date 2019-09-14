#!/usr/bin/env python3

from dotenv import load_dotenv, find_dotenv
import os
import telebot
import requests
import subprocess
import shutil

load_dotenv(find_dotenv())
bot = telebot.TeleBot(os.getenv("TELEGRAM_BOT_TOKEN"))
print(bot.get_me())

# content types: document, photo, sticker
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Howdy, how are you doing?")

@bot.message_handler(content_types=['document'])
def process_document(message):
    process_file(bot.get_file(message.document.file_id), message)

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

    # for files that aren't jpg, convert to jpg to be able to use the -quality flag
    # probably only applies to stickers (.webp)
    if ext != '.jpg':
        print(f'\tconverting {ext} to .jpg')
        subprocess.run(['convert', f'{file_info.file_id}{ext}', '-quality', '100', f'{file_info.file_id}.jpg'])

    # make a backup of the jpg
    shutil.copyfile(f'{file_info.file_id}.jpg', f'{file_info.file_id}_original.jpg')

    # Do the (image) magic
    q = 101 # quality ranges from [1,100]
    while True:
        print(f'\tResizing (q := {q}) {file_info.file_id}')
        # resize the image
        method = ''
        if dim.width < dim.height:
            method = 'x512'
        else:
            method = '512x'
        subprocess.run(['convert', f'{file_info.file_id}.jpg', '-resize', method, f'{file_info.file_id}_new.png'])
        subprocess.run(['pngcrush', f'{file_info.file_id}_new.png'])

        x = os.stat(f'{file_info.file_id}_new.png').st_size
        print(f'\tResized PNG (q := {q}) is {x/1024.0} KB ({x} bytes)')
        # verify sticker is compressed enough
        if x < 512000:
            break
        else:
            print(f'\tToo large ({x} > 512000)')
            # decrement the quality incrementally
            q -= 1
            # compress the jpg
            subprocess.run(['convert', f'{file_info.file_id}_original.jpg', '-quality', f'{q}', f'{file_info.file_id}.jpg'])
    # Send the new PNG document
    doc = open(f'{file_info.file_id}_new.png', 'rb')
    bot.send_document(message.chat.id, doc, reply_to_message_id=message.message_id)


bot.polling()