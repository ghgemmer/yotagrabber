"""Get a list of Toyota vehicles from the Toyota website."""
import datetime
import json
import os
import sys
import uuid
import random
from functools import cache
from secrets import randbelow
from time import sleep
from timeit import default_timer as timer

import pandas as pd
import requests

from yotagrabber import config, wafbypass

# Set to True to use local data and skip requests to the Toyota website.
USE_LOCAL_DATA_ONLY = False

DEBUG_ENABLED = False


# Get the model that we should be searching for.
MODEL = os.environ.get("MODEL")

forceQueryRspFailureTest = 0 # set to > 0 to perform tests related to forcing a query response failure to test query request retry

@cache
def get_vehicles_query(zone="west"):
    """Read vehicles query from a file."""
    with open(f"{config.BASE_DIRECTORY}/graphql/vehicles.graphql", "r") as fileh:
        query = fileh.read()

    zip_codes = {
        "alaska": "99518",  # Anchorage Alaska 99518
        "hawaii": "96720",  # Hilo HI 96720
        "west": "84101",  # Salt Lake City
        "central": "73007",  # Oklahoma City
        "east": "27608",  # Raleigh
    }

    # Replace certain place holders in the query with values.
    zip_code = zip_codes[zone]
    query = query.replace("ZIPCODE", zip_code)
    query = query.replace("MODELCODE", MODEL)
    query = query.replace("DISTANCEMILES", str(5823 + randbelow(1000)))
    query = query.replace("LEADIDUUID", str(uuid.uuid4()))

    return query


def read_local_data():
    """Read local raw data from the disk instead of querying Toyota."""
    return pd.read_parquet(f"output/{MODEL}_raw.parquet")


def query_toyota(page_number, query, headers):
    """Query Toyota for a list of vehicles."""
    global forceQueryRspFailureTest
    # Replace the page number in the query
    query = query.replace("PAGENUMBER", str(page_number))

    tryCount = 4
    result = None
    # TODO: still getting many query failures even with this retry method (goes through all retires withuot success)
    # and not sure why?  Printed resp.text does not seem to contain any readable ascii text.
    while tryCount:
        # Make request.
        json_post = {"query": query}
        url = "https://api.search-inventory.toyota.com/graphql"
        try:
            resp = requests.post(
                url,
                json=json_post,
                headers=headers,
                timeout=20,
            )
            if DEBUG_ENABLED:
                if resp is None:
                    print("query resp is None")
                else:
                    print("query request headers: ", repr(resp.request.headers))
                    print("query request.body: " + str(resp.request.body))
                    print("query resp", repr (resp.headers), repr(resp))
            try:
                result = resp.json()["data"]["locateVehiclesByZip"]
                if result and ("vehicleSummary" in result):
                    print(result["pagination"])
                    if (forceQueryRspFailureTest > 0) and (forceQueryRspFailureTest < 20):
                        forceFail = False
                        if forceQueryRspFailureTest in [2,3,10]:
                            print("Test forcing query page response failure, forceQueryRspFailureTest = ", forceQueryRspFailureTest)
                            forceFail = True
                        forceQueryRspFailureTest += 1
                        if not forceFail:
                            break
                    else:
                        break
            except (requests.exceptions.JSONDecodeError) as inst:
                print ("query_toyota: Exception occurred with accessing json response:", str(type(inst)) + " "  + str(inst))
                print("resp.status_code", resp.status_code)
                print("resp.headers", resp.headers)
                #print("resp.text", resp.text)
                #print("resp.content", resp.content)
                #return None
        except (requests.exceptions.ReadTimeout) as inst:
            print ("query_toyota: Exception occurred :", str(type(inst)) + " "  + str(inst))
        tryCount -= 1
        print("Trying query again for page number: " + str(page_number),  ", tryCount = " + str(tryCount))
        tm = 7 + (6 * random.random())
        print("sleeping", tm, " secs")
        sleep(tm)
    if not result or "vehicleSummary" not in result:
        print("Result is None, or vehicleSummary field not present in results")
        if resp is not None:
          print("resp.text", resp.text)
        return None
    else:
        return result


