"""Get a list of Toyota vehicles from the Toyota website."""
import datetime
import json
import os
import sys
from pathlib import Path
from pprint import pprint
import re
import uuid
import random
from functools import cache
from secrets import randbelow
from time import sleep
from timeit import default_timer as timer
import numpy as np
import glob
import numbers


import pandas as pd
import csv
import requests
from collections.abc import Iterable
from yotagrabber import config, wafbypass

PROGRAM_VERSION = "Vehicles Program Version 6.4.2 07-04-2025" #

# Set to True to use local data and skip requests to the Toyota website.
USE_LOCAL_DATA_ONLY = False

DEBUG_ENABLED = False

PAGE_FILES_DEBUG_ENABLED = False

# Get the model that we should be searching for.
MODEL = os.environ.get("MODEL")
# optional search parameters to use when want a single location search
MODEL_SEARCH_ZIPCODE = os.environ.get("MODEL_SEARCH_ZIPCODE")
MODEL_SEARCH_RADIUS = os.environ.get("MODEL_SEARCH_RADIUS")

changeHistoryUseThisAsTodaysDateForTesting = None # for testing change the environment variable string to yyyy-mm-dd hh:mm:ss, otherwise leave env variable not defined. 

forceQueryRspFailureTest = 0 # set to > 0 to perform tests related to forcing a query response failure to test query request retry

totalPageRetries= 0
MAX_TOTAL_PAGE_RETIRES_FOR_MODEL = 2 * 3 * 30 # say on avg 3 groups of 2 retries per page (10 sec avg per retry) over 30 pages  giving 30 minutes extra worst case per model

LastChangedDateTimeColName = "LastChangedDateTime"
columnsForEmptyDfParquet = ["vin", "isTempVin", "dealerCd", "dealerCategory", "price.baseMsrp", "price.totalMsrp", "price.sellingPrice", "price.dioTotalDealerSellingPrice", "price.advertizedPrice", "price.nonSpAdvertizedPrice", "price.dph", "price.dioTotalMsrp", "price.dealerCashApplied", "isPreSold", "holdStatus", "year", "drivetrain.code", "model.marketingName", "extColor.marketingName", "intColor.marketingName", "dealerMarketingName", "dealerWebsite", "eta.currFromDate", "eta.currToDate", 'transmission.transmissionType', 'mpg.combined', 'mpg.city', 'mpg.highway', 'engine.engineCd', 'engine.name', 'cab.code', 'cab', 'bed.code', 'bed', "FirstAddedDate", LastChangedDateTimeColName, "infoDateTime", "options"]
columnsForEmptyDfFinalCsv = ["Year", "Model", "Color", "Int Color", "Base MSRP", "Total MSRP", "Selling Price", "Selling Price Incomplete", "Markup", "TMSRP plus DIO", "Shipping Status", "Pre-Sold", "Hold Status", "eta.currFromDate", "eta.currToDate", "VIN", "isTempVin", "Dealer", "Dealer Website", "Dealer State", "Dealer City", "Dealer Zip", "Dealer Lat", "Dealer Long", "CenterLat", "CenterLong", "DistanceFromCenter", "Transmission", "MPG Combined", "MPG City", "MPG Highway", "Engine Code", "Engine Name", "Cab Code", "Cab", "Bed Code" , "Bed" , "FirstAddedDate", LastChangedDateTimeColName, "infoDateTime", "Options"]
# TODO should be able to construct the below from the columnsForEmptyDfFinalCsv
# columns need to be in the order we want.
rowModificationsColumnName = "List of Changes"
rowChangeTypeColumnName = "RowChangeType"
rowChangeDateTime = "Event DateTime"
columnsForEmptyChangeHistoryCsvDf = [rowChangeTypeColumnName, rowChangeDateTime, "Year", "Model", "Color", "Int Color", "Base MSRP", "Total MSRP", "Selling Price", "Selling Price Incomplete", "Markup", "TMSRP plus DIO", "Shipping Status", "Pre-Sold", "Hold Status", "eta.currFromDate", "eta.currToDate", "VIN", "isTempVin", "Dealer", "Dealer Website", "Dealer State", "Dealer City", "Dealer Zip", "Dealer Lat", "Dealer Long", "CenterLat", "CenterLong", "DistanceFromCenter", "Transmission", "MPG Combined", "MPG City", "MPG Highway", "Engine Code", "Engine Name", "Cab Code", "Cab", "Bed Code" , "Bed" , "FirstAddedDate", "infoDateTime", rowModificationsColumnName, "Options"]

columnValueChangedIndicator =  "----->"
columnValueNotChangedIndicator = "_"
rowAddedNewVINIndicator = "ADDED"
rowModifiedVINContentsIndicator = "MODED"
rowRemovedVINIndicator = "REMOVED"
rowSameVINContentsIndicator = ""

maxDaysOldToKeep = 14  # 2 weeks for change history entries
maxDaysToKeepTempVinSold = 7 * 16 #16 weeks for temp VIN in sold files.

@cache

