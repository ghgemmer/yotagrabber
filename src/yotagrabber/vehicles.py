"""Get a list of Toyota/Lexus vehicles from the Toyota/Lexus websites."""
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
from typing import Any, Dict, List, Optional, Tuple, Union, Set, cast

import pandas as pd
import csv
import requests
from collections.abc import Iterable
from yotagrabber import config, wafbypass, vehicleUtilities

PROGRAM_VERSION: str = "Vehicles Program Version 6.5.1 01-10-2026 - Multi-make support"

# Set to True to use local data and skip requests to the Toyota website.
USE_LOCAL_DATA_ONLY: bool = False

DEBUG_ENABLED: bool = False

PAGE_FILES_DEBUG_ENABLED: bool = False

# Get the model that we should be searching for.
MODEL: Optional[str] = os.environ.get("MODEL")
# Get the vehicle make (toyota, lexus)
VEHICLE_MAKE: Optional[str] = os.environ.get("VEHICLE_MAKE")
# optional search parameters to use when want a single location search
MODEL_SEARCH_ZIPCODE: Optional[str] = os.environ.get("MODEL_SEARCH_ZIPCODE")
MODEL_SEARCH_RADIUS: Optional[str] = os.environ.get("MODEL_SEARCH_RADIUS")

changeHistoryUseThisAsTodaysDateForTesting: Optional[str] = None # for testing change the environment variable string to yyyy-mm-dd hh:mm:ss

forceQueryRspFailureTest: int = 0 # set to > 0 to perform tests related to forcing a query response failure

totalPageRetries: int = 0
MAX_TOTAL_PAGE_RETIRES_FOR_MODEL: int = 2 * 3 * 30 

LastChangedDateTimeColName: str = "LastChangedDateTime"
columnsForEmptyDfParquet: List[str] = ["vin", "isTempVin", "dealerCd", "dealerCategory", "price.baseMsrp", "price.totalMsrp", "price.sellingPrice", "price.dioTotalDealerSellingPrice", "price.advertizedPrice", "price.nonSpAdvertizedPrice", "price.dph", "price.dioTotalMsrp", "price.dealerCashApplied", "isPreSold", "holdStatus", "year", "drivetrain.code", "model.marketingName", "extColor.marketingName", "intColor.marketingName", "dealerMarketingName", "dealerWebsite", "eta.currFromDate", "eta.currToDate", 'transmission.transmissionType', 'mpg.combined', 'mpg.city', 'mpg.highway', 'engine.engineCd', 'engine.name', 'cab.code', 'cab', 'bed.code', 'bed', "FirstAddedDate", LastChangedDateTimeColName, "infoDateTime", "options"]
columnsForEmptyDfFinalCsv: List[str] = ["Year", "Model", "Color", "Int Color", "Base MSRP", "Total MSRP", "Selling Price", "Selling Price Incomplete", "Markup", "TMSRP plus DIO", "Shipping Status", "Pre-Sold", "Hold Status", "eta.currFromDate", "eta.currToDate", "VIN", "isTempVin", "Dealer", "Dealer Website", "Dealer State", "Dealer City", "Dealer Zip", "Dealer Lat", "Dealer Long", "CenterLat", "CenterLong", "DistanceFromCenter", "Transmission", "MPG Combined", "MPG City", "MPG Highway", "Engine Code", "Engine Name", "Cab Code", "Cab", "Bed Code" , "Bed" , "FirstAddedDate", LastChangedDateTimeColName, "infoDateTime", "Options"]

rowModificationsColumnName: str = "List of Changes"
rowChangeTypeColumnName: str = "RowChangeType"
rowChangeDateTime: str = "Event DateTime"
columnsForEmptyChangeHistoryCsvDf: List[str] = [rowChangeTypeColumnName, rowChangeDateTime, "Year", "Model", "Color", "Int Color", "Base MSRP", "Total MSRP", "Selling Price", "Selling Price Incomplete", "Markup", "TMSRP plus DIO", "Shipping Status", "Pre-Sold", "Hold Status", "eta.currFromDate", "eta.currToDate", "VIN", "isTempVin", "Dealer", "Dealer Website", "Dealer State", "Dealer City", "Dealer Zip", "Dealer Lat", "Dealer Long", "CenterLat", "CenterLong", "DistanceFromCenter", "Transmission", "MPG Combined", "MPG City", "MPG Highway", "Engine Code", "Engine Name", "Cab Code", "Cab", "Bed Code" , "Bed" , "FirstAddedDate", "infoDateTime", rowModificationsColumnName, "Options"]

columnValueChangedIndicator: str =  "----->"
columnValueNotChangedIndicator: str = "_"
rowAddedNewVINIndicator: str = "ADDED"
rowModifiedVINContentsIndicator: str = "MODED"
rowRemovedVINIndicator: str = "REMOVED"
rowSameVINContentsIndicator: str = ""

maxDaysOldToKeep: int = 14  # 2 weeks for change history entries
maxDaysToKeepTempVinSold: int = 7 * 16 #16 weeks for temp VIN in sold files.

@cache
def getExcelDistanceFormulaForCsv(dfColumns: Tuple[str, ...], excelRowIndex: int = 2) -> str:
    # gets the Excel formula to put in row excelRowIndex in the DistanceFromCenter column
    # dfColumns is a tuple of the column names of a df in the order the df has them in, and unique.
    dealerLatColName = "Dealer Lat"
    dealerLongColName = "Dealer Long"
    centerLatColName = "CenterLat"
    centerLongColName ="CenterLong"
    colNameToColCsvIndex: Dict[str, Optional[int]] = {dealerLatColName: None, dealerLongColName: None, centerLatColName: None, centerLongColName: None}
    
    for colName in colNameToColCsvIndex:
        if colName in dfColumns:
            colNameToColCsvIndex[colName] = dfColumns.index(colName)
        else:
            print("Error: getExcelDistanceFormulaForCsv: name", colName, "not in dfColumns. Returning formula as blank")
            return ""
    colNameToExcelCellRef = {}
    for colName in colNameToColCsvIndex:
        excelColIndex = colNameToColCsvIndex[colName]
        if excelColIndex is None:
             # Should not happen given check above, but for typing safety
             return ""
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
    return formula

def getVehicleByVinWithBypass(vin: str) -> Optional[Dict[str, Any]]:
    print("Bypassing WAF")
    headers = wafbypass.WAFBypass().run()
    result = getVehicleByVin(vin, headers)
    return result

def getVehicleByVin(vin: str, headers: Optional[Dict[str, str]]) -> Optional[Dict[str, Any]]:
    global forceQueryRspFailureTest
    with open(f"{config.BASE_DIRECTORY}/graphql/vehicleByVin.graphql", "r") as fileh:
        query = fileh.read()
    query = query.replace("VINTOGETINFOFOR", vin)

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
                if resp:
                    print("resp.status_code", resp.status_code)
                    print("resp.headers", resp.headers)
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
    return result

