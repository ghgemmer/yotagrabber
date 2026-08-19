#!/usr/bin/env python3
"""
On demand search for Lexus RX 350h LUXURY awd vehicles with the Macadamia semi-aniline leather
and Ash Bamboo trim interior, at midwest dealers.

    py searchRx350hLuxuryMidwest.py                    collect fresh inventory, then search
    py searchRx350hLuxuryMidwest.py --use-last-data    search the last collected inventory, no queries
    py searchRx350hLuxuryMidwest.py --zip 52402 --radius 600      fresh, but only around that zip
    py searchRx350hLuxuryMidwest.py --states IL WI IA MN          override the states searched
    py searchRx350hLuxuryMidwest.py --any-interior --available-only

Run it from the src directory with the virtual environment activated.  It sets VEHICLE_MAKE=lexus
and MODEL=RXh itself, so no environment variables need setting first.

Matches are printed and written to a csv (see --out), closest dealer first.

What it searches
    MODEL=RXh is the RX 350h series, which is exactly the RX hybrid, so there is nothing to strip
    out of it.  Within it this keeps the LUXURY trim, drivetrain awd (the only one the RX 350h comes
    in) and the one interior named below, at dealers in the 12 census midwest states.  All of the
    values it matches on are literals at the top of this file, so they are easy to change.

Two data sources
    Default: query the website now for a complete national RXh inventory.  That takes a while (a
    measured run was around 20 pages with a WAF bypass refresh every 4 minutes) and deliberately
    writes NONE of the tracked output files, so an on demand search never disturbs the parquet,
    change history and sold files that the nightly runs and searchForVehicles.py maintain.
    --use-last-data: reuse output/lexus/RXh_Lastraw.parquet from the last collection instead.  Instant and
    makes no requests, but only as current as that file (the run date is printed).

    To collect inventory AND update the tracked files, that is the existing command, not this one:
        set VEHICLE_MAKE=lexus & set MODEL=RXh & py -c "from yotagrabber import vehicles; vehicles.update_vehicles()"

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
# strips a "<title> " prefix and "RXh " is not one), so the full "RX 350h" is present here.  Lexus
# returns the drivetrain lowercase, so "AWD" would match nothing.
MODEL_TEXT: str = "RX 350h"
TRIM_TEXT: str = "LUXURY"
DRIVETRAIN_TEXT: str = "awd"

# The interior, exactly as the website names it.  Note the plain "Macadamia leather and Ash Bamboo
# trim" is a DIFFERENT interior and is not wanted here, which is why this matches the whole string
# rather than just "Macadamia".
INTERIOR_TEXT: str = "Macadamia semi-aniline leather and Ash Bamboo trim"

# The census bureau midwest region.  ND and SD have no lexus dealers, so they never contribute, but
# they are left in so the region is the standard one rather than a guess.
MIDWEST_STATES: List[str] = ["IL", "IN", "IA", "KS", "MI", "MN", "MO", "NE", "ND", "OH", "SD", "WI"]

DEFAULT_OUTPUT_FILE: str = f"output/{VEHICLE_MAKE}/RXh_LUXURY_Macadamia_Midwest.csv"

# Columns printed to the console.  The csv written out keeps every column.
CONSOLE_COLUMNS: List[str] = [
    "Miles From Center", "Year", "Model", "Color", "Int Color", "Selling Price", "Total MSRP",
    "Markup", "Shipping Status", "Pre-Sold", "Hold Status", "eta.currFromDate", "eta.currToDate",
    "Dealer", "Dealer City", "Dealer State", "VIN",
]


def normalizeText(value: Any) -> str:
    """Lowercase with runs of whitespace collapsed, so a match does not turn on spacing or case."""
    if not isinstance(value, str):
        return ""
    return " ".join(value.split()).casefold()


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


def addMilesFromCenter(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add a numeric Miles From Center column from the dealer and center coordinates already in the df.

    vehicles.py leaves DistanceFromCenter holding an Excel formula in the first row only, and that
    formula's cell references are for its own column layout, so it does not survive filtering.  This
    replaces it with a real number on every row.
    """
    df = df.copy(deep=True)
    if df.empty:
        df["Miles From Center"] = pd.Series(dtype="float64")
        return df
    df["Miles From Center"] = [
        milesBetween(row.get("Dealer Lat"), row.get("Dealer Long"), row.get("CenterLat"), row.get("CenterLong"))
        for _, row in df.iterrows()
    ]
    return df