def get_all_pages():
    """Get all pages of results for a query to Toyota."""
    df = pd.DataFrame()
    page_number = 1

    # Read the query.
    alaska_query = get_vehicles_query(zone="alaska")
    hawaii_query = get_vehicles_query(zone="hawaii")
    west_query = get_vehicles_query(zone="west")
    central_query = get_vehicles_query(zone="central")
    east_query = get_vehicles_query(zone="east")

    # Get headers by bypassing the WAF.
    print("Bypassing WAF")
    headers = wafbypass.WAFBypass().run()

    # Start a timer.
    timer_start = timer()

    # Set a last run counter.
    last_run_counter = 0
    
    while True:
        
        # Toyota's API won't return any vehicles past past 40.
        maxPagesToGet = 40
        maxRecordsToGet = maxPagesToGet * 250 * 5 # 250 records pre page for a single request,  5 different locality requests.
        # Note that there may be more records than this since there may be more pages than maxPagesToGet,
        # but we can only access maxPagesToGet pages of records.
        pagesToGet = maxPagesToGet
        recordsToGet = maxRecordsToGet
        if page_number > maxPagesToGet:
            print("Error: Prematurely terminating due to limit of max pages can get of ", maxPagesToGet, ". All vehicles were not found!")
            break
        # The WAF bypass expires every 5 minutes, so we refresh about every 4 minutes.
        elapsed_time = timer() - timer_start
        if elapsed_time > 4 * 60:
            print("  >>> Refreshing WAF bypass >>>\n")
            headers = wafbypass.WAFBypass().run()
            timer_start = timer()

        # Get a page of vehicles.  
        # We request several different geographically spread out locales, each with a radius that
        # that reaches to anywhere in the US from that locale (including Alaska and Hawaii)
        # to get around the maximum pages the website will allow us to access for any one locale request.
        # Any one request would return all the records for the US if we could access all the pages, but the website won't let us access
        # more than a fixed maximum number of pages for any given request, even if the response indicates there are more pages.
        # Currently if a result has more than the current maxRecordsToGet then we will miss some vehicles
        # (and this is indicated in the log file)
        # This could be corrected by adding more spread out locales
        print(f"Getting page {page_number} of {MODEL} vehicles")

        hawaii_result = query_toyota(page_number, hawaii_query, headers)
        if hawaii_result and "vehicleSummary" in hawaii_result:
            pages = hawaii_result["pagination"]["totalPages"]
            records = hawaii_result["pagination"]["totalRecords"]
            print("Hawaii:    ", len(hawaii_result["vehicleSummary"]))
            df = pd.concat([df, pd.json_normalize(hawaii_result["vehicleSummary"])])
        if pagesToGet > pages:
            pagesToGet = pages
        if recordsToGet > records:
            recordsToGet = records

        alaska_result = query_toyota(page_number, alaska_query, headers)
        if alaska_result and "vehicleSummary" in alaska_result:
            pages = alaska_result["pagination"]["totalPages"]
            records = alaska_result["pagination"]["totalRecords"]
            print("Alaska:    ", len(alaska_result["vehicleSummary"]))
            df = pd.concat([df, pd.json_normalize(alaska_result["vehicleSummary"])])
        if pagesToGet > pages:
            pagesToGet = pages
        if recordsToGet > records:
            recordsToGet = records

        west_result = query_toyota(page_number, west_query, headers)
        if west_result and "vehicleSummary" in west_result:
            pages = west_result["pagination"]["totalPages"]
            records = west_result["pagination"]["totalRecords"]
            print("West:    ", len(west_result["vehicleSummary"]))
            df = pd.concat([df, pd.json_normalize(west_result["vehicleSummary"])])
        if pagesToGet > pages:
            pagesToGet = pages
        if recordsToGet > records:
            recordsToGet = records

        central_result = query_toyota(page_number, central_query, headers)
        if central_result and "vehicleSummary" in central_result:
            pages = central_result["pagination"]["totalPages"]
            records = central_result["pagination"]["totalRecords"]
            print("Central:    ", len(central_result["vehicleSummary"]))
            df = pd.concat([df, pd.json_normalize(central_result["vehicleSummary"])])
        if pagesToGet > pages:
            pagesToGet = pages
        if recordsToGet > records:
            recordsToGet = records
            
        east_result = query_toyota(page_number, east_query, headers)
        if east_result and "vehicleSummary" in east_result:
            pages = east_result["pagination"]["totalPages"]
            records = east_result["pagination"]["totalRecords"]
            print("East:    ", len(east_result["vehicleSummary"]))
            df = pd.concat([df, pd.json_normalize(east_result["vehicleSummary"])])
        if pagesToGet > pages:
            pagesToGet = pages
        if recordsToGet > records:
            recordsToGet = records

        # Drop any duplicate VINs.
        df.drop_duplicates(subset=["vin"], inplace=True)

        print(f"Found {len(df)} (+{len(df)-last_run_counter}) vehicles so far.\n")

        ## If we didn't find more cars from the previous run, we've found them all.
        #if len(df) == last_run_counter:
        if len(df) >= recordsToGet:
            # we found total records indicated by any one request, which is all the records we are looking for.
            print("All vehicles found.")
            break
        elif page_number >= pagesToGet:
            print("Error: Prematurely terminating page requests since reached total pages for this vehicle", page_number, ". All vehicles were not found!")
            break
        last_run_counter = len(df)
        page_number += 1
        sleep(10)
        continue

    return df


