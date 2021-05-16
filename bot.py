from typing import Any, Dict
from enum import Enum
from functools import partial
from telegram import Update
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    Updater,
)
from telegram.parsemode import ParseMode
from db import Database
from ticker_alarm import TickerAlarm
from ticker_query import TickerQuery


ABOUT_COMMAND = "about"
ABOUT_USAGE = f"/{ABOUT_COMMAND}"
ABOUT_DESCRIPTION = "get information about the bot"
HELP_COMMAND = "help"
HELP_USAGE = f"/{HELP_COMMAND}"
HELP_DESCRIPTION = "list of all commands, their usage and description"
SET_TICKER_ALARM_COMMAND = "set"
SET_TICKER_ALARM_USAGE = f"/{SET_TICKER_ALARM_COMMAND} <ticker: str> <condition: ['<', '>']>  <target: float> (<type: ['once', 'repeat']; default = 'once'>)"
SET_TICKER_ALARM_DESCRIPTION = "set an alarm for ticker with condition and target to get notified"
UNSET_TICKER_ALARM_COMMAND = "unset"
UNSET_TICKER_ALARM_USAGE = f"/{UNSET_TICKER_ALARM_COMMAND} <alarm_id: str>"
UNSET_TICKER_ALARM_DESCRIPTION = "unset an alarm"
UNSET_ALL_TICKER_ALARMS_COMMAND = "unset_all"
UNSET_ALL_TICKER_ALARMS_USAGE = f"/{UNSET_ALL_TICKER_ALARMS_COMMAND}"
UNSET_ALL_TICKER_ALARMS_DESCRIPTION = "unset all alarms"
LIST_TICKER_ALARMS_COMMAND = "list"
LIST_TICKER_ALARMS_USAGE = f"/{LIST_TICKER_ALARMS_COMMAND}"
LIST_TICKER_ALARMS_DESCRIPTION = "list all alarms"
GET_TICKER_PRICE_COMMAND = "price"
GET_TICKER_PRICE_USAGE = f"/{GET_TICKER_PRICE_COMMAND} <ticker: str>"
GET_TICKER_PRICE_DESCRIPTION = "get price of ticker"
GET_TICKER_PRICES_COMMAND = "prices"
GET_TICKER_PRICES_USAGE = f"/{GET_TICKER_PRICES_COMMAND} <ticker1: str> <ticker2: str> <ticker3: str> ..."
GET_TICKER_PRICES_DESCRIPTION = "get price of multiple tickers"


class BotMode(Enum):
    POLLING = "polling"
    WEBHOOK = "webhook"