def filterDataFrame(
    df: pd.DataFrame,
    states: Optional[List[str]] = None,
    interior: Optional[str] = INTERIOR_TEXT,
    availableOnly: bool = False,
) -> pd.DataFrame:
    """
    Keep the RX 350h LUXURY awd vehicles with the wanted interior at dealers in the wanted states.

    states None means the census midwest states, an empty list means do not filter on state at all.
    interior None means keep every interior.  availableOnly drops pre-sold and held vehicles the way
    the supplied Rx350hUserMatchCriteriaFilter.py does.
    """
    if df.empty:
        return df
    statesToUse = MIDWEST_STATES if states is None else states

    modelText = df["Model"].fillna("").map(normalizeText)
    mask = (
        modelText.str.contains(normalizeText(MODEL_TEXT), regex=False)
        & modelText.str.contains(normalizeText(TRIM_TEXT), regex=False)
        & modelText.str.contains(normalizeText(DRIVETRAIN_TEXT), regex=False)
    )
    if interior:
        mask &= df["Int Color"].fillna("").map(normalizeText) == normalizeText(interior)
    if statesToUse:
        mask &= df["Dealer State"].fillna("").str.strip().str.upper().isin([s.upper() for s in statesToUse])
    if availableOnly:
        mask &= (df["Pre-Sold"] != True)  # noqa: E712  - the column holds True/False/None, not only booleans
        mask &= df["Hold Status"].isin(["Available", None, "", "DealerHold"]) | df["Hold Status"].isna()
    return df[mask]


def criteriaPrintableString() -> str:
    """Return a printable description of the match criteria (searchForVehicles.py calls this)."""
    return (
        'Match criteria is: Model contains "' + MODEL_TEXT + '" and "' + TRIM_TEXT + '" and "' + DRIVETRAIN_TEXT
        + '", Int Color == "' + INTERIOR_TEXT + '", Dealer State in ' + str(MIDWEST_STATES)
    )


def reportWhyNothingMatched(df: pd.DataFrame, states: List[str], interior: Optional[str]) -> None:
    """
    Print what the data does contain when the search comes back empty.

    The trim and interior names are long literals that Lexus can rename between model years, and a
    renamed one looks exactly like no inventory.  So show the values actually present, narrowing one
    criterion at a time, rather than leaving the user to guess which one failed.
    """
    print("\nNo matches.  Where the criteria dropped everything:")
    print("  vehicles in the collected inventory:", len(df))
    if df.empty:
        return

    modelText = df["Model"].fillna("").map(normalizeText)
    trimMask = (
        modelText.str.contains(normalizeText(MODEL_TEXT), regex=False)
        & modelText.str.contains(normalizeText(TRIM_TEXT), regex=False)
        & modelText.str.contains(normalizeText(DRIVETRAIN_TEXT), regex=False)
    )
    print("  after the Model criteria (" + MODEL_TEXT, TRIM_TEXT, DRIVETRAIN_TEXT + "):", int(trimMask.sum()))
    if not trimMask.any():
        print("  Model values present:", ", ".join(sorted(set(df["Model"].dropna()))))
        return

    afterTrim = df[trimMask]
    if interior:
        interiorMask = afterTrim["Int Color"].fillna("").map(normalizeText) == normalizeText(interior)
        print("  after the Int Color criteria:", int(interiorMask.sum()))
        if not interiorMask.any():
            print("  Int Color values present on those vehicles:")
            for name, count in afterTrim["Int Color"].value_counts().items():
                print("     ", count, "x", name)
            return
        afterTrim = afterTrim[interiorMask]

    if states:
        print("  after the Dealer State criteria:", int(afterTrim["Dealer State"].fillna("").str.upper().isin(states).sum()))
        print("  states those vehicles are in:")
        for name, count in afterTrim["Dealer State"].value_counts().items():
            print("     ", count, "x", name)


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

    return (vehicles.transformRawDfToCsvStyleDf(rawDf), status)


