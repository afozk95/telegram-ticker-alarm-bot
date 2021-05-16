from __future__ import annotations
from re import A
from ticker_alarm import TickerAlarm
from typing import Any, Dict, List, Optional, Tuple
from copy import deepcopy
import prettytable as pt
from telegram import ParseMode
from html import escape as html_escape
import pymongo
from price import get_current_ticker_price_from_yahoo_finance


class TickerQuery:
    def __init__(self, ticker: str) -> None:
        self.ticker = ticker

    @staticmethod
    def get_parse_mode(reply_mode: str) -> Optional[ParseMode]:
        assert reply_mode in ["text", "HTML", "MARKDOWN_V2"], f"Unknown reply mode {reply_mode}"
        if reply_mode == "text":
            return None
        elif reply_mode == "HTML":
            return ParseMode.HTML
        elif reply_mode == "MARKDOWN_V2":
            return ParseMode.MARKDOWN_V2

    @staticmethod
    def run_and_get_reply(query: TickerQuery, user_id: int, db: pymongo.database.Database, reply_mode: str = "MARKDOWN_V2") -> Tuple[str, Optional[ParseMode]]:
        price_dict = query.run(user_id, db)
        reply, parse_mode = query.get_reply(price_dict, reply_mode)
        return reply, parse_mode
    
    @staticmethod
    def run_multiple_and_get_reply(query_lst: List[TickerQuery], user_id: int, db: pymongo.database.Database, reply_mode: str = "MARKDOWN_V2") -> Tuple[str, Optional[ParseMode]]:
        price_dicts = TickerQuery.run_multiple(query_lst, user_id, db)
        return TickerQuery.get_reply_multiple(query_lst, price_dicts, reply_mode)

    def get_reply(self, price_dict: Optional[Dict[str, Any]], reply_mode: str) -> Tuple[str, Optional[ParseMode]]:
        assert reply_mode in ["text", "HTML", "MARKDOWN_V2"], f"Unknown reply mode {reply_mode}"
        if reply_mode == "text":
            if price_dict is None:
                return self.get_ticker_query_price_error_text()
            return self.get_ticker_query_message_text(**price_dict), TickerQuery.get_parse_mode(reply_mode)
        else:
            return TickerQuery.get_table_reply([self.ticker], [price_dict], reply_mode), TickerQuery.get_parse_mode(reply_mode)
    
    @staticmethod
    def get_reply_multiple(query_lst: List[TickerQuery], price_dicts: List[Optional[Dict[str, Any]]], reply_mode: str) -> Tuple[str, Optional[ParseMode]]:
        assert reply_mode in ["text", "HTML", "MARKDOWN_V2"], f"Unknown reply mode {reply_mode}"
        if reply_mode == "text":
            replies = [query.get_reply(price_dict, reply_mode) for query, price_dict in zip(query_lst, price_dicts)]
            return "\n".join(replies), TickerQuery.get_parse_mode(reply_mode)
        else:
            return TickerQuery.get_table_reply([query.ticker for query in query_lst], price_dicts, reply_mode), TickerQuery.get_parse_mode(reply_mode)

    def run(self, user_id: int, db: pymongo.database.Database) -> Optional[Dict[str, Any]]:
        price_dict = get_current_ticker_price_from_yahoo_finance(self.ticker)
        db.insert_ticker_query(user_id, self, price_dict)
        return price_dict
        
    @staticmethod
    def run_multiple(query_lst: List[TickerQuery], user_id: int, db: pymongo.database.Database) -> List[Optional[Dict[str, Any]]]:
        price_dicts = [query.run(user_id, db) for query in query_lst]
        return price_dicts

    def get_ticker_query_message_text(self, current_price: float, absolute_price_change: float, percentage_price_change: float) -> str:
        return f"{self.ticker.lower()} {current_price} ({absolute_price_change} {percentage_price_change}%)"

    def get_ticker_query_price_error_text(self) -> str:
        return f"{self.ticker.lower()}: error occurred"

    def serialize(self) -> Dict[str, Any]:
        dct = deepcopy(self.__dict__)
        return dct

    @classmethod
    def deserialize(cls, dct: Dict[str, Any]) -> TickerQuery:
        return cls(**dct)

    @staticmethod
    def get_table_reply(tickers: List[str], price_dicts: List[Optional[Dict[str, Any]]], table_mode: str) -> str:
        table = pt.PrettyTable(["Ticker", "Price", "Change", "% Change"])
        table.align["Ticker"] = "l"
        table.align["Price"] = "r"
        table.align["Change"] = "r"
        table.align["% Change"] = "r"


        for ticker, price_dict in zip(tickers, price_dicts):
            if price_dict is None:
                table.add_row([ticker, "-", "-", "-"])
            else:
                price, abs_change, perc_change = tuple(price_dict[f] for f in ["current_price", "absolute_price_change", "percentage_price_change"])
                table.add_row([ticker, f"{price:.2f}", f"{abs_change:.3f}", f"{perc_change:.3f}"])

        if table_mode == "HTML":
            return f"<pre>{table}</pre>"
        elif table_mode == "MARKDOWN_V2":
            return f"```{table}```"
        else:
            raise ValueError("Unknown table mode {table_mode}, expected 'HTML' or 'MARKDOWN_V2'")
