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
    Get the relative output directory (no ending slash) that holds the output files.
    Returns path relative to the src/ directory (typical working directory).

    Every vehicle make writes into the one output directory.  Makes are told apart by a file
    name prefix (see getOutputFileNamePrefix) rather than by a per make subdirectory.
    """
    return "./output"

def getOutputFileNamePrefix(vehicleMake: str) -> str:
    """
    Return the prefix to put on output file names that are not already model specific.

    Toyota gets no prefix so that its existing output files keep their current names.  Any
    other make gets a prefix so its files sit alongside toyota's in the output directory
    without colliding.  Per model output files do not need this because toyota model codes
    are lowercase names and lexus model codes are uppercase series codes, so they never clash.
    """
    if vehicleMake == vehicleMakeToyota:
        return ""
    return vehicleMake + "_"

def getModelsFileName(vehicleMake: str) -> str:
    """Return the name of the curated models file for the vehicle make."""
    return getVehicleMakeRelOutDirNoEndSlash(vehicleMake) + "/" + getOutputFileNamePrefix(vehicleMake) + "models.json"

def getModelsRawFileName(vehicleMake: str) -> str:
    """Return the name of the raw models file for the vehicle make."""
    return getVehicleMakeRelOutDirNoEndSlash(vehicleMake) + "/" + getOutputFileNamePrefix(vehicleMake) + "models_raw.json"

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