from typing import Any, Union
from pathlib import Path
import json


def read_json(path: Union[Path, str]) -> Any:
    with open(path, "r") as f:
        json_object = json.load(f)
    return json_object


def read_token_from_bot_info(path: Union[Path, str]) -> str:
    bot_info = read_json(path)
    token = bot_info.get("token", None)

    if token is None:
        raise ValueError(f"Missing 'token' field in bot info file in {path}")

    return token


if __name__ == "__main__":
    read_token_from_bot_info("bot_info.json")
