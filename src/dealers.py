# Updates the dealer info in the dealers.csv file

import random
import numpy as np
from inputimeout import inputimeout, TimeoutOccurred
from timeit import default_timer as timer
import sys
import json
import os.path
from pathlib import Path
import ssl
import requests.exceptions
import requests
import pandas as pd
import re
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from inputimeout import inputimeout, TimeoutOccurred
from yotagrabber import wafbypassDealerInfo
from typing import List, Tuple, Dict, Any, Optional

forceRspFailureTest: int = 0 # set to > 0 to perform tests related to forcing a response failure to test request retry

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

def interruptibleSleep(sleepTime: float) -> bool:
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

def readInZipCodes(fileName: str, vehicleMake: str = "toyota") -> List[str]:
    # reads in and returns a list of zipCodes (Toyota) or state codes (Lexus) from the passed file
    zipCodes: List[str] = []
    with open(fileName, "r") as fileh:
        for zip in fileh:
            zip = zip.strip(" \n\r")
            if zip:
                if vehicleMake == "lexus":
                    # Lexus: validate state codes
                    if zip in ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"]:
                        zipCodes.append(zip)
                    else:
                        print("Error: Ignoring Invalid state code '" + zip + "' for Lexus")
                else:
                    #Toyota: validate zipcodes
                    if (len(zip) <= 5) and zip.isdecimal():
                        zipCodes.append(zip)
                    else:
                        print("Error: Ignoring Invalid zip code '" + zip + "' for Toyota")
    return zipCodes

def writeZipCodes(zipCodes: List[str], startIndex: int, fileName: str) -> None:
    with open(fileName, "w") as fileh:
        listLen = len(zipCodes)
        indx = startIndex
        while indx < listLen:
            # write out to file
            fileh.write(str(zipCodes[indx])+ "\n")
            indx += 1
            
def getAddressComponents(address: str) -> Tuple[str, str, str, str]:
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

def updateAddressComponentsIn(rowSeries: pd.Series) -> pd.Series:
    # takes a dataframe rowSeries with at least columns "state", "address", "address1", "city", "zip"
    # where address contains the full address including city, state, zipcode and updates the columns 
    # "state", "address1" (i.e. street address only), "city", "zip" with the corresponding information.
    # We cast to str to satisfy type checkers that these fields are strings
    streetAddressOnly, city, state, zipcode = getAddressComponents(str(rowSeries["address"]))
    rowSeries["address1"] = streetAddressOnly
    rowSeries["city"] = city
    rowSeries["state"] = state
    rowSeries["zip"] = zipcode
    return rowSeries
    
def formatPhoneNumber(phoneNumberStr: Any) -> str:
    # Strip all non-digit characters to handle both formatted and unformatted phone numbers
    # Input is Any because pandas might pass it as an object/int/str
    s_phoneNumber = str(phoneNumberStr)
    digitsOnly = ''.join(c for c in s_phoneNumber if c.isdigit())
    if len(digitsOnly) == 10:
        formattedPhoneNumberStr = "(" + digitsOnly[:3] + ") " + digitsOnly[3:6] + "-" + digitsOnly[6:]
        return formattedPhoneNumberStr 
    else:
        # Return original if not 10 digits
        return s_phoneNumber
    
def handle_response(response):
    # Print out URL and status code for every network resource
    print(f"URL: {response.url} | Status: {response.status}")
    
    # Conditionally extract data if it's a target API endpoint
    if "api.ws.dpcmaps.toyota.com/v1/dealers" in response.url and (response.status == 200):
        #print("JSON Data:", response.json())
        pass

