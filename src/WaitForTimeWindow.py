"""
Waits to be in the indicated Time window before returning.  User can terminate the wait by hitting the return key
The indicated time windows is the first parameter of the command line is of the form
"HH:MM, HH:MM,....." 
where the HH:MM are taken in pairs and each pair is the start and end time of a window in Hours and minutes.
For example "0:30, 4:00, 
"""

import random
import waitForSeconds
import time
import datetime
from inputimeout import inputimeout, TimeoutOccurred
import sys
import yaml
import os.path

def getTimeWindowsFromStrSpec(strng):
    """
    "HH:MM, HH:MM,....." 
    where the HH:MM are taken in pairs and each pair is the start and end time of a window in Hours and minutes.
    For example "0:30, 4:00,     
    returns a tuple ( ok, the time of day windows as a list of list with a start and end time datetime.time type entries )
    """
    ok = False
    timeWindows = []
    times = strng.split(",")
    if (len(times) % 2 == 0) and (len(times) > 0):
        parsingStartTime = True
        for tm in times:
            ok = False
            tmSpec = tm.split(":")
            if len(tmSpec) == 2:
               tmHour = tmSpec[0].rstrip().lstrip()
               tmMin = tmSpec[1].rstrip().lstrip()
               try:
                    tmHour = int(tmHour)
                    tmMin = int(tmMin)
                    if (tmHour >= 0) and (tmHour <= 23) and (tmMin >= 0) and (tmMin <= 59):
                        if parsingStartTime:
                            parsingStartTime = False
                            startTime = datetime.time(hour=tmHour, minute=tmMin)
                        else:
                            endTime = datetime.time(hour=tmHour, minute=tmMin)
                            parsingStartTime = True
                            ok = True
                            timeWindows.append([startTime, endTime])
                    else:
                        break
               except ValueError:
                    break
    print("getTimeWindowsFromStrSpec: ok, windows", ok, str(timeWindows) )          
    return (ok, timeWindows)

def searchTimeWindowWaitTime(timeOfDaySearchWindows):
    #returns 0 if in a search window or the time to the closest search window start time
    timeOfDayNow = datetime.datetime.now().time()
    timeOfDayNowSecs = (timeOfDayNow.hour * 3600) +  (timeOfDayNow.minute * 60) + timeOfDayNow.second
    minTimeToClosestWindowStart = 24*60*60 #sec
    for timeWindow in timeOfDaySearchWindows:
        startTimeOfDayForSearches, endTimeOfDayForSearches = timeWindow
        startTimeOfDayForSearchesSecs = (startTimeOfDayForSearches.hour * 3600) +  (startTimeOfDayForSearches.minute * 60) + startTimeOfDayForSearches.second
        endTimeOfDayForSearchesSecs = (endTimeOfDayForSearches.hour * 3600) +  (endTimeOfDayForSearches.minute * 60) + endTimeOfDayForSearches.second
        if startTimeOfDayForSearchesSecs > endTimeOfDayForSearchesSecs:
            # time window goes from startTimeOfDayForSearchesSecs to 24 hour point and then wraps from 0 to endTimeOfDayForSearchesSecs
            if (endTimeOfDayForSearchesSecs < timeOfDayNowSecs ) and (timeOfDayNowSecs < startTimeOfDayForSearchesSecs):
                timeToStart = startTimeOfDayForSearchesSecs - timeOfDayNowSecs
                if timeToStart < minTimeToClosestWindowStart:
                    minTimeToClosestWindowStart = timeToStart
            else:
                # in time window so done
                minTimeToClosestWindowStart = 0
                break
        else: #startTimeOfDayForSearchesSecs <= endTimeOfDayForSearchesSecs so time window is that interval
            if timeOfDayNowSecs > endTimeOfDayForSearchesSecs:
                timeToStart = (24*3600) - timeOfDayNowSecs + startTimeOfDayForSearchesSecs
                if timeToStart < minTimeToClosestWindowStart:
                    minTimeToClosestWindowStart = timeToStart
            elif timeOfDayNowSecs < startTimeOfDayForSearchesSecs:
                timeToStart = startTimeOfDayForSearchesSecs - timeOfDayNowSecs
                if timeToStart < minTimeToClosestWindowStart:
                    minTimeToClosestWindowStart = timeToStart
            else:
                # in time window so done
                minTimeToClosestWindowStart = 0
                break
    return (minTimeToClosestWindowStart)
    

if __name__ == "__main__":
    if len(sys.argv) > 1:
        ok, timeOfDaySearchWindows = getTimeWindowsFromStrSpec(sys.argv[1:][0])
        if ok:
            waitTime = searchTimeWindowWaitTime(timeOfDaySearchWindows)
            waitForSeconds.waitForSeconds(waitTime)
        else:
            print("time of day search windows not valid format", sys.argv[1:][0])
