#!/usr/bin/env python3
"""
On demand search for every Lexus RX 350h at the dealers in a given list of zipcodes.

    py searchRx350hByZipcodes.py                            the built in zipcode list, collect fresh
    py searchRx350hByZipcodes.py 60173 60559 60642 60025    those zipcodes instead
    py searchRx350hByZipcodes.py --use-last-data            search the last collected inventory, no queries
    py searchRx350hByZipcodes.py 60025 --radius 40          also dealers within 40 miles of a listed zip
    py searchRx350hByZipcodes.py --trim LUXURY --available-only

Run it from the src directory with the virtual environment activated.  It sets VEHICLE_MAKE=lexus
and MODEL=RXh itself, so no environment variables need setting first.

Matches are printed and written to a csv (see --out), grouped in the order the zipcodes were given.

What it searches
    MODEL=RXh is the RX 350h series, which is exactly the RX hybrid, so there is nothing to strip
    out of it.  By default every RX 350h is kept regardless of trim, colour or interior, and the
    only filter is the dealer's zipcode.  --trim and --interior narrow it further when wanted.

    A zipcode matches on the DEALER's zipcode, not on a radius, because the point of this search is
    to ask "what do these specific dealers have".  The four built in zipcodes are each the zipcode
    of one Lexus dealer.  Pass --radius to widen it to dealers near those zipcodes as well, which
    needs the zipcode to be resolvable to a location out of the dealers file (see resolveZipCoords).

Two data sources
    Default: query the website now for a complete national RXh inventory.  That takes a while and
    deliberately writes NONE of the tracked output files, so an on demand search never disturbs the
    parquet, change history and sold files that the nightly runs and searchForVehicles.py maintain.
    --use-last-data: reuse output/RXh_Lastraw.parquet from the last collection instead.  Instant and
    makes no requests, but only as current as that file (the run date is printed).

    A national collection is used even though only a few zipcodes are wanted, because one Lexus
    query already covers the whole country and the per zipcode search would need one collection per
    zipcode.  See Invocation.txt for the single locale MODEL_SEARCH_ZIPCODE alternative.

Two things this search cannot see, both from Invocation.txt
    Lexus does not publish factory to port vehicles to the inventory API at all, so a match here is
    always already at a port or at a dealer.  For the earlier "In Production" vehicles, whose port
    installed options can still be changed, use lexusDealerSiteInventory.py (DealerOn dealers only).
    Also, numberRawVehiclesMissing is not trustworthy on Lexus because the pagination totalRecords
    it is computed against is the whole RX family's count, not RXh's.  It is printed but a non zero
    value does not by itself mean vehicles were missed.

This file also works unchanged as a searchForVehicles.py userMatchCriteriaFilterFileName, since it
supplies filterDataFrame and criteriaPrintableString at module level and does its environment
setting and heavy imports inside main().
"""
import argparse
import math
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

# The lexus series code for the RX 350h.  Case sensitive: "RXH" returns nothing.
VEHICLE_MAKE: str = "lexus"
MODEL_CODE: str = "RXh"

# What to match in the Model column.  MODEL=RXh leaves the marketing name whole (vehicles.py only
# strips a "<title> " prefix and "RXh " is not one), so the full "RX 350h" is present here.
MODEL_TEXT: str = "RX 350h"

# The zipcodes searched when none are given on the command line.  Each of these is the zipcode of
# one Lexus dealer in the Chicago area:
#   60173  Woodfield Lexus, Schaumburg
#   60559  McGrath Lexus of Westmont, Westmont
#   60642  McGrath Lexus of Chicago, Chicago
#   60025  Fields Lexus Glenview, Glenview
ZIPCODES: List[str] = ["60173", "60559", "60642", "60025"]

DEFAULT_OUTPUT_FILE: str = "output/RXh_ByZipcode.csv"

# Columns printed to the console.  The csv written out keeps every column.
CONSOLE_COLUMNS: List[str] = [
    "Dealer Zip", "Miles From Zip", "Year", "Model", "Color", "Int Color", "Selling Price",
    "Total MSRP", "Markup", "Shipping Status", "Pre-Sold", "Hold Status", "eta.currFromDate",
    "eta.currToDate", "Dealer", "Dealer City", "VIN",
]


def normalizeText(value: Any) -> str:
    """Lowercase with runs of whitespace collapsed, so a match does not turn on spacing or case."""
    if not isinstance(value, str):
        return ""
    return " ".join(value.split()).casefold()