def update_vehicles_and_return_df(useLocalData = False):
    """Generate a curated database file for the given vehicle model environment variable, as well as returning that database as a dataframe as the function return value."""
    if not MODEL:
        sys.exit("Set the MODEL environment variable first")

    df = read_local_data() if (USE_LOCAL_DATA_ONLY or useLocalData) else get_all_pages()

    # Stop here if there are no vehicles to list.
    if df.empty:
        print(f"No vehicles found for model: {MODEL}")
        return

    # Write the raw data to a file.
    if (not USE_LOCAL_DATA_ONLY) and (not useLocalData):
        df.sort_values("vin", inplace=True)
        df.to_parquet(f"output/{MODEL}_raw.parquet", index=False)

    # Add dealer data.
    dealers = pd.read_csv(f"{config.BASE_DIRECTORY}/data/dealers.csv")[
        ["dealerId", "state"]
    ]
    dealers.rename(columns={"state": "Dealer State"}, inplace=True)
    df["dealerCd"] = df["dealerCd"].apply(pd.to_numeric)
    df = df.merge(dealers, left_on="dealerCd", right_on="dealerId")

    renames = {
        "vin": "VIN",
        "price.baseMsrp": "Base MSRP",
        "price.totalMsrp": "Total MSRP",
        "price.sellingPrice": "Selling Price",
        "model.marketingName": "Model",
        "extColor.marketingName": "Color",
        "dealerCategory": "Shipping Status",
        "dealerMarketingName": "Dealer",
        # "dealerWebsite": "Dealer Website",
        "isPreSold": "Pre-Sold",
        "holdStatus": "Hold Status",
        "year": "Year",
        "drivetrain.code": "Drivetrain",
        "options": "Options",
    }

    with open(f"output/models.json", "r") as fileh:
        title = [x["title"] for x in json.load(fileh) if x["modelCode"] == MODEL][0]

    df = (
        df[
            [
                "vin",
                "dealerCategory",
                "price.baseMsrp",
                "price.totalMsrp",
                "price.sellingPrice",
                "price.dioTotalDealerSellingPrice",
                "isPreSold",
                "holdStatus",
                "year",
                "drivetrain.code",
                # "media",
                "model.marketingName",
                "extColor.marketingName",
                "dealerMarketingName",
                # "dealerWebsite",
                "Dealer State",
                "options",
                "eta.currFromDate",
                "eta.currToDate",
            ]
        ]
        .copy(deep=True)
        .rename(columns=renames)
    )

    # Remove the model name (like 4Runner) from the model column (like TRD Pro).
    df["Model"] = df["Model"].str.replace(f"{title} ", "")

    # Clean up missing colors and colors with extra tags.
    df = df[df["Color"].notna()]
    df["Color"] = df["Color"].str.replace(" [extra_cost_color]", "", regex=False)

    # Calculate the dealer price + markup.
    df["Dealer Price"] = df["Base MSRP"] + df["price.dioTotalDealerSellingPrice"]
    df["Dealer Price"] = df["Dealer Price"].fillna(df["Base MSRP"])
    df["Markup"] = df["Dealer Price"] - df["Base MSRP"]
    df.drop(columns=["price.dioTotalDealerSellingPrice"], inplace=True)

    # Remove any old models that might still be there.
    last_year = datetime.date.today().year - 1
    df.drop(df[df["Year"] < last_year].index, inplace=True)

    statuses = {None: False, 1: True, 0: False}
    df.replace({"Pre-Sold": statuses}, inplace=True)

    statuses = {
        "A": "Factory to port",
        "F": "Port to dealer",
        "G": "At dealer",
    }
    df.replace({"Shipping Status": statuses}, inplace=True)

    # df["Image"] = df["media"].apply(
    #     lambda x: [x["href"] for x in x if x["type"] == "carjellyimage"][0]
    # )
    # df.drop(columns=["media"], inplace=True)

    df["Options"] = df["Options"].apply(extract_marketing_long_names)

    # Add the drivetrain to the model name to reduce complexity.
    df["Model"] = df["Model"] + " " + df["Drivetrain"]

    df = df[
        [
            "Year",
            "Model",
            "Color",
            "Base MSRP",
            "Total MSRP",
            "Selling Price",
            "Markup",
            "Dealer Price",
            "Shipping Status",
            "Pre-Sold",
            "Hold Status",
            "eta.currFromDate",
            "eta.currToDate",
            "VIN",
            "Dealer",
            # "Dealer Website",
            "Dealer State",
            # "Image",
            "Options",
        ]
    ]

    # Write the data to a file.
    df.sort_values(by=["VIN"], inplace=True)
    df.to_csv(f"output/{MODEL}.csv", index=False)
    return df

def update_vehicles(useLocalData = False):
    """Generate a curated database file for the given vehicle model environment variable."""
    # This function is used to generate the inventory database file for the given vehicle model,
    # but it has no return statement so that the correct system exit code applies 
    # (success is 0 anything else is failed) when called by "poetry run update_vehicles".
    update_vehicles_and_return_df(useLocalData = useLocalData)

def extract_marketing_long_names(options_raw):
    """extracts `marketingName` from `Options` col"""
    options = set()
    if options_raw:
        for item in options_raw:
            if item.get("marketingName"):
                options.add(item.get("marketingName"))
            elif item.get("marketingLongName"):
                options.add(item.get("marketingLongName"))
            else:
                continue
    return " | ".join(sorted(options))