def getDealersUsingBrowser(dealersInfoUrl):
    """Run a browser, to satisy the dealers WAF, to get the dealers json file.  Left in for history of what seemed to work or not"""
    resp = None
    dealersJson = None
    while True:
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=False) # headless=True does not seem to work for at all for anything, as get a status code 403 as the first and only response sent back by the server on the page.goto.
                #browser = playwright.firefox.launch(headless=True)  # page.on("response", response_handler) with Firefox regardless of headless or not,  does not seem to see last response which is the one we wanted and thus page.expect_response does not work
                try:
                    dealersJson = None
                    #context = browser.new_context(viewport={"width": 1920, "height": 1080})
                    context = browser.new_context(viewport={"width": 10, "height": 10})
                    page = context.new_page()
                    #page = browser.new_page()
                    #getUserInput("Enter Cr to terminate browser inspection", 10000)
                    #page.goto(dealersInfoUrl)
                    if 1:  # Works with firefox headless = True or False, and chromium headless = False  
                        page.goto(dealersInfoUrl)
                        print("page.wait_for_load_state('networkidle', timeout=10000)")
                        page.wait_for_load_state("networkidle", timeout=10000)
                        json_string = page.locator("body > pre").inner_text()
                        dealersJson = json.loads(json_string)
                    if 0:
                        response_info = page.wait_for_response(lambda resp: (resp.status == 200) and ("api.ws.dpcmaps.toyota.com/v1/dealers" in resp.url))
                        print("Got to point A")
                        page.goto(dealersInfoUrl)
                        responseA = response_info
                        dealersJson = responseA.json()
                        print("Json data", dealersJson)
                    if 0:
                        page.on("response", handle_response)
                        page.goto(dealersInfoUrl)
                        print("Waiting 7 seconds")
                        page.wait_for_timeout(7000)
                        print("Page content", page.content()) 
                        json_string = page.locator("body > pre").inner_text()
                        dealersJson = json.loads(json_string)
                        #getUserInput("Enter Cr to terminate browser inspection", 1000)
                    #getUserInput("Enter Cr to terminate browser inspection", 1000)
                    if 0:  # Works with chromium with headless = False.  Firefox seems to fail in any case of headless setting.
                        #page.on("response", handle_response) 
                        with page.expect_response(lambda response: (response.status == 200) and ("api.ws.dpcmaps.toyota.com/v1/dealers" in response.url)) as response_info:
                        #with page.expect_response(lambda response: (response.status == 200) and ("/mp_verify" in response.url)) as response_info:
                            page.goto(dealersInfoUrl)
                        #getUserInput("Enter Cr to terminate browser inspection", 1000)
                        responseA = response_info
                        print ("response_info.value" , repr(response_info.value))
                        response = response_info.value
                        print ("response.url", response.url)
                        print ("response.status", response.status)
                        print ("response.headers", response.headers)
                        #print("response.text()", response.text())
                        dealersJson = response.json()
                except Exception as inst:
                    print("Error: run_browser: exception in code going to dealersInfoUrl page: ", dealersInfoUrl, str(inst))
                finally:
                    browser.close()
            if dealersJson is not None:
                break
            else:
                print("Error: run_browser was None")
                sleepTime = 60* 10
                print("Waiting time ", sleepTime, "secs before retrying WAF Bypass")
                getUserInput("Enter Cr to terminate wait early", sleepTime)
        except Exception as inst:
            print("Error: run_browser: exception", str(inst))
            sleepTime = 60* 10
            print("Waiting time ", sleepTime, "secs before retrying WAF Bypass")
            getUserInput("Enter Cr to terminate wait early", sleepTime)
    return dealersJson