def get_vehicle_query_Objects() -> Dict[str, str]:
    """Read vehicle query from a file and create the query objects."""
    vehicleQueryObjects: Dict[str, str] = {}

    # Validate and get internal vehicle make
    ok, vehicle_make = vehicleUtilities.validateVehicleMake(VEHICLE_MAKE)
    if not ok:
        print("Error: get_vehicle_query_Objects: Invalid vehicle make specified:", VEHICLE_MAKE)
        return vehicleQueryObjects
    
    # Determine GraphQL brand parameter for vehicle search API
    brand = "LEXUS" if vehicle_make == vehicleUtilities.vehicleMakeLexus else "TOYOTA"

    if (MODEL_SEARCH_ZIPCODE is not None) and (MODEL_SEARCH_RADIUS is not None) and MODEL_SEARCH_ZIPCODE and MODEL_SEARCH_RADIUS:
        # single zipcode and radius search specified
        with open(f"{config.BASE_DIRECTORY}/graphql/vehiclesWithVehicleMake.graphql", "r") as fileh:
            query = fileh.read()
        if MODEL:
             query = query.replace("MODELCODE", MODEL)
        query = query.replace("ZIPCODE", MODEL_SEARCH_ZIPCODE)
        query = query.replace("VEHICLE_MAKE", brand)
        query = query.replace("DISTANCEMILES", MODEL_SEARCH_RADIUS)
        query = query.replace("LEADIDUUID", str(uuid.uuid4()))
        vehicleQueryObjects["SingleZipCode_" + MODEL_SEARCH_ZIPCODE + "_RadiusMiles_" + MODEL_SEARCH_RADIUS] = query
    else:
        # Determine zone strategy based on vehicle make
        vehicleQueryZonesToUse: List[str] = []
        default_radius: int = 5823
        
        if vehicle_make == vehicleUtilities.vehicleMakeLexus:
            vehicleQueryZonesToUse = ["central"]
            default_radius = 10000
        else:
            # Toyota: multi-zone strategy based on model volume
            if MODEL in [ "camry", "tacoma", "tundra", "rav4hybrid", "rav4", "corolla", "corollacross", "4runner"]:
                vehicleQueryZonesToUse = ["alaska", "hawaii", "west", "central", "midIllinois", "east", "atlanta", "topLeftCornerContlUS", "portlandOregon", "bottomLeftCornerContlUS", "midCalifornia", "upperCalifornia", "topRightCornerContlUS", "midPennsylvania", "rochesterNewYork", "albanyNewYork", "bostonMA", "midTennessee", "midOhio", "richmondVA", "bottomRightCornerContlUS", "panhandleFlorida", "midFlorida", "bottomCenterContlUS", "midTexas", "midArizona", "renoNevada", "topCenterContlUS" ]
            elif MODEL in ["grandhighlander" ]:
                vehicleQueryZonesToUse = ["alaska", "hawaii", "west", "central", "midIllinois", "topLeftCornerContlUS", "portlandOregon", "bottomLeftCornerContlUS", "midCalifornia", "upperCalifornia", "topRightCornerContlUS", "midPennsylvania", "rochesterNewYork", "albanyNewYork", "bostonMA", "midOhio", "richmondVA", "bottomCenterContlUS", "midTexas", "midArizona", "renoNevada", "topCenterContlUS" ]
            else:
                vehicleQueryZonesToUse = ["alaska", "hawaii", "west", "central", "east"]
            default_radius = 5823 # Toyota default

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
            with open(f"{config.BASE_DIRECTORY}/graphql/vehiclesWithVehicleMake.graphql", "r") as fileh:
                query = fileh.read()
            zip_code = zip_codes[zone]
            query = query.replace("ZIPCODE", zip_code)
            if MODEL:
                query = query.replace("MODELCODE", MODEL)
            query = query.replace("VEHICLE_MAKE", brand)
            query = query.replace("DISTANCEMILES", str(default_radius + randbelow(1000)))
            query = query.replace("LEADIDUUID", str(uuid.uuid4()))
            vehicleQueryObjects[zone] = query

    return vehicleQueryObjects
    
def getChangeHistoryParquetFileName() -> str:
    ok, vehicle_make = vehicleUtilities.validateVehicleMake(VEHICLE_MAKE)
    output_dir = vehicleUtilities.getVehicleMakeRelOutDirNoEndSlash(vehicle_make if (ok and vehicle_make) else "output")
    parquetFileName = f"{output_dir}/{MODEL}_ChangeHistory.parquet"
    return parquetFileName

def getChangeHistoryCsvFileName() -> str:
    ok, vehicle_make = vehicleUtilities.validateVehicleMake(VEHICLE_MAKE)
    output_dir = vehicleUtilities.getVehicleMakeRelOutDirNoEndSlash(vehicle_make if (ok and vehicle_make) else "output")
    parquetFileName = f"{output_dir}/{MODEL}_ChangeHistory.csv"
    return parquetFileName

def getLastRawParquetFileName() -> str:
    ok, vehicle_make = vehicleUtilities.validateVehicleMake(VEHICLE_MAKE)
    output_dir = vehicleUtilities.getVehicleMakeRelOutDirNoEndSlash(vehicle_make if (ok and vehicle_make) else "output")
    parquetFileName = f"{output_dir}/{MODEL}_Lastraw.parquet"
    return parquetFileName
    
def getInventoryTestParquetFileName() -> str:
    ok, vehicle_make = vehicleUtilities.validateVehicleMake(VEHICLE_MAKE)
    output_dir = vehicleUtilities.getVehicleMakeRelOutDirNoEndSlash(vehicle_make if (ok and vehicle_make) else "output")
    parquetFileName = f"{output_dir}/{MODEL}_raw.parquet"
    return parquetFileName

def getLastRawStatusFileName() -> str:
    ok, vehicle_make = vehicleUtilities.validateVehicleMake(VEHICLE_MAKE)
    output_dir = vehicleUtilities.getVehicleMakeRelOutDirNoEndSlash(vehicle_make if (ok and vehicle_make) else "output")
    statusFileName = f"{output_dir}/{MODEL}_LastStatusInfo.json"
    return statusFileName

def getInventoryTestStatusFileName() -> str:
    ok, vehicle_make = vehicleUtilities.validateVehicleMake(VEHICLE_MAKE)
    output_dir = vehicleUtilities.getVehicleMakeRelOutDirNoEndSlash(vehicle_make if (ok and vehicle_make) else "output")
    statusFileName = f"{output_dir}/{MODEL}_StatusInfo.json"
    return statusFileName
    
def readChangeHistoryParquetDf() -> pd.DataFrame:
    global columnsForEmptyChangeHistoryCsvDf
    
    df = pd.DataFrame(columns = columnsForEmptyChangeHistoryCsvDf)
    df[rowChangeTypeColumnName] = df[rowChangeTypeColumnName].astype('object')
    df[rowModificationsColumnName] = df[rowModificationsColumnName].astype('object')
    parquetFileName = getChangeHistoryParquetFileName()

    if Path(parquetFileName).exists():
        df = pd.read_parquet(parquetFileName)
    else:
        print("readChangeHistoryParquetDf: Change history parquet file does not exist", parquetFileName, " . Using emtpy dataframe for it")
    return df
    
