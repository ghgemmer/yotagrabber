#
import copy
import math
import random
import getpass
import smtplib
import ssl
import time
import datetime
from playsound import playsound  # note that must use version 1.2.2 of playsound as latest one has an exception and won't play mp3s or wavs.
import requests.exceptions
from inputimeout import inputimeout, TimeoutOccurred
import sys
import json
from pathlib import Path
import unidecode
import yaml
import os.path
import os
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import mimetypes
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import base64
import requests
from twilio.rest import Client as TwillioClient
import shutil
import pandas as pd
import numpy as np
import importlib.util
from timeit import default_timer as timer


from yotagrabber import vehicles

# Version
searchForVehiclesVersionStr = "Ver 2.1 June 26 2025"  #

class userMatchCriteria:
    def __init__(self):
        pass
    def filterDataFrame(self, df):
        if debugEnabled:
            print("userMatchCriteria.filterDataFrame df is \n ", df)
            print("userMatchCriteria.filterDataFrame df.columns", df.columns)
            self.print("")
        if len(df) == 0:
            dfFiltered = df
        else:
            dfFiltered = userMatchCriteriaFilterModule.filterDataFrame(df)
        if debugEnabled:
            print("userMatchCriteria.filterDataFrame dfFiltered is \n", dfFiltered)
        return dfFiltered
    def criteriaPrintableString(self):
        # returns a string of the printed criteria
        criteriaStr = ""
        criteriaStr += userMatchCriteriaFilterModule.criteriaPrintableString()
        return criteriaStr
    def print(self, prefix, fileHandle = 0, toConsole = True):
        # prints the criteria to a file and or console with the given prefix
        criteriaStr = prefix + self.criteriaPrintableString()
        if toConsole:
            print(criteriaStr)
        if fileHandle:
            fileHandle.write(criteriaStr + "\n")
        return criteriaStr

# event notification values
programStartUpEvent  = 0
programTerminateEvent = 1
matchesFoundEvent = 2

# emailingMethod is one of the following
emailMessagingWithGmailAndCredsMethod = 0
emailMessagingWithLoginMethod = 1

# textingMethod is one of the following
textMessagingViaEmailMethod = 0
textMessagingWithSinchMethod = 1
textMessagingWithTwilioMethod = 2

paramNotPresentEntry = None
paramNotPresentEntryWhenNoneValid = "!@#ParamNotPresent!!!"

# outputResultsMethod -  Determines how unfiltered match results are output to the running history file, and user notifications.
# Default is outputAllSearchResultsOnChange when commented out.
# outputResultsMethod is one of the following values:
# "outputAllSearchResultsOnChange" -  Outputs all the unfiltered search results to the history file and user notifications when changes occur
# "outputChangedSearchResultsOnChange" - Outputs only the changes in unfiltered search results to the history file and notifications when changes occur
# "outputAddedSearchResultsOnChange"  - Outputs only the added units compared to the previous results (thus removals and stay the same not printed) when changes occur
#outputResultsMethod: outputAllSearchResultsOnChange,
outputAllSearchResultsOnChange = 0
outputChangedSearchResultsOnChange = 1
outputAddedSearchResultsOnChange = 2

unitDetailsDelimiter = chr(9) #tab char to easily separate fields of information as no field should contain a tab char in it.

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



# -----------------------------------------------------------------------
#                                       Default User Specified Config items begin
# -----------------------------------------------------------------------
debugEnabled = False

useLocalInventoryFile = False

runOnceAndExit = False

maxNumberRawMissingVehicles = 0

minWaitTimeBetweenSearches = 60*20 #secs
maxRandomAdderTimeBetweenSearches = 60*10 #secs

resultsFileName = "" #invalid

username = "" #invalid

userMatchCriteriaFilterFileName = "" #invalid

CenterLatLong = [ None, None]

emailingMethod =  -1 # invalid
textingMethod =  -1 # invalid
notificationTextMsgToAddress = "" #invalid
notificationTextMsgFromAddress = "" #invalid
sinchServicePlanId = "" #invalid
sinchAuthorizationToken = "" #invalid
sinchRegion = ""  #invalid
twilioSid = ""  #invalid
twilioAppKeySid = ""  #invalid
twilioAppKeySecret = ""  #invalid
textOnlyMatchesNotification = True,
notificationEmailToAddress = "" #invalid
notificationSenderEmailAddress = "" #invalid
authenticationAuthorizationPath = "" #invalid
notificationMsgPrefixString = "" # No prefix. Prefixed to Msg notification Title or email subject title to differentiate multiple searches.
emailMessagingServerUrl = ""  #invalid

emailMessagingObject = None
textMessagingObject = None

computerSoundNotificationFileName = ""

outputResultsMethod = outputAllSearchResultsOnChange

showRemovalsWhenOutputStatusIsAll = False

alsoNotifyOnOnlyRemovals = False

emailNotificationEvents = [ matchesFoundEvent]
textNotificationEvents = [ matchesFoundEvent]
soundNotificationEvents = [ matchesFoundEvent]
# -----------------------------------------------------------------------
#                                       Default User Specified Config items end
# -----------------------------------------------------------------------

minSleepTime = 1.0  #  secs between post, get sends
minRandomTimeScaler = 1.0  #  secs between post, get sends

lastUserMatchesDf = pd.DataFrame() # empty dataframe
lastRunUserMatchesParquetFileName = "" #no last run parquet file

userMatchCriteriaFilterModule = ""

dbgUsingLocalVehicleDataFile = False #TODO change this back to False once finish debug

