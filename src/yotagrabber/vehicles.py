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
from collections.abc import Iterable
from yotagrabber import config, wafbypass

# Set to True to use local data and skip requests to the Toyota website.
USE_LOCAL_DATA_ONLY = False

DEBUG_ENABLED = False

PAGE_FILES_DEBUG_ENABLED = False

# Get the model that we should be searching for.
MODEL = os.environ.get("MODEL")
# optional search parameters to use when want a single location search
MODEL_SEARCH_ZIPCODE = os.environ.get("MODEL_SEARCH_ZIPCODE")
MODEL_SEARCH_RADIUS = os.environ.get("MODEL_SEARCH_RADIUS")

forceQueryRspFailureTest = 0 # set to > 0 to perform tests related to forcing a query response failure to test query request retry

totalPageRetries= 0
MAX_TOTAL_PAGE_RETIRES_FOR_MODEL = 2 * 3 * 30 # say on avg 3 groups of 2 retries per page (10 sec avg per retry) over 30 pages  giving 30 minutes extra worst case per model

@cache
def get_vehicle_query_Objects():
    """Read vehicle query from a file and create the query objects."""
    vehicleQueryObjects = {}
    if (MODEL_SEARCH_ZIPCODE is not None) and (MODEL_SEARCH_RADIUS is not None) and MODEL_SEARCH_ZIPCODE and MODEL_SEARCH_RADIUS:
        # single zipcode and radius search specified
        with open(f"{config.BASE_DIRECTORY}/graphql/vehicles.graphql", "r") as fileh:
            query = fileh.read()
        query = query.replace("ZIPCODE", MODEL_SEARCH_ZIPCODE)
        query = query.replace("MODELCODE", MODEL)
        query = query.replace("DISTANCEMILES", MODEL_SEARCH_RADIUS)
        query = query.replace("LEADIDUUID", str(uuid.uuid4()))
        vehicleQueryObjects["SingleZipCode_" + MODEL_SEARCH_ZIPCODE + "_RadiusMiles_" + MODEL_SEARCH_RADIUS] = query        
    else:
        if MODEL in [ "camry", "tacoma", "tundra", "rav4hybrid", "rav4", "corolla"]:
            # note that the tacoma is the largest number of vehicles (some 44,000 for the last 2 years), followed by tundra, camry, rav4hybrid, rav4
            vehicleQueryZonesToUse = ["alaska", "hawaii", "west", "central", "midIllinois", "east", "atlanta", "topLeftCornerContlUS", "portlandOregon", "bottomLeftCornerContlUS", "midCalifornia", "upperCalifornia", "topRightCornerContlUS", "midPennsylvania", "rochesterNewYork", "albanyNewYork", "bostonMA", "midTennessee", "midOhio", "richmondVA", "bottomRightCornerContlUS", "panhandleFlorida", "midFlorida", "bottomCenterContlUS", "midTexas", "midArizona", "renoNevada", "topCenterContlUS" ]
        elif MODEL in ["grandhighlander" ]:
            # some zone seem to almost never work so removed them and seemed to cause more problems in others.
            # Still get lots of retries so not sure this even fixes getting all the vehicles
            vehicleQueryZonesToUse = ["alaska", "hawaii", "west", "central", "midIllinois", "topLeftCornerContlUS", "portlandOregon", "bottomLeftCornerContlUS", "midCalifornia", "upperCalifornia", "topRightCornerContlUS", "midPennsylvania", "rochesterNewYork", "albanyNewYork", "bostonMA", "midOhio", "richmondVA", "bottomCenterContlUS", "midTexas", "midArizona", "renoNevada", "topCenterContlUS" ]
        else:
            vehicleQueryZonesToUse = ["alaska", "hawaii", "west", "central", "east"]
        zip_codes = {
            "alaska": "99518",  # Anchorage Alaska 99518
            "hawaii": "96720",  # Hilo HI 96720
            "west": "84101",  # Salt Lake City
            "central": "73007",  # Oklahoma City
            "midIllinois": "61614",  # Peoria, IL 61614
            "east": "27608",  # Raleigh
            "atlanta":  "30341", # Atlanta, GA 30341
            "topLeftCornerContlUS": "98271", # Marysville, WA 98271
            "portlandOregon": "97232", # OR 97232
            "bottomLeftCornerContlUS": "91911", # Chula Vista, CA 91911
            "midCalifornia":  "94901", # San Rafael, CA 94901
            "upperCalifornia":  "95503", # Eureka, CA 95503
            "topRightCornerContlUS": "04730", #  Houlton, ME 04730
            "midPennsylvania": "17044", # Lewistown, PA 17044
            "albanyNewYork": "12230", #Albany, NY 12230
            "rochesterNewYork": "14445", # 50 Marsh Rd, East Rochester, NY 14445
            "bostonMA": "02116", # Boston, MA 02116
            "midTennessee": "37211", #TN 37211
            "midMichigan": "48911", # Lansing, MI 48911
            "midOhio": "43232", #Columbus, OH 43232
            "richmondVA": "23249", # Richmond, VA 23249
            "bottomRightCornerContlUS": "33033", #  Homestead, FL 33033
            "panhandleFlorida": "32547", # 777 Beal Parkway, Fort Walton Beach, FL 32547
            "midFlorida":  "32837", # Orlando, FL 32837
            "bottomCenterContlUS":  "78526", # Brownsville, TX 78526
            "midTexas":  "76116", # TX 76116
            "midArizona":  "85014", # Phoenix, AZ 85014
            "renoNevada":  "89502", # Reno, NV 89502
            "topCenterContlUS":  "58701", # Minot, ND 58701
        }
        for zone in vehicleQueryZonesToUse:
            # Replace certain place holders in the query with values.
            with open(f"{config.BASE_DIRECTORY}/graphql/vehicles.graphql", "r") as fileh:
                query = fileh.read()
            zip_code = zip_codes[zone]
            query = query.replace("ZIPCODE", zip_code)
            query = query.replace("MODELCODE", MODEL)
            query = query.replace("DISTANCEMILES", str(5823 + randbelow(1000)))
            query = query.replace("LEADIDUUID", str(uuid.uuid4()))
            vehicleQueryObjects[zone] = query
        
    return vehicleQueryObjects


