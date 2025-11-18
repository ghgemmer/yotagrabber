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

def readInZipCodes(fileName, vehicleMake):
    # reads in and returns a list of zipCodes
    zipCodes = []
    with open(fileName, "r") as fileh:
        for zip in fileh:
            zip = zip.strip(" \n\r")
            if zip:
                if vehicleMake == "lexus":
                    if zip in ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"]:
                        zipCodes.append(zip)
                    else:
                        print("Ignoring Invalid state '" + zip + "'")
                else:
                    # toyota
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

def updateDealers(dealerFileName, zipCodeFileName, vehicleMake):
    print("This program updates the passed dealer file (or creates that file if not present)") 
    print("with any dealers found (new or update of existing), during the search ")
    print("of the remaining zip codes/states to look for dealers for, out of the zip code file")
    print("Note that when the vehicleMake is lexus the ZipCode file must actually contain state abbreviations (one per line)")
    print(" and not zipcodes.")
    print("When the vehicleMake is toyota the ZipCode file must actually contain zipcodes.")
    print("The remaining zip codes/states to search are in file <zipCodeFileName>.remainingToSearch.txt",)
    print("and that is an intermediate file the program creates and periodically updates to tell it what")
    print("remaining zip codes/states it needs to search for (out of the zip code file) in case the program is prematurely terminated")
    print("The program, if terminated before finishing, can be run again and will continue the search from the remaining zip codes/states.")
    print("Thus, if that remaining zip code file is present the program, when started, will start from that, otherwise it will start from")
    print("the zip code file.")
    print("The dealer file is also updated right before and in sync with the remaining zip code file is updated, again, in case the program is prematurely terminated")
    print("Once we have gone through all the zip codes/states, the remaining zip codes file will be deleted by the program")
    print("If needed you can manually delete the remaining zip codes file if you want to completely start over again.")
    print("Warning !!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    print("The program takes approx 4 seconds for each zipcode and every 100 zip codes an additional 30 seconds")
    print("For toyota zipcodes there are approx only 1250 zipcodes we need to search to get all toyota dealers in the continental US")
    print("For lexus you specify the states you want dealers for")
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    print ("Vehicle Make for which Dealers are being searched for is ", vehicleMake)    
    remainingZipCodeFileName = zipCodeFileName + ".remainingToSearch.txt"
    if Path(remainingZipCodeFileName).is_file():
        print("Reading in REMAINING zip codes from file:", remainingZipCodeFileName)
        zipCodesToUpdateDealers = readInZipCodes(remainingZipCodeFileName, vehicleMake)
    else:
        print("Reading in zip codes from file:", zipCodeFileName)
        zipCodesToUpdateDealers = readInZipCodes(zipCodeFileName, vehicleMake)
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
        if vehicleMake == "lexus":
            codeToSearch = zipCode
        else:
            #toyota
            codeToSearch = ("0" * (5 - len(zipCode))) + zipCode
        print("Getting dealers for/near zipcode/state",codeToSearch, ", at zipcode list index:", indx )
        tryCount = 1
        result = None
        while True:
            try:
                if vehicleMake == "lexus":
                    # lexus
                    getDealersBaseUrl = "https://www.lexus.com/rest/lexus/dealers?experience=dealers&state="
                else:
                    # toyota
                    getDealersBaseUrl = "https://www.toyota.com/service/tcom/locateDealer/zipCode/"
                resp = requests.get(
                        getDealersBaseUrl + codeToSearch,
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
            if vehicleMake == "lexus":
                # assumption is that lexus and toyota have unique dealer Id values (i.e. don't overlap and from observation it appears so)
                # Renames to match toyota standard fields
                renames = {
                    "id": "code",
                    "dealerName": "name",
                    "dealerSiteUrl": "url",
                    "dealerAddress.state": "state",
                    "dealerLatitude": "lat",
                    "dealerLongitude": "long",
                    "dealerAddress.address1": "address1",
                    "dealerAddress.city": "city",
                    "dealerAddress.zipCode": "zip",
                    "dealerPhone": "phone",
                }
                df = (df[["id", "dealerName", "dealerSiteUrl", "dealerLatitude", "dealerLongitude", "dealerAddress.address1", "dealerAddress.city", "dealerAddress.zipCode", "dealerAddress.state", "dealerPhone"]]
                .copy(deep=True)
                .rename(columns=renames)
                )
                # copy code to missing dealerId in lexus as the fields are both the same in toyota.
                df["dealerId"] = df["code"]
                # no regionId in lexus or don't care to use zipcode access
                df["regionId"] = None
                df["vehicleMake"] = "lexus"
            else:
                # toyota
                df = df[["code", "dealerId", "name", "url", "regionId", "state", "lat", "long", "address1", "city", "zip", "phone"]]
                df["vehicleMake"] = "toyota"
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
            print("Error: Failed getting dealers near zipcode/state.  Response is not json format or does not contain a 'dealers' field or dealers field was empty.  ZipCode/state checked was", codeToSearch)
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
    dealers.to_csv(dealerFileName, index=False)
    # delete the remaining zip codes file.
    Path(remainingZipCodeFileName).unlink(missing_ok=True)
    print("------------> UPDATE OF DEALERS COMPLETED <--------------")
if __name__ == "__main__":
    import sys
    # pass dealer file name
    dealerFileName = sys.argv[1:][0]
    zipCodeFileName = sys.argv[1:][1]
    vehicleMake = ""
    if len(sys.argv[1:]) > 2:
        vehicleMake = sys.argv[1:][2]
    updateDealers(dealerFileName, zipCodeFileName, vehicleMake)
