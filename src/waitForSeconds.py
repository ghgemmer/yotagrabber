import sys
from inputimeout import inputimeout, TimeoutOccurred
import datetime

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


def waitForSeconds(sleeptime):
    # waits for the sleep time or returns immediately if wait terminated by user input
    print("Sleeping", sleeptime, "secs, started ", datetime.datetime.now(), " ending at", datetime.datetime.now()+ datetime.timedelta(0,int(sleeptime)))
    if sleeptime > 0.20:
        # when this close just treat as 0 in case interruptible sleep rounds things up
        timedOut, userInput = getUserInput("Enter return to abort sleep", sleeptime)
    
if __name__ == "__main__":
    sleepTime = float(sys.argv[1:][0])
    waitForSeconds(sleepTime)