def normalizeZip(value: Any) -> str:
    """
    Return a zipcode as a 5 character string, or "" if there is not one.

    The Dealer Zip column arrives as int64, so a New England zipcode like 06810 has already lost its
    leading zero by the time it gets here and would never match the string "06810".  Zero padding
    both sides of the comparison is what makes those zipcodes work.  A ZIP+4 is cut back to the
    leading 5 so it still matches the 5 digit zipcode it belongs to.
    """
    if value is None:
        return ""
    if isinstance(value, float):
        if math.isnan(value):
            return ""
        value = int(value)
    text = str(value).strip()
    if not text:
        return ""
    # Drop a "-1234" ZIP+4 suffix, then keep digits only.
    text = text.split("-")[0]
    digits = "".join(ch for ch in text if ch.isdigit())
    if not digits:
        return ""
    return digits[:5].zfill(5)


def milesBetween(lat1: Any, long1: Any, lat2: Any, long2: Any) -> Optional[float]:
    """Great circle miles between two points, or None if any coordinate is missing."""
    try:
        lat1F, long1F, lat2F, long2F = float(lat1), float(long1), float(lat2), float(long2)
    except (TypeError, ValueError):
        return None
    if any(math.isnan(x) for x in (lat1F, long1F, lat2F, long2F)):
        return None
    # Same formula as the Excel one vehicles.py puts in the DistanceFromCenter column, computed here
    # so the number is usable outside Excel and survives being filtered and re-sorted.
    earthRadiusKm = 6371.0
    kmPerMile = 0.621371
    lat1R, lat2R = math.radians(90 - lat1F), math.radians(90 - lat2F)
    deltaLongR = math.radians(long1F - long2F)
    cosine = (math.cos(lat1R) * math.cos(lat2R)) + (math.sin(lat1R) * math.sin(lat2R) * math.cos(deltaLongR))
    # Clamp so floating point noise just past 1 does not make acos raise.
    cosine = max(-1.0, min(1.0, cosine))
    return round(math.acos(cosine) * earthRadiusKm * kmPerMile, 1)


def resolveZipCoords(zipCodes: List[str]) -> Dict[str, Tuple[float, float]]:
    """
    Map each zipcode to a latitude and longitude, taken from any dealer sitting in that zipcode.

    There is no zipcode to coordinate table in this project, but the dealers file has a location for
    every dealer along with its zipcode, and that is close enough to anchor a radius on.  Dealers of
    either make count, since a Toyota dealer in the wanted zipcode locates that zipcode just as well
    as a Lexus one would.  A zipcode with no dealer at all cannot be resolved and is reported by the
    caller rather than silently contributing nothing.
    """
    coords: Dict[str, Tuple[float, float]] = {}
    # vehicles.py reads this same file by this same path.  Note it does NOT use
    # vehicleUtilities.getVehicleMakeDealersFullFileName, which is missing the data directory.
    dealersFile = Path(__file__).parent.resolve() / "yotagrabber" / "data" / "dealers.csv"
    if not dealersFile.is_file():
        print("Warning: could not find", dealersFile, "so --radius cannot resolve any zipcode.")
        return coords
    dealers = pd.read_csv(dealersFile, dtype={"zip": "str"})
    dealers["zipNormalized"] = dealers["zip"].map(normalizeZip)
    wanted = set(zipCodes)
    for _, row in dealers.iterrows():
        zipNormalized = row["zipNormalized"]
        if (zipNormalized in wanted) and (zipNormalized not in coords):
            lat, long = row.get("lat"), row.get("long")
            try:
                coords[zipNormalized] = (float(lat), float(long))
            except (TypeError, ValueError):
                continue
    return coords


