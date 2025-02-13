#
import copy
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
searchForVehiclesVersionStr = "Ver 1.14 Feb 13 2025"  #

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
    
def printUnitDetails(prefix, details, columnsToIgnore, fileHandle = 0, printIt = True, suppressFixedUnitDetailsPrefix = False, sanitizeStrings = True, namesOfModifiedFieldsString = ""):
    # details is a DataFrame of exactly 1 row
    global unitDetailsDelimiter
    detailsStr = ""
    if suppressFixedUnitDetailsPrefix:
        fixedUnitDetailsPrefix = ""
    else:
        fixedUnitDetailsPrefix = " Unit Details ->"
    # Output is field delimited by unitDetailsDelimiter
    detailsStr = prefix  + fixedUnitDetailsPrefix
    for index1 in details.index:
        for column1 in details:
            if not (column1 in columnsToIgnore):
                detailsStr += unitDetailsDelimiter + str(column1) + ": " + unitDetailsDelimiter + str(details.at[index1,column1])
    if namesOfModifiedFieldsString:
        detailsStr += unitDetailsDelimiter + "Names Of Modified Fields: " + namesOfModifiedFieldsString
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
    print("outputResultsMethod:", getOutputResultsMethodString(outputResultsMethod))
    print("runOnceAndExit: ", runOnceAndExit)
    print("maxNumberRawMissingVehicles: ", maxNumberRawMissingVehicles)
    print(getModelToGetInfo())
    matchCriteria.print("", toConsole = True)
    print("Username:", username)

def getNamesOfModifiedFieldsIntoString (details1, details2, columnsToIgnore):
    # returns the names of the modified fields (fields whose value changed between details1 and details) as well as the 
    # the current value and prior value of the field
    # Assumes both passed details have the exact same field names and are not empty
    # details1 has the current values and details2 has the prior values
    global debugEnabled
    #if debugEnabled:
    #    print("detailsAreTheSame details1", details1)
    #    print("detailsAreTheSame details2", details2)
    namesOfModifiedFieldsString = ""
    theSame = False
    columns1 = []
    for column1 in details1:
        if not (column1 in columnsToIgnore):
            columns1.append(column1)
    columns1.sort()
    columns2 = []
    for column2 in details2:
        if not (column2 in columnsToIgnore):
            columns2.append(column2)
    columns2.sort()
    #print("detailsAreTheSame columns1 == columns2, columns1, columns2", columns1 == columns2, columns1, columns2)
    if columns1 == columns2:
        # both have all the exact same column labels (assumed to be unique)
        #print("getNamesOfModifiedFieldsIntoString details1.shape[0], details2.shape[0]", details1.shape[0], details2.shape[0])
        if  details1.shape[0] == details2.shape[0]:
            # both have same number of rows which should be 0 or 1.  We only compare the first row anyway
            for index1 in details1.index:
                for index2 in details2.index:
                    for column1 in columns1:
                        if details1.at[index1, column1] != details2.at[index2, column1]:
                            namesOfModifiedFieldsString += column1 + " :: " + str(details2.at[index2, column1]) + " --> " +  str(details1.at[index1, column1]) + " || "
                            #if debugEnabled:
                            #    print("getNamesOfModifiedFieldsIntoString index1, column1, index2, details1.at[index1, column1], details2.at[index2, column1]", index1, column1, index2, details1.at[index1, column1], details2.at[index2, column1])
                    break
                break
    else:
        Print("Error:  getNamesOfModifiedFieldsIntoString:  details1 and details2 do not have all the same field names")
    #if debugEnabled:
    #    print("getNamesOfModifiedFieldsIntoString returning namesOfModifiedFieldsString as", namesOfModifiedFieldsString)
    return namesOfModifiedFieldsString
    

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
  
def detailsAreTheSame(details1, details2, columnsToIgnore):
    # Determines if the single rows series are the same (same value in same column name is the same in each) ignoring the indicated column names
    # !!!!!Assumes nan has been replaced with None in the passed DataFrames.
    global debugEnabled
    #if debugEnabled:
    #   print("detailsAreTheSame details1 type and contents", type(details1), details1)
    #   print("detailsAreTheSame details2 type and contents", type(details2), details2)
    #   print("detailsAreTheSame columnsToIgnore", columnsToIgnore)
    theSame = False
    columns1 = []
    for column1 in details1.index:
        if not (column1 in columnsToIgnore):
            columns1.append(column1)
    columns1.sort()
    #if debugEnabled:
    #   print("detailsAreTheSame columns in details1 sorted excluding ignores", columns1)
    columns2 = []
    for column2 in details2.index:
        if not (column2 in columnsToIgnore):
            columns2.append(column2)
    columns2.sort()
    #if debugEnabled:
    #   print("detailsAreTheSame columns in details2 sorted excluding ignores", columns2)
    #   print("detailsAreTheSame columns1 == columns2, columns1, columns2", columns1 == columns2, columns1, columns2)
    if columns1 == columns2:
        # both have all the exact same column labels (assumed to be unique)
        theSame = True
        for column1 in columns1:
            if details1[column1] != details2[column1]:
                theSame = False
                #if debugEnabled:
                #    print("detailsAreTheSame index1, column1, index2, details1.at[index1, column1], details2.at[index2, column1]", index1, column1, index2, details1.at[index1, column1], details2.at[index2, column1])
                break
    #if debugEnabled:
    #    print("detailsAreTheSame returning theSame as", theSame)
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
        
