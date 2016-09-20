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

token = 'telegram_bot_api_key_here'
updater = Updater(token=token)
# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

weather = weather.Weather()
is_running = True

# Run start() when bot receives the /start command
dispatcher = updater.dispatcher
started = False
def start(bot, update):
	global started
	if started == False:
		send_message(bot, update, '***BOOTING UP***')
		print('Message ID: %s ' % update.message.chat_id)
		# Schedule a weather report at a certain time
		schedule.every().day.at('08:00').do(get_weather, bot, update)
		# Run the scheduler in the background
		t = threading.Thread(target=run_scheduler, args=(schedule,))
		t.daemon = True
		t.start()

		started = True

start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)


# Weather scheduler
def run_scheduler(schedule):
	while is_running:
		schedule.run_pending()
		time.sleep(1)


# Return a daily weather report
def get_weather(bot, update):
	global weather
	daily_weather = weather.get_daily_weather()
	clothes_suggestion = weather.suggest_clothes()
	full_summary = 'Today will have highs of %s and lows of %s, %s\n\n%s' % (
					daily_weather['apparentTemperatureMax'],
					daily_weather['apparentTemperatureMin'],
					daily_weather['summary'].lower(),
					clothes_suggestion)
	send_message(bot, update, full_summary)


def echo(bot, update):
	send_message(bot, update, update.message.text)

echo_handler = MessageHandler([Filters.text], echo)
dispatcher.add_handler(echo_handler)


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
