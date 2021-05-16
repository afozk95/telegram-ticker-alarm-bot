from typing import Any, Dict, Optional
from ticker_query import TickerQuery
import pymongo
import datetime
from ticker_alarm import TickerAlarm


class Database:
    DB_NAME = "telegram_ticker_alarm_bot"
    TICKER_ALARM_COLLECTION_NAME = "alarm"
    TICKER_QUERY_COLLECTION_NAME = "query"

    def __init__(self) -> None:
        self.client = pymongo.MongoClient("mongodb://localhost:27017/")
        self.db = self.client[self.DB_NAME]

    def insert_ticker_alarm(self, user_id: int, alarm: TickerAlarm) -> None:
        self.db[self.TICKER_ALARM_COLLECTION_NAME].insert_one({"created_at": datetime.datetime.utcnow(), "user_id": user_id, "alarm": alarm.serialize(), "active": True})
    
    def find_active_ticker_alarms_of_user(self, user_id: int) -> None:
        return self.db[self.TICKER_ALARM_COLLECTION_NAME].find({"user_id": user_id, "active": True}, {"alarm": 1, "_id": 0})

    def insert_ticker_query(self, user_id: int, query: TickerQuery, price_dict: Optional[Dict[str, Any]]) -> None:
        self.db[self.TICKER_QUERY_COLLECTION_NAME].insert_one({"created_at": datetime.datetime.utcnow(), "user_id": user_id, "query": query.serialize(), "price_dict": price_dict})

    def update_alarm(self, alarm_id: str, modification: str) -> None:
        q = {"alarm.alarm_id": alarm_id}
        vals = {"$set": {"active": False, "modification": modification, "modified_at": datetime.datetime.utcnow()}}
        self.db[self.TICKER_ALARM_COLLECTION_NAME].find_one_and_update(q, vals)