# Updates the dealer info in teh dealers.csv file

import random
import numpy as np
from inputimeout import inputimeout, TimeoutOccurred
import sys
import json
import os.path
from pathlib import Path
import ssl
import requests.exceptions
import requests
import pandas as pd
import re

forceRspFailureTest = 0 # set to > 0 to perform tests related to forcing a response failure to test request retry

def interruptibleSleep(sleepTime):
    wasInterrupted = False
    if sleepTime > 0:
        try:
            x = inputimeout(prompt='', timeout=(sleepTime))  # removed int(sleepTime) to get finer resolution when 1 second or so sleep times
            wasInterrupted = True
            print("Interrupted Sleep")
            if chr(9) in x: # Ctrl I, as Ctrl C does not seem to work even when KeyBoardInterrupt except used
                raise SystemExit #RuntimeError # as termination mechanism as KeyBoardInterrupt does not seem to work
        except TimeoutOccurred:
            pass
    #else:
    #    print("Interruptible Sleep time was 0")
    return wasInterrupted

def readInZipCodes(fileName):
    # reads in and returns a list of zipCodes
    zipCodes = []
    with open(fileName, "r") as fileh:
        for zip in fileh:
            zip = zip.strip(" \n\r")
            if zip:
                if (len(zip) <= 5) and zip.isdecimal():
                    zipCodes.append(zip)
                else:
                    print("Ignoring Invalid zip code '" + zip + "'")
    return zipCodes

def writeZipCodes(zipCodes, startIndex, fileName):
    with open(fileName, "w") as fileh:
        listLen = len(zipCodes)
        indx = startIndex
        while indx < listLen:
            # write out to file
            fileh.write(str(zipCodes[indx])+ "\n")
            indx += 1
            
def getAddressComponents(address):
    # Takes the full address which is in the form <street address>,<0 or more spaces><city>,<0 or more spaces>state<1 or more spaces>zipcode<0 or more spaces>
    # (streetAddressOnly, city, state, zipcode)
    streetAddressOnly = ""
    city = ""
    state = ""
    zipcode = ""
    rePattern = r'(^.*), *([^,]+), *([^ ]+) +([^ ]+) *$'
    match = re.search(rePattern, address)
    if match:
        streetAddressOnly = match[1]
        city = match[2]
        state  = match[3]
        zipcode  = match[4]
    else:
        print("getAddressComponents: Could not parse Address into streetAddressOnly, city, state, zipcode", address)
    return (streetAddressOnly, city, state, zipcode)

def updateAddressComponentsIn(rowSeries):
    # takes a dataframe rowSeries with at least columns "state", "address", "address1", "city", "zip"
    # where address contains the full address including city, state, zipcode and updates the columns 
    # "state", "address1" (i.e. street address only), "city", "zip" with the corresponding information.
    streetAddressOnly, city, state, zipcode = getAddressComponents(rowSeries["address"])
    rowSeries["address1"] = streetAddressOnly
    rowSeries["city"] = city
    rowSeries["state"] = state
    rowSeries["zip"] = zipcode
    return rowSeries

def formatPhoneNumber(phoneNumberStr):
    formattedPhoneNumberStr = "(" + phoneNumberStr[:3] + ") " + phoneNumberStr[3:6] + "-" + phoneNumberStr[6:]
    return formattedPhoneNumberStr 
    