def updateDealers(dealerFileName: str, zipCodeFileName: str, dealerAddersJsonFileName: str = "", vehicleMake: str = "toyota") -> None:
    print("This program updates the passed dealer file (or creates that file if not present)") 
    print("with any dealers found (new or update of existing), during the search ")
    print("of the remaining zip codes/state to look for dealers for, out of the zip code file,")
    print("and with the optional dealers Adders json file which contains dealers which for some reason the website does not return")
    print("Note that when the vehicleMake is lexus the ZipCode file must actually contain state abbreviations (one per line) instead of zip codes")
    print("When the vehicleMake is toyota the ZipCode file must actually contain zip codes (one per line).")
    print("The remaining zip codes to search are in file <zipCodeFileName>.remainingToSearch.txt",)
    print("and that is an intermediate file the program creates and periodically updates to tell it what")
    print("remaining zip codes/states it needs to search for (out of the zip code file) in case the program is prematurely terminated")
    print("The program, if terminated before finishing, can be run again and will continue the search from the remaining zip codes/states.")
    print("Thus, if that remaining zip code file is present the program, when started, will start from that, otherwise it will start from")
    print("the zip code file.")
    print("The dealer file is also updated right before and in sync with the remaining zip code file is updated, again, in case the program is prematurely terminated")
    print("Once we have gone through all the zip codes/states, the remaining zip codes file will be deleted by the program")
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
        zipCodesToUpdateDealers = readInZipCodes(remainingZipCodeFileName, vehicleMake)
    else:
        print("Reading in zip codes from file:", zipCodeFileName)
        zipCodesToUpdateDealers = readInZipCodes(zipCodeFileName, vehicleMake)

    dealers: pd.DataFrame
    if Path(dealerFileName).is_file():
        print("Reading in existing Dealer csv", dealerFileName)
        # leave the code and dealerId fields as strings (since they are unquoted)
        dealers = pd.read_csv(dealerFileName, dtype = { 'code': 'str', 'dealerId': 'str', 'zip': 'str', 'address1': 'str', 'phone': 'str'})
        if False:
            # force code and dealerId fields to be ints as vehicles.py expects this.
            dealers["code"] = dealers["code"].apply(pd.to_numeric)
            dealers["dealerId"] = dealers["dealerId"].apply(pd.to_numeric)
    else:
        # Instead of pd.DataFrame(), match the schema.
        dealers = pd.DataFrame(columns=["code", "dealerId", "name", "url", "regionId", "state", "lat", "long", "address1", "city", "zip", "phone"])

    print("Getting WAF bypass for dealer info website")
    headers = wafbypassDealerInfo.WAFBypass().run()
    # Start a timer.
    timer_start = timer()
    indx = 0
    for zipCode in zipCodesToUpdateDealers:
        # TODO add in retries
        codeToSearch: str
        if vehicleMake == "lexus":
            # Lexus: state codes are left padded with spaces to be 2 characters
            codeToSearch = zipCode # State for Lexus
        else:
            # Toyota: zipcode with leading zeroes
             codeToSearch = ("0" * (5 - len(zipCode))) + zipCode
        print("Getting dealers for/near zipcode/state",codeToSearch, ", at zipcode list index:", indx )
        tryCount = 1
        result: Optional[Dict[str, Any]] = None
        while True:
            resp: Optional[requests.Response] = None
            try:
                # Could not get url "https://dealers.prod.webservices.toyota.com/v1/dealers/?zipcode=" + zipCodeWithLeadingZeroes, to work
                # as it kept giving an resp.status_code 403 for not authorized, even when set host and authority to dealers.prod.webservices.toyota.com
                # , and even trying the wafpypass, so there is something that requires more authorization to access that.
                # That is what the inventory get uses to get the dealers for that zip code but could not get it to work.
                # So had to use the url below which is accessed when on the https://www.toyota.com/connected-services/toyota-app/ page
                # and  click on the Find Dealer https://www.toyota.com/dealers/#default link on that page which pops up a map window
                if vehicleMake == "lexus":
                    # Lexus: state-based API
                    getDealersBaseUrl = "https://www.lexus.com/rest/lexus/dealers?experience=dealer&state="
                    resp = requests.get(
                            getDealersBaseUrl + codeToSearch,
                            timeout=20,
                    )
                else:
                    # Toyota: zipcode-based API
                    resp = requests.get(
                            "https://api.ws.dpcmaps.toyota.com/v1/dealers?attributeKey=&searchMode=pmaProximityLayered&zipcode=" + codeToSearch,
                            timeout=20,
                    )
                
                if resp is not None:
                    result = resp.json()
                break
            except (requests.exceptions.JSONDecodeError) as inst:
                print ("updateDealers: Exception occurred with accessing json response:", str(type(inst)) + " "  + str(inst))
                if resp is not None:
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
                # Lexus field mapping
                rename = {
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
                df = (df[["id",
                          "dealerName",
                          "dealerSiteUrl",
                          "dealerLatitude",
                          "dealerLongitude",
                          "dealerAddress.address1",
                          "dealerAddress.city",
                          "dealerAddress.state",
                          "dealerAddress.zipCode",
                          "dealerPhone"]]
                      .copy(deep=True)
                      .rename(columns=rename)
                )
                # copy code to dealerId (same in Toyota)
                df["dealerId"] = df["code"]
                # no regionalId in Lexus
                df["regionId"] = ""
                df["vehicleMake"] = "lexus"
            else:
                # Toyota field mapping
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
                # Add vehicleMake column for Toyota
                df["vehicleMake"] = "toyota"
            # updated address1, city, state, zipcode from the address to match legacy format
            # Only needed for Toyota which has a full address field; Lexus already has separated components
            if vehicleMake == "toyota":
                df = df.apply(updateAddressComponentsIn, axis=1)
                # remove address field as it has been split into other fields (Toyota only)
                df.drop(columns=["address"], inplace=True)
            # format phone number
            df["phone"] = df["phone"].apply(formatPhoneNumber)
            
            if dealers.empty:
                dealers = df
            else:
                dealers = pd.concat([dealers, df], ignore_index=True)
            if False:
                # force the code and dealerId fields to ints as the vehicles.py expects that type (i.e. leading 0s are removed)
                df["code"] = df["code"].apply(pd.to_numeric)
                df["dealerId"] = df["dealerId"].apply(pd.to_numeric)
            #print(df)
            #print("type(df['code'][0])", type(df["code"][0]))
            #print("type(df['lat'][0])", type(df["lat"][0]))
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
        
    # Now concatenate the dealers adders file onto the dealers and keep only the first duplicate if any
    if not dealerAddersDf.empty:
        if dealers.empty:
            dealers = dealerAddersDf
        else:
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
    vehicleMake = "toyota"  # Default to toyota
    
    if len(sys.argv[1:]) >= 3:
        dealerAddersJsonFileName = sys.argv[1:][2]
    if len(sys.argv[1:]) >= 4:
        vehicleMake = sys.argv[1:][3]
    updateDealers(dealerFileName, zipCodeFileName, dealerAddersJsonFileName, vehicleMake)