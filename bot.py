from typing import Any, Dict
from functools import partial
from lxml.html import parse
from telegram import Update
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    Updater,
)
from db import Database
from ticker_alarm import TickerAlarm
from ticker_query import TickerQuery


SET_TICKER_ALARM_COMMAND = "set"
SET_TICKER_ALARM_USAGE = f"/{SET_TICKER_ALARM_COMMAND} <ticker: str> <condition: ['<', '>']>  <target: float> (<type: ['once', 'repeat']; default = 'once'>)"
UNSET_TICKER_ALARM_COMMAND = "unset"
UNSET_TICKER_ALARM_USAGE = f"/{UNSET_TICKER_ALARM_COMMAND} <alarm_id: str>"
UNSET_ALL_TICKER_ALARMS_COMMAND = "unset_all"
UNSET_ALL_TICKER_ALARMS_USAGE = f"/{UNSET_ALL_TICKER_ALARMS_COMMAND}"
LIST_MY_TICKER_ALARMS_COMMAND = "list"
LIST_MY_TICKER_ALARMS_USAGE = f"/{LIST_MY_TICKER_ALARMS_COMMAND}"
GET_TICKER_PRICE_COMMAND = "price"
GET_TICKER_PRICE_USAGE = f"/{GET_TICKER_PRICE_COMMAND} <ticker: str>"
GET_TICKER_PRICES_COMMAND = "prices"
GET_TICKER_PRICES_USAGE = f"/{GET_TICKER_PRICES_COMMAND} <ticker1: str> <ticker2: str> <ticker3: str> ..."


class Bot:
    def __init__(self, bot_info: Dict[str, Any]) -> None:
        self.name = bot_info["name"]
        self.handle = bot_info["handle"]
        self.description = bot_info["description"]
        self.updater = self._make_updater(bot_info["token"])
        self.db = Database()
        self.reply_mode = "MARKDOWN_V2"
        
    def _make_updater(self, token: str) -> None:
        updater = Updater(token)
        updater.dispatcher.add_handler(CommandHandler(SET_TICKER_ALARM_COMMAND, self.set_ticker_alarm))
        updater.dispatcher.add_handler(CommandHandler(UNSET_TICKER_ALARM_COMMAND, self.unset_ticker_alarm))
        updater.dispatcher.add_handler(CommandHandler(UNSET_ALL_TICKER_ALARMS_COMMAND, self.unset_all_ticker_alarms))
        updater.dispatcher.add_handler(CommandHandler(LIST_MY_TICKER_ALARMS_COMMAND, self.list_my_ticker_alarms))
        updater.dispatcher.add_handler(CommandHandler(GET_TICKER_PRICE_COMMAND, self.get_ticker_price))
        updater.dispatcher.add_handler(CommandHandler(GET_TICKER_PRICES_COMMAND, self.get_ticker_prices))
        return updater

    def start(self) -> None:
        self.updater.start_polling()
        self.updater.idle()

    def set_ticker_alarm(self, update: Update, context: CallbackContext) -> None:
        user_id, message_id = update.message.chat.id, update.message.message_id
        args = context.args

        if len(args) < 3:
            update.message.reply_text(f"/{SET_TICKER_ALARM_COMMAND} usage: {SET_TICKER_ALARM_USAGE}")
            return

        ticker = args[0]  # TODO: check if valid ticker

        condition = args[1]
        if condition not in ["<", ">"]:
            update.message.reply_text(f"valid condition options: '<', '>'")
            return

        try:
            target = float(args[2])
        except ValueError:
            update.message.reply_text(f"target should be int or float (e.g. 43, 65.1, 4.09)")
            return

        alarm_type = args[3].lower() if len(args) > 3 else "once"
        if alarm_type not in ["once", "repeat"]:
            update.message.reply_text(f"valid alarm_type options: 'once', 'repeat'")
            return

        alarm = TickerAlarm(TickerAlarm.make_alarm_id(user_id, message_id), ticker, condition, target, alarm_type)
        self.db.insert_ticker_alarm(user_id, alarm)
        callback_func = partial(TickerAlarm.run, alarm=alarm, db=self.db)
        context.job_queue.run_repeating(callback_func, interval=10, first=1, last=None, context={"user_id": user_id}, name=alarm.name)
        update.message.reply_text(alarm.get_ticker_alarm_set_message_text())

    def unset_ticker_alarm(self, update: Update, context: CallbackContext) -> None:
        args = context.args

        if len(args) < 1:
            update.message.reply_text(f"/{UNSET_TICKER_ALARM_COMMAND} usage: {UNSET_TICKER_ALARM_USAGE}")
            return
        
        alarm_id = args[0]
        is_removed, message = TickerAlarm.remove_alarm_from_jobs(self.db, context, alarm_id, modification="unset")
        update.message.reply_text(message)

    def unset_all_ticker_alarms(self, update: Update, context: CallbackContext) -> None:
        is_removed, message = TickerAlarm.remove_all_alarms_from_jobs(self.db, context, modification="unset")
        update.message.reply_text(message)

    def list_my_ticker_alarms(self, update: Update, context: CallbackContext) -> None:
        user_id = update.message.chat.id
        alarms = [TickerAlarm(**doc["alarm"]) for doc in self.db.find_active_ticker_alarms_of_user(user_id)]
        texts = [str(alarm) for alarm in alarms]
        update.message.reply_text("\n\n".join(texts) if len(texts) > 0 else "no alarm")

    def get_ticker_price(self, update: Update, context: CallbackContext) -> None:
        user_id = update.message.chat.id
        args = context.args
        if len(args) < 1:
            update.message.reply_text(f"/{GET_TICKER_PRICE_COMMAND} usage: {GET_TICKER_PRICE_USAGE}")
            return
        ticker = args[0]

        ticker_query = TickerQuery(ticker)
        reply, parse_mode = TickerQuery.run_and_get_reply(ticker_query, user_id, self.db, reply_mode=self.reply_mode)
        update.message.reply_text(reply, parse_mode=parse_mode)

    def get_ticker_prices(self, update: Update, context: CallbackContext) -> None:
        user_id = update.message.chat.id
        args = context.args
        if len(args) < 1:
            update.message.reply_text(f"/{GET_TICKER_PRICES_COMMAND} usage: {GET_TICKER_PRICES_USAGE}")
            return
        tickers = args  # TODO: check if valid ticker

        ticker_query_lst = [TickerQuery(ticker) for ticker in tickers]
        reply, parse_mode = TickerQuery.run_multiple_and_get_reply(ticker_query_lst, user_id, self.db, reply_mode=self.reply_mode)
        update.message.reply_text(reply, parse_mode=parse_mode)
