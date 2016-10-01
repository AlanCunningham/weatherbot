# -*- coding: utf-8 -*-

import telegram
import logging
import signal
import sys
import json
import schedule
import time
import weather as forecast
import Queue
import threading

from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler, Filters

token = ''
updater = Updater(token=token)
# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

is_running = True
message_groups = []
weather_timeout = 3600
response_timeout = 20
weather_summary = None

# Run start() when bot receives the /start command
dispatcher = updater.dispatcher
def start(bot, update):
	if update.message.chat_id not in message_groups:
		send_message(bot, update, '**INITIALISING**')
		# Schedule a weather report at a certain time
		schedule.every().day.at('08:00').do(schedule_weather, message_groups, bot, update)
		# Run the scheduler in the background
		t = threading.Thread(target=run_scheduler)
		t.daemon = True
		t.start()

start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)


# Weather scheduler
def run_scheduler():
	while is_running:
		schedule.run_pending()
		time.sleep(1)


# Subscribe a group to scheduled weather updates
def schedule_on(bot, update):
	if update.message.chat_id not in message_groups:
		message_groups.append(update.message.chat_id)
		send_message(bot, update, '**SCHEDULE ENABLED**')
	logging.info('Message groups: %s ' % message_groups)


schedule_on_handler = CommandHandler('schedule_on', schedule_on)
dispatcher.add_handler(schedule_on_handler)


# Unsubscribe a group from scheduled weather updates
def schedule_off(bot, update):
	if update.message.chat_id in message_groups:
		message_groups.remove(update.message.chat_id)
		send_message(bot, update, '**SCHEDULE DISABLED**')
	logging.info('Message groups: %s ' % message_groups)

schedule_off_handler = CommandHandler('schedule_off', schedule_off)
dispatcher.add_handler(schedule_off_handler)


def schedule_weather(bot, update):
	for group in message_groups:
		summary = request_weather()
		logging.info('Group: %s ' % group)
		bot.sendMessage(chat_id=group, text=request_weather())


# Return a daily weather report
def request_weather():
	global weather_timeout, weather_summary
	# Update the weather if we haven't requested it in a while.
	# If we've recently requested the weather, we just return the cached version
	if get_timeout_diff(weather_timeout) > 900:
		logging.debug('Getting weather - new')
		weather = forecast.Weather()
		daily_weather = weather.get_daily_weather()
		temp_low = int(round(daily_weather['apparentTemperatureMin']))
		temp_high = int(round(daily_weather['apparentTemperatureMax']))
		clothes_suggestion = weather.suggest_clothes()
		weather_summary = 'Today will have highs of %s%s and lows of %s%s, %s\n\n%s.' % (
						temp_high, unichr(176), # Degrees symbol
						temp_low, unichr(176), # Degrees symbol
						daily_weather['summary'].lower(),
						clothes_suggestion)
		weather_timeout = int(time.time())
	return weather_summary

weather_handler = CommandHandler('weather', lambda x,y: send_message(x, y, request_weather()))
dispatcher.add_handler(weather_handler)

# Respond to certain keywords in the chat
# There's most likely a better way of doing this...
def custom_responses(bot, update):
	global response_timeout
	message = update.message.text.lower()
	if 'hi sam' == message:
		send_message(bot, update, '**HELLO THERE**')
	if 'sam' == message:
		send_message(bot, update, '**WHAT**')
	if get_timeout_diff(response_timeout) > 900:
		if 'red lion' in message:
			send_message(bot, update, 'Which one?')
		response_timeout = int(time.time())

custom_responses = MessageHandler([Filters.text], custom_responses)
dispatcher.add_handler(custom_responses)


# Return how many seconds have elapsed since now and a given timestamp
def get_timeout_diff(timestamp):
	now = int(time.time())
	diff = now - timestamp
	return diff


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
