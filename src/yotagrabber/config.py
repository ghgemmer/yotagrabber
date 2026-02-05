"""Common configuration items used by the application."""
import json
import pathlib
import random
from typing import List, Dict, Optional

# BASE_DIRECTORY is a Path object
BASE_DIRECTORY: pathlib.Path = pathlib.Path(__file__).parent.resolve()

class DataProvider:
    """Handles lazy loading of resource files to avoid repeated disk I/O."""
    def __init__(self):
        self._user_agents: Optional[List[Dict[str, str]]] = None
        self._zip_codes: Optional[List[str]] = None

    @property
    def user_agents(self) -> List[Dict[str, str]]:
        if self._user_agents is None:
            with open(f"{BASE_DIRECTORY}/data/common_user_agents.json", "r") as f:
                self._user_agents = json.load(f)
        
        # Assert to satisfy type checker that this is no longer None
        assert self._user_agents is not None
        return self._user_agents

    @property
    def zip_codes(self) -> List[str]:
        if self._zip_codes is None:
            with open(f"{BASE_DIRECTORY}/data/zipcodes.txt", "r") as f:
                self._zip_codes = f.read().splitlines()
        
        # Assert to satisfy type checker that this is no longer None
        assert self._zip_codes is not None
        return self._zip_codes

# Create a single instance to be used by the functions
_DATA_PROVIDER = DataProvider()

def random_user_agent() -> str:
    """Choose a user agent from a list of commonly used agents."""
    return random.choice(_DATA_PROVIDER.user_agents)["ua"]

def random_zip_code() -> str:
    """Choose a random zip code from a list of zip codes."""
    return random.choice(_DATA_PROVIDER.zip_codes)