def addZipDistanceColumns(df: pd.DataFrame, zipCodes: List[str],
                          zipCoords: Dict[str, Tuple[float, float]]) -> pd.DataFrame:
    """
    Add "Nearest Zip" and "Miles From Zip", measured from the closest of the searched zipcodes.

    Distance is to the searched zipcode rather than to the collection's centre, because the centre
    is wherever the national collection happened to be anchored and means nothing to this search.
    A dealer sitting in one of the searched zipcodes gets that zipcode at 0 miles.
    """
    df = df.copy(deep=True)
    if df.empty:
        df["Nearest Zip"] = pd.Series(dtype="object")
        df["Miles From Zip"] = pd.Series(dtype="float64")
        return df
    nearestZips: List[Any] = []
    milesFromZip: List[Any] = []
    for _, row in df.iterrows():
        dealerZip = normalizeZip(row.get("Dealer Zip"))
        if dealerZip in zipCodes:
            nearestZips.append(dealerZip)
            milesFromZip.append(0.0)
            continue
        best: Optional[Tuple[float, str]] = None
        for zipCode in zipCodes:
            if zipCode not in zipCoords:
                continue
            zipLat, zipLong = zipCoords[zipCode]
            miles = milesBetween(row.get("Dealer Lat"), row.get("Dealer Long"), zipLat, zipLong)
            if (miles is not None) and ((best is None) or (miles < best[0])):
                best = (miles, zipCode)
        nearestZips.append(best[1] if best else None)
        milesFromZip.append(best[0] if best else None)
    df["Nearest Zip"] = nearestZips
    df["Miles From Zip"] = milesFromZip
    return df


def filterDataFrame(
    df: pd.DataFrame,
    zipCodes: Optional[List[str]] = None,
    radiusMiles: Optional[float] = None,
    zipCoords: Optional[Dict[str, Tuple[float, float]]] = None,
    trims: Optional[List[str]] = None,
    interior: Optional[str] = None,
    availableOnly: bool = False,
) -> pd.DataFrame:
    """
    Keep the RX 350h vehicles at dealers in the wanted zipcodes.

    zipCodes None means the built in list.  radiusMiles None keeps only dealers whose own zipcode is
    in the list, otherwise dealers within that many miles of a listed zipcode are kept too.  trims
    None and interior None keep every trim and interior, which is the default for this search since
    the question it answers is what these dealers have.  availableOnly drops pre-sold and held
    vehicles the way the supplied Rx350hUserMatchCriteriaFilter.py does.
    """
    if df.empty:
        return df
    zipsToUse = [normalizeZip(z) for z in (ZIPCODES if zipCodes is None else zipCodes)]
    zipsToUse = [z for z in zipsToUse if z]

    modelText = df["Model"].fillna("").map(normalizeText)
    mask = modelText.str.contains(normalizeText(MODEL_TEXT), regex=False)

    if zipsToUse:
        dealerZips = df["Dealer Zip"].map(normalizeZip)
        zipMask = dealerZips.isin(zipsToUse)
        if radiusMiles is not None:
            coords = zipCoords if zipCoords is not None else resolveZipCoords(zipsToUse)
            withinRadius = []
            for _, row in df.iterrows():
                nearest = None
                for zipCode in zipsToUse:
                    if zipCode not in coords:
                        continue
                    zipLat, zipLong = coords[zipCode]
                    miles = milesBetween(row.get("Dealer Lat"), row.get("Dealer Long"), zipLat, zipLong)
                    if (miles is not None) and ((nearest is None) or (miles < nearest)):
                        nearest = miles
                withinRadius.append((nearest is not None) and (nearest <= radiusMiles))
            zipMask = zipMask | pd.Series(withinRadius, index=df.index)
        mask &= zipMask

    if trims:
        # Any of the given trims, so --trim LUXURY --trim PREMIUM+ widens rather than narrows.
        trimMask = pd.Series([False] * len(df), index=df.index)
        for trim in trims:
            trimMask |= modelText.str.contains(normalizeText(trim), regex=False)
        mask &= trimMask
    if interior:
        mask &= df["Int Color"].fillna("").map(normalizeText).str.contains(normalizeText(interior), regex=False)
    if availableOnly:
        mask &= (df["Pre-Sold"] != True)  # noqa: E712  - the column holds True/False/None, not only booleans
        mask &= df["Hold Status"].isin(["Available", None, "", "DealerHold"]) | df["Hold Status"].isna()
    return df[mask]


def criteriaPrintableString() -> str:
    """Return a printable description of the match criteria (searchForVehicles.py calls this)."""
    return ('Match criteria is: Model contains "' + MODEL_TEXT + '" and Dealer Zip in '
            + str(ZIPCODES))


