"""Common configuration items used by the application."""
import json
import pathlib
import random
from typing import List, Dict, Any

# BASE_DIRECTORY is a Path object
BASE_DIRECTORY: pathlib.Path = pathlib.Path(__file__).parent.resolve()


def random_user_agent() -> str:
    """Choose a user agent from a list of commonly used agents."""
    with open(f"{BASE_DIRECTORY}/data/common_user_agents.json", "r") as fileh:
        # Type hint for the loaded JSON structure
        user_agents: List[Dict[str, str]] = json.load(fileh)

    random.shuffle(user_agents)
    return user_agents[0]["ua"]


def random_zip_code() -> str:
    """Choose a random zip code from a list of zip codes."""
    with open(f"{BASE_DIRECTORY}/data/zipcodes.txt", "r") as fileh:
        zip_codes: List[str] = fileh.readlines()

    random.shuffle(zip_codes)
    return zip_codes[0].strip()