"""Common vehicle utilities used by the programs."""
import json
import pathlib
from typing import Tuple, Optional, Union
from yotagrabber import config

vehicleMakeLexus: str = "lexus"
vehicleMakeToyota: str = "toyota"


def getVehicleMakeDealersFullFileName(vehicleMake: str) -> pathlib.Path:
    """
    Get the full path to the dealers file for the passed vehicle make.
    Using dealers.csv with vehicleMake column for all makes.
    """
    filename = pathlib.Path(f"{config.BASE_DIRECTORY}/dealers.csv")
    return filename

def getVehicleMakeRelOutDirNoEndSlash(vehicleMake: str) -> str:
    """
    Get the relative output directory (no ending slash) for the passed vehicle make.
    Returns path relative to the src/ directory (typical working directory).
    Need to go up one level to get to repo root, then into output/
    """
    if vehicleMake == "toyota":
        outputDir = "./output"
    else:
        # For Lexus and other makes, use subdirectory
        outputDir = f"./output/{vehicleMake}"
    return outputDir

def validateVehicleMake(userInputVehicleMake: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    Validate that the passed vehicle make is supported.
    The internal vehicleMake is used internally by the program
    returns tuples of (ok, vehicleMake)
    """
    vehicleMake: Optional[str] = None
    passedUserInputVehicleMake = userInputVehicleMake
    ok = False
    if isinstance(userInputVehicleMake, str):
        userInputVehicleMake = userInputVehicleMake.upper()
    
    if userInputVehicleMake == "LEXUS":
        vehicleMake = vehicleMakeLexus
        ok = True
    elif userInputVehicleMake in ("", None, "TOYOTA"):
        # Toyota
        vehicleMake = vehicleMakeToyota
        ok = True
        
    if not ok:
        print(f"Error: Unsupported vehicle make '{passedUserInputVehicleMake}'.  Supported makes are 'toyota' and 'lexus'.")
    return (ok, vehicleMake)