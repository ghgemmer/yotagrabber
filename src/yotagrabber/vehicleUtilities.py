"""Common vehicle utilities used by the programs."""
import json
import pathlib
from yotagrabber import config

vehicleMakeLexus = "lexus"
vehicleMakeToyota = "toyota"


def getVehicleMakeDealersFullFileName(vehicleMake):
    """
    Get the full path to the dealers file for the passed vehicle make.
    Using dealers.csv with vehicleMake column for all makes.
    """
    filename = pathlib.Path(f"{config.BASE_DIRECTORY}/dealers.csv")
    return filename

def getVehicleMakeRelOutDirNoEndSlash(vehicleMake):
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

def validateVehicleMake(userInputVehicleMake):
    """
    Validate that the passed vehicle make is supported.
    The internal vehicleMake is used internally by the program
    returns tuples of (ok, vehicleMake)
    """
    vehicleMake = None
    passedUserInputVehicleMake = userInputVehicleMake
    ok = False
    if type(userInputVehicleMake) is str:
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