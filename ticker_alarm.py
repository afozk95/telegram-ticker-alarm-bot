from __future__ import annotations
from typing import Any, Dict, Optional, Tuple, Union
from enum import Enum
from functools import partialmethod
from copy import deepcopy
import pymongo
from telegram.ext import CallbackContext
from price import get_current_ticker_info


class Condition(Enum):
    GREATER_THAN = ">"
    LESS_THAN = "<"


class AlarmType(Enum):
    ONCE = "once"
    REPEAT = "repeat"


class TickerAlarm:
    def __init__(self, alarm_id: str, ticker: str, condition: Union[Condition, str], target: float, alarm_type: Union[AlarmType, str], description: Optional[str] = None) -> None:
        self.alarm_id = alarm_id
        self.ticker = ticker
        self.condition = self._parse_condition(condition)
        self.target = target
        self.alarm_type = self._parse_alarm_type(alarm_type)
        self.description = description

    def _parse_condition(self, condition: Union[Condition, str]) -> None:
        if isinstance(condition, Condition):
            return condition
        elif isinstance(condition, str):
            return Condition(condition)
        else:
            raise TypeError("Unexpected type passed for condition, Condition or str expected")

    def _parse_alarm_type(self, alarm_type: Union[AlarmType, str]) -> None:
        if isinstance(alarm_type, AlarmType):
            return alarm_type
        elif isinstance(alarm_type, str):
            return AlarmType(alarm_type)
        else:
            raise TypeError("Unexpected type passed for alarm_type, AlarmType or str expected")

    @property
    def name(self) -> str:
        return self.alarm_id

    @staticmethod
    def make_alarm_id(user_id: str, message_id: str) -> str:
        return f"{user_id}-{message_id}"

    def check_alarm_condition(self) -> Optional[bool]:
        price_dict = get_current_ticker_info(self.ticker)
        if price_dict is not None:
            current_price = price_dict["current_price"]
            if self.condition == Condition.GREATER_THAN:
                return current_price > self.target
            elif self.condition == Condition.LESS_THAN:
                return current_price < self.target
        return None

    def __str__(self) -> str:
        text = f"[alarm_id = {self.alarm_id}, alarm_type = {self.alarm_type.value}]"
        text += f"\n{self.ticker} {self.condition.value} {self.target}"
        if self.description:
            text += f"\ndesc = {self.description}"
        return text

    def get_ticker_alarm_triggered_message_text(self) -> str:
        return f"alarm triggered\n{self}"
    
    def get_ticker_alarm_set_message_text(self) -> str:
        return f"alarm set\n{self}"
    
    def get_ticker_alarm_unset_message_text(self) -> str:
        return f"alarm unset\n{self}"

    def get_ticker_alarm_price_error_text(self) -> str:
        return f"price cannot be retrieved for ticker {self.ticker}, unsetting alarm"

    @staticmethod
    def run(callback_context: CallbackContext, alarm: TickerAlarm, db: pymongo.database.Database) -> None:
        job_context = callback_context.job.context
        user_id = job_context["user_id"]

        alarm_condition = alarm.check_alarm_condition()
        if alarm_condition is None:
            callback_context.bot.send_message(user_id, text=alarm.get_ticker_alarm_price_error_text())
            TickerAlarm.remove_alarm_from_jobs(db, callback_context, alarm.alarm_id, modification="error")
        elif alarm_condition:
            callback_context.bot.send_message(user_id, text=alarm.get_ticker_alarm_triggered_message_text())
            if alarm.alarm_type == AlarmType.ONCE:
                TickerAlarm.remove_alarm_from_jobs(db, callback_context, alarm.alarm_id, modification="trigger")

    @staticmethod
    def remove_alarm_from_jobs(db: pymongo.database.Database, context: CallbackContext, alarm_id: str, modification: str) -> Tuple[bool, str]:
        jobs = context.job_queue.get_jobs_by_name(alarm_id)

        if len(jobs) == 0:
            return False, f"no alarm with alarm_id {alarm_id}"

        for job in jobs:
            db.update_alarm(alarm_id, modification)
            job.schedule_removal()

        return True, f"removed alarm with alarm_id {alarm_id}"

    @staticmethod
    def remove_all_alarms_from_jobs(db: pymongo.database.Database, context: CallbackContext, modification: str) -> Tuple[bool, str]:
        jobs = context.job_queue.jobs()

        if len(jobs) == 0:
            return False, f"no alarm to unset"

        for job in jobs:
            alarm_id = job.name
            db.update_alarm(alarm_id, modification)
            job.schedule_removal()

        return True, f"all alarms unset"

    def serialize(self) -> Dict[str, Any]:
        dct = deepcopy(self.__dict__)
        dct["condition"] = dct["condition"].value
        dct["alarm_type"] = dct["alarm_type"].value
        return dct

    @classmethod
    def deserialize(cls, dct: Dict[str, Any]) -> TickerAlarm:
        return cls(**dct)
