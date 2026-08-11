"""Common vehicle utilities used by the programs."""
import http.client
import json
import logging
import os
import pathlib
from typing import Tuple, Optional, Union
from yotagrabber import config

vehicleMakeLexus: str = "lexus"
vehicleMakeToyota: str = "toyota"

# Set the HTTP_WIRE_DEBUG environment variable to a non empty value to dump every http request
# and response exchanged with the website.  See enableHttpWireLogging below.
HTTP_WIRE_DEBUG: Optional[str] = os.environ.get("HTTP_WIRE_DEBUG")

httpWireLoggingEnabled: bool = False


def enableHttpWireLogging(force: bool = False) -> bool:
    """
    Dump the complete http exchange (request line, request headers, request body, response status
    and response headers) for every request the requests library makes.

    This is wire level, unlike the resp.request.headers view the DEBUG_ENABLED prints use.  The
    Host header is added below requests by http.client, so it shows up here but not there, and the
    header order here is the order actually sent.  Both matter when comparing a request the website
    rejects against one a browser makes, because the WAF fingerprints on them.

    The response body is not printed, because it is often megabytes of gzipped json, and the caller
    already has it decompressed as resp.text / resp.json().

    Off unless the HTTP_WIRE_DEBUG environment variable is set, or force is passed, because it is
    very noisy over a full multi page run.  Returns whether logging is now on.
    """
    global httpWireLoggingEnabled
    if not (force or HTTP_WIRE_DEBUG):
        return False
    if httpWireLoggingEnabled:
        # basicConfig only takes effect once, and debuglevel is global, so there is nothing to
        # repeat.  Guard anyway so callers can call this freely.
        return True
    http.client.HTTPConnection.debuglevel = 1
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("urllib3").setLevel(logging.DEBUG)
    # http.client writes its dump with print rather than logging, so it lands on stdout while the
    # urllib3 lines land on stderr.  Redirect one of them if you need the two interleaved in a file.
    httpWireLoggingEnabled = True
    print("HTTP wire logging enabled")
    return True


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