def import_from_path(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

def stringsToStringAddingLineFeedDelimiters(listOfStrings):
    # combines the passed list of strings in order into a single string adding Line feed delimiters between the strings, and returns that combined string
    combinedString = ""
    for strng in listOfStrings:
        combinedString += str(strng) + "\n"
    return combinedString


def logToResultsFile(strng, printIt = False, timestamp = True, error = False, logToErrorFile = False):
    global resultsFileName
    prefix = ""
    if error:
        prefix += "Error: "
    if timestamp:
        prefix += getDatetimeWithTzStr(datetime.datetime.now().astimezone()) + " "
    if logToErrorFile:
        fileName = Path(resultsFileName + ".errorLog.txt")
    else:
        fileName = Path(resultsFileName)
    with open(fileName, 'a+') as f:
        f.write(prefix + strng)
        f.write("\n")
    if printIt:
        print(prefix + strng)

def sanitizeStr(strng, replaceTabs = False):
    # Replace characters in strng that cause/might cause issues with linux scripts, such as the Sightings/Matches,
    # with an  underscore "_"
    # Normally only used when outputing to the terminal or a file where that information would be
    # used by Linux scripts.
    rePattern = r'[^\u0000-\u007F]'  # only allow ascii chars represented by hex value 0 -7F.  Pattern is the negation of htis (ie finds anything not this()
    sanitizedString = re.sub(rePattern, '_', strng)
    if replaceTabs:
        rePattern = r'[\u0009]'
        sanitizedString = re.sub(rePattern, ' ', sanitizedString)
    return sanitizedString

class configParameterInfo:
    def __init__(self, present=False, valid=False, value=""):
        self.present = present
        self.valid = valid
        self.value = value

# Each entry is a configParameterInfo
configParametersInfo = {
"username": configParameterInfo(),
"resultsFileName": configParameterInfo(),
"userMatchCriteriaFilterFileName": configParameterInfo(),
"CenterLatLong": configParameterInfo(),
"useLocalInventoryFile": configParameterInfo(),
"runOnceAndExit": configParameterInfo(),
"maxNumberRawMissingVehicles": configParameterInfo(),
"minWaitTimeBetweenSearches": configParameterInfo(),
"maxRandomAdderTimeBetweenSearches": configParameterInfo(),
"debugEnabled": configParameterInfo(),
"notificationTextMsgToAddress": configParameterInfo(),
"notificationTextMsgFromAddress": configParameterInfo(),
"notificationEmailToAddress": configParameterInfo(),
"notificationSenderEmailAddress": configParameterInfo(),
"authenticationAuthorizationPath": configParameterInfo(),
"notificationMsgPrefixString": configParameterInfo(),
"emailingMethod": configParameterInfo(),
"textingMethod": configParameterInfo(),
"sinchServicePlanId": configParameterInfo(),
"sinchAuthorizationToken": configParameterInfo(),
"sinchRegion": configParameterInfo(),
"twilioSid": configParameterInfo(),
"twilioAppKeySecret": configParameterInfo(),
"twilioAppKeySid": configParameterInfo(),
"computerSoundNotificationFileName": configParameterInfo(),
"emailMessagingServerUrl": configParameterInfo(),
"textOnlyMatchesNotification": configParameterInfo(),
"outputResultsMethod": configParameterInfo(),
"alsoNotifyOnOnlyRemovals": configParameterInfo(),
"showRemovalsWhenOutputStatusIsAll": configParameterInfo(),
"emailNotificationEvents": configParameterInfo(),
"textNotificationEvents": configParameterInfo(),
"soundNotificationEvents": configParameterInfo()
}

configEmailingMethodMap = {"emailMessagingWithGmailAndCreds": emailMessagingWithGmailAndCredsMethod, "emailMessagingWithLogin": emailMessagingWithLoginMethod }
configTextingMethodMap = {"textMessagingViaEmail": textMessagingViaEmailMethod, "textMessagingWithSinch": textMessagingWithSinchMethod, "textMessagingWithTwilio": textMessagingWithTwilioMethod}
configOutputResultsMethodMap = {"outputAllSearchResultsOnChange": outputAllSearchResultsOnChange, "outputChangedSearchResultsOnChange": outputChangedSearchResultsOnChange, "outputAddedSearchResultsOnChange": outputAddedSearchResultsOnChange}
configNotificationEventMap = {"programStartUpEvent": programStartUpEvent, "programTerminateEvent": programTerminateEvent, "matchesFoundEvent": matchesFoundEvent }

def parseConfigFile(fileName):
    global username
    global resultsFileName
    global userMatchCriteriaFilterFileName
    global CenterLatLong
    global useLocalInventoryFile
    global runOnceAndExit
    global maxNumberRawMissingVehicles
    global minWaitTimeBetweenSearches
    global maxRandomAdderTimeBetweenSearches
    global debugEnabled
    global notificationTextMsgToAddress
    global notificationTextMsgFromAddress
    global notificationEmailToAddress
    global notificationSenderEmailAddress
    global authenticationAuthorizationPath
    global notificationMsgPrefixString
    global emailingMethod
    global textingMethod
    global sinchServicePlanId
    global sinchAuthorizationToken
    global sinchRegion
    global twilioSid
    global twilioAppKeySid
    global twilioAppKeySecret
    global computerSoundNotificationFileName
    global emailMessagingWithLoginMethod
    global emailMessagingServerUrl
    global textOnlyMatchesNotification
    global outputResultsMethod
    global alsoNotifyOnOnlyRemovals
    global showRemovalsWhenOutputStatusIsAll
    global emailNotificationEvents
    global textNotificationEvents
    global soundNotificationEvents
    configOk = False
    configFile = Path(fileName)
    if fileName and configFile.is_file():
        with open(Path(fileName), "r") as f:
            configOk = True
            try:
                paramsDic = yaml.safe_load(f)
            except yaml.YAMLError as inst:
                print("Error: Config file not valid YAML format", str(inst))
                configOk = False
            if configOk:
                for paramName in paramsDic:
                    if paramName in configParametersInfo:
                        if debugEnabled:
                            print("parseConfigFile: found parameter", str(paramsDic[paramName]))
                        configParametersInfo[paramName].present = True
                        configParametersInfo[paramName].value = paramsDic[paramName]
                        configParametersInfo[paramName].valid = True
                        # TODO add in validation for each parameter.  Possibly replace the code below with a parsing class for each item that can
                        # validate and set the value for each item or at least validate the range of the item
                        if paramName == "username":
                            username = paramsDic[paramName]
                        elif paramName == "resultsFileName":
                            resultsFileName = paramsDic[paramName]
                        elif paramName == "useLocalInventoryFile":
                            useLocalInventoryFile = paramsDic[paramName]
                        elif paramName == "runOnceAndExit":
                            runOnceAndExit = paramsDic[paramName]
                        elif paramName == "maxNumberRawMissingVehicles":
                            maxNumberRawMissingVehicles = paramsDic[paramName]
                        elif paramName == "userMatchCriteriaFilterFileName":
                            userMatchCriteriaFilterFileName = paramsDic[paramName]
                        elif paramName == "CenterLatLong":
                            CenterLatLong = paramsDic[paramName]
                        elif paramName == "minWaitTimeBetweenSearches":
                            minWaitTimeBetweenSearches = paramsDic[paramName]
                        elif paramName == "maxRandomAdderTimeBetweenSearches":
                            maxRandomAdderTimeBetweenSearches = paramsDic[paramName]
                        elif paramName == "debugEnabled":
                            debugEnabled = paramsDic[paramName]
                        elif paramName == "notificationTextMsgToAddress":
                            notificationTextMsgToAddress = paramsDic[paramName]
                        elif paramName == "notificationTextMsgFromAddress":
                            notificationTextMsgFromAddress = paramsDic[paramName]
                        elif paramName == "notificationEmailToAddress":
                            notificationEmailToAddress = paramsDic[paramName]
                        elif paramName == "notificationSenderEmailAddress":
                            notificationSenderEmailAddress = paramsDic[paramName]
                        elif paramName == "authenticationAuthorizationPath":
                            authenticationAuthorizationPath = paramsDic[paramName]
                        elif paramName == "notificationMsgPrefixString":
                            notificationMsgPrefixString = paramsDic[paramName]
                        elif paramName == "emailingMethod":
                            if paramsDic[paramName] in configEmailingMethodMap:
                                emailingMethod = configEmailingMethodMap[paramsDic[paramName]]
                            else:
                                print("Error: parseConfigFile: emailingMethod not valid in config file ", paramsDic[paramName])
                                configOk = False
                        elif paramName == "textingMethod":
                            if paramsDic[paramName] in configTextingMethodMap:
                                textingMethod = configTextingMethodMap[paramsDic[paramName]]
                            else:
                                print("Error: parseConfigFile: textingMethod not valid in config file ", paramsDic[paramName])
                                configOk = False
                        elif paramName == "sinchServicePlanId":
                            sinchServicePlanId = paramsDic[paramName]
                        elif paramName == "sinchAuthorizationToken":
                            sinchAuthorizationToken = paramsDic[paramName]
                        elif paramName == "sinchRegion":
                            sinchRegion = paramsDic[paramName]
                        elif paramName == "twilioSid":
                            twilioSid = paramsDic[paramName]
                        elif paramName == "twilioAppKeySid":
                            twilioAppKeySid = paramsDic[paramName]
                        elif paramName == "twilioAppKeySecret":
                            twilioAppKeySecret = paramsDic[paramName]
                        elif paramName == "computerSoundNotificationFileName":
                            computerSoundNotificationFileName = paramsDic[paramName]
                        elif paramName == "emailMessagingServerUrl":
                            emailMessagingServerUrl = paramsDic[paramName]
                        elif paramName == "continueSearchingAfterMatch":
                            continueSearchingAfterMatch = paramsDic[paramName]
                        elif paramName == "textOnlyMatchesNotification":
                            textOnlyMatchesNotification = paramsDic[paramName]
                        elif paramName == "outputResultsMethod":
                            if paramsDic[paramName] in configOutputResultsMethodMap:
                                outputResultsMethod = configOutputResultsMethodMap[paramsDic[paramName]]
                            else:
                                print("Error: parseConfigFile: outputResultsMethod not valid in config file ", paramsDic[paramName])
                                configOk = False
                        elif paramName == "alsoNotifyOnOnlyRemovals":
                             alsoNotifyOnOnlyRemovals = paramsDic[paramName]
                        elif paramName == "showRemovalsWhenOutputStatusIsAll":
                             showRemovalsWhenOutputStatusIsAll = paramsDic[paramName]
                        elif paramName == "emailNotificationEvents":
                            emailNotificationEvents = []
                            for event in paramsDic[paramName]:
                                if event in configNotificationEventMap:
                                    emailNotificationEvents.append(configNotificationEventMap[event])
                                else:
                                    print("Error: parseConfigFile: emailNotificationEvents event not valid in config file ", event)
                                    configOk = False
                        elif paramName == "textNotificationEvents":
                            textNotificationEvents = []
                            for event in paramsDic[paramName]:
                                if event in configNotificationEventMap:
                                    textNotificationEvents.append(configNotificationEventMap[event])
                                else:
                                    print("Error: parseConfigFile: textNotificationEvents event not valid in config file ", event)
                                    configOk = False
                        elif paramName == "soundNotificationEvents":
                            soundNotificationEvents = []
                            for event in paramsDic[paramName]:
                                if event in configNotificationEventMap:
                                    soundNotificationEvents.append(configNotificationEventMap[event])
                                else:
                                    print("Error: parseConfigFile: soundNotificationEvents event not valid in config file ", event)
                                    configOk = False
                    else:
                        print("Error: parseConfigFile:", paramName, "not a valid parameter name in the config file", fileName)
                        configOk = False
                if configOk:
                    # check to ensure all needed values present
                    if not username:
                        print("Error: parseConfigFile: username missing or blank in config file")
                        configOk = False
                    elif not((textOnlyMatchesNotification == True) or (textOnlyMatchesNotification == False)):
                        print("Error: parseConfigFile: textOnlyMatchesNotification invalid in config file")
                        configOk = False
                    elif not resultsFileName:
                        print("Error: parseConfigFile: resultsFileName missing or blank in config file")
                        configOk = False
                    elif (not userMatchCriteriaFilterFileName) or not(Path(userMatchCriteriaFilterFileName).is_file()):
                        print("Error: parseConfigFile: userMatchCriteriaFilterFileName file does not exist. File name is:", userMatchCriteriaFilterFileName )
                        configOk = False
                    elif (not authenticationAuthorizationPath) and (emailingMethod == emailMessagingWithGmailAndCredsMethod):
                        print("Error: parseConfigFile: authenticationAuthorizationPath missing or invalid in config file but needed when emailingMethod specified use of credentials")
                        # clear email to addresses so can use these in conditionals later on even if config bad elsewhere.
                        notificationEmailToAddress = ""
                        configOk = False
                    elif (not emailMessagingServerUrl) and (emailingMethod == emailMessagingWithLoginMethod):
                        print("Error: parseConfigFile: emailMessagingServerUrl missing or invalid in config file but needed when emailingMethod specified use of Login")
                        # clear email to addresses so can use these in conditionals later on even if config bad elsewhere.
                        notificationEmailToAddress = ""
                        configOk = False
                    elif notificationTextMsgToAddress and (textingMethod != textMessagingViaEmailMethod) and not((textingMethod != -1) and notificationTextMsgFromAddress ):
                        print("Error: parseConfigFile: notificationTextMsgToAddress present enabling text notifications and textingMethod != textMessagingViaEmailMethod but needs the following to be true: ((textingMethod valid) and notificationTextMsgFromAddress) ")
                        # clear text to address so can use these in conditionals later on even if config bad elsewhere.
                        notificationTextMsgToAddress = ""
                        configOk = False
                    elif notificationTextMsgToAddress and (textingMethod == textMessagingViaEmailMethod) and not( notificationSenderEmailAddress and (emailingMethod != -1)):
                        print("Error: parseConfigFile: notificationTextMsgToAddress present enabling text notifications and textingMethod == textMessagingViaEmailMethod  but needs the following to be true: (notificationSenderEmailAddress and (emailingMethod valid)) ")
                        # clear text to address so can use these in conditionals later on even if config bad elsewhere.
                        notificationTextMsgToAddress = ""
                        configOk = False
                    elif notificationTextMsgToAddress and (textingMethod == textMessagingWithSinchMethod) and not( sinchServicePlanId and sinchAuthorizationToken and sinchRegion ):
                        print("Error: parseConfigFile: notificationTextMsgToAddress present enabling text notifications and textMessagingWithSinchMethod textingMethod but needs all the following to be valid  sinchServicePlanId sinchAuthorizationToken sinchRegion")
                        # clear text to address so can use these in conditionals later on even if config bad elsewhere.
                        notificationTextMsgToAddress = ""
                        configOk = False
                    elif notificationTextMsgToAddress and (textingMethod == textMessagingWithTwilioMethod) and not( twilioSid and twilioAppKeySid and twilioAppKeySecret ):
                        print("Error: parseConfigFile: notificationTextMsgToAddress present enabling text notifications and textMessagingWithTwilioMethod textingMethod but needs all the following to be valid  twilioSid twilioAppKeySid twilioAppKeySecret")
                        # clear text to address so can use these in conditionals later on even if config bad elsewhere.
                        notificationTextMsgToAddress = ""
                        configOk = False
                    elif notificationEmailToAddress and not( notificationSenderEmailAddress and (emailingMethod != -1)):
                        print("Error: parseConfigFile: notificationEmailToAddress present enabling emailing notifications but needs the following to be true: notificationSenderEmailAddress and (emailingMethod valid) ")
                        # clear text to address so can use these in conditionals later on even if config bad elsewhere.
                        notificationEmailToAddress = ""
                        configOk = False
                    elif computerSoundNotificationFileName and not(Path(computerSoundNotificationFileName).is_file()):
                        print("Error: parseConfigFile: computerSoundNotificationFileName does not exist: ", computerSoundNotificationFileName)
                        configOk = False
    else:
        print("Error: Config file", fileName, "does not exist. Cannot continue" )
    return configOk


class textMessaging:
    #Class for all text messaging operations.
    def __init__(self):
        pass
    def Initialize(self):
        pass
    def maintainOperations(self):
        pass
    def sendMessage(self, toNumber = "", fromNumber = "", msgText = ""):
        # Sends a text message using the indicated parameters
        print("Implement this in the derived class")

class textMessagingWithSinch(textMessaging):
    #Class for all text messaging operations using Sinch account.
    def __init__(self, servicePlanId = "", authorizationToken = "", region = "us"):
        super().__init__()
        self._servicePlanId = servicePlanId
        self._authorizationToken = authorizationToken
        self._region = region
        
    def sendMessage(self, toNumber = "", fromNumber = "", msgText = ""):
        # Sends a text message using the indicated parameters
        #print("textMessagingWithSinch:sendMessage: toNumber , fromNumber , msgText :", toNumber, fromNumber, msgText)
        #print("textMessagingWithSinch:sendMessage: self._servicePlanId, self._authorizationToken, self._region", self._servicePlanId, self._authorizationToken, self._region)
        url = "https://" + self._region + ".sms.api.sinch.com/xms/v1/" + self._servicePlanId + "/batches"
        #print("textMessagingWithSinch:sendMessage:url - ", url)
        payload = {
          "from": fromNumber,
          "to": [
             toNumber
          ],
          "body": msgText
        }
        headers = {
          "Content-Type": "application/json",
          "Authorization": "Bearer " + self._authorizationToken
        }
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()
        if debugEnabled:
            print("textMessagingWithSinch:SendMessagedata: response data is", data)


class textMessagingWithTwilio(textMessaging):
    #Class for all text messaging operations using Twilio account.
    def __init__(self, sid = "", appKeySid = "", appKeySecret = ""):
        super().__init__()
        self._sid = sid  # account sid
        self._appKeySid = appKeySid
        self._appKeySecret = appKeySecret
    def sendMessage(self, toNumber = "", fromNumber = "", msgText = ""):
        # Sends a text message using the indicated parameters
        #print("textMessagingWithSinch:sendMessage: toNumber , fromNumber , msgText :", toNumber, fromNumber, msgText)
        client = TwillioClient(self._appKeySid, self._appKeySecret, self._sid)
        message = client.messages.create(  # this also sends the messsage
             body = msgText,
             from_ = '+' + fromNumber,
             to = '+' + toNumber
             )
        if debugEnabled:
            print("textMessagingWithTwilio:SendMessage: response data is", message)

class textMessagingViaEmail(textMessaging):
    #Class for all text messaging operations via sending an email to an sms gateway.
    def __init__(self, emailMessagingObject = None ):
        super().__init__()
        self._emailMessagingObject = emailMessagingObject
    def sendMessage(self, toNumber = "", fromNumber = "", msgText = ""):
        # Sends a text message using the indicated parameters.
        # The toNumber is of the form <phone number>@<smsgateway>
        # Note that the fromNumber is not used as the reference to the email object
        # is passed and it already contains this among other things.
        self._emailMessagingObject.sendMessage(toNumber, "Search Notification:", msgText) # use a non blank subjec to keep things happy


class emailMessaging:
    #Class for all email messaging operations.
    def __init__(self, fromAddress = ""):
        self._fromAddress = fromAddress
    def Initialize(self):
        pass
    def maintainOperations(self):
        pass
    def sendMessage(self, toAddress = "", subject = "", msgText = "", attachmentFile = ""):
        # Sends an email using the indicated parameters
        print("Implement this in the derived class")


class emailMessagingWithLogin(emailMessaging):
    #Class for email messaging operations using an email server and user login.
    def __init__(self, fromAddress = "", serverUrl = ""):
        super().__init__(fromAddress)
        self._serverUrl = serverUrl
        self._password = ""
    def Initialize(self):
        print("Enter email password and press enter")
        self._password = getpass.getpass()
    def sendMessage(self, toAddress = "", subject = "", msgText = "", attachmentFile = ""):
        # Sends an email using the indicated parameters
        if not attachmentFile:
            msg = create_message(self._fromAddress, toAddress, subject, msgText, False);
        else:
            msg = create_message_with_attachment(self._fromAddress, toAddress, subject, msgText, attachmentFile, False);
        text = msg
        #text = msg['raw']
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(self._serverUrl, 465, context=context) as server:
            server.login(self._fromAddress, self._password)
            server.sendmail(self._fromAddress, toAddress, text)


class emailMessagingWithGmailAndCreds(emailMessaging):
    #Class for gmail with oauth2 credentials email messaging operations.
    def Initialize(self):
        get_credentials()
    def sendMessage(self, toAddress = "", subject = "", msgText = "", attachmentFile = ""):
        # Sends an email using the indicated parameters
        creds = get_credentials()
        if not attachmentFile:
            service = build('gmail', 'v1', credentials=creds)
            msg = create_message(self._fromAddress, toAddress, subject, msgText);
            results =  send_message(service, "me", msg)
        else:
            service = build('gmail', 'v1', credentials=creds)
            msg = create_message_with_attachment(self._fromAddress, toAddress, subject, msgText, attachmentFile);
            results =  send_message(service, "me", msg)
    def maintainOperations(self):
        # maintain credential authorizations.
        get_credentials()


# Note: Large text messages (1044 bytes is too long) for receiving a google text message.
# It does however work fine if receiving an e-mail (i.e not sending a google voice text message)
# So for example can send a short text message saying found a timeshare exchange and to check your email
# and send an email with all the information.
# Attachments only work for email messages, not text messages based on testing.
# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def create_message_with_attachment(
    sender, to, subject, message_text, file, raw = True):
  """Create a message for an email.
  Args:
    sender: Email address of the sender.
    to: Email address of the receiver.
    subject: The subject of the email message.
    message_text: The text of the email message.
    file: The path to the file to be attached.
    raw:  True: See Returns below
          False: See Returns below
    Returns:
    When raw True:  A dictionary containing a base64url encoded email object entry {'raw':  the base64.urlsafe_b64encode(message.as_string().encode()).decode()
    When raw False: An object that is the emailObject.as_string() conversion.
  """
  message = MIMEMultipart()
  message['to'] = to
  message['from'] = sender
  message['subject'] = subject
  msg = MIMEText(message_text)
  message.attach(msg)
  content_type, encoding = mimetypes.guess_type(file)
  if content_type is None or encoding is not None:
    content_type = 'application/octet-stream'
  main_type, sub_type = content_type.split('/', 1)
  if main_type == 'text':
    fp = open(Path(file), 'r') # 'rb' will send this error: 'bytes' object has no attribute 'encode'
    msg = MIMEText(fp.read(), _subtype=sub_type)
    fp.close()
  elif main_type == 'image':
    fp = open(Path(file), 'rb')
    msg = MIMEImage(fp.read(), _subtype=sub_type)
    fp.close()
  elif main_type == 'audio':
    fp = open(Path(file), 'rb')
    msg = MIMEAudio(fp.read(), _subtype=sub_type)
    fp.close()
  else:
    fp = open(Path(file), 'rb')
    msg = MIMEBase(main_type, sub_type)
    msg.set_payload(fp.read())
    fp.close()
  filename = os.path.basename(file)
  msg.add_header('Content-Disposition', 'attachment', filename=filename)
  message.attach(msg)
  if raw:
    return {'raw': base64.urlsafe_b64encode(message.as_string().encode()).decode()}
  else:
    return message.as_string()