class Bot:
    def __init__(self, bot_info: Dict[str, Any]) -> None:
        self.name = bot_info["name"]
        self.handle = bot_info["handle"]
        self.description = bot_info["description"]
        self.token = bot_info["token"]
        self.github_repo_link = bot_info["github_repo_link"]
        self.mode = self._make_mode(bot_info["config"]["mode"])
        self.updater = self._make_updater(bot_info["token"])
        self.db = Database()
        self.reply_mode = "MARKDOWN_V2"

    def _make_mode(self, mode: str) -> BotMode:
        try:
            bot_mode = BotMode(mode)
        except ValueError:
            raise ValueError(f"mode = f{mode} is unknown, expected BotMode.")
        return bot_mode

    def _make_updater(self, token: str) -> None:
        updater = Updater(token)
        updater.dispatcher.add_handler(CommandHandler(ABOUT_COMMAND, self.about))
        updater.dispatcher.add_handler(CommandHandler(HELP_COMMAND, self.help))
        updater.dispatcher.add_handler(CommandHandler(SET_TICKER_ALARM_COMMAND, self.set_ticker_alarm))
        updater.dispatcher.add_handler(CommandHandler(UNSET_TICKER_ALARM_COMMAND, self.unset_ticker_alarm))
        updater.dispatcher.add_handler(CommandHandler(UNSET_ALL_TICKER_ALARMS_COMMAND, self.unset_all_ticker_alarms))
        updater.dispatcher.add_handler(CommandHandler(LIST_TICKER_ALARMS_COMMAND, self.list_ticker_alarms))
        updater.dispatcher.add_handler(CommandHandler(GET_TICKER_PRICE_COMMAND, self.get_ticker_price))
        updater.dispatcher.add_handler(CommandHandler(GET_TICKER_PRICES_COMMAND, self.get_ticker_prices))
        return updater

    def get_user_id(self, update: Update, context: CallbackContext) -> int:
        if update.message is not None:
            # text message
            user_id = update.message.chat.id
        elif update.callback_query is not None:
            # callback message
            user_id = update.callback_query.message.chat.id
        elif update.poll is not None:
            # answer in Poll
            user_id = context.bot_data[update.poll.id]
        else:
            raise Exception("Unknown update and context structure, cannot get user_id")

        return user_id
    
    def get_message_id(self, update: Update, context: CallbackContext) -> int:
        if update.message is not None:
            # text message
            message_id = update.message.message_id
        elif update.callback_query is not None:
            # callback message
            message_id = update.callback_query.message.message_id
        elif update.poll is not None:
            # answer in Poll
            # TODO: implement this
            raise NotImplementedError
        else:
            raise Exception("Unknown update and context structure, cannot get message_id")

        return message_id

    def run(self) -> None:
        if self.mode == BotMode.POLLING:
            self.updater.start_polling()
            self.updater.idle()
        elif self.mode == BotMode.WEBHOOK:
            self.updater.start_webhook(listen="0.0.0.0", port=8443, url_path=self.token, webhook_url=f"https://{self.name}.herokuapp.com/{self.token}")
        else:
            raise ValueError("Unknow mode attribute.")

    def about(self, update: Update, context: CallbackContext) -> None:
        update.message.reply_text(f"Please see the GitHub repo [here]({self.github_repo_link})", parse_mode=ParseMode.MARKDOWN_V2)

    def help(self, update: Update, context: CallbackContext) -> None:
        misc_str = "Misc\n"
        misc_str += f"/{ABOUT_COMMAND}\n{ABOUT_DESCRIPTION}\nusage = {ABOUT_USAGE}\n\n"
        misc_str += f"/{HELP_COMMAND}\n{HELP_DESCRIPTION}\nusage = {HELP_USAGE}\n\n"

        alarm_str = "Alarm\n"
        alarm_str += f"/{SET_TICKER_ALARM_COMMAND}\n{SET_TICKER_ALARM_DESCRIPTION}\nusage = {SET_TICKER_ALARM_USAGE}\n\n"
        alarm_str += f"/{UNSET_TICKER_ALARM_COMMAND}\n{UNSET_TICKER_ALARM_DESCRIPTION}\nusage = {UNSET_TICKER_ALARM_USAGE}\n\n"
        alarm_str += f"/{UNSET_ALL_TICKER_ALARMS_COMMAND}\n{UNSET_ALL_TICKER_ALARMS_DESCRIPTION}\nusage = {UNSET_ALL_TICKER_ALARMS_USAGE}\n\n"
        alarm_str += f"/{LIST_TICKER_ALARMS_COMMAND}\n{LIST_TICKER_ALARMS_DESCRIPTION}\nusage = {LIST_TICKER_ALARMS_USAGE}\n\n"

        query_str = "Query\n"
        query_str += f"/{GET_TICKER_PRICE_COMMAND}\n{GET_TICKER_PRICE_DESCRIPTION}\nusage = {GET_TICKER_PRICE_USAGE}\n\n"
        query_str += f"/{GET_TICKER_PRICES_COMMAND}\n{GET_TICKER_PRICES_DESCRIPTION}\nusage = {GET_TICKER_PRICES_USAGE}\n\n"

        reply = "\n\n".join([misc_str, alarm_str, query_str])
        update.message.reply_text(reply)

    def set_ticker_alarm(self, update: Update, context: CallbackContext) -> None:
        user_id, message_id = self.get_user_id(update, context), self.get_message_id(update, context)
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

    def list_ticker_alarms(self, update: Update, context: CallbackContext) -> None:
        user_id = self.get_user_id(update, context)
        alarms = [TickerAlarm(**doc["alarm"]) for doc in self.db.find_active_ticker_alarms_of_user(user_id)]
        texts = [str(alarm) for alarm in alarms]
        update.message.reply_text("\n\n".join(texts) if len(texts) > 0 else "no alarm")

    def get_ticker_price(self, update: Update, context: CallbackContext) -> None:
        user_id = self.get_user_id(update, context)
        args = context.args
        if len(args) < 1:
            update.message.reply_text(f"/{GET_TICKER_PRICE_COMMAND} usage: {GET_TICKER_PRICE_USAGE}")
            return
        ticker = args[0]

        ticker_query = TickerQuery(ticker)
        reply, parse_mode = TickerQuery.run_and_get_reply(ticker_query, user_id, self.db, reply_mode=self.reply_mode)
        update.message.reply_text(reply, parse_mode=parse_mode)

    def get_ticker_prices(self, update: Update, context: CallbackContext) -> None:
        user_id = self.get_user_id(update, context)
        args = context.args
        if len(args) < 1:
            update.message.reply_text(f"/{GET_TICKER_PRICES_COMMAND} usage: {GET_TICKER_PRICES_USAGE}")
            return
        tickers = args  # TODO: check if valid ticker

        ticker_query_lst = [TickerQuery(ticker) for ticker in tickers]
        reply, parse_mode = TickerQuery.run_multiple_and_get_reply(ticker_query_lst, user_id, self.db, reply_mode=self.reply_mode)
        update.message.reply_text(reply, parse_mode=parse_mode)
