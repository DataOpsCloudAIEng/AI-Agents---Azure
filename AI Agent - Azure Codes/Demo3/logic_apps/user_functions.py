import json
import datetime
from typing import Any, Callable, Set, Dict, List, Optional

# These are the user-defined functions that can be called by the agent.


def fetch_current_datetime(format: Optional[str] = None) -> str:
    """
    Get the current time as a JSON string, optionally formatted.

    :param format (Optional[str]): The format in which to return the current time. Defaults to None, which uses a standard format.
    :return: The current time in JSON format.
    :rtype: str
    """
    current_time = datetime.datetime.now()

    # Use the provided format if available, else use a default format
    if format:
        time_format = format
    else:
        time_format = "%Y-%m-%d %H:%M:%S"

    time_json = json.dumps({"current_time": current_time.strftime(time_format)})
    return time_json



# Example User Input for Each Function
# 1. Fetch Current DateTime
#    User Input: "What is the current date and time?"
#    User Input: "What is the current date and time in '%Y-%m-%d %H:%M:%S' format?"

# Statically defined user functions for fast reference
user_functions: Set[Callable[..., Any]] = {
    fetch_current_datetime
}