def reportWhyNothingMatched(df: pd.DataFrame, zipCodes: List[str]) -> None:
    """
    Print what the data does contain when the search comes back empty.

    A zipcode with no dealer in it looks exactly like a dealer with no inventory, so show which of
    the searched zipcodes are present in the collected data at all rather than leaving the user to
    guess whether they mistyped one.
    """
    print("\nNo matches.  Where the criteria dropped everything:")
    print("  vehicles in the collected inventory:", len(df))
    if df.empty:
        return

    modelText = df["Model"].fillna("").map(normalizeText)
    modelMask = modelText.str.contains(normalizeText(MODEL_TEXT), regex=False)
    print("  after the Model criteria (" + MODEL_TEXT + "):", int(modelMask.sum()))
    if not modelMask.any():
        print("  Model values present:", ", ".join(sorted(set(df["Model"].dropna()))))
        return

    afterModel = df[modelMask]
    dealerZips = afterModel["Dealer Zip"].map(normalizeZip)
    print("  after the Dealer Zip criteria:", int(dealerZips.isin(zipCodes).sum()))
    for zipCode in zipCodes:
        atZip = int((dealerZips == zipCode).sum())
        print("     ", zipCode, ":", atZip, "vehicles")
    # These are the busiest zipcodes anywhere in the country, not ones near the searched zipcodes.
    # They are here to show the zipcode column really is populated and what its values look like,
    # so a mistyped zipcode is distinguishable from a dealer that genuinely has nothing.
    print("  Zipcodes holding the most inventory anywhere (top 10), for comparison:")
    for name, count in dealerZips.value_counts().head(10).items():
        print("     ", name, ":", count)