def updateDealers(dealerFileName, zipCodeFileName, dealerAddersJsonFileName = ""):
    print("This program updates the passed dealer file (or creates that file if not present)") 
    print("with any dealers found (new or update of existing), during the search ")
    print("of the remaining zip codes to look for dealers for, out of the zip code file,")
    print("and with the optional dealers Adders json file which contains dealers which for some reason the website does not return")
    print("The remaining zip codes to search are in file <zipCodeFileName>.remainingToSearch.txt",)
    print("and that is an intermediate file the program creates and periodically updates to tell it what")
    print("remaining zip codes it needs to search for (out of the zip code file) in case the program is prematurely terminated")
    print("The program, if terminated before finishing, can be run again and will continue the search from the remaining zip codes.")
    print("Thus, if that remaining zip code file is present the program, when started, will start from that, otherwise it will start from")
    print("the zip code file.")
    print("The dealer file is also updated right before and in sync with the remaining zip code file is updated, again, in case the program is prematurely terminated")
    print("Once we have gone through all the zip codes, the remaining zip codes file will be deleted by the program")
    print("If needed you can manually delete the remaining zip codes file if you want to completely start over again.")
    print("Warning !!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    print("When the set of zipcodes is very large, (possibly 42,000), this program will take a long time to run")
    print("The program takes approx 4 seconds for each zipcode and every 100 zip codes an additional 30 seconds")
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    dealerAddersDf = pd.DataFrame()
    if dealerAddersJsonFileName:
        if Path(dealerAddersJsonFileName).is_file():
            print("Reading in Dealers Adders json file", dealerAddersJsonFileName)
            dealerAddersDf = pd.read_json(dealerAddersJsonFileName, dtype = { 'code': 'str', 'dealerId': 'str', 'zip': 'str', 'address1': 'str', 'phone': 'str'})
        else:
            print("Error: Dealer Adders json file does not exist", dealerAddersJsonFileName)
            return
    remainingZipCodeFileName = zipCodeFileName + ".remainingToSearch.txt"
    if Path(remainingZipCodeFileName).is_file():
        print("Reading in REMAINING zip codes from file:", remainingZipCodeFileName)
        zipCodesToUpdateDealers = readInZipCodes(remainingZipCodeFileName)
    else:
        print("Reading in zip codes from file:", zipCodeFileName)
        zipCodesToUpdateDealers = readInZipCodes(zipCodeFileName)
    if Path(dealerFileName).is_file():
        print("Reading in existing Dealer csv", dealerFileName)
        # leave the code and dealerId fields as strings (since they are unquoted)
        dealers = pd.read_csv(dealerFileName, dtype = { 'code': 'str', 'dealerId': 'str', 'zip': 'str', 'address1': 'str', 'phone': 'str'})
        if False:
            # force code and dealerId fields to be ints as vehicles.py expects this.
            dealers["code"] = dealers["code"].apply(pd.to_numeric)
            dealers["dealerId"] = dealers["dealerId"].apply(pd.to_numeric)
    else:
        dealers = pd.DataFrame()
    indx = 0
    for zipCode in zipCodesToUpdateDealers:
        # TODO add in retries
        zipCodeWithLeadingZeroes = ("0" * (5 - len(zipCode))) + zipCode
        print("Getting dealers for/near zipcode",zipCodeWithLeadingZeroes, ", at zipcode list index:", indx )
        tryCount = 1
        result = None
        while True:
            try:
                # Could not get url "https://dealers.prod.webservices.toyota.com/v1/dealers/?zipcode=" + zipCodeWithLeadingZeroes, to work
                # as it kept giving an resp.status_code 403 for not authorized, even when set host and authority to dealers.prod.webservices.toyota.com
                # , and even trying the wafpypass, so there is something that requires more authorization to access that.
                # That is what the inventory get uses to get the dealers for that zip code but could not get it to work.
                # So had to use the url below which is accessed when on the https://www.toyota.com/connected-services/toyota-app/ page
                # and  click on the Find Dealer https://www.toyota.com/dealers/#default link on that page which pops up a map window
                resp = requests.get(
                        "https://api.ws.dpcmaps.toyota.com/v1/dealers?attributeKey=&searchMode=pmaProximityLayered&zipcode=" + zipCodeWithLeadingZeroes,
                        timeout=20,
                )
                result = resp.json()
                break
            except (requests.exceptions.JSONDecodeError) as inst:
                print ("updateDealers: Exception occurred with accessing json response:", str(type(inst)) + " "  + str(inst))
                print("resp.status_code", resp.status_code)
                print("resp.headers", resp.headers)
                result = None
                # retry
                if tryCount <= 0:
                    break
                tryCount -= 1
                interruptibleSleep(4)
                print("Retrying request, tryCount = ", tryCount)
        if (result is not None) and result and ("dealers" in result) and (len(result["dealers"]) > 0):
            #print("Result is", result)
            #df = pd.DataFrame.from_dict(result["dealers"])
            df = pd.json_normalize(result["dealers"])
            #print ("df is", df)
            #address column includes street address, city, state zipcode
            df = df[["code", "label", "details.uriWebsite", "position.lat", "position.lng", "address", "phone"]]
            #legacy format columns are "code", "dealerId", "name", "url", "regionId", "state", "lat", "long", "address1", "city", "zip", "phone"
            # Add dealerId to match legacy format which is the same as the code field
            df["dealerId"] = df["code"]
            # add other columns to match legacy format
            df["regionId"] = 9999  # use dummy value as this url data does not have region ID and other processing fortunately doesn't need it currently.
            df["state"] = ""
            df["address1"] = ""
            df["city"] = ""
            df["zip"] = ""
            
            # perform renames to match legacy format
            renames = {
                "label": "name",
                "details.uriWebsite": "url",
                "position.lat": "lat",
                "position.lng": "long"
            }
            df = (
                df[
                    ["code",
                    "dealerId",
                    "label", 
                    "details.uriWebsite",
                    "regionId",
                    "state",
                    "position.lat", 
                    "position.lng", 
                    "address",
                    "address1", 
                    "city",
                    "zip",
                    "phone"]
                    ]
                .copy(deep=True)
                .rename(columns=renames)
            )
            # updated address1, city, state, zipcode from the address to match legacy format
            df = df.apply(updateAddressComponentsIn, axis=1)
            # format phone number
            df["phone"] = df["phone"].apply(formatPhoneNumber)
            # remove address field as it has been split into other fields
            df.drop(columns=["address"], inplace=True)
            if False:
                # force the code and dealerId fields to ints as the vehicles.py expects that type (i.e. leading 0s are removed)
                df["code"] = df["code"].apply(pd.to_numeric)
                df["dealerId"] = df["dealerId"].apply(pd.to_numeric)
            #print(df)
            #print("type(df['code'][0])", type(df["code"][0]))
            #print("type(df['lat'][0])", type(df["lat"][0]))
            dealers = pd.concat([dealers, df])
            dealers.drop_duplicates(subset=["code"], keep='last', inplace=True)
        else:
            print("Error: Failed getting dealers near zipcode.  Response is not json format or does not contain a 'dealers' field or dealers field was empty.  ZipCode checked was", zipCodeWithLeadingZeroes)
        indx +=1
        if (indx % 50) == 0:
            # Since the number of zipCodesToUpdateDealers could be very large,  i.e. 42000, 
            # we periodically update the output csv with what we have so far in case we are prematurely terminated
            print("Saving results up to this point to dealers file and remaining zip codes file")
            dealers.to_csv(dealerFileName, index=False)
            writeZipCodes(zipCodesToUpdateDealers, indx, remainingZipCodeFileName)
            # delay a longer period of time so we don't swamp the toyota website
            sleepTime = 30
            print("Sleeping", sleepTime)
            interruptibleSleep(sleepTime)
        # delay a bit since the number of zipCodesToUpdateDealers could be very large
        # and we don't want to swamp the toyota website otherwise our connection could be closed/denied or worse
        # we could be blacklisted for some period of time
        interruptibleSleep(4)
        
    # Now concatenate the dealers adders file onto the dealers and keep only the first duplicate if any
    dealers = pd.concat([dealers, dealerAddersDf])
    dealers.drop_duplicates(subset=["code"], keep='first', inplace=True)
    dealers.sort_values(by=["code"], inplace=True)
    # Write out to the results ot the csv file.
    dealers.to_csv(dealerFileName, index=False)
    # delete the remaining zip codes file.
    Path(remainingZipCodeFileName).unlink(missing_ok=True)
    print("------------> UPDATE OF DEALERS COMPLETED <--------------")
if __name__ == "__main__":
    import sys
    # pass dealer file name
    dealerFileName = sys.argv[1:][0]
    zipCodeFileName = sys.argv[1:][1]
    dealerAddersJsonFileName = ""
    if len(sys.argv[1:]) >= 3:
        dealerAddersJsonFileName = sys.argv[1:][2]
    updateDealers(dealerFileName, zipCodeFileName, dealerAddersJsonFileName)
