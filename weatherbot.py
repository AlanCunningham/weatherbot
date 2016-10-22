# -*- coding: utf-8 -*-

import logging
import signal
import sys
import schedule
import time
import weather as forecast
import threading
import random
import time
import ConfigParser

from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler, Filters


config = ConfigParser.ConfigParser()
config.read('config.py')
updater = Updater(token=config.get('telegram', 'api_key'))
# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

is_running = True
message_groups = {}
weather_timeout = 3600
response_timeout = 20
spam_timeout = 60
weather_summary = None
scheduler_running = False
dispatcher = updater.dispatcher


# Respond to certain keywords in the chat
# There's most likely a better way of doing this...
def custom_responses(bot, update):
	global response_timeout
	thumbs_up = '\xF0\x9F\x91\x8D'

	# Start the scheduler on startup
	start_scheduler(bot, update)
	message = update.message.text.lower()

	responses = {
		'hi sam': '**HELLO THERE**',
		'sam': 'What',
		'thanks sam': thumbs_up
	}

	if message in responses:
		send_message(bot, update, responses[message])

	if get_timeout_diff(response_timeout) > 900:
		if 'red lion' in message:
			send_message(bot, update, 'Which one?')
			response_timeout = int(time.time())

custom_responses = MessageHandler([Filters.text], custom_responses)
dispatcher.add_handler(custom_responses)


def start_scheduler(bot, update):
	global scheduler_running, message_groups
	if scheduler_running == False:
		logging.info('Starting schedule')
		# Schedule a weather report at a certain time
		schedule.every().day.at('08:00').do(send_scheduled_weather, bot, update)
		scheduler_running = True
		# Run the scheduler in the background
		t = threading.Thread(target=run_scheduler)
		t.daemon = True
		t.start()

	if update.message.chat_id not in message_groups:
		subscribe_group(bot, update)


# Weather scheduler
def run_scheduler():
	while is_running:
		schedule.run_pending()
		time.sleep(1)


# Subscribe a group to scheduled weather updates
def subscribe_group(bot, update):
	global message_groups
	if update.message.chat_id not in message_groups:
		message_groups[update.message.chat_id] = {
				'subscribed': True
		}
	else:
		message_groups[update.message.chat_id]['subscribed'] = True
		# send_message(bot, update, '**SUBSCRIBED**')
	logging.info('Message groups: %s ' % message_groups)


subscribe_group_handler = CommandHandler('subscribe', subscribe_group)
dispatcher.add_handler(subscribe_group_handler)


# Unsubscribe a group from scheduled weather updates
def unsubscribe_group(bot, update):
	global message_groups
	message_groups[update.message.chat_id]['subscribed'] = False
	# send_message(bot, update, '**UNSUBSCRIBED**')
	logging.info('Message groups: %s ' % message_groups)

unsubscribe_group_handler = CommandHandler('unsubscribe', unsubscribe_group)
dispatcher.add_handler(unsubscribe_group_handler)


def send_scheduled_weather(bot, update):
	global message_groups
	for group in message_groups:
		if message_groups[group]['subscribed'] == True:
			summary = get_weather()
			logging.info('Group: %s ' % group)
			if summary is not None:
				bot.sendMessage(chat_id=group, text=summary)


def get_weather():
	global weather_timeout, weather_summary
	# Update the weather if we haven't requested it in a while.
	# If we've recently requested the weather, we just return the cached version
	if get_timeout_diff(weather_timeout) > 900:
		logging.info('Getting weather - new')
		weather = forecast.Weather()

		current_hour = int(time.strftime('%H'))
		# current_hour = 19
		logging.info('Time: %s', current_hour)

		daily_weather = weather.get_daily_weather()
		hourly_weather = weather.get_hourly_weather()
		morning_avg = get_average_temp(hourly_weather, 8, 12)
		afternoon_avg = get_average_temp(hourly_weather, 12, 17)
		evening_avg = get_average_temp(hourly_weather, 17, 23)

		if current_hour >= 6 and current_hour < 12:
			hourly_summary = \
				'Expect %s%s in the morning, %s%s in the afternoon ' \
				'and %s%s in the evening' % (
				morning_avg, unichr(176),
				afternoon_avg, unichr(176),
				evening_avg, unichr(176))
		elif current_hour >= 12 and current_hour < 17:
			hourly_summary = \
				'Expect %s%s in the afternoon and %s%s in the evening' % \
				(afternoon_avg, unichr(176),
				evening_avg, unichr(176))
		elif current_hour >= 17 and current_hour <= 23:
			hourly_summary = \
				'Expect %s%s this evening' % (evening_avg, unichr(176))
		else:
			current_temp = int(round(hourly_weather[(current_hour)]['apparentTemperature']))
			hourly_summary = "It's %s%s right now" % (current_temp, unichr(176))

		logging.info('Hourly weather: %s', hourly_summary)
		clothes_suggestion = weather.suggest_clothes()
		weather_summary = '%s. %s\n\n%s.' % (
			hourly_summary,
			daily_weather['summary'],
			clothes_suggestion)
		weather_timeout = int(time.time())
	return weather_summary


def get_average_temp(hourly_weather, start_time, end_time):
	temps = []
	while start_time <= end_time:
		temps.append(hourly_weather[start_time]['apparentTemperature'])
		start_time += 1
	logging.info('temps %s', temps)
	return int(round(sum(temps) / len(temps)))


def weather_command(bot, update):
	global spam_timeout
	if get_timeout_diff(spam_timeout) > 30:
		send_message(bot, update, get_weather())
		spam_timeout = int(time.time())


weather_handler = CommandHandler('weather', weather_command)
dispatcher.add_handler(weather_handler)


# Return how many seconds have elapsed since now and a given timestamp
def get_timeout_diff(timestamp):
	now = int(time.time())
	diff = now - timestamp
	return diff


def send_message(bot, update, text):
	if text is not None:
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
