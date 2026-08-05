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


def getUserInput(promptStr, sleepTime):
    # Outputs the prompt if not null, and waits for a user input (with an ending CR which is not returned with the result) for the sleepTime
    # returns a tuple (timedOut, userInput) where timedOut is True if timed out before input, otherwise userInput has the user entry
    # without the CR
    userInput = ""
    timedOut = False
    try:
        userInput = inputimeout(prompt=promptStr, timeout=(sleepTime))
    except TimeoutOccurred:
        timedOut = True
    return (timedOut, userInput)


forceRspFailureTest = 0 # set to > 0 to perform tests related to forcing a response failure to test request retry

def printSendRequestDetailsToString(r, dataInRequest=None, showHeaders = False, showData = True):
    #Excludes r.history redirects.
    printString = "-----------------------"  + "\n"
    printString += "r.request.method  " + str(r.request.method) + "\n"
    #print("r.request.method", r.request.method)
    printString += "r.request.url  " + str(r.request.url) + "\n"
    #print("r.request.url",r.request.url )
    if dataInRequest is not None:
        printString += "dataInRequest =  " + str(dataInRequest) + "\n"
        #print("dataInRequest =", str(dataInRequest))
    if showHeaders:
        printString += "r.request.headers  " + str(r.request.headers) + "\n"
        #print("r.request.headers", r.request.headers)
        printString += "response r.headers  " + str(r.headers) + "\n"
        #print("response r.headers", r.headers)
    printString += "r.url  " + str(r.url) + "\n"
    #print("r.url", r.url)
    printString += "r.status_code  " + str(r.status_code) + "\n"
    #print("r.status_code", r.status_code )
    if showData:
        printString += "r.request.body: " + str(r.request.body) + "\n"
    return printString

def printSendRequestDetails(r, dataInRequest=None, showHeaders = False, printIt = True, showData = True, showHistory = True):
    # ShowHistory - indicates if r.history is shown which occurs when redirects occur
    # showData - if True shows the body data in a POST request
    # showHeaders - if True shows the request and response headers
    # dataInRequest -  If not None prints the dataInRequest which is a dictionary that represents what the data in a POST Body is (which matches
    # the data shown by showData but easier to view.
    printString = ""
    if showHistory:
        # Print everything before last redirect that occurred if there were redirects.
        for rsp in r.history:
            printString += printSendRequestDetailsToString(rsp, dataInRequest=dataInRequest, showHeaders=showHeaders, showData=showData)
            dataInRequest = None  # only print dataInRequest on first request that was sent.
    printString += printSendRequestDetailsToString(r, dataInRequest=dataInRequest, showHeaders=showHeaders, showData=showData)
    if printIt:
        print(printString)
    return printString


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
    print("The dealer file is also updated right before and in sync with the remaining zip code file update, again, in case the program is prematurely terminated")
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
        zipCodeWithLeadingZeroes = ("0" * (5 - len(zipCode))) + zipCode
        print("Getting dealers for/near zipcode",zipCodeWithLeadingZeroes, ", at zipcode list index:", indx )
        tryCount = 3
        result = None
        while True:
            try:
                resp = requests.get(
                        "https://dealers.prod.webservices.toyota.com/v1/dealers/?zipcode=" + zipCodeWithLeadingZeroes,
                        headers={"Origin": "https://www.toyota.com"}, # required otherwise get a status code of 403 and fail.
                        timeout=20,
                )
                #print("resp.status_code", resp.status_code)
                result = resp.json()
                break
            except (requests.exceptions.ReadTimeout) as inst:
                print ("updateDealers: Exception occurred with ReadTimeout")
                #print("resp.status_code", resp.status_code)
                result = None
                # retry
                if tryCount <= 0:
                    break
                tryCount -= 1
                interruptibleSleep(4)
                print("Retrying request, tryCount = ", tryCount)
                
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
        #print("zipCodeWithLeadingZeroes", zipCodeWithLeadingZeroes)
        #printSendRequestDetails(resp, dataInRequest=None, showHeaders = True, printIt = True, showData = True, showHistory = True)
        #print("result is", str(result))
        if (result is not None) and result and ("dealers" in result) and (len(result["dealers"]) > 0):
            #print("Result is", result)
            #df = pd.DataFrame.from_dict(result["dealers"])
            df = pd.json_normalize(result["dealers"])
            #print ("df is", df)
            df = df[["code", "dealerId", "name", "url", "regionId", "state", "lat", "long", "address1", "city", "zip", "phone"]]
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
