"""Common vehicle utilities used by the programs."""
import json
import pathlib
from yotagrabber import config

vehicleMakeLexus = "lexus"
vehicleMakeToyota = "toyota"


def getVehicleMakeDealersFullFileName(vehicleMake):
    # returns the full filename as a pathlib.Path of the dealers csv file for that internal vehicleMake
    # Each vehicle make has its oww dealer file
    filename = pathlib.Path(f"{config.BASE_DIRECTORY}/data/dealers_{vehicleMake}.csv")
    if vehicleMake == "toyota":
        # special case to retain prior behavior of toyota using dealers.csv filename
        filename = pathlib.Path(f"{config.BASE_DIRECTORY}/data/dealers.csv")
    return filename

def getVehicleMakeRelOutDirNoEndSlash(vehicleMake):
    # gets the relative output dir as a str type with no ending slash from the validated vehicle make
    outputDir = "output/" + vehicleMake
    if vehicleMake == "toyota":
        # special case to retain prior behavior of toyota make inventory directly in the root output
        outputDir = "output"
    return outputDir

def validateVehicleMake(userInputVehicleMake):
    #Takes the user input vehicle Make and validates and returns an internal vehicleMake
    #The internal vehicleMake is used internally by the program
    #returns tuple of (ok, vehicleMake)
    vehicleMake = None
    passedUserInputVehicleMake = userInputVehicleMake
    ok = False
    if type(userInputVehicleMake) == str:
        userInputVehicleMake = userInputVehicleMake.upper()
    if userInputVehicleMake == "LEXUS":
        vehicleMake = vehicleMakeLexus
        ok = True
    elif userInputVehicleMake in ["", None, "TOYOTA"]:
        # Toyota
        vehicleMake = vehicleMakeToyota
        ok = True
    if not ok:
        print(passedUserInputVehicleMake, "is not a valid User Input Vehicle Make (like Lexus, Toyota, blank)")
    return (ok, vehicleMake)