def collectInventoryDf(useLastData: bool) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Return the RXh inventory as a csv style dataframe, along with the status of how it was obtained.

    The yotagrabber import happens here rather than at module level because vehicles.py reads MODEL
    and VEHICLE_MAKE once, at import time, so they have to be in the environment before it is
    imported.  Keeping it here also keeps this file importable as a match criteria filter.
    """
    os.environ["VEHICLE_MAKE"] = VEHICLE_MAKE
    os.environ["MODEL"] = MODEL_CODE
    sys.path.insert(0, str(Path(__file__).parent.resolve()))
    from yotagrabber import vehicles  # noqa: E402  - deliberately imported after the environment is set

    if useLastData:
        rawParquetExists, statusFileExists, rawDf, status = vehicles.readLastParquetDf()
        if not rawParquetExists:
            print("Error: no", vehicles.getLastRawParquetFileName(), "to search.")
            print("Run this without --use-last-data once to collect inventory from the website.")
            sys.exit(1)
        if not statusFileExists:
            print("Warning: the status file for that parquet is missing, so how complete it is is unknown.")
    else:
        print("Collecting", MODEL_CODE, "inventory from the website.  This takes a while.")
        rawDf, status = vehicles.get_all_pages()
        if not status.get("completedOk"):
            # Keep going and search what did come back.  A partial collection still answers the
            # question for the vehicles it did reach, and the incompleteness is reported below.
            print("Warning: the collection did not complete cleanly:", status.get("completionMsg") or "(no message)")
        if status.get("lossyRun"):
            # A page never came back even after the recovery pass, so a dealer that looks empty here
            # may simply have been on the page that was lost.
            print("Warning: this collection was lossy, so an empty result for a dealer is not proof "
                  "that the dealer has nothing.")

    return (vehicles.transformRawDfToCsvStyleDf(rawDf), status)


def parseArgs(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Search Lexus RX 350h inventory at the dealers in a list of zipcodes.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("zipcodes", nargs="*", default=None, metavar="ZIP",
                        help="dealer zipcodes to search, default " + " ".join(ZIPCODES))
    parser.add_argument("--use-last-data", action="store_true",
                        help="search output/%s_Lastraw.parquet instead of querying the website" % MODEL_CODE)
    parser.add_argument("--radius", type=float, default=None, metavar="MILES",
                        help="also keep dealers within this many miles of a listed zipcode, "
                             "instead of only dealers whose own zipcode is listed")
    parser.add_argument("--trim", action="append", default=None, metavar="TEXT",
                        help="keep only this trim, repeatable (e.g. --trim LUXURY --trim PREMIUM+)")
    parser.add_argument("--interior", default=None, metavar="TEXT",
                        help="keep only interiors containing this text")
    parser.add_argument("--available-only", action="store_true",
                        help="drop pre-sold and held vehicles")
    parser.add_argument("--out", default=DEFAULT_OUTPUT_FILE,
                        help="csv file to write the matches to")
    args = parser.parse_args(argv)
    if args.radius is not None and args.radius <= 0:
        parser.error("--radius must be a positive number of miles")
    return args


def main(argv: Optional[List[str]] = None) -> int:
    args = parseArgs(argv)

    # vehicles.py reads and writes its files through paths relative to the working directory
    # ("./output/..."), so run from this file's directory whatever directory it was invoked from.
    os.chdir(Path(__file__).parent.resolve())

    zipCodes = [normalizeZip(z) for z in (args.zipcodes if args.zipcodes else ZIPCODES)]
    badZips = [given for given, normalized in zip(args.zipcodes if args.zipcodes else ZIPCODES, zipCodes)
               if not normalized]
    if badZips:
        print("Error: these do not look like zipcodes:", ", ".join(str(z) for z in badZips))
        return 1

    zipCoords: Dict[str, Tuple[float, float]] = {}
    if args.radius is not None:
        zipCoords = resolveZipCoords(zipCodes)
        unresolved = [z for z in zipCodes if z not in zipCoords]
        if unresolved:
            print("Warning: no dealer sits in", ", ".join(unresolved),
                  "so those zipcodes cannot anchor a radius and will only match exactly.")

    print("Searching for", MODEL_TEXT, "at dealers in:", ", ".join(zipCodes))
    if args.radius is not None:
        print("  plus any dealer within", args.radius, "miles of one of them")
    print("  trim:", ", ".join(args.trim) if args.trim else "(any)")
    print("  interior:", args.interior or "(any)")
    print()

    df, status = collectInventoryDf(args.use_last_data)
    print("\nInventory searched:", len(df), "vehicles, collected", status.get("date", "(unknown date)"))
    missing = status.get("numberRawVehiclesMissing", 0)
    if missing:
        print("Note: the run reports", missing, "vehicles missing.  On lexus that count is measured "
              "against the whole RX family's record count, so it is not reliable evidence of a gap.")

    matches = filterDataFrame(df, zipCodes=zipCodes, radiusMiles=args.radius, zipCoords=zipCoords,
                              trims=args.trim, interior=args.interior,
                              availableOnly=args.available_only)
    if matches.empty:
        reportWhyNothingMatched(df, zipCodes)
        return 0

    matches = addZipDistanceColumns(matches, zipCodes, zipCoords)
    # Group in the order the zipcodes were given rather than alphabetically, so the output reads in
    # the order that was asked for.
    zipOrder = {zipCode: position for position, zipCode in enumerate(zipCodes)}
    matches["_zipOrder"] = matches["Nearest Zip"].map(lambda z: zipOrder.get(z, len(zipCodes)))
    matches = matches.sort_values(by=["_zipOrder", "Miles From Zip", "Selling Price"],
                                 na_position="last")
    matches = matches.drop(columns=["_zipOrder"]).reset_index(drop=True)
    # The stale first row Excel formula is meaningless once the rows have been filtered and re-sorted.
    if "DistanceFromCenter" in matches.columns:
        matches = matches.drop(columns=["DistanceFromCenter"])

    print("\n" + "=" * 100)
    print(len(matches), "matching vehicles")
    print("=" * 100)
    printable = matches[[c for c in CONSOLE_COLUMNS if c in matches.columns]]
    with pd.option_context("display.max_rows", None, "display.width", 250, "display.max_colwidth", 40):
        print(printable.to_string(index=False))

    print("\nBy dealer:")
    for (dealerZip, dealer), count in matches.groupby(["Dealer Zip", "Dealer"]).size().items():
        print("   ", normalizeZip(dealerZip), dealer, count)
    print("\nBy trim:")
    for trim, count in matches["Model"].value_counts().items():
        print("   ", trim, count)
    prices = pd.to_numeric(matches["Selling Price"], errors="coerce").dropna()
    if len(prices):
        print("\nSelling price: low", f"{prices.min():,.0f}", " high", f"{prices.max():,.0f}",
              " median", f"{prices.median():,.0f}")

    outPath = Path(args.out)
    if outPath.parent and not outPath.parent.exists():
        outPath.parent.mkdir(parents=True, exist_ok=True)
    try:
        matches.to_csv(outPath, index=False)
    except PermissionError:
        # On windows this is almost always the csv being open in Excel.
        print("\nError: could not write", outPath, "because another program holds it open (Excel keeps "
              "a lock on an open csv).  Close it and run again, or pass --out with another name.")
        return 1
    print("\nWrote", len(matches), "matches to", outPath.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