def readLastParquetDf() -> Tuple[bool, bool, pd.DataFrame, Dict[str, Any]]:
    global columnsForEmptyDfParquet
    
    rawParquetFileExists = False
    statusOfGetAllPagesFileExists = False
    df = pd.DataFrame(columns = columnsForEmptyDfParquet)
    statusOfGetAllPages: Dict[str, Any] = {"completedOk": False, "numberRawVehiclesFound": 0, "numberRawVehiclesMissing": 100000, "completionMsg": "", "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    statusFileName = getLastRawStatusFileName()
    parquetFileName = getLastRawParquetFileName()
    
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
        df.drop(["Sold"], axis=1, inplace=True)
    if not("FirstAddedDate" in df.columns):
        df["FirstAddedDate"] = None
    if not(LastChangedDateTimeColName in df.columns):
        df[LastChangedDateTimeColName] = None
    return (rawParquetFileExists, statusOfGetAllPagesFileExists, df , statusOfGetAllPages )
     

def read_local_data(testModeOn: bool = False) -> Tuple[bool, bool, pd.DataFrame, Dict[str, Any]]:
    global columnsForEmptyDfParquet
    
    rawParquetFileExists = False
    statusOfGetAllPagesFileExists = False
    df = pd.DataFrame(columns = columnsForEmptyDfParquet)
    statusOfGetAllPages: Dict[str, Any] = {"completedOk": False, "numberRawVehiclesFound": 0, "numberRawVehiclesMissing": 100000, "completionMsg": "", "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    if testModeOn:
        statusFileName = getInventoryTestStatusFileName()
        parquetFileName = getInventoryTestParquetFileName()
    else:
        statusFileName = getLastRawStatusFileName()
        parquetFileName = getLastRawParquetFileName()
        
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
        df.drop(["Sold"], axis=1, inplace=True)
    if "FirstAddedDate" in df.columns:
        df.drop(["FirstAddedDate"], axis=1, inplace=True)
    if LastChangedDateTimeColName in df.columns:
        df.drop([LastChangedDateTimeColName], axis=1, inplace=True)
    return (rawParquetFileExists, statusOfGetAllPagesFileExists, df , statusOfGetAllPages )


def writeCompletionStatusToFile(statusOfGetAllPages: Dict[str, Any]) -> None:
    statusFileName = getLastRawStatusFileName()
    with open(statusFileName, "w") as f:
        json.dump(statusOfGetAllPages, f, indent=4)

def query_toyota(page_number: int, query: str, headers: Optional[Dict[str, str]]) -> Optional[Dict[str, Any]]:
    """Query Toyota for a list of vehicles."""
    global forceQueryRspFailureTest
    global totalPageRetries
    query = query.replace("PAGENUMBER", str(page_number))
    
    tryCount = 3
    result = None
    resp = None
    
    while tryCount:
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
                if resp:
                    print("resp.status_code", resp.status_code)
                    print("resp.headers", resp.headers)
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


def get_all_pages() -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Get all pages of results for a query to Toyota/Lexus."""
    global totalPageRetries
    totalPageRetries = 0

    ok, vehicle_make = vehicleUtilities.validateVehicleMake(VEHICLE_MAKE)
    if not ok:
        print("Error: get_all_pages: Invalid vehicle make specified:", VEHICLE_MAKE)
        return (pd.DataFrame(), {"completedOk": False, "numberRawVehiclesFound": 0, "numberRawVehiclesMissing": 100000, "completionMsg": "Invalid vehicle make specified", "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

    assert vehicle_make is not None

    df = pd.DataFrame()
    page_number = 1

    vehicleQueryObjects = get_vehicle_query_Objects()

    print("Bypassing WAF")
    headers = wafbypass.WAFBypass(vehicle_make).run()

    timer_start = timer()

    recordsToGet = -1
    numberRawVehiclesMissing = -1
    gotPageInfoAtLeastOnce = False
    last_run_counter = 0
    maxPagesToGet = 40
    maxRecordsToGet =  100000
    pagesToGet = maxPagesToGet
    recordsToGet = maxRecordsToGet
    
    while True:
        if page_number > maxPagesToGet:
            print("Error: Prematurely terminating due to limit of max pages can get of ", maxPagesToGet, ". All vehicles were not found! Model ", MODEL)
            break
        elapsed_time = timer() - timer_start
        if elapsed_time > 4 * 60:
            print("  >>> Refreshing WAF bypass >>>\n")
            if vehicle_make:
                headers = wafbypass.WAFBypass(vehicle_make).run()
            else:
                headers = wafbypass.WAFBypass().run()
            timer_start = timer()
        
        print(f"Getting page {page_number} of {MODEL} vehicles")
        firstPageInfoForThisPageNumber = True
        for queryDetailString in vehicleQueryObjects:
            result = query_toyota(page_number, vehicleQueryObjects[queryDetailString], headers)
            if result and "vehicleSummary" in result:
                pages = result["pagination"]["totalPages"]
                if pages is None:
                    print("Warning: Pages field was None type so treating it as 0 pages")
                    pages = 0
                gotPageInfoAtLeastOnce = True
                records = result["pagination"]["totalRecords"]
                if records is None:
                    print("Warning: records field was None type so treating it as 0 records")
                    records = 0
                if firstPageInfoForThisPageNumber:
                    firstPageInfoForThisPageNumber = False
                    pagesToGet = pages
                    recordsToGet = records
                print(queryDetailString + ":    ", len(result["vehicleSummary"]))
                adderDfNormalized = pd.json_normalize(result["vehicleSummary"])
                infoDateTime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                adderDfNormalized["infoDateTime"] = infoDateTime
                if PAGE_FILES_DEBUG_ENABLED:
                    adderDfNormalized.to_csv(f"output/pages/{MODEL}{queryDetailString}_raw_page{page_number}.csv", index=False)
                if df.empty:
                    df = adderDfNormalized
                else:
                    df = pd.concat([df, adderDfNormalized], ignore_index=True)
                
                if pagesToGet > pages:
                    pagesToGet = pages
                if recordsToGet > records:
                    recordsToGet = records
            elapsed_time = timer() - timer_start
            if elapsed_time > 4 * 60:
                print("  >>> Refreshing WAF bypass >>>\n")
                if vehicle_make:
                     headers = wafbypass.WAFBypass(vehicle_make).run()
                else:
                     headers = wafbypass.WAFBypass().run()
                timer_start = timer()
        df.drop_duplicates(subset=["vin"], inplace=True)
        if PAGE_FILES_DEBUG_ENABLED:
            df.to_csv(f"output/pages/{MODEL}_raw_page{page_number}.csv", index=False)
        print(f"Found {len(df)} (+{len(df)-last_run_counter}) vehicles so far.\n")
        
        if len(df) >= recordsToGet:
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
        df.drop(["Sold"], axis=1, inplace=True)
    if "FirstAddedDate" in df.columns:
        df.drop(["FirstAddedDate"], axis=1, inplace=True)
    return (df, statusInfo )

def sanitizeStr(strng: Any) -> Any:
    # Replace tabs, and characters outside ascii 0 -7F range in string that might cause issues with other programs
    sanitizedString = strng
    if isinstance(sanitizedString, str):
        sanitizedString = sanitizedString.replace('&nbsp;', ' ')
        sanitizedString = sanitizedString.replace('<br>', ' ')
        rePattern = r'[^\u0000-\u007F]'
        sanitizedString = re.sub(rePattern, ' ', sanitizedString)
        rePattern = r'[\u0009]'
        sanitizedString = re.sub(rePattern, ' ', sanitizedString)
    return sanitizedString

def isNumber(value: Any) -> bool:
    return ((isinstance(value, int)) or (isinstance(value, float)))
    
def calcPrices(rowSeries: pd.Series) -> pd.Series:
    sellingPrice = rowSeries["Selling Price"]
    sellingPriceIncomplete = False
    isSmartPath = rowSeries.get("isSmartPath")
    nonSpAdvertizedPrice = rowSeries.get("price.nonSpAdvertizedPrice")
    advertizedPrice = rowSeries.get("price.advertizedPrice")
    dioTotalDealerSellingPrice = rowSeries.get("price.dioTotalDealerSellingPrice")
    tMsrpPlusDio = np.nan
    baseMsrp = rowSeries["Base MSRP"]
    totalMsrp = rowSeries["Total MSRP"]
    markup = np.nan
    
    isSmartPathPresentAndTrue = isinstance(isSmartPath, bool) and isSmartPath
    
    if valueIsNanNoneNull(baseMsrp) or not(isinstance(baseMsrp, (int,float))):
        baseMsrp = np.nan
    if valueIsNanNoneNull(totalMsrp) or not(isinstance(totalMsrp, (int,float))):
        totalMsrp = baseMsrp
    if valueIsNanNoneNull(dioTotalDealerSellingPrice) or not isinstance(dioTotalDealerSellingPrice, (int, float)):
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

def transformRawDfToCsvStyleDf(inputDf: pd.DataFrame) -> pd.DataFrame:
    df = inputDf.copy(deep=True)
    if not df.empty:
        dealers = pd.read_csv(f"{config.BASE_DIRECTORY}/data/dealers.csv", dtype = { 'zip': 'str', 'address1': 'str', 'phone': 'str'})[
            ["dealerId", "state", "city", "zip", "lat", "long"]
        ]
        dealers.rename(columns={"state": "Dealer State", "city": "Dealer City", "zip": "Dealer Zip", "lat": "Dealer Lat", "long": "Dealer Long"}, inplace=True)
        df["dealerCd"] = df["dealerCd"].apply(pd.to_numeric)
        df = df.merge(dealers, left_on="dealerCd", right_on="dealerId", how='left')
        
        dfMissingDealerState = df[df["Dealer State"].isnull() | df["Dealer State"].isin(["", None])].drop_duplicates(subset=["dealerMarketingName"], inplace=False)
        if len(dfMissingDealerState) > 0:
            for index, row in dfMissingDealerState.iterrows():
                print("Missing State for dealer Name, website:", row["dealerMarketingName"], ",", row["dealerWebsite"])
                
        if 'cab.title' in df.columns:
            df['cab'] = df['cab.title']
        elif 'cab' not in df.columns:
            df['cab'] = None
            
        if 'bed.title' in df.columns:
            df['bed'] = df['bed.title']
        elif 'bed' not in df.columns:
            df['bed'] = None
            
        if not ('cab.code' in df.columns):
            df['cab.code'] = None
            
        if not ('bed.code' in df.columns):
            df['bed.code'] = None
            
        if not ('mpg.combined' in df.columns):
            df['mpg.combined'] = None
        if not ('mpg.city' in df.columns):
            df['mpg.city'] = None
        if not ('mpg.highway' in df.columns):
            df['mpg.highway'] = None
        if not ('FirstAddedDate' in df.columns):
            df['FirstAddedDate'] = None
        if not (LastChangedDateTimeColName in df.columns):
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
    
        ok, vehicle_make = vehicleUtilities.validateVehicleMake(VEHICLE_MAKE)
        output_dir = vehicleUtilities.getVehicleMakeRelOutDirNoEndSlash(vehicle_make if (ok and vehicle_make) else "output")
        with open(f"{output_dir}/models.json", "r") as fileh:
            models_list = json.load(fileh)
            matching_models = [x["title"] for x in models_list if x["modelCode"].lower() == (MODEL.lower() if MODEL else "")]
            if not matching_models:
                 if MODEL:
                    raise ValueError(f"Model code {MODEL} not found in {output_dir}/models.json. Available models: {', '.join(x['modelCode'] for x in models_list)}")
                 else:
                     # fallback
                     title = ""
            else:
                title = matching_models[0]
    
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
    
        df["Model"] = df["Model"].str.replace(f"{title} ", "")
    
        df["Color"] = df["Color"].str.replace(" [extra_cost_color]", "", regex=False)
        df["Int Color"] = df["Int Color"].apply(sanitizeStr)
        
        df["Raw Selling Price"] = df["Selling Price"]
        df["Selling Price Incomplete"] = False
        df["TMSRP plus DIO"] = np.nan
        df["Markup"] = np.nan
        if len(df):
            df = df.apply(calcPrices, axis=1)
        
        df.drop(columns=["price.dioTotalDealerSellingPrice"], inplace=True)
        
        statuses = {None: False, 1: True, 0: False}
        df.replace({"Pre-Sold": statuses}, inplace=True)
        
        statuses_shipping = {
            "A": "Factory to port",
            "F": "Port to dealer",
            "G": "At dealer",
        }
        df.replace({"Shipping Status": statuses_shipping}, inplace=True)
    
        df["Options"] = df["Options"].apply(extract_marketing_long_names)
    
        df["Model"] = df["Model"] + " " + df["Drivetrain"]
    
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
                "Shipping Status",
                "Pre-Sold",
                "Hold Status",
                "eta.currFromDate",
                "eta.currToDate",
                "VIN",
                "isTempVin",
                "Dealer",
                "Dealer Website",
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
                "Options",
            ]
        ]
        df.sort_values(by=["VIN"], inplace=True)
        df.reset_index(drop=True, inplace=True)
        if len(df):
            distanceFormula = getExcelDistanceFormulaForCsv(tuple(df.columns), 2)
            df.at[0,"DistanceFromCenter"] =  distanceFormula
    else:
        df = pd.DataFrame(columns = columnsForEmptyDfFinalCsv)
    return df
    
def getFileNameForSoldRawParquet(model: str, year: int) -> str:
    # model is a str, and year is a number
    ok, vehicle_make = vehicleUtilities.validateVehicleMake(VEHICLE_MAKE)
    output_dir = vehicleUtilities.getVehicleMakeRelOutDirNoEndSlash(vehicle_make if (ok and vehicle_make) else "output")
    return f"{output_dir}/" + model + "_" + "{:04d}".format(year) + "_Sold_raw.parquet"
    
def getFileNameForSoldCsv(model: str, year: int) -> str:
    # model is a str, and year is a number
    ok, vehicle_make = vehicleUtilities.validateVehicleMake(VEHICLE_MAKE)
    output_dir = vehicleUtilities.getVehicleMakeRelOutDirNoEndSlash(vehicle_make if (ok and vehicle_make) else "output")
    return f"{output_dir}/" + model + "_" + "{:04d}".format(year) + "_Sold.csv"
    
def valueIsStrType(value: Any) -> bool:
    isStrType = False
    if isinstance(value, str):
        isStrType = True
    return isStrType

def pruneSoldFiles(model: str) -> None:
    global changeHistoryUseThisAsTodaysDateForTesting
    global maxDaysToKeepTempVinSold
    searchPathAndPatterns = os.path.join("output/", model + "_????_Sold_raw.parquet")
    fileNamesWithPath = glob.glob(searchPathAndPatterns)
    for fileNameWithPath in fileNamesWithPath:
        if os.path.isfile(Path(fileNameWithPath)):
            df = pd.read_parquet(fileNameWithPath)
            today = datetime.datetime.today()
            format_time_string = "%Y-%m-%d %H:%M:%S"
            if not (changeHistoryUseThisAsTodaysDateForTesting is None):
                print("!!!!!!!! Warning: pruneSoldFiles:  Using a test date in place of Todays Date for testing date filtering. Test date is:", changeHistoryUseThisAsTodaysDateForTesting)
                today = datetime.datetime.strptime(changeHistoryUseThisAsTodaysDateForTesting, format_time_string)
            lowerKeepDate = today - datetime.timedelta(days=maxDaysToKeepTempVinSold)
            lowerKeepDateStr = lowerKeepDate.strftime(format_time_string)
            if "infoDateTime" in df.columns:
                lenDfOld = len(df)
                df = df[(df["infoDateTime"].apply(valueIsStrType) == False) | (df["infoDateTime"] >= lowerKeepDateStr)]
                if (lenDfOld - len(df)) > 0:
                    print ("Pruning Sold File", fileNameWithPath, "of", lenDfOld - len(df), "old Temp VINs")
                if True:
                    df.to_parquet(fileNameWithPath, index=False)
                    cvsStyleDf = transformRawDfToCsvStyleDf(df)
                    lenSuffix = len("_raw.parquet")
                    fileNameWithPathCsv = fileNameWithPath[:-lenSuffix] + ".csv"
                    cvsStyleDf.to_csv(fileNameWithPathCsv, index=False)
                else:
                    pass
            else:
                print("Error: pruneSoldFiles : dataframe does not contain infoDateTime column. Leaving sold file unchanged")

def writeLastParquetAndAssociatedFiles(inputDf: pd.DataFrame) -> None:
    df = inputDf.copy(deep=True)
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
        combinedModelYears = list(set(modelYearsSold + modelYearsNotSold))
        combinedModelYears.sort()
        for year in combinedModelYears:
            modelYearSoldFileName = getFileNameForSoldRawParquet(MODEL if MODEL else "", year)
            modelYearSoldCsvFileName = getFileNameForSoldCsv(MODEL if MODEL else "", year)
            if Path(modelYearSoldFileName).exists():
                modelYearSoldRawParquetDf = pd.read_parquet(modelYearSoldFileName)
            else:
                print("writeLastParquetAndAssociatedFiles: ", modelYearSoldFileName, "does not exist. Using empty dataframe with the appropriate columns")
                modelYearSoldRawParquetDf = pd.DataFrame(columns = df.columns)
            if year in modelYearsSold:
                soldEntriesForYear = modelSoldDf[modelSoldDf["year"] == year]
                if modelYearSoldRawParquetDf.empty:
                    modelYearSoldRawParquetDf = soldEntriesForYear
                else:
                    modelYearSoldRawParquetDf = pd.concat([modelYearSoldRawParquetDf, soldEntriesForYear], ignore_index=True)
                modelYearSoldRawParquetDf.drop_duplicates(subset=["vin"], keep='last', inplace=True)
            if year in modelYearsNotSold:
                modelNotSoldMergeColumnsOnlyDf = modelNotSoldDf[modelNotSoldDf["year"] == year][["vin"]]
                if "WhoDidMergeComeFrom_" in modelYearSoldRawParquetDf.columns:
                    modelYearSoldRawParquetDf.drop(columns=["WhoDidMergeComeFrom_"], axis=1, inplace=True)
                modelYearSoldRawParquetDf = modelYearSoldRawParquetDf.merge(modelNotSoldMergeColumnsOnlyDf,  left_on="vin", right_on="vin", how='left', indicator = "WhoDidMergeComeFrom_")
                modelYearSoldRawParquetDf = modelYearSoldRawParquetDf[modelYearSoldRawParquetDf["WhoDidMergeComeFrom_"] != 'both']
                modelYearSoldRawParquetDf.drop(columns=["WhoDidMergeComeFrom_"], axis=1, inplace=True)
            modelYearSoldRawParquetDf.sort_values(by=["vin"], inplace=True)
            if "Sold" in modelYearSoldRawParquetDf.columns:
                modelYearSoldRawParquetDf.drop(["Sold"], axis=1, inplace=True)
            modelYearSoldRawParquetDf.to_parquet(modelYearSoldFileName, index=False)
            cvsStyleDf = transformRawDfToCsvStyleDf(modelYearSoldRawParquetDf)
            cvsStyleDf.to_csv(modelYearSoldCsvFileName, index=False)
        
    df = df[df["Sold"] != True]
    df.drop(["Sold"], axis=1, inplace=True)
    df.to_parquet(rawParquetFileName, index=False)

def debugCheckingDf(df: pd.DataFrame, msg: str = "", vin: str = "") -> None:
    return
        
def updateDfsLastChangedDateTimeUsingChangeHistory(df: pd.DataFrame, lastParquetDf: pd.DataFrame, changeHistoryCurrentOnlyDf: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    df = df.copy(deep=True)
    lastParquetDf = lastParquetDf.copy(deep=True)
    changeHistoryOnlyMergeColsDf = changeHistoryCurrentOnlyDf[["VIN", rowChangeTypeColumnName]].copy(deep=True)
    changeHistoryOnlyMergeColsWithModedDf = changeHistoryOnlyMergeColsDf[changeHistoryOnlyMergeColsDf[rowChangeTypeColumnName] == rowModifiedVINContentsIndicator]
    dfMerged = df.merge(changeHistoryOnlyMergeColsWithModedDf, left_on="VIN", right_on="VIN", how='left', indicator = "WhoDidMergeComeFrom_")
    dfMerged[LastChangedDateTimeColName] = dfMerged[LastChangedDateTimeColName].where(dfMerged["WhoDidMergeComeFrom_"] != "both", dfMerged["infoDateTime"])
    dfLastParquetMerged = lastParquetDf.merge(changeHistoryOnlyMergeColsWithModedDf, left_on="vin", right_on="VIN", how='left', indicator = "WhoDidMergeComeFrom_")
    dfLastParquetMerged[LastChangedDateTimeColName] = dfLastParquetMerged[LastChangedDateTimeColName].where(dfLastParquetMerged["WhoDidMergeComeFrom_"] != "both", dfLastParquetMerged["infoDateTime"])
    
    dfMerged.drop(["WhoDidMergeComeFrom_", rowChangeTypeColumnName], axis=1, inplace=True)
    dfLastParquetMerged.drop(["WhoDidMergeComeFrom_", rowChangeTypeColumnName, "VIN"], axis=1, inplace=True)
    return (dfMerged, dfLastParquetMerged)
    

def getChangeHistoryFinalColumnsSelect(originalColumnsInOld: pd.Index, originalColumnsInNew: pd.Index) -> List[str]:
    finalColumnsSelect = []
    finalColumnsSelect.append(rowChangeTypeColumnName)
    finalColumnsSelect.append(rowChangeDateTime)
    for column in originalColumnsInNew:
        if column == "Options":
            finalColumnsSelect.append(rowModificationsColumnName)
        finalColumnsSelect.append(column)
    return finalColumnsSelect

def valueIsNanNoneNull(value: Any) -> bool:
    return (value is None) or (isinstance(value, float) and np.isnan(value))
    
def getOptionDifferences(oldOptions: Any, newOptions: Any) -> str:
    diffs = ""
    removedOptionsStr = ""
    addedOptionsStr = ""
    sameOptionsStr = ""
    oldOptionsIsStrType = isinstance(oldOptions, str)
    newOptionsIsStrType = isinstance(newOptions, str)
    if (not oldOptionsIsStrType) or (not newOptionsIsStrType):
        removedOptionsStr = str(oldOptions)
        addedOptionsStr = str(newOptions)
    else: 
        oldOptionsSplit = []
        for option in oldOptions.split("|"):
            oldOptionsSplit.append(option.rstrip().lstrip())
        oldOptionsSplit.sort(key=str.lower)
        oldOptionsSplit = list(dict.fromkeys(oldOptionsSplit))
        newOptionsSplit = []
        for option in newOptions.split("|"):
            newOptionsSplit.append(option.rstrip().lstrip())
        newOptionsSplit.sort(key=str.lower) 
        newOptionsSplit = list(dict.fromkeys(newOptionsSplit)) 
        oldIndiciesOfOldIsSameAsNew = []
        newIndex = 0
        for newOption in newOptionsSplit:
            newOptionForCompare = newOption.lower().rstrip(":")
            newOptionForCompare = newOptionForCompare.replace("[installed_msrp]", "").rstrip().rstrip(":")
            wasInOld = False
            oldIndex = 0
            for oldOption in oldOptionsSplit:
                oldOptionForCompare = oldOption.lower().rstrip(":").rstrip()
                oldOptionForCompare = oldOptionForCompare.replace("[installed_msrp]", "").rstrip().rstrip(":")
                if newOptionForCompare == oldOptionForCompare:
                    if not (oldIndex in oldIndiciesOfOldIsSameAsNew):
                        sameOptionsStr += newOption + " | "
                    wasInOld = True
                    oldIndiciesOfOldIsSameAsNew.append(oldIndex)
                    #break
                oldIndex += 1
            if not wasInOld:
                addedOptionsStr += newOption + " | "
            newIndex += 1
        for oldIndex in range(len(oldOptionsSplit)):
            if not (oldIndex in oldIndiciesOfOldIsSameAsNew):
                removedOptionsStr += oldOptionsSplit[oldIndex] + " | "
        
    if sameOptionsStr:
        sameOptionsStr = " :Same---> " + sameOptionsStr
    if removedOptionsStr:
        removedOptionsStr = " :Removed---> " + removedOptionsStr
    if addedOptionsStr:
        addedOptionsStr = " :Added---> " + addedOptionsStr
    if (not removedOptionsStr) and (not addedOptionsStr):
        diffs = ""
    else:
        diffs =  addedOptionsStr + removedOptionsStr + sameOptionsStr
    return diffs

def determineRowDifferences(row: pd.Series, columnsToIgnore: List[str], originalColumnsInOld: pd.Index, originalColumnsInNew: pd.Index, mergeSuffixRight: str) -> pd.Series:
    row = row.astype(object)
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
        columns1.sort(key=str.lower)
        for column in columns1:
            oldValue = row[column+mergeSuffixRight]  
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
        print("Warning: determineRowDifferences: columns names in old orginal and new original were not all the same.  Handling this.")
        columnsTemp = columns1 + columns2
        columnsCombined = []
        for column in columnsTemp:
            if column not in columnsCombined:
                columnsCombined.append(column)
        columnsCombined.sort(key=str.lower)
        for column in columnsCombined:
            if (column in columns2) and (column in columns1):
                oldValue = row[column+mergeSuffixRight] 
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
            elif (column not in columns2):
                rowIsTheSame = False
                newValue = row[column]
                namesOfModifiedFieldsString += column + " :: " + "-" + " --Added-> " +  str(newValue) + " || "
            else:
                rowIsTheSame = False
                oldValue = row[column] 
                namesOfModifiedFieldsString += column + " :: " + str(oldValue) + " --Removed-> " + "-"  + " || "        
    if rowIsTheSame:
        row[rowChangeTypeColumnName] = rowSameVINContentsIndicator
        row[rowModificationsColumnName] = None
    else:
        row[rowChangeTypeColumnName] = rowModifiedVINContentsIndicator
        row[rowModificationsColumnName] = namesOfModifiedFieldsString
        
    return row

def getChangeHistory(oldDf: pd.DataFrame, newDf: pd.DataFrame, lastChangeHistorydf: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    global columnsForEmptyChangeHistoryCsvDf
    global changeHistoryUseThisAsTodaysDateForTesting
    global maxDaysOldToKeep
    print("Determining change history by analyzing ", len(newDf), " entries. Warning: This could take up to 90 seconds for approx 40000 entries")
    dfOld = oldDf.copy(deep=True)
    dfNew = newDf.copy(deep=True)
    
    dfChangeHistory = pd.DataFrame(columns = columnsForEmptyChangeHistoryCsvDf)
    dfChangeHistory[rowChangeTypeColumnName] = dfChangeHistory[rowChangeTypeColumnName].astype('object')
    dfChangeHistory[rowModificationsColumnName] = dfChangeHistory[rowModificationsColumnName].astype('object')
    
    originalColumnsInOld = dfOld.columns
    originalColumnsInNew = dfNew.columns
    mergeSuffixRight = "_y"
    
    dfNewMerged = dfNew.merge(dfOld, left_on="VIN", right_on="VIN", how='left', suffixes = (None, mergeSuffixRight), indicator = "WhoDidMergeComeFrom_")
    
    dfNewMergeColumnsToUse = dfNew[["VIN"]]
    dfOldMerged = dfOld.merge(dfNewMergeColumnsToUse, left_on="VIN", right_on="VIN", how='left', indicator = "WhoDidMergeComeFrom_")
    
    dfNewMerged[rowChangeTypeColumnName] = pd.Series([rowSameVINContentsIndicator] * len(dfNewMerged), dtype='object', index=dfNewMerged.index)
    dfNewMerged[rowModificationsColumnName] = pd.Series([None] * len(dfNewMerged), dtype='object', index=dfNewMerged.index)
    dfOldMerged[rowChangeTypeColumnName] = pd.Series([rowSameVINContentsIndicator] * len(dfOldMerged), dtype='object', index=dfOldMerged.index)
    dfOldMerged[rowModificationsColumnName] = pd.Series([None] * len(dfOldMerged), dtype='object', index=dfOldMerged.index)   
    
    dfNewMerged[rowChangeTypeColumnName] = dfNewMerged[rowChangeTypeColumnName].where(dfNewMerged["WhoDidMergeComeFrom_"] != 'left_only', rowAddedNewVINIndicator )
    dfOldMerged[rowChangeTypeColumnName] = dfOldMerged[rowChangeTypeColumnName].where(dfOldMerged["WhoDidMergeComeFrom_"] != 'left_only', rowRemovedVINIndicator )
    
    columnsToIgnoreForComparison = ["WhoDidMergeComeFrom_", rowChangeTypeColumnName, rowModificationsColumnName, "VIN", "CenterLat", "CenterLong", "DistanceFromCenter", LastChangedDateTimeColName, "infoDateTime", "FirstAddedDate"]
    dfNewMergeOnlyCommonVins = dfNewMerged[dfNewMerged["WhoDidMergeComeFrom_"] == 'both'].copy(deep=True)
    dfNewMergeOnlyCommonVins[rowChangeTypeColumnName] = dfNewMergeOnlyCommonVins[rowChangeTypeColumnName].astype(object)
    dfNewMergeOnlyCommonVins[rowModificationsColumnName] = dfNewMergeOnlyCommonVins[rowModificationsColumnName].astype(object)
    dfNewMergeOnlyCommonVins = dfNewMergeOnlyCommonVins.apply(determineRowDifferences, axis=1, args= (columnsToIgnoreForComparison, originalColumnsInOld, originalColumnsInNew, mergeSuffixRight))
    
    frames_to_concat = [
        dfNewMerged[dfNewMerged[rowChangeTypeColumnName] == rowAddedNewVINIndicator],
        dfNewMergeOnlyCommonVins[dfNewMergeOnlyCommonVins[rowChangeTypeColumnName] == rowModifiedVINContentsIndicator],
        dfOldMerged[dfOldMerged[rowChangeTypeColumnName] == rowRemovedVINIndicator]
    ]
    frames_to_concat = [df for df in frames_to_concat if not df.empty]
    
    if frames_to_concat:
        dfChangeHistory = pd.concat(frames_to_concat, ignore_index=True)
    else:
        dfChangeHistory = pd.DataFrame(columns=columnsForEmptyChangeHistoryCsvDf)
    
    if LastChangedDateTimeColName not in dfChangeHistory.columns:
        dfChangeHistory[LastChangedDateTimeColName] = pd.Series(dtype='object')
    
    dfChangeHistory[LastChangedDateTimeColName] = dfChangeHistory[LastChangedDateTimeColName].where(dfChangeHistory[rowChangeTypeColumnName] != rowModifiedVINContentsIndicator, dfChangeHistory["infoDateTime"])
    today = datetime.datetime.today()
    format_time_string = "%Y-%m-%d %H:%M:%S"
    dfChangeHistory[rowChangeDateTime] = today.strftime(format_time_string)
    
    changeHistoryCurrentOnlyDf = dfChangeHistory.copy(deep=True)
    
    if lastChangeHistorydf.empty:
        dfChangeHistory = dfChangeHistory
    elif dfChangeHistory.empty:
        dfChangeHistory = lastChangeHistorydf 
    else:
        dfChangeHistory = pd.concat([lastChangeHistorydf, dfChangeHistory], ignore_index=True)
    if not (changeHistoryUseThisAsTodaysDateForTesting is None):
        print("!!!!!!!! Warning: getChangeHistory:  Using a test date in place of Todays Date for testing date filtering. Test date is:", changeHistoryUseThisAsTodaysDateForTesting)
        today = datetime.datetime.strptime(changeHistoryUseThisAsTodaysDateForTesting, format_time_string)
    lowerKeepDate = today - datetime.timedelta(days=maxDaysOldToKeep)
    lowerKeepDateStr = lowerKeepDate.strftime(format_time_string)
    dfChangeHistory = dfChangeHistory[dfChangeHistory[rowChangeDateTime] >= lowerKeepDateStr ]
    
    finalColumnsSelect = getChangeHistoryFinalColumnsSelect(originalColumnsInOld, originalColumnsInNew)
    dfChangeHistory = dfChangeHistory[
        finalColumnsSelect
    ].copy(deep=True)
    dfChangeHistory.reset_index(drop=True, inplace=True) 
    if len(dfChangeHistory) and ("DistanceFromCenter" in dfChangeHistory.columns):
        distanceFormula = getExcelDistanceFormulaForCsv(tuple(dfChangeHistory.columns), 2)
        dfChangeHistory["DistanceFromCenter"] = None
        dfChangeHistory.at[0,"DistanceFromCenter"] =  distanceFormula
    return (dfChangeHistory, changeHistoryCurrentOnlyDf)

def getEnvVariableTestMode() -> Tuple[bool, str, Optional[str]]:
    testModeEnvVarName = "MODEL_UPDATE_VEHICLES_TEST_MODE"
    testModeEnvValue = os.environ.get(testModeEnvVarName)
    testModeEnvOn = False
    if (testModeEnvValue is not None) and (testModeEnvValue.upper() == "ON"):
        testModeEnvOn = True
    return (testModeEnvOn, testModeEnvVarName, testModeEnvValue)
    
def getEnvVariableTestModeTodayDate() -> Tuple[str, Optional[str]]:
    testModeTodayDateEnvVarName = "MODEL_UPDATE_VEHICLES_TEST_MODE_TODAY_DATE"
    testModeTodayDateEnvValue = os.environ.get(testModeTodayDateEnvVarName)
    return (testModeTodayDateEnvVarName, testModeTodayDateEnvValue)
    

def update_vehicles_and_return_df(useLocalData: bool = False, testModeOn: bool = False) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Generate a curated database file for the given vehicle model environment variable, as well as
    returning that database as a dataframe and status of the inventory Get.
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
        changeHistoryUseThisAsTodaysDateForTesting = testModeTodayDateEnvValue
    rawParquetFileExists = False
    statusOfGetAllPagesFileExists = False
    df = pd.DataFrame()
    statusOfGetAllPages: Dict[str, Any] = {"completedOk": False, "numberRawVehiclesFound": 0, "numberRawVehiclesMissing": 100000, "completionMsg": "", "date": ""}
    
    lastRawParquetFileExists, lastRawStatusOfGetAllPagesFileExists, lastParquetDf, statusOfGetAllPagesLastParquet = readLastParquetDf()

    originalLastParquetDF = lastParquetDf.copy(deep=True)
    
    if (USE_LOCAL_DATA_ONLY or useLocalData or testModeEnabled):
        if testModeEnabled:
            print("Using Local Test Data")
        else:
            print("Using Local Data")
        rawParquetFileExists, statusOfGetAllPagesFileExists, df, statusOfGetAllPages = read_local_data(testModeEnabled)
        if not rawParquetFileExists:
            sys.exit("Error: The raw Parquet file does not exist when using local data")
        if not statusOfGetAllPagesFileExists:
            sys.exit("Error: The Status Info file associated with raw Parquet file does not exist when using local data")
    else:
        df, statusOfGetAllPages = get_all_pages()
        
    if df.empty:
        print(f"No vehicles found for model: {MODEL}")
        if not statusOfGetAllPages["completedOk"]:
            print(f"Error: Completion status not Ok for model: {MODEL}, not storing any results in output files and leaving them as is.")
            print(f"update_vehicles_and_return_df returning empty dataframe and status not Ok to caller so caller does nothing")
            emptyDfWithFinalColumnsForCsv = pd.DataFrame(columns = columnsForEmptyDfParquet)
            return (emptyDfWithFinalColumnsForCsv, statusOfGetAllPages)
        
    df["Sold"] = False
    if lastRawParquetFileExists:
        if len(lastParquetDf):
            if not("FirstAddedDate" in lastParquetDf.columns):
                lastParquetDf["FirstAddedDate"] = None
            if not(LastChangedDateTimeColName in lastParquetDf.columns):
                lastParquetDf[LastChangedDateTimeColName] = None
            lastParquetMergeColumnsOnlyDf = lastParquetDf[["vin", "FirstAddedDate", LastChangedDateTimeColName]]
            if "FirstAddedDate" in df.columns:
                df.drop(['FirstAddedDate'], axis=1, inplace=True)
            if LastChangedDateTimeColName in df.columns:
                df.drop([LastChangedDateTimeColName], axis=1, inplace=True)
            if "WhoDidMergeComeFrom_" in df.columns:
                df.drop(['WhoDidMergeComeFrom_'], axis=1, inplace=True)
            lastParquetDf["Sold"] = True
            df = df.merge(lastParquetMergeColumnsOnlyDf, left_on="vin", right_on="vin", how='left', indicator = "WhoDidMergeComeFrom_")
            df["FirstAddedDate"] = df["FirstAddedDate"].where(df["WhoDidMergeComeFrom_"] != "left_only", df["infoDateTime"])
            df[LastChangedDateTimeColName] = df[LastChangedDateTimeColName].where(df["WhoDidMergeComeFrom_"] != "left_only", df["infoDateTime"])
            df.drop(["WhoDidMergeComeFrom_"], axis=1, inplace=True)
            if df.empty:
                pass
            else:
                lastParquetDf = pd.concat([lastParquetDf, df], ignore_index=True)
            lastParquetDf.drop_duplicates(subset=["vin"], keep='last', inplace=True)
        else:
            df["FirstAddedDate"] = df["infoDateTime"]
            df[LastChangedDateTimeColName] = df["infoDateTime"]
            lastParquetDf = df.copy(deep=True)
    else:
        df["FirstAddedDate"] = None
        df[LastChangedDateTimeColName] = None
        lastParquetDf = df.copy(deep=True)
        
    df.drop(["Sold"], axis=1, inplace=True)
    
    df.sort_values("vin", inplace=True)
    df = transformRawDfToCsvStyleDf(df)
    
    lastChangeHistorydf = readChangeHistoryParquetDf()
    originalLastParquetInCsvStyleDf = transformRawDfToCsvStyleDf(originalLastParquetDF)
    changeHistoryDf, changeHistoryCurrentOnlyDf = getChangeHistory(originalLastParquetInCsvStyleDf, df, lastChangeHistorydf)
    changeHistoryDf.to_parquet(getChangeHistoryParquetFileName(), index=False)
    changeHistoryDf.to_csv(getChangeHistoryCsvFileName(), index=False)
    
    df, lastParquetDf = updateDfsLastChangedDateTimeUsingChangeHistory(df, lastParquetDf, changeHistoryCurrentOnlyDf)
    lastParquetDf.sort_values("vin", inplace=True)
    writeLastParquetAndAssociatedFiles(lastParquetDf)
    writeCompletionStatusToFile(statusOfGetAllPages)
    
    pruneSoldFiles(MODEL if MODEL else "")
    
    df.reset_index(drop=True, inplace=True)
    
    ok, vehicle_make = vehicleUtilities.validateVehicleMake(VEHICLE_MAKE)
    output_dir = vehicleUtilities.getVehicleMakeRelOutDirNoEndSlash(vehicle_make if (ok and vehicle_make) else "output")
    df.to_csv(f"{output_dir}/{MODEL}.csv", index=False)
    return (df, statusOfGetAllPages )

def update_vehicles(useLocalData: bool = False, testModeOn: bool = False) -> None:
    """Generate a curated database file for the given vehicle model environment variable."""
    update_vehicles_and_return_df(useLocalData = useLocalData, testModeOn = testModeOn)

def extract_marketing_long_names(options_raw: Any) -> str:
    """extracts `marketingName` from `Options` col"""
    options: Set[str] = set()
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
                replacementStrings = { "All-Weather": "All Weather"}
                for stringToBeReplaced in replacementStrings:
                    compileObj = re.compile(re.escape(stringToBeReplaced), re.IGNORECASE)
                    option = compileObj.sub(replacementStrings[stringToBeReplaced], option)
                option = sanitizeStr(option)
                options.add(option)
    return " | ".join(sorted(options, key=str.lower))

if __name__ == "__main__":
    import sys
    useLocalData = False
    testModeOn = False
    if len(sys.argv) > 1:
        useLocalDatastr = sys.argv[1:][0]
        if useLocalDatastr.upper() ==  "USELOCALDATA":
            useLocalData = True
    if len(sys.argv) > 2:
        testModeOnstr = sys.argv[1:][1]
        if testModeOnstr.upper() ==  "TESTMODEON":
            testModeOn = True
    
    update_vehicles(useLocalData, testModeOn)