def parseArgs(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Search Lexus RX 350h LUXURY awd inventory with the Macadamia semi-aniline "
                    "leather and Ash Bamboo trim interior at midwest dealers.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--use-last-data", action="store_true",
                        help="search output/%s/%s_Lastraw.parquet instead of querying the website" % (VEHICLE_MAKE, MODEL_CODE))
    parser.add_argument("--zip", dest="zipCode", default=None,
                        help="collect only around this zip code instead of nationally (needs --radius)")
    parser.add_argument("--radius", default=None,
                        help="miles around --zip to collect")
    parser.add_argument("--states", nargs="*", default=None, metavar="ST",
                        help="dealer states to keep, default the census midwest states. "
                             "Pass --states with no values to search every state")
    parser.add_argument("--any-interior", action="store_true",
                        help="keep every interior instead of only the Macadamia semi-aniline one")
    parser.add_argument("--available-only", action="store_true",
                        help="drop pre-sold and held vehicles")
    parser.add_argument("--out", default=DEFAULT_OUTPUT_FILE,
                        help="csv file to write the matches to")
    args = parser.parse_args(argv)
    if bool(args.zipCode) != bool(args.radius):
        parser.error("--zip and --radius must be given together")
    if args.zipCode and args.use_last_data:
        parser.error("--zip/--radius only apply to a fresh collection, not to --use-last-data")
    return args


def main(argv: Optional[List[str]] = None) -> int:
    args = parseArgs(argv)

    # vehicles.py reads and writes its files through paths relative to the working directory
    # ("./output/..."), so run from this file's directory whatever directory it was invoked from.
    os.chdir(Path(__file__).parent.resolve())

    if args.zipCode:
        # These are the environment variables vehicles.py already supports for a single locale
        # search.  A midwest sized radius is far quicker than a national collection.
        os.environ["MODEL_SEARCH_ZIPCODE"] = args.zipCode
        os.environ["MODEL_SEARCH_RADIUS"] = str(args.radius)
        print("Collecting only within", args.radius, "miles of", args.zipCode)

    states = MIDWEST_STATES if args.states is None else [s.upper() for s in args.states]
    interior = None if args.any_interior else INTERIOR_TEXT

    print("Searching for", MODEL_TEXT, TRIM_TEXT, DRIVETRAIN_TEXT)
    print("  interior:", interior or "(any)")
    print("  dealer states:", ", ".join(states) if states else "(all)")
    print()

    df, status = collectInventoryDf(args.use_last_data)
    print("\nInventory searched:", len(df), "vehicles, collected", status.get("date", "(unknown date)"))
    missing = status.get("numberRawVehiclesMissing", 0)
    if missing:
        print("Note: the run reports", missing, "vehicles missing.  On lexus that count is measured "
              "against the whole RX family's record count, so it is not reliable evidence of a gap.")

    matches = filterDataFrame(df, states=states, interior=interior, availableOnly=args.available_only)
    if matches.empty:
        reportWhyNothingMatched(df, states, interior)
        return 0

    matches = addMilesFromCenter(matches)
    matches = matches.sort_values(by=["Miles From Center", "Selling Price"], na_position="last")
    matches = matches.reset_index(drop=True)
    # The stale first row Excel formula is meaningless once the rows have been filtered and re-sorted.
    if "DistanceFromCenter" in matches.columns:
        matches = matches.drop(columns=["DistanceFromCenter"])

    print("\n" + "=" * 100)
    print(len(matches), "matching vehicles")
    print("=" * 100)
    printable = matches[[c for c in CONSOLE_COLUMNS if c in matches.columns]]
    with pd.option_context("display.max_rows", None, "display.width", 250, "display.max_colwidth", 40):
        print(printable.to_string(index=False))

    print("\nBy state:")
    for state, count in matches["Dealer State"].value_counts().items():
        print("   ", state, count)
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