def updateMatchingVinIndex(rowSeries, lastUserMatchesDfCopy, columnsToIgnore):
    if rowSeries["VinIsInLast"] == True:
        vin = rowSeries["VIN"]
        rowLastDf = lastUserMatchesDfCopy[lastUserMatchesDfCopy["VIN"] == vin]
        rowLastIndex = rowLastDf.index[0]
        rowLastSeries = rowLastDf.loc[rowLastIndex]
        rowSeries["VinLastRowLoc"] = rowLastIndex
        detailsSame = detailsAreTheSame(rowSeries, rowLastSeries, columnsToIgnore)  #TODO fix ignoring added columns
        rowSeries["VinLastRowModified"] = not detailsSame
    return rowSeries
    
def outputSearchResultsToUser(matchCriteria, dfMatches, lastUserMatchesDf, updateVehiclesStatusMsg = ""):
    global outputResultsMethod
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
    dfMatchesCopyEmpty = True
    lastUserMatchesDfCopyEmpty = True
    dfMatchesCopy = dfMatches.copy()
    dfMatchesCopy.reset_index()
    lastUserMatchesDfCopy = lastUserMatchesDf.copy()
    lastUserMatchesDfCopy.reset_index()  #So save off the unique index value of the item to reference it as needed and have it match the iloc value.
    if len(dfMatchesCopy) and ("VIN" in dfMatchesCopy):
        dfMatchesCopyEmpty = False
        if len(lastUserMatchesDfCopy) and ("VIN" in lastUserMatchesDfCopy):
            dfMatchesCopy["VinIsInLast"] = dfMatchesCopy["VIN"].isin(lastUserMatchesDfCopy["VIN"])
        else:
            dfMatchesCopy["VinIsInLast"] = False
        dfMatchesCopy["VinLastRowLoc"] = -1
        dfMatchesCopy["VinLastRowModified"] = False
    if len(lastUserMatchesDf) and ("VIN" in lastUserMatchesDf):
        lastUserMatchesDfCopyEmpty = False
        if len(dfMatchesCopy) and ("VIN" in dfMatchesCopy):
            lastUserMatchesDfCopy["VinIsInCurrent"] = lastUserMatchesDfCopy["VIN"].isin(dfMatchesCopy["VIN"])
        else:
            lastUserMatchesDfCopy["VinIsInCurrent"] = False
    # !!!! Update the Ignore columns below if add any columns to dfMatchesCopy or lastUserMatchesDfCopy that are not in the non copies
    detailsSameColumnsToIgnore = ["VinIsInLast", "VinLastRowLoc", "VinLastRowModified", "VinIsInCurrent", "infoDateTime" ]
    printColumnsToIgnore = ["VinIsInLast", "VinLastRowLoc", "VinLastRowModified", "VinIsInCurrent" ]
    
    addedUnitTo = False
    if (not dfMatchesCopyEmpty) and (not dfMatchesCopy["VinIsInLast"].all()):
        addedUnitTo = True
    
    removedUnitFrom = False
    if (not lastUserMatchesDfCopyEmpty) and (not lastUserMatchesDfCopy["VinIsInCurrent"].all()):
        removedUnitFrom = True
    
    modifiedUnitTo = False
    if (not dfMatchesCopyEmpty):
        # TODO can we do the apply to a slice of the dfMatchesCopy and then copy it to the dfMatchesCopy?? (overwritting the same indexes) would that be faster (i.e ony entires we know are inboth)
        dfMatchesCopy = dfMatchesCopy.apply(updateMatchingVinIndex, axis=1, args= (lastUserMatchesDfCopy, detailsSameColumnsToIgnore ))
        if dfMatchesCopy["VinLastRowModified"].any():
            modifiedUnitTo = True
        
    if addedUnitTo or (modifiedUnitTo and (outputResultsMethod != outputAddedSearchResultsOnChange))  or (removedUnitFrom and (outputResultsMethod in [outputAllSearchResultsOnChange, outputChangedSearchResultsOnChange])):
        # This section is only for log file and user text/email notifications.  We only update those when something has changed
        # This keeps from flooding text/email notifications when nothing changed and we have a small between searches delay,
        # as well as not sending text/email notifications when there are only removals
        currentMatchesFileName = Path(resultsFileName + ".temp.txt")
        f = open(currentMatchesFileName, "w")
        f.write("-------------------------------------------------------------------------- \n")
        f.write("outputResultsMethod: " + getOutputResultsMethodString(outputResultsMethod) + "\n")
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
        for detailsCurIndex in dfMatchesCopy.index:
            curRowSeries = dfMatchesCopy.loc[detailsCurIndex]
            addedUnit = False
            if not curRowSeries["VinIsInLast"]:
                addedUnit = True
            modedUnit = False
            if not addedUnit:
                # no need to check for modified if it was an added unit, as these are mutually exclusive
                if curRowSeries["VinLastRowModified"]:
                    modedUnit = True
            if (outputResultsMethod == outputAllSearchResultsOnChange) or addedUnit or (modedUnit and (outputResultsMethod != outputAddedSearchResultsOnChange)):
                addedString = ":,           "
                namesOfModifiedFieldsString = ""
                if addedUnit:
                    addedString = ":,   ***ADDED"  # Use word Added to easily see what was added out of all the matches
                elif modedUnit:
                    addedString = ":,   ***MODED"  # Use word Moded to easily see what was modified out of all the matches
                    namesOfModifiedFieldsString = getNamesOfModifiedFieldsIntoString(dfMatchesCopy.loc[[detailsCurIndex]], lastUserMatchesDfCopy.loc[[curRowSeries["VinLastRowLoc"]]], detailsSameColumnsToIgnore) 
                printUnitDetails(dateTimeWithTimeZoneStr + unitDetailsDelimiter + addedString, dfMatchesCopy.loc[[detailsCurIndex]], printColumnsToIgnore, f, printIt = False, suppressFixedUnitDetailsPrefix = False, sanitizeStrings = True, namesOfModifiedFieldsString = namesOfModifiedFieldsString)  #  use ":, " to make ultra edit filtering of non Went Unavailable strings easier
        if outputResultsMethod == outputChangedSearchResultsOnChange:
            # also print units that disappeared
            removedUnit = False
            if not lastUserMatchesDfCopyEmpty:
                for detailsPreviousIndex in lastUserMatchesDfCopy.index:
                    if not lastUserMatchesDfCopy.loc[detailsPreviousIndex]["VinIsInCurrent"]:
                        removedUnit = True
                        printUnitDetails(dateTimeWithTimeZoneStr + unitDetailsDelimiter +  ":, ***REMOVED", lastUserMatchesDfCopy.loc[[detailsPreviousIndex]], printColumnsToIgnore, f, printIt = False)
        f.close()
        # Append this file to the cumulative match history file
        with open(Path(resultsFileName), 'a+') as f1:
            with open(currentMatchesFileName, 'r') as f2:
                f1.write(f2.read())
        if addedUnitTo or (modifiedUnitTo and (outputResultsMethod != outputAddedSearchResultsOnChange)):
            # only notify user via text and emails if we added/modified something to the list compared to the prior list
            notifyRemoteUserOfMatches(currentMatchesFileName)
    if not dfMatchesCopy.empty:
        # This section is for terminal output and sounding the computer alarm for matches
        resultsHeaderStr =  "The following list of matching units was found on " + dateTimeWithTimeZoneStr
        print(resultsHeaderStr)
        for detailsCurIndex in dfMatchesCopy.index:
            curRowSeries = dfMatchesCopy.loc[detailsCurIndex]
            addedUnit = False
            if not curRowSeries["VinIsInLast"]:
                addedUnit = True
            modedUnit = False
            if not addedUnit:
                # no need to check for modified if it was an added unit, as these are mutually exclusive
                if curRowSeries["VinLastRowModified"]:
                    modedUnit = True
            addedString = ":,         "
            namesOfModifiedFieldsString = ""
            if addedUnit:
                addedString = ":, ***ADDED"  # Use word Added to easily see what was added out of all the matches
            elif modedUnit:
                addedString = ":, ***MODED"  # Use word Moded to easily see what was modified out of all the matches
                namesOfModifiedFieldsString = getNamesOfModifiedFieldsIntoString(dfMatchesCopy.loc[[detailsCurIndex]], lastUserMatchesDfCopy.loc[[curRowSeries["VinLastRowLoc"]]], detailsSameColumnsToIgnore) 
            printUnitDetails(dateTimeWithTimeZoneStr + unitDetailsDelimiter + addedString, dfMatchesCopy.loc[[detailsCurIndex]], printColumnsToIgnore, fileHandle = 0 , printIt = True, suppressFixedUnitDetailsPrefix = False, sanitizeStrings = True, namesOfModifiedFieldsString = namesOfModifiedFieldsString )  #  use ":, " to make ultra edit filtering of non Went Unavailable strings easier
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
                #replace nan with None in the DataFrame to ease computations later on 
                df = df.replace({np.nan: None})
                # Filter the dataframe against user defined match criteria
                print("Determining matches from criteria")
                dfMatches = matchCriteria.filterDataFrame(df)
                # output search results to user
                outputSearchResultsToUser(matchCriteria, dfMatches, lastUserMatchesDf, updateVehiclesStatusMsg = updateVehiclesStatusMsg)
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