def read_local_data():
    """Read local raw data from the disk instead of querying Toyota, and also the Status Info and return them"""
    statusFileName = f"output/{MODEL}_StatusInfo.json"
    with open(statusFileName, "r") as f:
        statusOfGetAllPages = json.load(f)
    # TODO do we need to convert fields that are int strings to ints, and what about booleans?
    df = pd.read_parquet(f"output/{MODEL}_raw.parquet")
    return (df , statusOfGetAllPages )

def writeCompletionStatusToFile(statusOfGetAllPages):
    statusFileName = f"output/{MODEL}_StatusInfo.json"
    with open(statusFileName, "w") as f:
        json.dump(statusOfGetAllPages, f, indent=4)
    
def query_toyota(page_number, query, headers):
    """Query Toyota for a list of vehicles."""
    global forceQueryRspFailureTest
    global totalPageRetries
    # Replace the page number in the query
    query = query.replace("PAGENUMBER", str(page_number))

    tryCount = 3
    result = None
    resp = None
    # TODO: still getting many query failures even with this retry method (goes through all retires withuot success)
    # and not sure why?  Printed resp.text does not seem to contain any readable ascii text.
    while tryCount:
        # Make request.
        json_post = {"query": query}
        url = "https://api.search-inventory.toyota.com/graphql"
        try:
            resp = None
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
            except Exception as inst:
                print ("query_toyota: Exception occurred with accessing json response:", str(type(inst)) + " "  + str(inst))
                print("resp.status_code", resp.status_code)
                print("resp.headers", resp.headers)
                #print("resp.text", resp.text)
                #print("resp.content", resp.content)
                #return None
        except Exception as inst:
            print ("query_toyota: Exception occurred :", str(type(inst)) + " "  + str(inst))
        tryCount -= 1
        tm = 7 + (6 * random.random())
        print("sleeping", tm, " secs")
        sleep(tm)
        if tryCount:
            print("Trying query again for page number: " + str(page_number),  ", tryCount = " + str(tryCount))
            totalPageRetries += 1
    if not result or "vehicleSummary" not in result:
        print("Result is None, or vehicleSummary field not present in results")
        if resp is not None:
          print("resp.text", resp.text)
        return None
    else:
        return result