def create_message(sender, to, subject, message_text, raw = True):
    """Create a message for an email.
    Args:
    sender: Email address of the sender.
    to: Email address of the receiver.
    subject: The subject of the email message.
    message_text: The text of the email message.
    raw:  True: See Returns below
          False: See Returns below
    Returns:
    When raw True:  A dictionary containing a base64url encoded email object entry {'raw':  the base64.urlsafe_b64encode(message.as_string().encode()).decode()
    When raw False: An object that is the emailObject.as_string() conversion.
    """
    message = MIMEText(message_text)
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    if debugEnabled:
        print(message.as_string())
    if raw:
        return {'raw': base64.urlsafe_b64encode(message.as_string().encode()).decode()}
    else:
        return message.as_string()

def send_message(service, user_id, message):
    """Send an email message.
    Args:
    service: Authorized Gmail API service instance.
    user_id: User's email address. The special value "me"
    can be used to indicate the authenticated user.
    message: Message to be sent.
    Returns:
    Sent Message.
    """
    try:
        message = (service.users().messages().send(userId=user_id, body=message)
                   .execute())
        if debugEnabled:
            print ('Message Id: %s', message['id'])
        return message
    except(errors.HttpError) as error:
        print('An error occurred: %s', error)

def get_credentials():
    global authenticationAuthorizationPath
    global resultsFileName
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    tokenFileName = Path(resultsFileName + '.token.json')
    if os.path.exists(tokenFileName):
        creds = Credentials.from_authorized_user_file(tokenFileName, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing remote notifications authorization/authentication token")
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                Path(authenticationAuthorizationPath + 'credentials.json'), SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(tokenFileName, 'w') as token:
            token.write(creds.to_json())
    return creds

def notificationsInitialization():
    global emailMessagingObject
    global textMessagingObject
    global sinchServicePlanId
    global sinchAuthorizationToken
    global sinchRegion
    global twilioSid
    global twilioAppKeySid
    global twilioAppKeySecret
    global notificationTextMsgToAddress
    global notificationEmailToAddress
    global notificationSenderEmailAddress
    global textingMethod
    global textMessagingViaEmailMethod
    global textMessagingWithSinchMethod
    global textMessagingWithTwilioMethod
    global emailingMethod
    global emailMessagingWithGmailAndCredsMethod
    global emailMessagingWithLoginMethod
    if notificationEmailToAddress or (notificationTextMsgToAddress and (textingMethod == textMessagingViaEmailMethod)):
        if emailingMethod == emailMessagingWithGmailAndCredsMethod:
            emailMessagingObject = emailMessagingWithGmailAndCreds(notificationSenderEmailAddress)
        elif emailingMethod == emailMessagingWithLoginMethod:
            emailMessagingObject = emailMessagingWithLogin(notificationSenderEmailAddress, emailMessagingServerUrl)
        else:
            print("Error:  notificationsInitialization:  emailingMethod is not valid", emailingMethod)
            raise SystemExit
    if notificationTextMsgToAddress:
        if textingMethod == textMessagingViaEmailMethod:
            textMessagingObject = textMessagingViaEmail(emailMessagingObject)
        elif textingMethod == textMessagingWithSinchMethod:
            #print("notificationsInitialization sinchServicePlanId, sinchAuthorizationToken, sinchRegion", sinchServicePlanId, sinchAuthorizationToken, sinchRegion)
            textMessagingObject = textMessagingWithSinch(sinchServicePlanId, sinchAuthorizationToken, sinchRegion)
        elif textingMethod == textMessagingWithTwilioMethod:
            #print("notificationsInitialization twilioSid (acct sid), twilioAppKeySid, twilioAppKeySecret,", twilioSid, twilioAppKeySid, twilioAppKeySecret)
            textMessagingObject = textMessagingWithTwilio(twilioSid, twilioAppKeySid, twilioAppKeySecret)
        else:
            print("Error:  notificationsInitialization:  textingMethod is not valid", textingMethod)
            raise SystemExit
    if emailMessagingObject:
        emailMessagingObject.Initialize()
    if textMessagingObject:
        textMessagingObject.Initialize()

def notifyRemoteUserOfSearchStart():
    global notificationTextMsgToAddress
    global notificationEmailToAddress
    global notificationSenderEmailAddress
    global notificationMsgPrefixString
    global emailNotificationEvents
    global textNotificationEvents
    global programStartUpEvent
    if (programStartUpEvent in textNotificationEvents) and (notificationTextMsgToAddress and (not textOnlyMatchesNotification)):
        textMessagingObject.sendMessage(notificationTextMsgToAddress, notificationTextMsgFromAddress, notificationMsgPrefixString + getDatetimeWithTzStr(datetime.datetime.now().astimezone(), includeHundredthSeconds = True) + " Started Vehicle program Search")
        # Note that notificationTextMsgFromAddress ignored when textingMethod is textMessagingViaEmailMethod
        # Date time down to fractional seconds used in text to make the text message have a different content so that different close in time text messages get sent and not suppressed (when using google voice at least)
    if (programStartUpEvent in emailNotificationEvents) and (notificationEmailToAddress):
        emailMessagingObject.sendMessage(notificationEmailToAddress, notificationMsgPrefixString + "Started Vehicle program Search ", notificationMsgPrefixString + getDatetimeWithTzStr(datetime.datetime.now().astimezone()) + " Started Vehicle program Search")


def notifyRemoteUserOfMatches(resultsFileName):
    global notificationTextMsgToAddress
    global notificationEmailToAddress
    global notificationSenderEmailAddress
    global notificationMsgPrefixString
    global emailNotificationEvents
    global textNotificationEvents
    global matchesFoundEvent
    if (matchesFoundEvent in textNotificationEvents) and  notificationTextMsgToAddress:
        textMessagingObject.sendMessage(notificationTextMsgToAddress, notificationTextMsgFromAddress, notificationMsgPrefixString + getDatetimeWithTzStr(datetime.datetime.now().astimezone(), includeHundredthSeconds = True) + " Vehicle match was found.  See email for matches.")
        # Note that notificationTextMsgFromAddress ignored when textingMethod is textMessagingViaEmailMethod
        # Date time down to fractional seconds used in text to make the text message have a different content so that different close in time text messages get sent and not suppressed (when using google voice at least)
    if (matchesFoundEvent in emailNotificationEvents) and (notificationEmailToAddress):
        emailMessagingObject.sendMessage(notificationEmailToAddress, notificationMsgPrefixString + "Vehicle Match Found", notificationMsgPrefixString + "Vehicle match was found for search.  See attached file for results", resultsFileName)

def notifyRemoteUserOfTerminate():
    global notificationTextMsgToAddress
    global notificationEmailToAddress
    global notificationSenderEmailAddress
    global notificationMsgPrefixString
    global emailNotificationEvents
    global textNotificationEvents
    global programTerminateEvent
    if (programTerminateEvent in textNotificationEvents) and (notificationTextMsgToAddress and (not textOnlyMatchesNotification)):
        textMessagingObject.sendMessage(notificationTextMsgToAddress, notificationTextMsgFromAddress, notificationMsgPrefixString + getDatetimeWithTzStr(datetime.datetime.now().astimezone(), includeHundredthSeconds = True) + " Terminated Vehicle program Search")
        # Note that notificationTextMsgFromAddress is ignored when textingMethod is textMessagingViaEmailMethod
        # Date time down to fractional seconds used in text to make the text message have a different content so that different close in time text messages get sent and not suppressed (when using google voice at least)
    if (programTerminateEvent in emailNotificationEvents) and (notificationEmailToAddress):
        emailMessagingObject.sendMessage(notificationEmailToAddress, notificationMsgPrefixString + "Terminated Vehicle program Search", notificationMsgPrefixString + str(datetime.datetime.now().astimezone()) + " Terminated Vehicle program Search")

def notificationsAuthorization():
    # This will also handle slightly expired authorizations.
    if emailMessagingObject:
        emailMessagingObject.maintainOperations()
    if textMessagingObject:
        textMessagingObject.maintainOperations()



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
    
    
def printUnitDetailsUsingChangeType(rowSeries, prefix, unitDetailsDelimiter, printColumnsToUse, fileHandle = 0, printIt = True, suppressFixedUnitDetailsPrefix = False, sanitizeStrings = True):
    # prints to display and or writes to a file(or does neither) the indicated rowSeries columns printColumnsToUse using the unitDetailsDelimiter.
    # Returns the string that would be/was printed/written regardless of whether it was actually printed/written.
    # suppressFixedUnitDetailsPrefix suppresses the " Unit Details ->" prefix text
    # if rowSeries contains the rowChangeTypeColumnName then one of ADDED, REMOVED, SAME is appened to the prefix, otherwise blanks are added in that place.
    # 
    #print("printUnitDetailsUsingChangeType: prefix ", prefix, "unitDetailsDelimiter" , unitDetailsDelimiter, "printColumnsToUse", printColumnsToUse, "fileHandle", fileHandle, "printIt", printIt, "suppressFixedUnitDetailsPrefix", suppressFixedUnitDetailsPrefix, "sanitizeStrings", sanitizeStrings)
    detailsStr = ""
    if suppressFixedUnitDetailsPrefix:
        fixedUnitDetailsPrefix = ""
    else:
        fixedUnitDetailsPrefix = " Unit Details ->"
    changeTypeStr = ":,         "
    if rowChangeTypeColumnName in rowSeries:
        if rowSeries[rowChangeTypeColumnName] == rowAddedNewVINIndicator:
            changeTypeStr = ":, ***ADDED"
        elif rowSeries[rowChangeTypeColumnName] == rowModifiedVINContentsIndicator:
            changeTypeStr = ":, ***MODED"
        elif rowSeries[rowChangeTypeColumnName] == rowRemovedVINIndicator:
            changeTypeStr = ":, ***REMOVED"
    detailsStr = prefix  + unitDetailsDelimiter + changeTypeStr + fixedUnitDetailsPrefix
    # Output is field delimited by unitDetailsDelimiter
    for column in rowSeries.index:
        if (column != rowChangeTypeColumnName) and (column in printColumnsToUse):
            value = rowSeries[column]
            if not( (column == rowModificationsColumnName) and (valueIsNanNoneNull(value))):
                detailsStr += unitDetailsDelimiter + str(column) + ": " + unitDetailsDelimiter + str(value)
    if printIt:
        print(detailsStr)
    if fileHandle:
        fileHandle.write(detailsStr + '\n')
    return detailsStr

def getOutputResultsMethodString(outputResultsMethod):
    strng = "Unknown"
    for method in configOutputResultsMethodMap:
        if configOutputResultsMethodMap[method] == outputResultsMethod:
            strng = method
            break
    return strng

def outputSearchingInfoToUser(matchCriteria):
    global username
    global maxNumberRawMissingVehicles
    global alsoNotifyOnOnlyRemovals
    global showRemovalsWhenOutputStatusIsAll
    global outputResultsMethod
    print("outputResultsMethod:", getOutputResultsMethodString(outputResultsMethod))
    print("alsoNotifyOnOnlyRemovals:", alsoNotifyOnOnlyRemovals)
    print("showRemovalsWhenOutputStatusIsAll", showRemovalsWhenOutputStatusIsAll)
    print("runOnceAndExit: ", runOnceAndExit)
    print("maxNumberRawMissingVehicles: ", maxNumberRawMissingVehicles)
    print(getModelToGetInfo())
    matchCriteria.print("", toConsole = True)
    print("Username:", username)

def getSearchResultsColumnsLabelsStr(columns , columnsToIgnore):
    # returns the column lables string that is output to match the search results lines 
    # Can be used when open text file with Excel and specifying to use the delimiter to read it in.
    # columns and columnsToIgnore is either a pandas Index type object or a list.
    global unitDetailsDelimiter
    labelsStr = ""
    labelsStr += "Found Date" + unitDetailsDelimiter + "Diff Prefix" + unitDetailsDelimiter 
    for column in columns:
        if not (column in columnsToIgnore):
            # Add a dummy blank column label and then the actual column label to match how the
            # search results outputs a label name + delimiter + value + delimiter  for each column in the dataframe
            labelsStr += unitDetailsDelimiter + column + unitDetailsDelimiter 
    return labelsStr
    
def valueIsNanNoneNull(value):
    return (value is None) or (isinstance(value, float) and np.isnan(value))



def vinNumberIsTheSame(details1, details2):
    # Determines if the single row or empty panda.dataframe details1 and single row or empty panda.dataframe details2 have
    # the same VIN number
    # Compares the VIN column of the dataframes.
    # !!!!!Assumes nan has been replaced with None in the passed DataFrames.
    global debugEnabled
    #if debugEnabled:
    #timer_start = timer()
    #print("vinNumberIsTheSame details1", details1)
    #print("vinNumberIsTheSame details2", details2)
    #return False  # remove when implemented
    vinFieldName = "VIN"
    theSame = False
    if (vinFieldName in details1) and (vinFieldName in details2):
        # both have VIN field
        if  details1.shape[0] == details2.shape[0]:
            # both have same number of rows which should be 0 or 1.  We only compare the first row anyway
            theSame = True
            for index1 in details1.index:
                for index2 in details2.index:
                    if details1.at[index1, vinFieldName] != details2.at[index2, vinFieldName]:
                        theSame = False
                        #if debugEnabled:
                        #    print("vinNumberIsTheSame", index1, vinFieldName, index2, details1.at[index1, vinFieldName], details2.at[index2, vinFieldName], index1, vinFieldName, index2, details1.at[index1, vinFieldName], details2.at[index2, vinFieldName])
                        break
                    break
                break
    #if debugEnabled:
    #print("vinNumberIsTheSame returning theSame as", theSame)
    #print("Elapsed time", timer() - timer_start )
    return theSame
  


def getTimeZoneStr(dt, getFullString = False):
    # gets the time zone string of the datetime class object.  When getFullString = True it gets the full time zone string otherwise it gets the
    # abbreviated time zone string.
    Str = ""
    if dt.tzinfo is not None:
        dtm = dt
    else:
        dtm = dt.astimezone() # add in local time zone
    if getFullString:
        Str = dtm.tzinfo.tzname(dtm)
    else:
        words = dtm.tzinfo.tzname(dtm).split()
        # get first letter of each word
        Str = ""
        for word in words:
            Str += word[0]
    return Str


def getDatetimeWithTzStr(dt, getFullTimeZoneString = False, includeHundredthSeconds = False):
    # returns a string of the date time along with the timezone for the passed in datetime class object or None
    # It is assumed that the dt is datetime object with timezone info already in it.
    # Typically usage to get the timezone i is getDatetimeWithTzStr(datetime.datetime.now().astimezone())
    dateTimeWithTimeZoneStr = ""
    if dt is not None:
        if includeHundredthSeconds:
            dateTimeStr = str(dt)[0:22]  # 2022-09-20 19:59:17.202390-05:00
        else:
            dateTimeStr = str(dt)[0:20]  # remove all the microseconds part
        dateTimeWithTimeZoneStr = dateTimeStr + " " + getTimeZoneStr(dt, getFullTimeZoneString)
    else:
        dateTimeWithTimeZoneStr = "NoTimeStamp             "
    return dateTimeWithTimeZoneStr

def updatePreviousMatchingList(matchingUnitsList):
    global lastUserMatchesDf
    #previousMatchingResortUnitsList = []
    #for details in matchingResortUnitsList:
    #    previousMatchingResortUnitsList.append(details)
    #for details in previousMatchingResortUnitsList:
    #    printUnitDetails("Previous list entry: ", details)
    lastUserMatchesDf = copy.deepcopy(matchingUnitsList)


def waitForNextSearchTime():
    # waits for the next time to search Or returns immediately if wait terminated by user input
    global minWaitTimeBetweenSearches
    global maxRandomAdderTimeBetweenSearches
    notificationsAuthorization()
    sleeptime = minWaitTimeBetweenSearches + (maxRandomAdderTimeBetweenSearches*random.random()) #seconds
    print("Sleeping", sleeptime, "secs, started ", datetime.datetime.now(), " ending at", datetime.datetime.now()+ datetime.timedelta(0,int(sleeptime)))
    if sleeptime > 0.20:
        # when this close just treat as 0 in case interruptible sleep rounds things up
        timedOut, userInput = getUserInput("Enter command if desired", sleeptime)
    notificationsAuthorization()

def notifyWithSound(computerSoundFile = "", playCount = 5, playInBackground = False):
    global computerSoundNotificationFileName
    # play the sound passed sound file with 1 sec gaps between it.
    # if computerSoundFile is "" then computerSoundNotificationFileName is used instead
    # Currently does not support playInBackground == True
    # A keyboard input of return aborts the sound playing
    if not computerSoundFile:
        computerSoundFile = computerSoundNotificationFileName
        #print("computerSoundNotificationFileName", computerSoundNotificationFileName)
    if Path(computerSoundFile).exists():
        for i in range(1,playCount):
            if interruptibleSleep(1):
                break
            #print("Sound file", str(Path(computerSoundFile)))
            playsound(str(Path(computerSoundFile)))
    else:
        print("Error: notifyWithSound: sound file does not exist", str(Path(computerSoundFile)))
        
def calcDistanceFromCenter(rowSeries, CenterLat, CenterLong):
    # rowSeries is a row of df
    radiansPerdegree =  math.pi/180
    dealerLat = rowSeries["Dealer Lat"]
    dealerLong = rowSeries["Dealer Long"]
    if not (valueIsNanNoneNull(dealerLat) or valueIsNanNoneNull(dealerLong) or valueIsNanNoneNull(CenterLat) or valueIsNanNoneNull(CenterLong)):
        rowSeries["DistanceFromCenter"] = math.acos(math.cos(radiansPerdegree * (90-dealerLat))*math.cos(radiansPerdegree * (90-CenterLat))+math.sin(radiansPerdegree * (90-dealerLat))*math.sin(radiansPerdegree * (90-CenterLat))*math.cos(radiansPerdegree * (dealerLong-CenterLong)))*6371*0.621371
    else:
        rowSeries["DistanceFromCenter"] =  None
    return rowSeries

def calculateDistanceFromCenter(df, CenterLatLong):
    # Calculates the dealer distance from CenterLatLong using the passed df and updates the passed df with this
    # 
    CenterLat = CenterLatLong[0]
    CenterLong = CenterLatLong[1]
    dfNew = df
    if not (valueIsNanNoneNull(CenterLat) or valueIsNanNoneNull(CenterLong)):
        if len(dfNew):
            dfNew = dfNew.apply(calcDistanceFromCenter, axis=1, args= (CenterLat, CenterLong ))
    else:
        dfNew["DistanceFromCenter"] =  None
    return dfNew

def getChangeHistoryFinalColumnsSelect(originalColumnsInOld, originalColumnsInNew):
    # returns an ordered list of columns for the final columns we want in the change history
    # The original columns passed are are in order we want for the dataframes.
    # It is assumed that the selection are for dfChangeHistory in getChangeHistory right before
    # it returns it to the caller. 
    #nonHistoryCsvFinalColumns = columnsForEmptyDfFinalCsv  # this is an ordered list of how we want the column names to be ordered
    finalColumnsSelect = []
    # new column in the change history dataframe indicating the type of change for that row (added, modified, removed, nothing changed)
    finalColumnsSelect.append(rowChangeTypeColumnName)
    for column in originalColumnsInNew:
        if column == "Options":
            # insert this one right before Options
            finalColumnsSelect.append(rowModificationsColumnName)
        finalColumnsSelect.append(column)
    return finalColumnsSelect
    
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

def outputSearchResultsToUser(matchCriteria, dfMatches, lastUserMatchesDf, dfUnfilteredInventory, updateVehiclesStatusMsg = ""):
    global outputResultsMethod
    global alsoNotifyOnOnlyRemovals
    global showRemovalsWhenOutputStatusIsAll
    global soundNotificationEvents
    global matchesFoundEvent
    global resultsFileName
    global unitDetailsDelimiter
    global maxNumberRawMissingVehicles
    print("Started analyzing ", len(dfMatches), "vehicle matches for differences from prior vehicle matches")
    print("Note: This could take from several seconds for 2000 matches to close to 90 seconds for 20,000 matches")
    modelInfoStr = getModelToGetInfo()
    # get date and time for timstamping this log entry
    dt = datetime.datetime.now().astimezone()  #local date time with timezone
    dateTimeWithTimeZoneStr = getDatetimeWithTzStr(dt, getFullTimeZoneString = True)
    # next we determine additions (new VIN number not in last results),
    # modifications where same VIN number in last results but any other field is different between current and last,
    # and removals (VIN number is now gone) compared to last results
    dfOld = lastUserMatchesDf.copy(deep=True)
    dfNew = dfMatches.copy(deep=True)
    # comment out when done debugging
    #print("Debug outputSearchResultsToUser len(dfNew), len(dfOld)", len(dfNew), len(dfOld))
    # Add minimal columns needed to reduce conditional testing in operations below.
    if (len(dfOld) == 0) and (not ("VIN" in dfOld.columns)):
        dfOld["VIN"] = None
    if (len(dfNew) == 0) and (not ("VIN" in dfNew.columns)):
        dfNew["VIN"] = None
    if not (LastChangedDateTimeColName in dfOld.columns):
        dfOld[LastChangedDateTimeColName] = None
    if not (LastChangedDateTimeColName in dfNew.columns):
        dfNew[LastChangedDateTimeColName] = None
    
    if not ("VIN" in dfOld.columns):
        print("Error: outputSearchResultsToUser: dfOld did not contain VIN column ")
    if not ("VIN" in dfOld.columns):
        print("Error: outputSearchResultsToUser: dfNew did not contain VIN column ")
    
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
    if len(dfNewMergeOnlyCommonVins):
        # Ensure the dataframe is not empty otherwise if it was empty the apply function would be called once by pandas with an empty series which we dont want. !!!!
        dfNewMergeOnlyCommonVins = dfNewMergeOnlyCommonVins.apply(determineRowDifferences, axis=1, args= (columnsToIgnoreForComparison, originalColumnsInOld, originalColumnsInNew, mergeSuffixRight))
    
    addedUnitTo = False
    modifiedUnitTo = False
    removedUnitFrom = False
    
    if len(dfNewMerged[dfNewMerged[rowChangeTypeColumnName] == rowAddedNewVINIndicator]):
        addedUnitTo = True
    if len(dfOldMerged[dfOldMerged[rowChangeTypeColumnName] == rowRemovedVINIndicator]):
        removedUnitFrom = True
    if len(dfNewMergeOnlyCommonVins[dfNewMergeOnlyCommonVins[rowChangeTypeColumnName] == rowModifiedVINContentsIndicator]):
        modifiedUnitTo = True
    
    finalColumnsSelect = getChangeHistoryFinalColumnsSelect(originalColumnsInOld, originalColumnsInNew)
    # comment out when done
    #print("Debug outputSearchResultsToUser: len(dfNewMerged), dfNewMerged.columns", len(dfNewMerged), dfNewMerged.columns)
    #print("Debug outputSearchResultsToUser: len(dfOldMerged), dfOldMerged.columns", len(dfOldMerged), dfOldMerged.columns)
    #print("Debug outputSearchResultsToUser: addedUnitTo, modifiedUnitTo, removedUnitFrom", addedUnitTo, modifiedUnitTo, removedUnitFrom)
    # TODO modify below to use above changes.
    if addedUnitTo or (modifiedUnitTo and (outputResultsMethod != outputAddedSearchResultsOnChange))  or (removedUnitFrom and (outputResultsMethod in [outputAllSearchResultsOnChange, outputChangedSearchResultsOnChange])):
        # This section is only for log file and user text/email notifications.  We only update those when something has changed
        # This keeps from flooding text/email notifications when nothing changed and we have a small between searches delay
        # 
        currentMatchesFileName = Path(resultsFileName + ".temp.txt")
        f = open(currentMatchesFileName, "w")
        f.write("-------------------------------------------------------------------------- \n")
        f.write("outputResultsMethod: " + getOutputResultsMethodString(outputResultsMethod) + "\n")
        f.write("alsoNotifyOnOnlyRemovals: " + str(alsoNotifyOnOnlyRemovals) + "\n")
        f.write("showRemovalsWhenOutputStatusIsAll: " + str(showRemovalsWhenOutputStatusIsAll) + "\n")
        f.write(modelInfoStr + "\n")
        f.write("maxNumberRawMissingVehicles: " + str(maxNumberRawMissingVehicles) + "\n")
        f.write(updateVehiclesStatusMsg + "\n")
        matchCriteria.print("", f, toConsole = False)
        f.write("Username: " + username + "\n")
        if outputResultsMethod != outputAllSearchResultsOnChange:
            resultsHeaderStr =  "The following Differences were found on " + dateTimeWithTimeZoneStr
        else:
            resultsHeaderStr =  "The following list of matching units was found on: " + dateTimeWithTimeZoneStr
        f.write(resultsHeaderStr + "\n")
        printColumnsToIgnore = ["WhoDidMergeComeFrom_", rowChangeTypeColumnName]
        columnsForLabels = originalColumnsInNew.tolist()
        columnsForLabels.append(rowModificationsColumnName)
        f.write(getSearchResultsColumnsLabelsStr(columnsForLabels , "") +"\n")
        printIt = False
        suppressFixedUnitDetailsPrefix = False
        sanitizeStrings = True
        printColumnsToUse = finalColumnsSelect
        if addedUnitTo and (outputResultsMethod in [outputAllSearchResultsOnChange, outputChangedSearchResultsOnChange, outputAddedSearchResultsOnChange]):
            # above test of addedUnitTo guarantees the dataframe is not empty otherwise if it was empty and .apply used, the apply function would be called once by pandas with an empty series which we dont want. !!!!
            dfNewMerged[dfNewMerged[rowChangeTypeColumnName].isin([rowAddedNewVINIndicator])].apply(printUnitDetailsUsingChangeType, axis= 1, args=[dateTimeWithTimeZoneStr, unitDetailsDelimiter, printColumnsToUse, f, printIt, suppressFixedUnitDetailsPrefix, sanitizeStrings])
        if modifiedUnitTo and ((outputResultsMethod == outputAllSearchResultsOnChange) or (outputResultsMethod != outputAddedSearchResultsOnChange)):
            # above test of modifiedUnitTo guarantees the dataframe is not empty otherwise if it was empty and .apply used, the apply function would be called once by pandas with an empty series which we dont want. !!!!
            dfNewMergeOnlyCommonVins[dfNewMergeOnlyCommonVins[rowChangeTypeColumnName].isin([rowModifiedVINContentsIndicator])].apply(printUnitDetailsUsingChangeType, axis= 1, args=[dateTimeWithTimeZoneStr, unitDetailsDelimiter, printColumnsToUse, f, printIt, suppressFixedUnitDetailsPrefix, sanitizeStrings])
        if (outputResultsMethod == outputAllSearchResultsOnChange):
            if len(dfNewMergeOnlyCommonVins[dfNewMergeOnlyCommonVins[rowChangeTypeColumnName].isin([rowSameVINContentsIndicator])]):
                # guarantees the dataframe is not empty otherwise if it was empty and .apply used, the apply function would be called once by pandas with an empty series which we dont want. !!!!
                dfNewMergeOnlyCommonVins[dfNewMergeOnlyCommonVins[rowChangeTypeColumnName].isin([rowSameVINContentsIndicator])].apply(printUnitDetailsUsingChangeType, axis= 1, args=[dateTimeWithTimeZoneStr, unitDetailsDelimiter, printColumnsToUse, f, printIt, suppressFixedUnitDetailsPrefix, sanitizeStrings])
        if removedUnitFrom and ((outputResultsMethod == outputChangedSearchResultsOnChange) or ((outputResultsMethod == outputAllSearchResultsOnChange) and showRemovalsWhenOutputStatusIsAll)):
            # For this condtion we want to print all the removed VIN row entries  (dfOld rows for VINs that are not in dfNew)
            # Also out of those VINs where the VIN was also in the unfiltered new, but not in the match criteria filtered new (i.e. dfNew) the changes
            # from dfOld to unfiltered New,  put in the rowModificationsColumnName, so we could see what caused the match criteria to go away in
            # that case.
            dfUnfilteredCopy = dfUnfilteredInventory.copy(deep=True)
            # Add minimal columns needed to reduce conditional testing in operations below.
            if (len(dfUnfilteredCopy) == 0) and (not ("VIN" in dfUnfilteredCopy.columns)):
                dfUnfilteredCopy["VIN"] = None
            if not (LastChangedDateTimeColName in dfUnfilteredCopy.columns):
                dfUnfilteredCopy[LastChangedDateTimeColName] = None
            if not ("VIN" in dfUnfilteredCopy.columns):
                print("Error: outputSearchResultsToUser: dfUnfilteredCopy did not contain VIN column ")
            if not ("VIN" in dfUnfilteredCopy.columns):
                print("Error: outputSearchResultsToUser: dfUnfilteredCopy did not contain VIN column ")
                
            #print("Debug outputSearchResultsToUser: len(dfUnfilteredInventory), len(dfUnfilteredCopy)", len(dfUnfilteredInventory), len(dfUnfilteredCopy) )
            
            # Save off the original column names in unfiltered for later use
            originalColumnsInUnfiltered = dfUnfilteredCopy.columns
            # Merge with dfOld to get old (filtered) and new unfiltered values for contents of common VINS only.  These are  VINs
            # that could be either be in Dfnew (and thus dfUnfilteredCopy) and DfOld,  and/or just in dfUnfilteredCopy and DfOld
            dfUnfilteredMergedWithOldOnlyCommon = dfUnfilteredCopy.merge(dfOld, left_on="VIN", right_on="VIN", how='inner', suffixes = (None, mergeSuffixRight), indicator = "WhoDidMergeComeFrom_")
            # Add change type and modifications columns with defaults
            dfUnfilteredMergedWithOldOnlyCommon[rowChangeTypeColumnName] = rowSameVINContentsIndicator
            dfUnfilteredMergedWithOldOnlyCommon[rowModificationsColumnName] = None
            # Filter dfUnfilteredMergedWithOldOnlyCommon for only rows whose VIN is also in dfOldMerged rows with change type of rowRemovedVINIndicator  (i.e. for only VINs that were in dfOld but not in DfNew,  i.e. removed VINs)
            dfUnfilteredMergedWithOldOnlyCommon = dfUnfilteredMergedWithOldOnlyCommon.merge(dfOldMerged[dfOldMerged[rowChangeTypeColumnName] == rowRemovedVINIndicator][["VIN"]], left_on="VIN", right_on="VIN", how='inner', suffixes = (None, mergeSuffixRight), indicator = "WhoDidMergeComeFrom_A")
            dfUnfilteredMergedWithOldOnlyCommon.drop(columns= ["WhoDidMergeComeFrom_A"], inplace= True)
            # determine and update the change type and modifications columns  (dfOld contenst are the suffixed columns which is the old values and dfUnfilteredMergedWithOldOnlyCommon is the new in this comparison)
            # That is we want to see differences for items that are not in dfNew but in dfOld due to match filtering compared to the unfiltered new.
            if len(dfUnfilteredMergedWithOldOnlyCommon):
                # guarantees the dataframe is not empty otherwise if it was empty and .apply used, the apply function would be called once by pandas with an empty series which we dont want. !!!!
                dfUnfilteredMergedWithOldOnlyCommon = dfUnfilteredMergedWithOldOnlyCommon.apply(determineRowDifferences, axis=1, args= (columnsToIgnoreForComparison, originalColumnsInOld, originalColumnsInUnfiltered, mergeSuffixRight))
            
            # Create a df that is dfOldMerged but only contains VIN rows where the VIN is marked removed in dfOldMerged and add the row modifications column from dfUnfilteredMergedWithOldOnlyCommon for those VINs.
            # So now we have modifications for VINs that were not in dfNew due to match criteria not matching them (but in inventory and dfOld) , 
            # and also have VINs that no longer appeared in inventory (not in unfiltered new) but in dfOld
            dfOldMergedRemovedOnlyWithLastChange = dfOldMerged[dfOldMerged[rowChangeTypeColumnName] == rowRemovedVINIndicator].merge(dfUnfilteredMergedWithOldOnlyCommon[["VIN", rowModificationsColumnName]], left_on="VIN", right_on="VIN", how='left', suffixes = (None, mergeSuffixRight), indicator = "WhoDidMergeComeFrom_A").copy(deep=True)
            dfOldMergedRemovedOnlyWithLastChange[rowModificationsColumnName] = dfOldMergedRemovedOnlyWithLastChange[rowModificationsColumnName + mergeSuffixRight]
            # Note that at this point rowChangeTypeColumnName column has rowRemovedVINIndicator for all its values.
            if len(dfOldMergedRemovedOnlyWithLastChange):
                # guarantees the dataframe is not empty otherwise if it was empty and .apply used, the apply function would be called once by pandas with an empty series which we dont want. !!!!
                dfOldMergedRemovedOnlyWithLastChange.apply(printUnitDetailsUsingChangeType, axis= 1, args=[dateTimeWithTimeZoneStr, unitDetailsDelimiter, printColumnsToUse, f, printIt, suppressFixedUnitDetailsPrefix, sanitizeStrings])
        
        f.close()
        # Append this file to the cumulative match history file
        with open(Path(resultsFileName), 'a+') as f1:
            with open(currentMatchesFileName, 'r') as f2:
                f1.write(f2.read())
        if addedUnitTo or (modifiedUnitTo and (outputResultsMethod != outputAddedSearchResultsOnChange)) or (removedUnitFrom and ((outputResultsMethod == outputChangedSearchResultsOnChange) or ((outputResultsMethod == outputAllSearchResultsOnChange) and alsoNotifyOnOnlyRemovals))):
            # only notify user via text and emails if we added/(modified with conditions/(removed with conditions) something to the list compared to the prior list
            notifyRemoteUserOfMatches(currentMatchesFileName)
    if not (dfNewMerged.empty):
        # This section is for terminal output and sounding the computer alarm for matches
        resultsHeaderStr =  "The following list of matching units was found on " + dateTimeWithTimeZoneStr
        print(resultsHeaderStr)
        printIt = True
        suppressFixedUnitDetailsPrefix = False
        sanitizeStrings = True
        printColumnsToUse = finalColumnsSelect
        f= 0
        if addedUnitTo:
            dfNewMerged[dfNewMerged[rowChangeTypeColumnName].isin([rowAddedNewVINIndicator])].apply(printUnitDetailsUsingChangeType, axis= 1, args=[dateTimeWithTimeZoneStr, unitDetailsDelimiter, printColumnsToUse, f, printIt, suppressFixedUnitDetailsPrefix, sanitizeStrings])
        if modifiedUnitTo:
            dfNewMergeOnlyCommonVins[dfNewMergeOnlyCommonVins[rowChangeTypeColumnName].isin([rowModifiedVINContentsIndicator])].apply(printUnitDetailsUsingChangeType, axis= 1, args=[dateTimeWithTimeZoneStr, unitDetailsDelimiter, printColumnsToUse, f, printIt, suppressFixedUnitDetailsPrefix, sanitizeStrings])
        if len(dfNewMergeOnlyCommonVins[dfNewMergeOnlyCommonVins[rowChangeTypeColumnName].isin([rowSameVINContentsIndicator])]):
            # guarantees the dataframe is not empty otherwise if it was empty and .apply used, the apply function would be called once by pandas with an empty series which we dont want. !!!!
            dfNewMergeOnlyCommonVins[dfNewMergeOnlyCommonVins[rowChangeTypeColumnName].isin([rowSameVINContentsIndicator])].apply(printUnitDetailsUsingChangeType, axis= 1, args=[dateTimeWithTimeZoneStr, unitDetailsDelimiter, printColumnsToUse, f, printIt, suppressFixedUnitDetailsPrefix, sanitizeStrings])
        if computerSoundNotificationFileName and (matchesFoundEvent in soundNotificationEvents) and (addedUnitTo or (modifiedUnitTo and (outputResultsMethod != outputAddedSearchResultsOnChange))):
            notifyWithSound()
    else:
        print("No matches found")


def getModelToGetInfo():
    global useLocalInventoryFile
    inventoryModel = os.environ.get("MODEL")
    if not useLocalInventoryFile:
        inventoryZipCode = os.environ.get("MODEL_SEARCH_ZIPCODE")
        inventoryZipCodeRadius = os.environ.get("MODEL_SEARCH_RADIUS")
    else:
        # when using local inventory file all we know is the Model which is what vehicles.py uses in that case to find that local file
        inventoryZipCode = None
        inventoryZipCodeRadius = None
    infoString = "Model: "  + str(inventoryModel) + ", ZipCode: " + str(inventoryZipCode) + ", Radius: " + str(inventoryZipCodeRadius) + ", useLocalInventoryFile: " + str(useLocalInventoryFile)
    return infoString

def logModelToGetInfo():
    infoString = getModelToGetInfo()
    logToResultsFile(infoString, printIt = True)
    
def createUpdateVehiclesStatusMsg(updateVehiclesCompletionStatus):
    updateVehiclesStatusMsg = "updateVehiclesCompletionStatus: completedOk: " + str(updateVehiclesCompletionStatus["completedOk"]) + ", numberRawVehiclesFound: " +  str(updateVehiclesCompletionStatus["numberRawVehiclesFound"]) + ", numberRawVehiclesMissing: " +  str(updateVehiclesCompletionStatus["numberRawVehiclesMissing"]) +  ", completionMsg: " + updateVehiclesCompletionStatus["completionMsg"] + ", date: " + str(updateVehiclesCompletionStatus["date"])
    return updateVehiclesStatusMsg
    
def searchForVehicles(args):
    """Searches for Vehicles continuously and reports results to user
    """
    global computerSoundNotificationFileName
    global resultsFileName
    global searchForVehiclesVersionStr
    global lastUserMatchesDf
    global userMatchCriteriaFilterModule
    global userMatchCriteriaFilterFileName
    global lastRunUserMatchesParquetFileName
    global useLocalInventoryFile
    global runOnceAndExit
    global maxNumberRawMissingVehicles
    global CenterLatLong
    try:
        print("Search for Vehicles program", searchForVehiclesVersionStr)
        done = False
        numberArgs = len(args)
        if numberArgs >= 1:
            configOk = parseConfigFile(args[0])
            if not configOk:
                print("Error: Config file not valid or missing")
                raise SystemExit
        else:
            print("Error: Config file name missing as first arguement in command line")
            raise SystemExit
        # import the match criteria filter file
        userMatchCriteriaFilterModule = import_from_path("userMatchCriteriaFilter_Module", userMatchCriteriaFilterFileName)
        logToResultsFile("--------------------------------------------------------------------------", printIt = False, timestamp = False)        
        logToResultsFile("Started Up Search For Vehicles program " + searchForVehiclesVersionStr + " ------------------------------------------", printIt = False) 
        logModelToGetInfo()
        logToResultsFile("maxNumberRawMissingVehicles: " + str(maxNumberRawMissingVehicles) , printIt = True, timestamp = False)
        notificationsInitialization()
        notificationsAuthorization()
        notifyRemoteUserOfSearchStart()
        lastUserMatchesDf = pd.DataFrame()
        lastRunUserMatchesParquetFileName = resultsFileName + ".lastUserMatches.parquet"
        if Path(lastRunUserMatchesParquetFileName).exists():
            # start from this file as the last matches that occurred so that if terminate program and start again we
            # pick up where we left off in regards to the last matches.
            logToResultsFile("Reading in last user matches file "  + lastRunUserMatchesParquetFileName, printIt = True)
            lastUserMatchesDf = pd.read_parquet(lastRunUserMatchesParquetFileName)
        else:
            logToResultsFile("No last user matches file"  + lastRunUserMatchesParquetFileName + " , so starting from empty", printIt = True)
        matchCriteria = userMatchCriteria()
        logToResultsFile(matchCriteria.print("", toConsole = False), printIt = False, timestamp = False)
        logToResultsFile("--------------------------------------------------------------------------", printIt = False, timestamp = False)        
        outputSearchingInfoToUser(matchCriteria)
        while not done:
            outputSearchingInfoToUser(matchCriteria)
            # get dataframe of all vehicles in US (this also writes them out to a .csv file)
            # Possibly as an enhancement can pass an optional zipcode and miles radius to search to reduce the search time and results
            print("Collecting list of vehicles to run match criteria against")
            if dbgUsingLocalVehicleDataFile:
                print("Warning: Debugging using local vehicle inventory data file for the model selected instead of querying Web for it")
                interruptibleSleep(3)
            df, updateVehiclesCompletionStatus = vehicles.update_vehicles_and_return_df(dbgUsingLocalVehicleDataFile or useLocalInventoryFile)
            updateVehiclesStatusMsg = createUpdateVehiclesStatusMsg(updateVehiclesCompletionStatus)
            print(updateVehiclesStatusMsg)
            print("maxNumberRawMissingVehicles: ", maxNumberRawMissingVehicles)
            if (df is not None) and updateVehiclesCompletionStatus["completedOk"] and (updateVehiclesCompletionStatus["numberRawVehiclesMissing"] <= maxNumberRawMissingVehicles):
                # Update CenterLat and CenterLong columns with specified values
                df["CenterLat"] = CenterLatLong[0]
                df["CenterLong"] = CenterLatLong[1]
                #replace nan with None in the DataFrame to ease computations later on 
                df = df.replace({np.nan: None})
                # Calculate distances from center
                df = calculateDistanceFromCenter(df, CenterLatLong)
                # Filter the dataframe against user defined match criteria
                print("Determining matches from criteria")
                dfMatches = matchCriteria.filterDataFrame(df)
                # output search results to user
                outputSearchResultsToUser(matchCriteria, dfMatches, lastUserMatchesDf, df, updateVehiclesStatusMsg = updateVehiclesStatusMsg)
                updatePreviousMatchingList(dfMatches)
                # save off previous matching to parquet file in case the program is terminated and restarted so we pick
                # up where we left off in regards to the last matches.
                # Note that we save it off here after we have output all results to the user so we logs and notifications
                # have gone out for this run.
                lastUserMatchesDf.to_parquet(lastRunUserMatchesParquetFileName, index=False)
                if debugEnabled:
                    print("searchForVehicles lastUserMatchesDf \n", lastUserMatchesDf)
            else:
                logToResultsFile(updateVehiclesStatusMsg, printIt = False)
                logToResultsFile("maxNumberRawMissingVehicles: " + str(maxNumberRawMissingVehicles) , printIt = False, timestamp = False)
            if useLocalInventoryFile or runOnceAndExit:
                break
            waitForNextSearchTime()
            # Reauthorize notifications often enough to meet expiration dates..
            notificationsAuthorization()
    except (SystemExit) as inst:
        pass

if __name__ == "__main__":
    import sys
    searchForVehicles(sys.argv[1:])
