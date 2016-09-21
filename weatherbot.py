# -*- coding: utf-8 -*-

import telegram
import logging
import signal
import sys
import json
import schedule
import time
import weather
import Queue
import threading

from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler, Filters

token = ''
updater = Updater(token=token)
# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

weather = weather.Weather()
is_running = True

message_groups = []

# Run start() when bot receives the /start command
dispatcher = updater.dispatcher
started = False
def start(bot, update):
	global started
	if update.message.chat_id not in message_groups:
		message_groups.append(update.message.chat_id)
		send_message(bot, update, '**INITIALISING**')
		print('Message ID: %s ' % update.message.chat_id)
		print('Message groups: %s ' % message_groups)
		# Schedule a weather report at a certain time
		my_schedule = schedule.every().day.at('08:00').do(get_weather, bot, update)
		# Run the scheduler in the background
		t = threading.Thread(target=run_scheduler, args=(my_schedule,))
		t.daemon = True
		t.start()

		started = True

start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)


# Weather scheduler
def run_scheduler(my_schedule):
	while is_running:
		schedule.run_pending()
		time.sleep(1)


# Return a daily weather report
def get_weather(bot, update):
	global weather
	daily_weather = weather.get_daily_weather()
	temp_low = int(round(daily_weather['apparentTemperatureMin']))
	temp_high = int(round(daily_weather['apparentTemperatureMax']))
	clothes_suggestion = weather.suggest_clothes()
	full_summary = 'Today will have highs of %s%s and lows of %s%s, %s\n\n%s.' % (
					temp_high, unichr(176), # Degrees symbol
					temp_low, unichr(176), # Degrees symbol
					daily_weather['summary'].lower(),
					clothes_suggestion)
	send_message(bot, update, full_summary)

weather_handler = CommandHandler('weather', get_weather)
dispatcher.add_handler(weather_handler)


# Respond to certain keywords in the chat
# There's most likely a better way of doing this...
def custom_responses(bot, update):
	global greeting_timeout
	message = update.message.text.lower()
	if 'hi sam' == message:
		send_message(bot, update, '**HELLO THERE**')
	if 'sam' == message:
		send_message(bot, update, '**WHAT**')
	if 'red lion' in message:
		send_message(bot, update, 'Which one?')

custom_responses = MessageHandler([Filters.text], custom_responses)
dispatcher.add_handler(custom_responses)


def send_message(bot, update, text):
	bot.sendMessage(chat_id=update.message.chat_id, text=text)


# Gracefully stop the bot on Ctrl-C
def signal_handler(signal, frame):
	global is_running
	print('\nGracefully closing, please wait a moment')
	is_running = False
	updater.stop()
	sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

# Start the bot
updater.start_polling()
signal.pause()