def get_all_pages():
    """Get all pages of results for a query to Toyota."""
    global totalPageRetries
    totalPageRetries = 0
    
    df = pd.DataFrame()
    page_number = 1
    
    # Get the query.
    vehicleQueryObjects = get_vehicle_query_Objects()
    
    # Get headers by bypassing the WAF.
    print("Bypassing WAF")
    headers = wafbypass.WAFBypass().run()
    
    # Start a timer.
    timer_start = timer()
    
    recordsToGet = -1
    numberRawVehiclesMissing = -1
    gotPageInfoAtLeastOnce = False
    # Set a last run counter.
    last_run_counter = 0
    # Perform the queries for the model
    # Toyota's API won't return any vehicles past past 40.
    maxPagesToGet = 40
    maxRecordsToGet =  100000 # limit this to the max vehicles we will ever get from all the pages
    # Note that there may be more records than this since there may be more pages than maxPagesToGet,
    # but we can only access maxPagesToGet pages of records.
    pagesToGet = maxPagesToGet
    recordsToGet = maxRecordsToGet
    while True:
        
        if page_number > maxPagesToGet:
            print("Error: Prematurely terminating due to limit of max pages can get of ", maxPagesToGet, ". All vehicles were not found! Model ", MODEL)
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
        # more than 40 pages for any given request, even if the response indicates there are more pages.
        # Currently if a result has more than the current maxRecordsToGet then we will miss some vehicles
        # (and this is indicated in the log file)
        # This could be corrected by adding more spread out locales
        print(f"Getting page {page_number} of {MODEL} vehicles")
        firstPageInfoForThisPageNumber = True
        for queryDetailString in vehicleQueryObjects:
            result = query_toyota(page_number, vehicleQueryObjects[queryDetailString], headers)
            if result and "vehicleSummary" in result:
                pages = result["pagination"]["totalPages"]
                if pages is None:
                    #Treat pages returned as None as 0
                    print("Warning: Pages field was None type so treating it as 0 pages")
                    pages = 0
                gotPageInfoAtLeastOnce = True
                records = result["pagination"]["totalRecords"]
                if records is None:
                    #Treat records returned as None as 0
                    print("Warning: records field was None type so treating it as 0 records")
                    records = 0
                if firstPageInfoForThisPageNumber:
                    firstPageInfoForThisPageNumber = False
                    # reset pages and records to get to this as the maximum and let the actual pages gotten for this page number reduce it as needed. 
                    pagesToGet = pages
                    recordsToGet = records
                print(queryDetailString + ":    ", len(result["vehicleSummary"]))
                adderDfNormalized = pd.json_normalize(result["vehicleSummary"])
                # Add in date that got this vehicle info
                infoDateTime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                adderDfNormalized["infoDateTime"] = infoDateTime
                if PAGE_FILES_DEBUG_ENABLED:
                    adderDfNormalized.to_csv(f"output/pages/{MODEL}{queryDetailString}_raw_page{page_number}.csv", index=False)
                df = pd.concat([df, adderDfNormalized])
                #df = pd.concat([df, pd.json_normalize(result["vehicleSummary"])])
                if pagesToGet > pages:
                    pagesToGet = pages
                if recordsToGet > records:
                    recordsToGet = records
            elapsed_time = timer() - timer_start
            if elapsed_time > 4 * 60:
                print("  >>> Refreshing WAF bypass >>>\n")
                headers = wafbypass.WAFBypass().run()
                timer_start = timer()
        # Drop any duplicate VINs.
        df.drop_duplicates(subset=["vin"], inplace=True)
        if PAGE_FILES_DEBUG_ENABLED:
            df.to_csv(f"output/pages/{MODEL}_raw_page{page_number}.csv", index=False)
        print(f"Found {len(df)} (+{len(df)-last_run_counter}) vehicles so far.\n")
        ## If we didn't find more cars from the previous run, we've found them all.
        #if len(df) == last_run_counter:
        if len(df) >= recordsToGet:
            # we found total records indicated by any one request, which is all the records we are looking for.
            print("All vehicles found. Model ", MODEL)
            break
        elif page_number >= pagesToGet:
            print("Error: Reached total pages for this vehicle (or page limit) of", page_number, ". All vehicles were not found! Model " , MODEL ,  "missing ", recordsToGet - len(df), "vehicles")
            break
        elif totalPageRetries > MAX_TOTAL_PAGE_RETIRES_FOR_MODEL:
            print("Error: Reached total page retries limit", totalPageRetries, ". All vehicles were not found! Model " , MODEL ,  "missing ", recordsToGet - len(df), "vehicles")
            break 
        last_run_counter = len(df)
        page_number += 1
        sleep(10)
        continue
    completionMsg = ""
    if gotPageInfoAtLeastOnce:
        numberRawVehiclesFound = len(df)
        numberRawVehiclesMissing = recordsToGet - len(df)
        if numberRawVehiclesMissing < 0:
            numberRawVehiclesMissing = 0
    else:
        completionMsg = "Did not get any vehicle pages"
        numberRawVehiclesMissing = -1
        numberRawVehiclesFound = -1
    statusInfo = {"completedOk": gotPageInfoAtLeastOnce, "numberRawVehiclesFound": numberRawVehiclesFound, "numberRawVehiclesMissing": numberRawVehiclesMissing, "completionMsg": completionMsg, "date": str(datetime.datetime.now())}
    return (df, statusInfo )