def getExcelDistanceFormulaForCsv(dfColumns, excelRowIndex = 2):
    # gets the Excel formula to put in row excelRowIndex in the DistanceFromCenter column
    # dfColumns is a tuple of the column names of a df in the order the df has them in, and unique.
    dealerLatColName = "Dealer Lat"
    dealerLongColName = "Dealer Long"
    centerLatColName = "CenterLat"
    centerLongColName ="CenterLong"
    colNameToColCsvIndex = {dealerLatColName: None, dealerLongColName: None, centerLatColName: None, centerLongColName: None}
    for colName in colNameToColCsvIndex:
        if colName in dfColumns:
            colNameToColCsvIndex[colName] = dfColumns.index(colName)
        else:
            print("Error: getExcelDistanceFormulaForCsv: name", colName, "not in dfColumns. Returning formula as blank")
            return ""
    colNameToExcelCellRef = {}
    for colName in colNameToColCsvIndex:
        excelColIndex = colNameToColCsvIndex[colName]
        excelColRef = ""
        remainder = excelColIndex
        alphabetSize = 26
        if remainder == 0:
            excelColRef = "A"
        else:
            while remainder >= 0:
                modulo = remainder % alphabetSize
                excelColRef = chr(ord("A") + modulo) + excelColRef
                remainder = (remainder // alphabetSize) - 1
        colNameToExcelCellRef[colName] = excelColRef + str(excelRowIndex)
    
    formula = f'=ACOS(COS(RADIANS(90-{colNameToExcelCellRef[dealerLatColName]}))*COS(RADIANS(90-{colNameToExcelCellRef[centerLatColName]}))+SIN(RADIANS(90-{colNameToExcelCellRef[dealerLatColName]}))*SIN(RADIANS(90-{colNameToExcelCellRef[centerLatColName]}))*COS(RADIANS({colNameToExcelCellRef[dealerLongColName]}-{colNameToExcelCellRef[centerLongColName]})))*6371*0.621371'
    # 
    return formula

def getVehicleByVinWithBypass(vin):
    print("Bypassing WAF")
    headers = wafbypass.WAFBypass().run()
    result = getVehicleByVin(vin, headers)
    return result

def getVehicleByVin(vin, headers):
    global forceQueryRspFailureTest
    # queries the vehicle information by the VIN  from the website using the passed bypass request headers and returns it.
    # The information is the same as what vehicles.graphql returns excluding the fields
    # colorFamilies, distance, isUnlockPriceDealer
    # vehicleByVin.graphql is the same as vehicles.graphql with colorFamilies, distance, isUnlockPriceDealer removed
    # from vehicles.graphql as the getVehicleByVin query to the website does not work with those in them.
    # Note that the full set of fields that can be in a getVehicleByVin is shown in vehicleByVinFullSetOfQueryItems.graphq
    # and is has many more fields than vehicles.graphql.
    #
    #print("Entered getVehicleByVin")
    #print(headers)
    with open(f"{config.BASE_DIRECTORY}/graphql/vehicleByVin.graphql", "r") as fileh:
        query = fileh.read()
    query = query.replace("VINTOGETINFOFOR", vin)
    #print("query is ", query)
    #print("Bypassing WAF")
    #headers = wafbypass.WAFBypass().run()
    tryCount = 3
    result = None
    resp = None
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
                result = resp.json()["data"]["getVehicleByVin"]
                if result and ("vin" in result):
                    print(result["vin"])
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
            print("Trying VIN query again", "tryCount = " + str(tryCount))
    if not result or "vin" not in result:
        print("getVehicleByVin: Result is None, or vin field not present in results")
        if resp is not None:
            print("resp.text", resp.text)
        result = None
    #print("type of result is", type(result))
    #pprint(result, indent=4)
    return result

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
        if MODEL in [ "camry", "tacoma", "tundra", "rav4hybrid", "rav4", "corolla", "4runner"]:
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
    
def getChangeHistoryParquetFileName():
    parquetFileName = f"output/{MODEL}_ChangeHistory.parquet"
    return parquetFileName

def getChangeHistoryCsvFileName():
    parquetFileName = f"output/{MODEL}_ChangeHistory.csv"
    return parquetFileName

def getLastRawParquetFileName():
    parquetFileName = f"output/{MODEL}_Lastraw.parquet"
    return parquetFileName
    
def getInventoryTestParquetFileName():
    parquetFileName = f"output/{MODEL}_raw.parquet"
    return parquetFileName

def getLastRawStatusFileName():
    # The status Info file associated with the last raw parque file named getLastParquetFileName
    statusFileName = f"output/{MODEL}_LastStatusInfo.json"
    return statusFileName

def getInventoryTestStatusFileName():
    # The status Info file associated with the last raw parque file named getLastParquetFileName
    statusFileName = f"output/{MODEL}_StatusInfo.json"
    return statusFileName
    
def readChangeHistoryParquetDf():
    # Reads the change history file containing the last change history dataframe and returns the dataframe
    # If there is no such parquet file an empty dataframe with default columns is returned
    global columnsForEmptyChangeHistoryCsvDf
    
    df = pd.DataFrame(columns = columnsForEmptyChangeHistoryCsvDf)
    parquetFileName = getChangeHistoryParquetFileName()
    # TODO do we need to convert fields that are int strings to ints, and what about booleans?
    if Path(parquetFileName).exists():
        df = pd.read_parquet(parquetFileName)
    else:
        print("readChangeHistoryParquetDf: Change history parquet file does not exist", parquetFileName, " . Using emtpy dataframe for it")
    return df
    
    
def readLastParquetDf():
    # Reads the last parquet file containing the last inventory extracted and returns the dataframe for it
    # and its associated Last StatusOfGetAllPages Info.
    # tuple returned is (rawParquetFileExists, StatusOfGetAllPagesFileExists, rawParquetDf, statusOfGetAllPages)
    # If there is no such parquet file an empty dataframe with default columns is returned
    global columnsForEmptyDfParquet
    
    rawParquetFileExists = False
    statusOfGetAllPagesFileExists = False
    df = pd.DataFrame(columns = columnsForEmptyDfParquet)
    statusOfGetAllPages = {"completedOk": False, "numberRawVehiclesFound": 0, "numberRawVehiclesMissing": 100000, "completionMsg": "", "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    statusFileName = getLastRawStatusFileName()
    parquetFileName = getLastRawParquetFileName()
    # TODO do we need to convert fields that are int strings to ints, and what about booleans?
    if Path(parquetFileName).exists():
        df = pd.read_parquet(parquetFileName)
        rawParquetFileExists = True
    else:
        print("readLastParquetDf: Last raw parquet file does not exist", parquetFileName, " . Using emtpy dataframe for it")
    if Path(statusFileName).exists():
        with open(statusFileName, "r") as f:
            statusOfGetAllPages = json.load(f)
        statusOfGetAllPagesFileExists = True
    else:
        print("readLastParquetDf: Last Raw Status Info file associated with the last raw parquet file does not exist", statusFileName, " . Using status with CompletedOk as False")
    if "Sold" in df.columns:
        # remove it as it is not needed in this file.
        df.drop(["Sold"], axis=1, inplace=True)
    if not("FirstAddedDate" in df.columns):
        # add the column in
        df["FirstAddedDate"] = None
    if not(LastChangedDateTimeColName in df.columns):
        # add the column in
        df[LastChangedDateTimeColName] = None
    return (rawParquetFileExists, statusOfGetAllPagesFileExists, df , statusOfGetAllPages )
     

def read_local_data(testModeOn = False):
    """
    Read local raw data from the disk instead of querying Toyota, and also the StatusOfGetAllPages Info and return them along with
    the rawParquetExists,  StatusOfGetAllPagesFileExists indicating those files existed.
    When test mode is not on the local data and staus is the same as the last parquet data and last status,
    otherwise the local data and status info is the inventory test data and inventory test status info
    tuple returned is (rawParquetFileExists, StatusOfGetAllPagesFileExists, rawParquetDf, statusOfGetAllPages)
    
    """
    global columnsForEmptyDfParquet
    
    rawParquetFileExists = False
    statusOfGetAllPagesFileExists = False
    df = pd.DataFrame(columns = columnsForEmptyDfParquet)
    statusOfGetAllPages = {"completedOk": False, "numberRawVehiclesFound": 0, "numberRawVehiclesMissing": 100000, "completionMsg": "", "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    if testModeOn:
        # we use different files for inventory gotten and status
        statusFileName = getInventoryTestStatusFileName()
        parquetFileName = getInventoryTestParquetFileName()
    else:
        # In this case just use the last raw data and status.
        statusFileName = getLastRawStatusFileName()
        parquetFileName = getLastRawParquetFileName()
        
    # TODO do we need to convert fields that are int strings to ints, and what about booleans?
    if Path(parquetFileName).exists():
        df = pd.read_parquet(parquetFileName)
        rawParquetFileExists = True
    else:
        print("read_local_data: Local parquet data file does not exist", parquetFileName)
    if Path(statusFileName).exists():
        with open(statusFileName, "r") as f:
            statusOfGetAllPages = json.load(f)
        statusOfGetAllPagesFileExists = True
    else:
        print("read_local_data: Local Status Info file does not exist", statusFileName)
    if "Sold" in df.columns:
        # remove it as the inventory website does not have this.
        df.drop(["Sold"], axis=1, inplace=True)
    if "FirstAddedDate" in df.columns:
        # remove it as the inventory website does not have this.
        df.drop(["FirstAddedDate"], axis=1, inplace=True)
    if LastChangedDateTimeColName in df.columns:
        # remove it as the inventory website does not have this.
        df.drop([LastChangedDateTimeColName], axis=1, inplace=True)
    return (rawParquetFileExists, statusOfGetAllPagesFileExists, df , statusOfGetAllPages )


def writeCompletionStatusToFile(statusOfGetAllPages):
    # Only need to write out to the last status info file, as the test status info file is left unchanged.
    statusFileName = getLastRawStatusFileName()
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
    # TODO: still getting many query failures even with this retry method (when retries usually goes through all the retires without success but sometimes does not)
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
    if not len(df):
        df = pd.DataFrame(columns = columnsForEmptyDfParquet)
    if "Sold" in df.columns:
        # remove it as the inventory website does not have this, and if it does we don't want to include it anyway
        df.drop(["Sold"], axis=1, inplace=True)
    if "FirstAddedDate" in df.columns:
        # remove it as the inventory website does not have this, and if it does we don't want to include it anyway
        df.drop(["FirstAddedDate"], axis=1, inplace=True)
    return (df, statusInfo )

def sanitizeStr(strng):
    # Replace tabs, and characters outside ascii 0 -7F range in string that might cause issues with other programs,
    # with a " ".
    # Also replaces &nbsp with a " "
    sanitizedString = strng
    if isinstance(sanitizedString, str):
        sanitizedString = sanitizedString.replace('&nbsp;', ' ')
        sanitizedString = sanitizedString.replace('<br>', ' ')
        rePattern = r'[^\u0000-\u007F]'  # only allow ascii chars represented by hex value 0 -7F.  Pattern is the negation of htis (ie finds anything not this()
        sanitizedString = re.sub(rePattern, ' ', sanitizedString)
        rePattern = r'[\u0009]'
        sanitizedString = re.sub(rePattern, ' ', sanitizedString)
    return sanitizedString

def isNumber(value):
    return ((isinstance(value, int)) or (isinstance(value, float)))
    
def calcPrices(rowSeries):
    # Returns the row series with the updated prices and Selling Price Incomplete from the df row series
    # Assumes the series has columns "Selling Price", "Selling Price Incomplete", "price.nonSpAdvertizedPrice", "price.advertizedPrice", 
    # "price.dioTotalDealerSellingPrice", "TMSRP plus DIO", "Total MSRP", "Base MSRP", "Markup", "isSmartPath"
    # Selling price is the TMSRP + Dealer installed options + Dealer discounts/markups with the exception when Selling Price Incomplete is True
    # Markup is everything above the TMSRP to get to the Selling Price.
    # Note that in the below, Markup and Selling Price Incomplete are columns I added and not something the website returns
    # TMSRP plus DIO is calculated as "Total MSRP" + price.dioTotalDealerSellingPrice if present otherwise just "Total MSRP".  This is based on observation so may not be exactly correct.
    # The selling price is calculated logically equivalent to the javascript source code from the Toyota search inventory website as follows with the noted modifications:
    # See ToyotaSearchInventoryWebSourcePages\SnippetWithPriceDetermination.js for the exact javascript code from the website (the below is pretty much it but in python and with the noted exceptions)
    # 
    #    sellingPriceIncomplete = False
    #    if sellingPrice is present and (sellingPrice >= 10000):
    #        # selling price ok as is
    #    else:
    #        if isSmartPathPresentAndTrue:
    #            if advertizedPrice is present:
    #                sellingPrice = advertizedPrice
    #            else:
    #                sellingPrice = 0
    #        else:
    #            if nonSpAdvertizedPrice is present:
    #                sellingPrice = nonSpAdvertizedPrice
    #            else:
    #                sellingPrice = 0
    #        if sellingPrice is present and (sellingPrice >= 10000):
    #            # selling price ok as is
    #        else:
    #            if tMsrpPlusDio is present and (tMsrpPlusDio >= 10000): (!!!!The actual website java script code uses the Total MSRP column instead.  Decided to use the TMSRP plus DIO to show worst case price)
    #                sellingPriceIncomplete = True
    #                sellingPrice = tMsrpPlusDio
    #            else:
    #                sellingPriceIncomplete = True
    #                sellingPrice = totalMsrp
    #
    sellingPrice = rowSeries["Selling Price"]
    sellingPriceIncomplete = False
    isSmartPath = rowSeries["isSmartPath"]
    nonSpAdvertizedPrice = rowSeries["price.nonSpAdvertizedPrice"]
    advertizedPrice = rowSeries["price.advertizedPrice"]
    dioTotalDealerSellingPrice = rowSeries["price.dioTotalDealerSellingPrice"]
    tMsrpPlusDio = np.NaN
    baseMsrp = rowSeries["Base MSRP"]
    totalMsrp = rowSeries["Total MSRP"]
    markup = np.NaN
    
    isSmartPathPresentAndTrue = isinstance(isSmartPath, bool) and isSmartPath
    
    if valueIsNanNoneNull(baseMsrp) or not(isinstance(baseMsrp, (int,float))):
        baseMsrp = np.NaN
    if valueIsNanNoneNull(totalMsrp) or not(isinstance(totalMsrp, (int,float))):
        totalMsrp = baseMsrp
    if valueIsNanNoneNull(dioTotalDealerSellingPrice):
        tMsrpPlusDio = totalMsrp
    else:
        tMsrpPlusDio = totalMsrp + dioTotalDealerSellingPrice # yields NaN if either is NaN
    
    if not(valueIsNanNoneNull(sellingPrice)) and isinstance(sellingPrice, (int,float)) and  (sellingPrice >= 10000):
        # selling price ok as is
        pass        
    else:
        if isSmartPathPresentAndTrue:
            if not(valueIsNanNoneNull(advertizedPrice)) and isinstance(advertizedPrice, (int,float)):
                sellingPrice = advertizedPrice
            else:
                sellingPrice = 0
        else:
            if not(valueIsNanNoneNull(nonSpAdvertizedPrice)) and isinstance(nonSpAdvertizedPrice, (int,float)):
                sellingPrice = nonSpAdvertizedPrice
            else:
                sellingPrice = 0
        if not(valueIsNanNoneNull(sellingPrice)) and isinstance(sellingPrice, (int,float)) and (sellingPrice >= 10000):
            # selling price ok as is
            pass
        else:
            if not(valueIsNanNoneNull(tMsrpPlusDio)) and isinstance(tMsrpPlusDio, (int,float)) and (tMsrpPlusDio >= 10000):
                sellingPriceIncomplete = True
                sellingPrice = tMsrpPlusDio
            else:
                sellingPriceIncomplete = True
                sellingPrice = totalMsrp
                
    markup = sellingPrice - totalMsrp # yields NaN if either is NaN
    
    rowSeries["Selling Price"]                     = sellingPrice
    rowSeries["Selling Price Incomplete"]          = sellingPriceIncomplete
    rowSeries["Base MSRP"]                         = baseMsrp
    rowSeries["Total MSRP"]                        = totalMsrp
    rowSeries["TMSRP plus DIO"]                    = tMsrpPlusDio
    rowSeries["Markup"]                            = markup
    
    return rowSeries

def transformRawDfToCsvStyleDf ( inputDf):
    # transforms the input raw df (one that has all the raw parquet fields) into an output df for a csv file.
    # Note that year range is not limited in the return and must be done outside of this.
    # the index is reset on the returned df
    df = inputDf.copy(deep=True)
    if not df.empty:
        # Add dealer data.  Note that without a dtype parameter on the dealerID field the line below will automatically convert unquoted dealerId field to numeric thus removing any leading 0s the dealerId has
        # which is what we want for the dealerId.
        dealers = pd.read_csv(f"{config.BASE_DIRECTORY}/data/dealers.csv", dtype = { 'zip': 'str', 'address1': 'str', 'phone': 'str'})[
            ["dealerId", "state", "city", "zip", "lat", "long"]
        ]
        dealers.rename(columns={"state": "Dealer State", "city": "Dealer City", "zip": "Dealer Zip", "lat": "Dealer Lat", "long": "Dealer Long"}, inplace=True)
        df["dealerCd"] = df["dealerCd"].apply(pd.to_numeric)
        df = df.merge(dealers, left_on="dealerCd", right_on="dealerId", how='left')
        # how = 'left' will keep vehicle entry even if can't find dealer code for it, so state will show up as blank or NAN.
        # Without the how = 'left' any row we can't find the matching dealer code in dealers would be removed from df which we don't want.
        # Note that we still have the dealer name and VIN to find the car externally manually.
        dfMissingDealerState = df[df["Dealer State"].isnull() | df["Dealer State"].isin(["", None])].drop_duplicates(subset=["dealerMarketingName"], inplace=False)
        if len(dfMissingDealerState) > 0:
            #print("Found missing dealer states. Number of missing dealer states is", len(dfMissingDealerState))
            for index, row in dfMissingDealerState.iterrows():
                print("Missing State for dealer Name, website:", row["dealerMarketingName"], ",", row["dealerWebsite"])
                
        if 'cab.title' in df.columns:
            df['cab'] = df['cab.title']
        elif 'cab' in df.columns:
            pass
        else:
            df['cab'] = None
            
        if 'bed.title' in df.columns:
            df['bed'] = df['bed.title']
        elif 'bed' in df.columns:
            pass
        else:
            df['bed'] = None
            
        if not ('cab.code' in df.columns):
            df['cab.code'] = None
            
        if not ('bed.code' in df.columns):
            df['bed.code'] = None
            
        # The mirai model does not return these columns, probably due to it being a Fuel Cell,
        # so add empty empty columns for them.
        if not ('mpg.combined' in df.columns):
            df['mpg.combined'] = None
        if not ('mpg.city' in df.columns):
            df['mpg.city'] = None
        if not ('mpg.highway' in df.columns):
            df['mpg.highway'] = None
        if not ('FirstAddedDate' in df.columns):
            # This can happen if the passed df is the originalLastParquet before the
            # FirstAddedDate column has ever been added to it such as when the last parquet file did not exist
            df['FirstAddedDate'] = None
        if not (LastChangedDateTimeColName in df.columns):
            # This can happen if the passed df is the originalLastParquet before the
            # LastChangedDateTimeColName column has ever been added to it such as when the last parquet file did not exist
            df[LastChangedDateTimeColName] = None
        
        renames = {
            "vin": "VIN",
            "price.baseMsrp": "Base MSRP",
            "price.totalMsrp": "Total MSRP",
            "price.sellingPrice": "Selling Price",
            "model.marketingName": "Model",
            "extColor.marketingName": "Color",
            "intColor.marketingName": "Int Color",
            "dealerCategory": "Shipping Status",
            "dealerMarketingName": "Dealer",
            "dealerWebsite": "Dealer Website",
            "isPreSold": "Pre-Sold",
            "holdStatus": "Hold Status",
            "year": "Year",
            "drivetrain.code": "Drivetrain",
            "options": "Options",
            'transmission.transmissionType': "Transmission",
            'mpg.combined': "MPG Combined",
            'mpg.city': "MPG City",
            'mpg.highway': "MPG Highway",
            'engine.engineCd': "Engine Code",
            'engine.name': "Engine Name",
            'cab.code': "Cab Code", 
            'bed.code': "Bed Code",
            'cab': "Cab",
            'bed': "Bed",
        }
    
        with open(f"output/models.json", "r") as fileh:
            title = [x["title"] for x in json.load(fileh) if x["modelCode"] == MODEL][0]
    
        df = (
            df[
                [
                    "vin",
                    "isTempVin",
                    "dealerCategory",
                    "price.baseMsrp",
                    "price.totalMsrp",
                    "price.sellingPrice",
                    "price.dioTotalDealerSellingPrice",
                    "price.advertizedPrice",
                    "price.nonSpAdvertizedPrice",
                    "price.dph",
                    "price.dioTotalMsrp",
                    "price.dealerCashApplied",
                    "isPreSold",
                    "holdStatus",
                    "year",
                    "drivetrain.code",
                    # "media",
                    "model.marketingName",
                    "extColor.marketingName",
                    "intColor.marketingName",
                    "dealerMarketingName",
                    "dealerWebsite",
                    "isSmartPath",
                    "Dealer State",
                    "Dealer City",
                    "Dealer Zip",
                    "Dealer Lat",
                    "Dealer Long",
                    "options",
                    "eta.currFromDate",
                    "eta.currToDate",
                    'transmission.transmissionType',
                    'mpg.combined',
                    'mpg.city',
                    'mpg.highway',
                    'engine.engineCd',
                    'engine.name',
                    'cab.code',
                    'cab',
                    'bed.code',
                    'bed',
                    "FirstAddedDate",
                    LastChangedDateTimeColName,
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
        df["Int Color"] = df["Int Color"].apply(sanitizeStr)
        
        # Calculate the various prices.
        df["Raw Selling Price"] = df["Selling Price"] # create column with default
        df["Selling Price Incomplete"] = False  # create column with default
        df["TMSRP plus DIO"] = np.NaN # create column with default
        df["Markup"] = np.NaN # create column with default
        if len(df):
            # Note: Using a slice of the df that contains just the columns needed for the price calculation does not
            # execute any faster than passing all columns to the apply.
            df = df.apply(calcPrices, axis=1)
        
        df.drop(columns=["price.dioTotalDealerSellingPrice"], inplace=True)
        
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
    
        # Add columns for CenterLat, CenterLong, DistanceFromCenter
        df["CenterLat"] = 41.978382
        df["CenterLong"] = -91.668626
        df["DistanceFromCenter"] = None
    
    
        df = df[
            [
                "Year",
                "Model",
                "Color",
                "Int Color",
                "Base MSRP",
                "Total MSRP",
                "Selling Price",
                "Selling Price Incomplete",
                "Markup",
                "TMSRP plus DIO",
                #"Raw Selling Price",
                #"price.advertizedPrice",
                #"price.nonSpAdvertizedPrice",
                #"price.dph",
                #"price.dioTotalMsrp",
                #"price.dioTotalDealerSellingPrice",
                #"price.dealerCashApplied",
                "Shipping Status",
                "Pre-Sold",
                "Hold Status",
                "eta.currFromDate",
                "eta.currToDate",
                "VIN",
                "isTempVin",
                "Dealer",
                "Dealer Website",
                #"isSmartPath",
                "Dealer State",
                "Dealer City",
                "Dealer Zip",
                "Dealer Lat",
                "Dealer Long",
                "CenterLat",
                "CenterLong",
                "DistanceFromCenter",
                "Transmission",
                "MPG Combined",
                "MPG City",
                "MPG Highway",
                "Engine Code",
                "Engine Name",
                "Cab Code", 
                "Cab",
                "Bed Code",
                "Bed",
                "FirstAddedDate",
                LastChangedDateTimeColName,
                "infoDateTime",
                # "Image",
                "Options",
            ]
        ]
        df.sort_values(by=["VIN"], inplace=True)
        df.reset_index(drop=True, inplace=True)  # drop keeps from inserting current index as a column in dataframe
        # Add the distance From Center formula to DistanceFromCenter column in the first cell only
        # to keep size of csv decent and convienient to look at with a text editor.  User can easily do copy down of this cell
        # once it is open in Excel
        #print("type df.columns", type(df.columns))
        #print("df.columns", df.columns)
        #print("df", df)
        if len(df):
            # tuple is needed below to make passed item be hashable otherwise python throws an error.
            distanceFormula = getExcelDistanceFormulaForCsv(tuple(df.columns), 2)
            #print("transformRawDfToCsvStyleDf distanceFormula", distanceFormula)
            df.at[0,"DistanceFromCenter"] =  distanceFormula
    else:
        df = pd.DataFrame(columns = columnsForEmptyDfFinalCsv)
    return df
    
def getFileNameForSoldRawParquet(model, year):
    # model is a str, and year is a number
    #  output/<model>_<year>_Sold_raw.parquet
    return f"output/" + model + "_" + "{:04d}".format(year) + "_Sold_raw.parquet"
    
def getFileNameForSoldCsv(model, year):
    # model is a str, and year is a number
    # returns output/<model>_<year>_Sold.csv
    return f"output/" + model + "_" + "{:04d}".format(year) + "_Sold.csv"
    
def valueIsStrType(value):
    isStrType = False
    if isinstance(value, str):
        isStrType = True
    return isStrType

def pruneSoldFiles(model):
    # Prunes the models Sold files of Temp VIN entries whose infoDateTime is older than 12 weeks.
    # The assumption is by that time they have been turned into a real VINs with production starting.
    global changeHistoryUseThisAsTodaysDateForTesting
    global maxDaysToKeepTempVinSold
    # Get the sold raw parquet file names for the model
    searchPathAndPatterns = os.path.join("output/", model + "_????_Sold_raw.parquet")
    fileNamesWithPath = glob.glob(searchPathAndPatterns)
    #print("Pruning Sold files of old temp VINs")
    for fileNameWithPath in fileNamesWithPath:
        if os.path.isfile(Path(fileNameWithPath)):
            #print("Pruning file", fileNameWithPath, "of old temp VINs")
            df = pd.read_parquet(fileNameWithPath)
            today = datetime.datetime.today()
            format_time_string = "%Y-%m-%d %H:%M:%S"
            # Now filter these to only keep the ones that were at most maxDaysTempVinSold
            if not (changeHistoryUseThisAsTodaysDateForTesting is None):
                print("!!!!!!!! Warning: pruneSoldFiles:  Using a test date in place of Todays Date for testing date filtering. Test date is:", changeHistoryUseThisAsTodaysDateForTesting)
                # override the actual current today gotten above with this test date.
                # This allows us to include none, some, or all entries in lastChangeHistorydf for testing purposes of the days to keep filtering
                today = datetime.datetime.strptime(changeHistoryUseThisAsTodaysDateForTesting, format_time_string)
            lowerKeepDate = today - datetime.timedelta(days=maxDaysToKeepTempVinSold)
            lowerKeepDateStr = lowerKeepDate.strftime(format_time_string)
            #print("lowerKeepDateStr", lowerKeepDateStr)
            if "infoDateTime" in df.columns:
                lenDfOld = len(df)
                df = df[(df["infoDateTime"].apply(valueIsStrType) == False) | (df["infoDateTime"] >= lowerKeepDateStr)]
                if (lenDfOld - len(df)) > 0:
                    print ("Pruning Sold File", fileNameWithPath, "of", lenDfOld - len(df), "old Temp VINs")
                if True: #len(df) < lenDfOld:
                    # write out parquet
                    df.to_parquet(fileNameWithPath, index=False)
                    # transform df to cvs style and write out to cvs file.
                    cvsStyleDf = transformRawDfToCsvStyleDf(df)
                    lenSuffix = len("_raw.parquet")
                    fileNameWithPathCsv = fileNameWithPath[:-lenSuffix] + ".csv"
                    cvsStyleDf.to_csv(fileNameWithPathCsv, index=False)
                else:
                    # leave files untouched.
                    pass
            else:
                print("Error: pruneSoldFiles : dataframe does not contain infoDateTime column. Leaving sold file unchanged")

def writeLastParquetAndAssociatedFiles(inputDf):
    # Updates the <model>_<year>_Sold_raw.parquet, and <model>_<year>_Sold.csv files with the inputDf, by appending the
    # sold entries (by year) in the inputDf to corresponding sold model year parquet files and then removing duplicate VIns 
    # in those sold model parquet files, and then removing any entries from those sold model parquet files that were
    # not sold in the inputDf  (due to inventory disappearing and reappearing or having detected missing vehicles in the inventory extraction)
    # and then removes any Sold entries from the inputDf, drops the inputDf Sold column, and writes inputDf out to its raw parquet.
    # Each model year raw parquet df is then transformed into a cvs style df and written to the corresponding cvs model year file
    # inputDf is assumed to be the raw parquet df with Sold column info indicating which entries have been sold or not.
    df = inputDf.copy(deep=True)
    #print("writeLastParquetAndAssociatedFiles: Input df contains Sold column:", "Sold" in df.columns)
    rawParquetFileName = getLastRawParquetFileName()
    if not df.empty:
        modelSoldDf = df[df["Sold"] == True]
        modelNotSoldDf = df[df["Sold"] != True]
        modelYearsUniqueSoldDf = modelSoldDf.drop_duplicates(subset=["year"])
        modelYearsUniqueNotSoldDf = modelNotSoldDf.drop_duplicates(subset=["year"])
        modelYearsSold = []
        modelYearsNotSold = []
        for index, row in modelYearsUniqueSoldDf.iterrows():
            modelYearsSold.append(row["year"])
        for index, row in modelYearsUniqueNotSoldDf.iterrows():
            modelYearsNotSold.append(row["year"])
        # get the combined unique model years (includes both sold and not sold years)
        # so this means if the year is in this list then the model year file needs to be updated
        # FYI.  using list(set(modelYearsSold + modelYearsNotSold)).sort() does not work.  You must do in
        # 2 separate steps for some reason as looks like sort looks to do it in place and not return the list.
        combinedModelYears = list(set(modelYearsSold + modelYearsNotSold))
        combinedModelYears.sort()
        #print("modelYearsNotSold", modelYearsNotSold, "modelYearsSold", modelYearsSold)
        #print("combinedModelYears", combinedModelYears)
        for year in combinedModelYears:
            modelYearSoldFileName = getFileNameForSoldRawParquet(MODEL, year)
            modelYearSoldCsvFileName = getFileNameForSoldCsv(MODEL, year)
            if Path(modelYearSoldFileName).exists():
                modelYearSoldRawParquetDf = pd.read_parquet(modelYearSoldFileName)
            else:
                print("writeLastParquetAndAssociatedFiles: ", modelYearSoldFileName, "does not exist. Using empty dataframe with the appropriate columns")
                modelYearSoldRawParquetDf = pd.DataFrame(columns = df.columns)
            #print("writeLastParquetAndAssociatedFiles: Gotten modelYearSoldRawParquetDf contains Sold column:", "Sold" in modelYearSoldRawParquetDf.columns)
            if year in modelYearsSold:
                # append the Sold entries from the raw parquet df for that model year to the Sold model year raw parquet df
                # and drop any duplicates
                modelYearSoldRawParquetDf = pd.concat([modelYearSoldRawParquetDf, modelSoldDf[modelSoldDf["year"] == year]])
                modelYearSoldRawParquetDf.drop_duplicates(subset=["vin"], keep='last', inplace=True)
            if year in modelYearsNotSold:
                # remove any VIN entires, if any, from model year sold parquet df that are not sold in the raw parquet df
                modelNotSoldMergeColumnsOnlyDf = modelNotSoldDf[modelNotSoldDf["year"] == year][["vin"]] # while the filtering on year is not needed it can reduce processing later on due to a smaller size
                if "WhoDidMergeComeFrom_" in modelYearSoldRawParquetDf.columns:
                    # remove it to ensure only one such column results from the merge
                    modelYearSoldRawParquetDf.drop(columns=["WhoDidMergeComeFrom_"], axis=1, inplace=True)
                modelYearSoldRawParquetDf = modelYearSoldRawParquetDf.merge(modelNotSoldMergeColumnsOnlyDf,  left_on="vin", right_on="vin", how='left', indicator = "WhoDidMergeComeFrom_")
                modelYearSoldRawParquetDf = modelYearSoldRawParquetDf[modelYearSoldRawParquetDf["WhoDidMergeComeFrom_"] != 'both']
                # remove the WhoDidMergeComeFrom_ column as not needed in final model sold dataframe
                modelYearSoldRawParquetDf.drop(columns=["WhoDidMergeComeFrom_"], axis=1, inplace=True)
            # Write the sorted by VIN sold model year parquet df to its corresponding file.  Remove the Sold column
            modelYearSoldRawParquetDf.sort_values(by=["vin"], inplace=True)
            if "Sold" in modelYearSoldRawParquetDf.columns:
                # It's possible that "Sold" might not be in the modelYearSoldRawParquetDf if the year was not in  modelYearsSold
                # as we would not concatenate with a df that has a Sold column.
                modelYearSoldRawParquetDf.drop(["Sold"], axis=1, inplace=True)
            modelYearSoldRawParquetDf.to_parquet(modelYearSoldFileName, index=False)
            # Write out the csv style transformed sold model year df to the csv file
            cvsStyleDf = transformRawDfToCsvStyleDf(modelYearSoldRawParquetDf)
            cvsStyleDf.to_csv(modelYearSoldCsvFileName, index=False)
        
    # Now remove the sold entries from the df as the Last Parquet file it is written to should only contain non sold entries.
    df = df[df["Sold"] != True]
    df.drop(["Sold"], axis=1, inplace=True)
    df.to_parquet(rawParquetFileName, index=False)
    # For debugging only comment out when done.
    # Note that certain columns cannot be written out as it can cause issues when the .csv is opened in EXCEL and then saved in
    # .xlsx format and then the .xlsx hangs when it is opened.  Seems like the columns that have dictionaries, or lists in them cause issues.
    # So raw columns like options, families, etc cause issues and cannot be written out as is so are skipped as not needed for debug
    # at this point.  If needed would need to process them like in the model csv file.
    #debugCols = ["vin", "isTempVin", 'isSmartPath', 'isUnlockPriceDealer', "dealerCategory", "price.baseMsrp", "price.totalMsrp", "price.sellingPrice", "price.dioTotalDealerSellingPrice", "price.advertizedPrice", "price.nonSpAdvertizedPrice", "price.dph", "price.dioTotalMsrp", "price.dealerCashApplied", "isPreSold", "holdStatus", "year", "drivetrain.code", "model.marketingName", "extColor.marketingName", "intColor.marketingName", "dealerMarketingName", "dealerWebsite", "eta.currFromDate", "eta.currToDate", 'transmission.transmissionType', 'mpg.combined', 'mpg.city', 'mpg.highway', 'engine.engineCd', 'engine.name', "FirstAddedDate", "LastChangedDateTime", "infoDateTime"]
    #df.to_csv(rawParquetFileName[:-7] + "csv", columns= debugCols, index=False)

def debugCheckingDf(df, msg= "", vin= ""):
    # Used to check various aspect of the dataframe at various points to see if something is or is not present
    # for debugging puposes.
    return
    if "vin" in df.columns:
        vinColumnName = "vin"
    elif "VIN" in df.columns:
        vinColumnName = "VIN"
    else:
        vinColumnName = ""
    if not vin:
        vinLookingFor = "3TMKB5FN0RM015921"
    else:
        vinLookingFor = vin
    if vinColumnName:
        if not (len(df[df[vinColumnName] == vinLookingFor])):
            print("debugCheckingDf: At point", msg, ": vin/VIN",vinLookingFor, "not found in the df" )
        else:
            print("debugCheckingDf: At point", msg, ": vin/VIN",vinLookingFor, "was found in the df" )
    else:
        print("debugCheckingDf: At point", msg, ": df has no vin or VIN column name")
        

def updateDfsLastChangedDateTimeUsingChangeHistory(df, lastParquetDf, changeHistoryCurrentOnlyDf):
    # Updates copies of the df (a passed CSV style df), and lastParquetDf (a passed raw parquet df) LastChangedDateTimeColName 
    # values using the infoDateTime field of the changeHistoryCurrentOnlyDf for VINs in those dataframes with MODED in changeHistoryCurrentOnlyDf, 
    # and returns them as a tuple (df, lastParquetDf)
    # Thus only current changes (between the current and prior dataframe) have the LastChangeDate
    # changeHistoryCurrentOnlyDf can be empty but must have the normal column names for a change history.
    #
    df = df.copy(deep=True)
    lastParquetDf = lastParquetDf.copy(deep=True)
    changeHistoryOnlyMergeColsDf = changeHistoryCurrentOnlyDf[["VIN", rowChangeTypeColumnName]].copy(deep=True)
    changeHistoryOnlyMergeColsWithModedDf = changeHistoryOnlyMergeColsDf[changeHistoryOnlyMergeColsDf[rowChangeTypeColumnName] == rowModifiedVINContentsIndicator]
    dfMerged = df.merge(changeHistoryOnlyMergeColsWithModedDf, left_on="VIN", right_on="VIN", how='left', indicator = "WhoDidMergeComeFrom_")
    # if MODED VIN in both then set the LastChangedDateTimeColName value with the infoDateTime  value from that row.
    dfMerged[LastChangedDateTimeColName] = dfMerged[LastChangedDateTimeColName].where(dfMerged["WhoDidMergeComeFrom_"] != "both", dfMerged["infoDateTime"])
    # Note that when different left_on and right_on columns names used for merge the right_on column name is also added as a column to the merge result in 
    # addition to any other columns in the right df, possibly with suffixes.  This occurs even if both dfs are empty (i.e. no rows) but have
    # column names.
    dfLastParquetMerged = lastParquetDf.merge(changeHistoryOnlyMergeColsWithModedDf, left_on="vin", right_on="VIN", how='left', indicator = "WhoDidMergeComeFrom_")
    # if MODED VIN in both then set the LastChangedDateTimeColName value with the infoDateTime  value from that row.
    dfLastParquetMerged[LastChangedDateTimeColName] = dfLastParquetMerged[LastChangedDateTimeColName].where(dfLastParquetMerged["WhoDidMergeComeFrom_"] != "both", dfLastParquetMerged["infoDateTime"])
    
    # Remove the temporary columns "WhoDidMergeComeFrom_", and rowChangeTypeColumnName column from both dfs and
    # VIN from the dfLastParquetMerged before returning them
    dfMerged.drop(["WhoDidMergeComeFrom_", rowChangeTypeColumnName], axis=1, inplace=True)
    dfLastParquetMerged.drop(["WhoDidMergeComeFrom_", rowChangeTypeColumnName, "VIN"], axis=1, inplace=True)
    return (dfMerged, dfLastParquetMerged)
    

def getChangeHistoryFinalColumnsSelect(originalColumnsInOld, originalColumnsInNew):
    # returns an ordered list of columns for the final columns we want in the change history
    # The original columns passed are are in order we want for the dataframes.
    # It is assumed that the selection are for dfChangeHistory in getChangeHistory right before
    # it returns it to the caller. 
    #nonHistoryCsvFinalColumns = columnsForEmptyDfFinalCsv  # this is an ordered list of how we want the column names to be ordered
    finalColumnsSelect = []
    # new column in the change history dataframe indicating the type of change for that row (added, modified, removed, nothing changed)
    finalColumnsSelect.append(rowChangeTypeColumnName)
    finalColumnsSelect.append(rowChangeDateTime)
    for column in originalColumnsInNew:
        if column == "Options":
            # insert this one right before Options
            finalColumnsSelect.append(rowModificationsColumnName)
        finalColumnsSelect.append(column)
    return finalColumnsSelect

def valueIsNanNoneNull(value):
    return (value is None) or (isinstance(value, float) and np.isnan(value))
    
def getOptionDifferences(oldOptions, newOptions):
    # returns a string of the differences between the old and new options.  If null is returned then there are no differences.
    diffs = ""
    removedOptionsStr = ""
    addedOptionsStr = ""
    sameOptionsStr = ""
    oldOptionsIsStrType = isinstance(oldOptions, str)
    newOptionsIsStrType = isinstance(newOptions, str)
    if (not oldOptionsIsStrType) or (not newOptionsIsStrType):
        removedOptionsStr = str(oldOptions)
        addedOptionsStr = str(newOptions)
    else: # both are strings
        # split up the Options into each individual option using the options separator "|" and strip of any leading
        # or trailing white spaces.
        oldOptionsSplit = []
        for option in oldOptions.split("|"):
            oldOptionsSplit.append(option.rstrip().lstrip())
        # Note that the list(dict.fromkeys(oldOptionsSplit)) only removes case sensitive duplicates which the above are not (different case)
        oldOptionsSplit.sort(key=str.lower) # sort case insensitive to make it easy to visually look through the changed options
        # See below for TODO on how to resolve this.
        oldOptionsSplit = list(dict.fromkeys(oldOptionsSplit)) # remove duplicates (keeping order) as sometimes these do occur for some unknown reason
        newOptionsSplit = []
        for option in newOptions.split("|"):
            newOptionsSplit.append(option.rstrip().lstrip())
        newOptionsSplit.sort(key=str.lower) # sort case insensitive to make it easy to visually look through the changed options
        newOptionsSplit = list(dict.fromkeys(newOptionsSplit)) # remove duplicates (keeping order) as sometimes these do occur for some unknown reason
        # now get same and added
        oldIndiciesOfOldIsSameAsNew = []
        newIndex = 0
        for newOption in newOptionsSplit:
            newOptionForCompare = newOption.lower().rstrip(":")
            # newOptionForCompare = newOption.replace("  ", " ")
            newOptionForCompare = newOptionForCompare.replace("[installed_msrp]", "").rstrip().rstrip(":")
            wasInOld = False
            oldIndex = 0
            for oldOption in oldOptionsSplit:
                oldOptionForCompare = oldOption.lower().rstrip(":").rstrip()
                # oldOptionForCompare = oldOption.replace("  ", " ")
                oldOptionForCompare = oldOptionForCompare.replace("[installed_msrp]", "").rstrip().rstrip(":")
                if newOptionForCompare == oldOptionForCompare:
                    if not (oldIndex in oldIndiciesOfOldIsSameAsNew):
                        sameOptionsStr += newOption + " | "
                    wasInOld = True
                    oldIndiciesOfOldIsSameAsNew.append(oldIndex)
                    # Note that going through all the entries to find duplicates increases the time it takes to run through this but hopefully it is still acceptable.
                    # TODO An alternative to the above to decrease execution time 
                    # is to just initially remove case insenstive massaged (trimmed, installed_msrp removed, etc)
                    # duplicates from the newOptionsSplit
                    # and the oldOptionsSplit, keeping only the first one, before running through these for loops.
                    # But then you have an issue if different cases mean something different as mentioned above.
                    #break
                oldIndex += 1
            if not wasInOld:
                # then must be an added one from new
                addedOptionsStr += newOption + " | "
            newIndex += 1
        # now process removed ones
        for oldIndex in range(len(oldOptionsSplit)):
            if not (oldIndex in oldIndiciesOfOldIsSameAsNew):
                # must be removed
                removedOptionsStr += oldOptionsSplit[oldIndex] + " | "
        
    if sameOptionsStr:
        sameOptionsStr = " :Same---> " + sameOptionsStr
    if removedOptionsStr:
        removedOptionsStr = " :Removed---> " + removedOptionsStr
    if addedOptionsStr:
        addedOptionsStr = " :Added---> " + addedOptionsStr
    if (not removedOptionsStr) and (not addedOptionsStr):
        # They are all the same Options
        diffs = ""
    else:
        diffs =  addedOptionsStr + removedOptionsStr + sameOptionsStr
    return diffs

def determineRowDifferences( row, columnsToIgnore, originalColumnsInOld, originalColumnsInNew, mergeSuffixRight):
    # Determines if there are any differences between the row's new values and the row's old values for each
    # column name in row that is not in columnsToIgnore and updates the row's rowChangeTypeColumnName column, and 
    # rowModificationsColumnName column values.
    # Assumes any such column name, not in columnsToIgnore, must be guaranteed to be in either originalColumnsInNew, or originalColumnsInOld
    # If the row has a column name say for example "Color" and that name is not in columnsToIgnore, 
    # and in both originalColumnsInNew And originalColumnsInOld
    # then the new value is row["Color"], and the old value is row["Color" + mergeSuffixRight].
    # If there are columns only in originalColumnsInNew, or only in originalColumnsInOld, and not in columnsToIgnore
    # then that is also considred a difference although this probably cannot happen if 
    # the row was created from a merge of old to new and old and new were csv style dfs (which must have the same columns)
    # and any other columns added in for processing are to be ignored via the columnsToIgnore. 
    # If there are any differences the row's rowModificationsColumnName column value (a str type column)
    # is set with the name of each column that was different along with the old and new values. 
    # For columns only in one or the other there is an indication of that and 
    # only one value is shown.  
    # Also the row's rowChangeTypeColumnName column value is to be updated with an indication if there was any difference or not
    #
    global debugEnabled
    namesOfModifiedFieldsString = ""
    rowIsTheSame = True
    columns1 = []
    for column1 in originalColumnsInNew:
        if not (column1 in columnsToIgnore):
            columns1.append(column1)
    columns1.sort()
    columns2 = []
    for column2 in originalColumnsInOld:
        if not (column2 in columnsToIgnore):
            columns2.append(column2)
    columns2.sort()
    if columns1 == columns2:
        # Both have all the exact same column labels (assumed to be unique)
        # At this point we can sort case insensitive since operations below do not depend on the order.  
        # This makes it visually easy to find the column in a line of changed columns. 
        columns1.sort(key=str.lower)
        for column in columns1:
            oldValue = row[column+mergeSuffixRight]  # this column must exist due to the merge of old to new as the old has a new column created as the common column name +  
            newValue = row[column]
            oldValueForCompare = oldValue
            newValueForCompare = newValue
            if column == "Options":
                diffs = getOptionDifferences(oldValue, newValue)
                if diffs:
                    rowIsTheSame = False
                    namesOfModifiedFieldsString += column + " :: " + diffs + " || "
            elif (oldValueForCompare != newValueForCompare):
                if not (valueIsNanNoneNull(newValueForCompare) and valueIsNanNoneNull(oldValueForCompare)):
                    rowIsTheSame = False
                    namesOfModifiedFieldsString += column + " :: " + str(oldValue) + " --> " +  str(newValue) + " || "
    else:
        # Not sure if this case can actually occur if both are csv style dfs from a merge
        print("Warning: determineRowDifferences: columns names in old orginal and new original were not all the same.  Handling this.")
        columnsTemp = columns1 + columns2
        columnsCombined = []
        for column in columnsTemp:
            if column not in columnsCombined:
                columnsCombined.append(column)
        # At this point we can sort case insensitive since operations below do not depend on the order.  
        # This makes it visually easy to find the column in a line of changed columns. 
        columnsCombined.sort(key=str.lower)
        for column in columnsCombined:
            if (column in columns2) and (column in columns1):
                # column in both
                oldValue = row[column+mergeSuffixRight]  # this column must exist due to the merge of old to new as the old has a new column created as the common column name +  
                newValue = row[column]
                oldValueForCompare = oldValue
                newValueForCompare = newValue
                if column == "Options":
                    diffs = getOptionDifferences(oldValue, newValue)
                    if diffs:
                        rowIsTheSame = False
                        namesOfModifiedFieldsString += column + " :: " + diffs + " || "
                elif (oldValueForCompare != newValueForCompare):
                    if not (valueIsNanNoneNull(newValueForCompare) and valueIsNanNoneNull(oldValueForCompare)):
                        rowIsTheSame = False
                        namesOfModifiedFieldsString += column + " :: " + str(oldValue) + " --> " +  str(newValue) + " || "
                        #if debugEnabled:
                        #    print("getNamesOfModifiedFieldsIntoString index1, column1, index2, details1.at[index1, column1], details2.at[index2, column1]", index1, column1, index2, details1.at[index1, column1], details2.at[index2, column1])
            elif (column not in columns2):
                # column not in column2 so a column was added as originalColumnsInNew has the new  and  originalColumnsInOld has the old
                rowIsTheSame = False
                newValue = row[column]
                namesOfModifiedFieldsString += column + " :: " + "-" + " --Added-> " +  str(newValue) + " || "
            else:
                # column must not be in columns1 as combined has only columns in 1 and or 2
                # column not in column1 so a column was removed as originalColumnsInNew has the current and  originalColumnsInOld has the old
                rowIsTheSame = False
                oldValue = row[column]  # Since the column name does not overlap the old one does not have the mergeSuffixRight appended to it.
                namesOfModifiedFieldsString += column + " :: " + str(oldValue) + " --Removed-> " + "-"  + " || "        
    if rowIsTheSame:
        row[rowChangeTypeColumnName] = rowSameVINContentsIndicator
        row[rowModificationsColumnName] = None
    else:
        row[rowChangeTypeColumnName] = rowModifiedVINContentsIndicator
        row[rowModificationsColumnName] = namesOfModifiedFieldsString
        
    return row

def getChangeHistory(oldDf, newDf, lastChangeHistorydf):
    # returns a data frame  that is the concatenation of the lastChangeHistorydf
    # and the added, modified, removed entries between the passed old df and the new df with 
    # an indicator if the old and new value in the row was different and the old value as well, and
    # then limits the result to only the last 2 weeks of entries (infoDateTime field is not older than 2 weeks)
    # and also returns a dataframe that does not include the lastChangeHistorydf.
    # The tuple returned is  (changeHistoryWithLastDf,  changeHistoryCurrentOnlyDf)
    # All passed data frames must be df raw to csv style generated dataframes 
    #
    global columnsForEmptyChangeHistoryCsvDf
    global changeHistoryUseThisAsTodaysDateForTesting
    global maxDaysOldToKeep
    #print(datetime.datetime.now(), "getChangeHistory: Entered")
    print("Determining change history by analyzing ", len(newDf), " entries. Warning: This could take up to 90 seconds for approx 40000 entries")
    #print("len(oldDf)", len(oldDf), "len(newDf)", len(newDf))
    # make copies of the oldDf and newDf to avoid modifying them.
    dfOld = oldDf.copy(deep=True)
    dfNew = newDf.copy(deep=True)
    
    # initialize the return dataframe
    dfChangeHistory = pd.DataFrame(columns = columnsForEmptyChangeHistoryCsvDf)
    
    # Save off the original column names in both to make operations later easier since duplicate column names with
    # suffixes will be added.
    originalColumnsInOld = dfOld.columns
    originalColumnsInNew = dfNew.columns
    # Set the right merge suffix that will be appended to the right df column names in a merge that are the same as the left
    # column names
    mergeSuffixRight = "_y"
    
    # create a new merged df so that for any common VIN (in both old and new) we tack on new columns to dfNew 
    # that are the existing column names (from dfOld) with the mergeSuffixRight and those new columns contain the values from
    # the old df.
    # It also adds a column WhoDidMergeComeFrom_ so we can tell if the row was only in dfNew or in both 
    dfNewMerged = dfNew.merge(dfOld, left_on="VIN", right_on="VIN", how='left', suffixes = (None, mergeSuffixRight), indicator = "WhoDidMergeComeFrom_")
    
    # The next merge does the same thing but in the opposite direction. In this one we only care to know which VINs
    # in the old one were not in the new one and can get this from WhoDidMergeComeFrom_  
    
    dfNewMergeColumnsToUse = dfNew[["VIN"]]
    dfOldMerged = dfOld.merge(dfNewMergeColumnsToUse, left_on="VIN", right_on="VIN", how='left', indicator = "WhoDidMergeComeFrom_")
    
    #Now add a RowChangeType column to both dfNewMerged, and dfOldMerged and initialize to indicate the 
    # the row previously existed and did not change (i.e the VIN is in both and all the data associated with it is the same).
    # Also add a rowModificationsColumnName and initialize it to None for no modifications.
    dfNewMerged[rowChangeTypeColumnName] = rowSameVINContentsIndicator
    dfNewMerged[rowModificationsColumnName] = None
    dfOldMerged[rowChangeTypeColumnName] = rowSameVINContentsIndicator
    dfOldMerged[rowModificationsColumnName] = None
    
    
    # Update the RowChangeType column for those merged dfs.
    # The WhoDidMergeComeFrom_ is used to determine if the row was in left only, both.  right only is not possible because 
    # the merge how is 'left'. Thus we can determine if the row was added to new or removed from old 
    dfNewMerged[rowChangeTypeColumnName] = dfNewMerged[rowChangeTypeColumnName].where(dfNewMerged["WhoDidMergeComeFrom_"] != 'left_only', rowAddedNewVINIndicator )
    dfOldMerged[rowChangeTypeColumnName] = dfOldMerged[rowChangeTypeColumnName].where(dfOldMerged["WhoDidMergeComeFrom_"] != 'left_only', rowRemovedVINIndicator )
    
    columnsToIgnoreForComparison = ["WhoDidMergeComeFrom_", rowChangeTypeColumnName, rowModificationsColumnName, "VIN", "CenterLat", "CenterLong", "DistanceFromCenter", LastChangedDateTimeColName, "infoDateTime", "FirstAddedDate"]
    # Now do the determination on just the rows that were in both.  We can create a slice of just those rows with common VINs
    # and run the determination on then and then the result is what gets concatenated later on for that.
    dfNewMergeOnlyCommonVins = dfNewMerged[dfNewMerged["WhoDidMergeComeFrom_"] == 'both'].copy(deep=True)
    dfNewMergeOnlyCommonVins = dfNewMergeOnlyCommonVins.apply(determineRowDifferences, axis=1, args= (columnsToIgnoreForComparison, originalColumnsInOld, originalColumnsInNew, mergeSuffixRight))
    
    # Concatenate just the new and old merged dfs together first since will need to do renames
    # of mergeSuffixRight suffixed old values columns which lastChangeHistorydf already has these renamed columns in them
    # and would cause that to fail if it was also included as can't rename to a column name that already exists.
    # Also before this need to reset the index in the dfs as the concat can fail without that.
    #dfNewMerged.reset_index(drop=True, inplace=True)
    #dfNewMergeOnlyCommonVins.reset_index(drop=True, inplace=True)
    #dfOldMerged.reset_index(drop=True, inplace=True)
    dfChangeHistory = pd.concat([
        dfNewMerged[dfNewMerged[rowChangeTypeColumnName] == rowAddedNewVINIndicator],
        dfNewMergeOnlyCommonVins[dfNewMergeOnlyCommonVins[rowChangeTypeColumnName] == rowModifiedVINContentsIndicator],
        dfOldMerged[dfOldMerged[rowChangeTypeColumnName] == rowRemovedVINIndicator] 
        ])
    
    # Updated the LastChangedDateTimeColName for MODED entries with the infoDateTime column
    dfChangeHistory[LastChangedDateTimeColName] = dfChangeHistory[LastChangedDateTimeColName].where(dfChangeHistory[rowChangeTypeColumnName] != rowModifiedVINContentsIndicator, dfChangeHistory["infoDateTime"])
    # Add the Change DateTime column with the current datetime
    today = datetime.datetime.today()
    format_time_string = "%Y-%m-%d %H:%M:%S"
    dfChangeHistory[rowChangeDateTime] = today.strftime(format_time_string)
    
    changeHistoryCurrentOnlyDf = dfChangeHistory.copy(deep=True)
    
    # Now concatenate the new change history to the last change history with the last change history first
    dfChangeHistory = pd.concat([lastChangeHistorydf, dfChangeHistory])
    # Now filter these to only keep the ones that were at most maxDaysOldToKeep days old (rowChangeDateTime within the last maxDaysOldToKeep).
    if not (changeHistoryUseThisAsTodaysDateForTesting is None):
        print("!!!!!!!! Warning: getChangeHistory:  Using a test date in place of Todays Date for testing date filtering. Test date is:", changeHistoryUseThisAsTodaysDateForTesting)
        # override the actual current today gotten above with this test date.
        # This allows us to include none, some, or all entries in lastChangeHistorydf for testing purposes of the days to keep filtering
        today = datetime.datetime.strptime(changeHistoryUseThisAsTodaysDateForTesting, format_time_string)
    lowerKeepDate = today - datetime.timedelta(days=maxDaysOldToKeep)
    lowerKeepDateStr = lowerKeepDate.strftime(format_time_string)
    dfChangeHistory = dfChangeHistory[dfChangeHistory[rowChangeDateTime] >= lowerKeepDateStr ]
    
    # select which columns we want to keep and their order
    # TODO we could probably just do this with a fixed list defined up where columnsForEmptyChangeHistoryCsvDf
    # since we know what columns must be in the csv styled old and new dfs.
    # although calculating them keeps us from having to remember to update additional fixed lists 
    finalColumnsSelect = getChangeHistoryFinalColumnsSelect(originalColumnsInOld, originalColumnsInNew)
    dfChangeHistory = dfChangeHistory[
        finalColumnsSelect
    ].copy(deep=True)
    dfChangeHistory.reset_index(drop=True, inplace=True) 
    if len(dfChangeHistory) and ("DistanceFromCenter" in dfChangeHistory.columns):
        distanceFormula = getExcelDistanceFormulaForCsv(tuple(dfChangeHistory.columns), 2)
        dfChangeHistory["DistanceFromCenter"] = None
        #print("Change History file distanceFormula", distanceFormula)
        dfChangeHistory.at[0,"DistanceFromCenter"] =  distanceFormula
    #print(datetime.datetime.now(), "getChangeHistory: Exited")
    return (dfChangeHistory, changeHistoryCurrentOnlyDf)

def getEnvVariableTestMode():
    # returns a tuple that indicates if the environement variable indicates test mode is enabled
    # testModeEnvOn is boolean and the other values are strings.
    # ( testModeEnvOn , testModeEnvVarName,  testModeEnvValue) 
    testModeEnvVarName = "MODEL_UPDATE_VEHICLES_TEST_MODE"
    testModeEnvValue = os.environ.get(testModeEnvVarName)
    testModeEnvOn = False
    if (testModeEnvValue is not None) and (testModeEnvValue.upper() == "ON"):
        testModeEnvOn = True
    return (testModeEnvOn, testModeEnvVarName, testModeEnvValue)
    
def getEnvVariableTestModeTodayDate():
    # returns a tuple that indicates if the environement variable indicates the todays date to use for some testing.
    # testModeEnvOn is boolean and the other values are strings.
    # (testModeTodayDateEnvVarName, testModeTodayDateEnvValue) 
    testModeTodayDateEnvVarName = "MODEL_UPDATE_VEHICLES_TEST_MODE_TODAY_DATE"
    testModeTodayDateEnvValue = os.environ.get(testModeTodayDateEnvVarName)
    return (testModeTodayDateEnvVarName, testModeTodayDateEnvValue)
    

def update_vehicles_and_return_df(useLocalData = False, testModeOn = False):
    """Generate a curated database file for the given vehicle model environment variable, as well as
    returning that database as a dataframe and status of the inventory Get.
    Returns:  a tuple   (dataframe, status ) where dataframe is a pandas dataframe and
    status is a dictionary of ("completedOk", "numberRawVehiclesFound", "numberRawVehiclesMissing", "completionMsg")
    for that dataframe
    In the following the term using local data =  (useLocalData or USE_LOCAL_DATA_ONLY ) and
    test mode enabled = (testModeOn or environment variable MODEL_UPDATE_VEHICLES_TEST_MODE=ON
    When using local data and test mode is disabled  we use the data from the 
    last raw parquet file and last raw status info file 
    for the data we normally get from the inventory website.
    This basically results in no change to those files once the update_vehicles is run, but supplies
    any external caller of update_vehicles_and_return_df with this data, transformed to csv sytle dataframe,
    and status as well.
    When test mode is enabled,  we use the data from the 
    test inventory parquet file and test inventory status info file
    for the data we normally get from the inventory website 
    When not using local data and test mode is not enabled we get the data and status info from the inventory website.
    """
    global columnsForEmptyDfParquet
    global columnsForEmptyDfFinalCsv
    global changeHistoryUseThisAsTodaysDateForTesting
    global PROGRAM_VERSION
    print(PROGRAM_VERSION)
    if not MODEL:
        sys.exit("Set the MODEL environment variable first")
    print("update_vehicles: Getting inventory for model", MODEL)
    testModeEnvOn , testModeEnvVarName,  testModeEnvValue = getEnvVariableTestMode()
    testModeTodayDateEnvVarName, testModeTodayDateEnvValue = getEnvVariableTestModeTodayDate()
    print("Enviroment variable",testModeTodayDateEnvVarName, " = ",  testModeTodayDateEnvValue)
    print("Enviroment variable", testModeEnvVarName, " = ",  testModeEnvValue)
    print("Passed parameter testModeOn is", testModeOn)
    print("Passed parameter useLocalData is", useLocalData)
    print("Static Var USE_LOCAL_DATA_ONLY is", USE_LOCAL_DATA_ONLY)
    testModeEnabled = False
    if (testModeEnvOn or testModeOn):
        testModeEnabled = True
        print("Running in Test Mode")
    if (not(testModeTodayDateEnvValue is None)) and testModeEnabled:
        # only use test today date if test mode enabled
        changeHistoryUseThisAsTodaysDateForTesting = testModeTodayDateEnvValue
    rawParquetFileExists = False
    statusOfGetAllPagesFileExists = False
    df = pd.DataFrame()
    statusOfGetAllPages = {"completedOk": False, "numberRawVehiclesFound": 0, "numberRawVehiclesMissing": 100000, "completionMsg": "", "date": ""}
    
    # Read in the last inventory gotten (last parquet file) and associated status file.
    lastRawParquetFileExists, lastRawStatusOfGetAllPagesFileExists, lastParquetDf, statusOfGetAllPagesLastParquet = readLastParquetDf()

    # Save off the original last parquet for use later on in getting change history as the lastParquetDf will be modfied
    # below.
    originalLastParquetDF = lastParquetDf.copy(deep=True)
    
    if (USE_LOCAL_DATA_ONLY or useLocalData or testModeEnabled):
        if testModeEnabled:
            print("Using Local Test Data")
        else:
            print("Using Local Data")
        # get the current inventory and status from  a local file
        rawParquetFileExists, statusOfGetAllPagesFileExists, df, statusOfGetAllPages = read_local_data(testModeEnabled)
        if not rawParquetFileExists:
            sys.exit("Error: The raw Parquet file does not exist when using local data")
        if not statusOfGetAllPagesFileExists:
            sys.exit("Error: The Status Info file associated with raw Parquet file does not exist when using local data")
    else:
        # get the current inventory and status from the website
        df, statusOfGetAllPages = get_all_pages()
        
    if df.empty:
        print(f"No vehicles found for model: {MODEL}")
        if not statusOfGetAllPages["completedOk"]:
            print(f"Error: Completion status not Ok for model: {MODEL}, not storing any results in output files and leaving them as is.")
            print(f"update_vehicles_and_return_df returning empty dataframe and status not Ok to caller so caller does nothing")
            # When completion status is not Ok it was decided we don't want to overwrite the stored files but just leave them as is
            # with their last data for any user to access as that is the last valid data we got, and the user can know how old it is by the
            # status file and the infoDateTime field in the inventory file.
            # Even if we are told to use local data on the next run it will return the last valid data we got (when we had completion OK = True)
            # and so no change is seen by the higher level calling program.  We want to avoid the higher level caller
            # thinking we got a valid response of empty when the completion status was not ok thinking there was no
            # inventory for that model anymore which would be incorrect as it was because of an error (incomplete)
            emptyDfWithFinalColumnsForCsv = pd.DataFrame(columns = columnsForEmptyDfParquet)
            return (emptyDfWithFinalColumnsForCsv, statusOfGetAllPages)
        
    # TODO Determine how missing vehicles in the statusOfGetAllPages affects the below.  Do not want to update certain things
    #
    # The following code section updates the df and lastParquetDf appropriately as follows:
    '''
    We want to update the df (current inventory) with the FirstAddedDates, and LastChangedDateTimeColName from the lastParquetDf for VINs in both, 
    and set the FirstAddedDates and LastChangedDateTimeColName to infoDateTime in the df for those new entries (VIN entries not in the lastParquetDf).
    At that point the df is completely updated for use later on.
    Then we want to update the lastParquetDf with everthing in the df  (existing VINs and new VINs) and 
    for VINs in the lastParquetDf that are not in the df (i.e. removed) we mark them as Sold, otherwise we mark an entry
    as not Sold
    At this point the lastParquetDf update is complete and can be used to update sold files later on below and
    once that occurs the sold entries can be removed from the lastParquetDf and the lastParquetDf can be written out.
    
    The above is accomplishes by doing the following:
    A FirstAddedDate column is added to the df (current inventory), and its value is set to the the df infoDateTime for df VINs not in 
    lastParquetDf  (i.e  for VINs that are new or have gone away and reappeared use date of when that entry was gotten from inventory website), 
    otherwise it is set to the FirstAddedDate of the lastParquetDf for the matching VIN  (an exisiting VIN for which
    we have already determined the FirstAddedDate and it is what is in the lastParquetDf).
    LastChangedDateTimeColName is added to the df and its value is set to what is in the lastParquetDf for VINs in both,
    and for VINs only in df it is set to the df infoDateTime.
    A Sold column is added to the lastParquetDf, and its value is set to True 
    A Sold column is added to the df and its value is set to False
    Then any VIN in both lastParquetDf and df has the df row replacing the lastParquetDf row so the lastParquetDf
    is updated with the information from the df (current inventory), and any new VIN entries from 
    the df are added to the last lastParquetDf (all done by concatenting the df to the end of the lastParquetDf
    and then removing duplicate VINs keeping only the last one in the concatenation). 
    Thus the Sold field in those is False, and then 
    any VIN in the lastParquetDf that was not updated, which are those not in the df (current inventory), 
    has the Sold field remaining as True since that VIN has disappered from the df (current inventory) and thus is sold. 
    
    Note:  The Sold column of the lastParquetDf is only needed temporarily for making other
    calculations below and is removed from the lastParquetDf (along with removing the sold VIN rows from it)
    before it is written out to its file as only not sold entries are retained in the lastParquetDf file.
    '''
    # Add a Sold column to df and set all to False as this is inventory that is present (from website or local file)
    # This temporary addition will be used below when determining the Sold column for the lastParquetDf
    df["Sold"] = False
    if lastRawParquetFileExists:
        # TODO Do we need to consider when we did not get all the inventory from the website.  I.e. some vehicles were missing,
        # maybe not since on the next update if they reappear then we will update and they are no longer sold
        # although if we are missing some large percentage then we might not want to update the last parquet at all????
        if len(lastParquetDf):
            # it is not empty
            if not("FirstAddedDate" in lastParquetDf.columns):
                # use None
                lastParquetDf["FirstAddedDate"] = None
            if not(LastChangedDateTimeColName in lastParquetDf.columns):
                # use None
                lastParquetDf[LastChangedDateTimeColName] = None
            lastParquetMergeColumnsOnlyDf = lastParquetDf[["vin", "FirstAddedDate", LastChangedDateTimeColName]]
            if "FirstAddedDate" in df.columns:
                # if for some reason that df gotten from the inventory website or local file has a FirstAddedDate, remove it (it shouldn't)
                df.drop(['FirstAddedDate'], axis=1, inplace=True)
            if LastChangedDateTimeColName in df.columns:
                # if for some reason that df gotten from the inventory website or local file has a LastChangedDateTimeColName, remove it (it shouldn't)
                df.drop([LastChangedDateTimeColName], axis=1, inplace=True)
            if "WhoDidMergeComeFrom_" in df.columns:
                # if for some reason that df has this which it shouldn't, remove it
                df.drop(['WhoDidMergeComeFrom_'], axis=1, inplace=True)
            # Set all entries in lastParquetDf to initially sold. This will later on be overriden if there is a matching VIN in the new raw df, 
            # otherwise it must be sold if it no longer appears in the new raw df which was obtained from the inventory website.
            lastParquetDf["Sold"] = True
            # Note that the merge below will add a FirstAddedDate, LastChangedDateTimeColName, and WhoDidMergeComeFrom_ to df even if
            # there are no VINs in common between df and lastParquetMergeColumnsOnlyDf, those not matching VINs in df
            # will have either None or NaN in the FirstAddedDate and LastChangedDateTimeColName column
            # how = 'left' will keep vehicle entry in df even if can't find vin for it in lastParquetMergeColumnsOnlyDf, so FirstAddedDate will show up as blank or NAN for those.
            # Without the how = 'left' any row we can't find the matching vin would be removed from df which we don't want.
            df = df.merge(lastParquetMergeColumnsOnlyDf, left_on="vin", right_on="vin", how='left', indicator = "WhoDidMergeComeFrom_")
            #df["FirstAddedDate"] = df["FirstAddedDate"].where(df["WhoDidMergeComeFrom_"] == "both", firstAddedDate)
            # for those entries that were not in both, it was a new VIN in df so use the infoDateTime value for that row also as the FirstAddedDate
            # and LastChangedDateTimeColName
            df["FirstAddedDate"] = df["FirstAddedDate"].where(df["WhoDidMergeComeFrom_"] != "left_only", df["infoDateTime"])
            df[LastChangedDateTimeColName] = df[LastChangedDateTimeColName].where(df["WhoDidMergeComeFrom_"] != "left_only", df["infoDateTime"])
            # drop the merge info column from the df as no longer need it.
            df.drop(["WhoDidMergeComeFrom_"], axis=1, inplace=True)
            # append the df to the last raw parquet
            lastParquetDf = pd.concat([lastParquetDf, df])
            # drop duplicate VINs keeping the last one encountered as when there are common VINs then the df is the one we want to keep
            # as it has the latest information we want to keep,
            # and as the df is concatenated to the end of lastParquetDf it will be the last occurrence
            # In regards to the Sold column this basically replaces for VINs in both the Sold of the lastParquetDf (True)
            # with the Sold of the df (False) since when in both those are not Sold entries.  And thus any other VIN entires in lastParquetDf
            # are left as sold as those VINs aren't in df  (disappered from the current inventory).
            lastParquetDf.drop_duplicates(subset=["vin"], keep='last', inplace=True)
        else:
            # In this case all VINs in df are first time added so use the date when they were found, 
            # and make lastParquetDf the same as df
            df["FirstAddedDate"] = df["infoDateTime"]
            df[LastChangedDateTimeColName] = df["infoDateTime"]
            lastParquetDf = df.copy(deep=True)
    else:
        # lastParquetDf file does not exist
        # Make all df FirstAddedDate None for unknown to alert us of this, 
        # and make lastParquetDf same as df in this case
        df["FirstAddedDate"] = None
        df[LastChangedDateTimeColName] = None
        lastParquetDf = df.copy(deep=True)
        
    # drop Sold column in current inventory (df), as no longer needed
    df.drop(["Sold"], axis=1, inplace=True)
    
    df.sort_values("vin", inplace=True)
    df = transformRawDfToCsvStyleDf(df)
    
    # Read in the change history file to get the last change history
    lastChangeHistorydf = readChangeHistoryParquetDf()
    # Get new change history using the original last parquet in a csv style data frame as the old df
    #  and the df (already in csv style) as the new df
    originalLastParquetInCsvStyleDf = transformRawDfToCsvStyleDf(originalLastParquetDF)
    changeHistoryDf, changeHistoryCurrentOnlyDf = getChangeHistory(originalLastParquetInCsvStyleDf, df, lastChangeHistorydf)
    # write out the change history to its associated files
    changeHistoryDf.to_parquet(getChangeHistoryParquetFileName(), index=False)
    changeHistoryDf.to_csv(getChangeHistoryCsvFileName(), index=False)
    
    # Update the df and lastParquetDf LastChangedDateTimeColName values using the MODED entries from changeHistoryCurrentOnlyDf
    df, lastParquetDf = updateDfsLastChangedDateTimeUsingChangeHistory(df, lastParquetDf, changeHistoryCurrentOnlyDf)
    #  
    # Write out the sorted Last parquet data and associated files.
    # Do this after all the above in case an exception occurs so that all the above has completed before
    # we write out what is now the last inventory that the next run of this program bases change history on.
    lastParquetDf.sort_values("vin", inplace=True)
    writeLastParquetAndAssociatedFiles(lastParquetDf)
    writeCompletionStatusToFile(statusOfGetAllPages)
    
    # Prune the Sold files (of old temp VIN entries, etc)
    pruneSoldFiles(MODEL)
    
    # reset the index as the returned df assumes it. 
    df.reset_index(drop=True, inplace=True)  # drop keeps from inserting current index as a column in dataframe
    
    # Write the data out to its corresponding file.
    df.to_csv(f"output/{MODEL}.csv", index=False)
    return (df, statusOfGetAllPages )

def update_vehicles(useLocalData = False, testModeOn = False):
    """Generate a curated database file for the given vehicle model environment variable."""
    # This function is used to generate the inventory database file for the given vehicle model,
    # but it has no return statement so that the correct system exit code applies
    # (success is 0 anything else is failed) when called by "poetry run update_vehicles".
    update_vehicles_and_return_df(useLocalData = useLocalData, testModeOn = testModeOn)

def extract_marketing_long_names(options_raw):
    """extracts `marketingName` from `Options` col"""
    options = set()
    if isinstance(options_raw, Iterable):
        for item in options_raw:
            gotIt = False
            option = ""
            if item.get("marketingName"):
                gotIt = True
                option = item.get("marketingName")
            elif item.get("marketingLongName"):
                gotIt = True
                option = item.get("marketingLongName")
            else:
                pass
            if gotIt:
                # Remove certain slight differences so as to standardize some options to make searching for or
                # seeing actual differences easier later on.
                # Note that use of re for case insensitive search does add about 2 secs over case insenitive search
                # for 40000 processed entries for the just one string replacement.  If this time starts to increase as more strings are added to be replaced
                # may just do a case insenitive search for some of these as they are usually the same case when present.
                replacementStrings = { "All-Weather": "All Weather"}  # !!!!! must be unique keys for the string to be replaced
                # "[installed_msrp]": "",
                for stringToBeReplaced in replacementStrings:
                    compileObj = re.compile(re.escape(stringToBeReplaced), re.IGNORECASE)
                    option = compileObj.sub(replacementStrings[stringToBeReplaced], option)
                    #option = option.replace(stringToBeReplaced, replacementStrings[stringToBeReplaced])
                option = sanitizeStr(option)
                options.add(option)
    return " | ".join(sorted(options, key=str.lower))  # sort case insensitive to make it easy to find options

if __name__ == "__main__":
    import sys
    useLocalData = False
    testModeOn = False
    if len(sys.argv) > 1:
        useLocalDatastr = sys.argv[1:][0]
        #print("useLocalDatastr:" + useLocalDatastr + ":")
        if useLocalDatastr.upper() ==  "USELOCALDATA":
            useLocalData = True
    if len(sys.argv) > 2:
        testModeOnstr = sys.argv[1:][1]
        #print("testModeOnstr:" + testModeOnstr + ":")
        if testModeOnstr.upper() ==  "TESTMODEON":
            testModeOn = True
    
    #print("useLocalData", useLocalData, "type", str(type(useLocalData)))
    #print("useLocalData", useLocalData, "type", str(type(useLocalData)))
    update_vehicles(useLocalData, testModeOn)