def update_vehicles_and_return_df(useLocalData = False):
    """Generate a curated database file for the given vehicle model environment variable, as well as 
    returning that database as a dataframe and status of the inventory Get.
    Returns:  a tuple   (dataframe, status ) where dataframe is a pandas dataframe and 
    status is a dictionary of ("completedOk", "numberRawVehiclesFound", "numberRawVehiclesMissing", "completionMsg")
    """    
    if not MODEL:
        sys.exit("Set the MODEL environment variable first")
    
    if (USE_LOCAL_DATA_ONLY or useLocalData):
        df, statusOfGetAllPages = read_local_data()
    else:
        df, statusOfGetAllPages = get_all_pages()
        
    # Stop here if there are no vehicles to list.
    if df.empty:
        print(f"No vehicles found for model: {MODEL}")
        emptyDfWithFinalColumns = pd.DataFrame(columns = ["vin", "dealerCategory", "price.baseMsrp", "price.totalMsrp", "price.sellingPrice", "price.dioTotalDealerSellingPrice", "isPreSold", "holdStatus", "year", "drivetrain.code", "model.marketingName", "extColor.marketingName", "dealerMarketingName", "dealerWebsite", "Dealer State", "options", "eta.currFromDate", "eta.currToDate", "infoDateTime"])
        if statusOfGetAllPages["completedOk"]:
            # store current results
            emptyDfWithFinalColumns.to_csv(f"output/{MODEL}.csv", index=False)
            df.to_parquet(f"output/{MODEL}_raw.parquet", index=False)
            writeCompletionStatusToFile(statusOfGetAllPages)
        else:
            print(f"Completion status not Ok for model: {MODEL}, not storing any results in output files")
        return (emptyDfWithFinalColumns, statusOfGetAllPages)

    # Write the raw data to a file.
    if (not USE_LOCAL_DATA_ONLY) and (not useLocalData):
        df.sort_values("vin", inplace=True)
        df.to_parquet(f"output/{MODEL}_raw.parquet", index=False)
        writeCompletionStatusToFile(statusOfGetAllPages)

    # Add dealer data.  Note that without a dtype parameter the line below will automatically convert unquoted dealerId field to numeric thus removing any leading 0s the dealerId has 
    dealers = pd.read_csv(f"{config.BASE_DIRECTORY}/data/dealers.csv")[
        ["dealerId", "state"]
    ]
    dealers.rename(columns={"state": "Dealer State"}, inplace=True)
    df["dealerCd"] = df["dealerCd"].apply(pd.to_numeric)
    df = df.merge(dealers, left_on="dealerCd", right_on="dealerId", how='left')  
    # how = 'left' will keep vehicle entry even if can't find dealer code for it, so state will show up as blank or NAN.  
    # Without the how = 'left' any row we can't find the matching dealer code in dealers would be removed from df which we don't want.
    # Note that we still have the dealer name and VIN to find the car externally manually.
    dfMissingDealerState = df[df["Dealer State"].isnull() | df["Dealer State"].isin(["", None])].drop_duplicates(subset=["dealerWebsite"], inplace=False)
    if len(dfMissingDealerState) > 0:
        #print("Found missing dealer states. Number of missing dealer states is", len(dfMissingDealerState))
        print("Missing State for the following dealers (update the dealers csv file):")
        for value in dfMissingDealerState["dealerWebsite"]:
            print(value)
    renames = {
        "vin": "VIN",
        "price.baseMsrp": "Base MSRP",
        "price.totalMsrp": "Total MSRP",
        "price.sellingPrice": "Selling Price",
        "model.marketingName": "Model",
        "extColor.marketingName": "Color",
        "dealerCategory": "Shipping Status",
        "dealerMarketingName": "Dealer",
        "dealerWebsite": "Dealer Website",
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
                "dealerWebsite",
                "Dealer State",
                "options",
                "eta.currFromDate",
                "eta.currToDate",
                "infoDateTime",
            ]
        ]
        .copy(deep=True)
        .rename(columns=renames)
    )

    # Remove the model name (like 4Runner) from the model column (like TRD Pro).
    df["Model"] = df["Model"].str.replace(f"{title} ", "")

    # Clean up colors with extra tags.
    # df = df[df["Color"].notna()]  # don't remove entries with missing color as still want to see those vehicles.
    df["Color"] = df["Color"].str.replace(" [extra_cost_color]", "", regex=False)

    # Calculate the various prices.
    df["TMSRP plus DIO"] = df["Total MSRP"] + df["price.dioTotalDealerSellingPrice"]
    df["TMSRP plus DIO"] = df["TMSRP plus DIO"].fillna(df["Total MSRP"])
    # Set selling price to 0 if it was NAN
    df["Selling Price"] = df["Selling Price"].fillna(0.0)
    # Selling Price Incomplete indicates if the Selling Price did not include Dealer Discounts/Markups
    # This occurs when the raw Selling Price value is 0 or NAN
    df["Selling Price Incomplete"] = True
    df["Selling Price Incomplete"] = df["Selling Price Incomplete"].where(df["Selling Price"] == 0, False)
    # Selling price is the TMSRP + Dealer installed options + Dealer discounts/markups with the exception when Selling Price Incomplete is True as indicated above
    df["Selling Price"] = df["Selling Price"].where(df["Selling Price Incomplete"] != True, df["TMSRP plus DIO"] )
    # The Markup column is defined to show the cost of the Dealer Installed Options plus the actual dealer discount/markup
    # i.e everything the dealer adds on to the TMSRP including discounts/markups
    df["Markup"] = df["Selling Price"] - df["Total MSRP"]
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
            "Selling Price Incomplete",
            "Markup",
            "TMSRP plus DIO",
            "Shipping Status",
            "Pre-Sold",
            "Hold Status",
            "eta.currFromDate",
            "eta.currToDate",
            "VIN",
            "Dealer",
            "Dealer Website",
            "Dealer State",
            "infoDateTime",
            # "Image",
            "Options",
        ]
    ]

    # Write the data to a file.
    df.sort_values(by=["VIN"], inplace=True)
    df.to_csv(f"output/{MODEL}.csv", index=False)
    return (df, statusOfGetAllPages )

def update_vehicles(useLocalData = False):
    """Generate a curated database file for the given vehicle model environment variable."""
    # This function is used to generate the inventory database file for the given vehicle model,
    # but it has no return statement so that the correct system exit code applies 
    # (success is 0 anything else is failed) when called by "poetry run update_vehicles".
    update_vehicles_and_return_df(useLocalData = useLocalData)

def extract_marketing_long_names(options_raw):
    """extracts `marketingName` from `Options` col"""
    options = set()
    if isinstance(options_raw, Iterable):
        for item in options_raw:
            if item.get("marketingName"):
                options.add(item.get("marketingName"))
            elif item.get("marketingLongName"):
                options.add(item.get("marketingLongName"))
            else:
                continue
    return " | ".join(sorted(options))
    
if __name__ == "__main__":
    import sys
    useLocalData = False
    if len(sys.argv) > 1:
        useLocalDatastr = sys.argv[1:][0]
        #print("useLocalDatastr:" + useLocalDatastr + ":")
        if useLocalDatastr ==  "useLocalData":
            useLocalData = True
    #print("useLocalData", useLocalData, "type", str(type(useLocalData)))
    update_vehicles(useLocalData)

