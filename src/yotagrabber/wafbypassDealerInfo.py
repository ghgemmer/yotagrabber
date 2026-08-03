# Bypass the AWS WAF in front of the Dealer Info website.  Returns the headers needed to send in future requests 
# to the dealer info website to bypass the waf
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from inputimeout import inputimeout, TimeoutOccurred


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
    
def mergeCookie(fromHeaders, toHeaders):
    """  merges cookie from fromHeaders into toHeaders and returns the result """
    cookie = ""
    merged = toHeaders
    if "cookie" in fromHeaders: 
        cookie = fromHeaders["cookie"]
    elif "Cookie" in fromHeaders: 
        cookie = fromHeaders["Cookie"]
    if cookie:
        merged["Cookie"] = cookie
    return merged
class WAFBypass:
    """Bypass the AWS WAF in front of the dealer info website."""
    def __init__(self):
        self.valid_headers = None

    def intercept_request(self, request):
        """Find the dealer info request that has the aws token cookie headers."""
        print("request.url", request.url)
        print("request.method", request.method)
        print("request.all_headers()", request.all_headers())
        print("request.headers", request.headers)
        print("request.response().status", request.response().status)

    def intercept_response(self, response):
        """Find the dealer info request that has the aws token cookie headers."""
        print("response.url", response.url)
        print("response.request.method", response.request.method)
        print("response.request.all_headers()", response.request.all_headers())
        print("response.request.headers", response.request.headers)
        print("response.status", response.status)

    def get_headers(self) -> None:
        """Run a browser to get valid headers for a WAF bypass."""
        while True:
            try:
                self.valid_headers = None
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(headless=False) # headless=True does not seem to work for at all for anything, as get a status code 403 as the first and only response sent back by the server on the page.goto.
                    try:
                        #context = browser.new_context(viewport={"width": 1920, "height": 1080})
                        context = browser.new_context(viewport={"width": 10, "height": 10})  # use a small window to unobtrusive as possible since can't use headless mode
                        page = context.new_page()
                        if 0:
                            #page.on("request", self.intercept_request)
                            # and ('aws-waf-token=' in request.header_value('cookie'))
                            with page.expect_request(lambda request: ("https://api.ws.dpcmaps.toyota.com/v1/dealers" in request.url) and (request.method == "GET")  and ('cookie' in request.all_headers())) as request_info:
                            # Use any zipcode as WAF headers are not dependent on the zipcode used
                                page.goto("https://api.ws.dpcmaps.toyota.com/v1/dealers?attributeKey=&searchMode=pmaProximityLayered&zipcode=90210")
                            #print("request_info.value.all_headers()", repr(request_info.value.all_headers()))
                            #print("request_info.value.headers", request_info.value.headers)
                            headers = mergeCookie(request_info.value.all_headers(), request_info.value.headers)
                            self.valid_headers = headers
                        else:
                            #page.on("response", self.intercept_response)
                            # and ('aws-waf-token=' in request.header_value('cookie'))
                            with page.expect_response(lambda response: ("https://api.ws.dpcmaps.toyota.com/v1/dealers" in response.url)  and (response.status == 200) ) as response_info:
                            # Use any zipcode as WAF headers are not dependent on the zipcode used
                                page.goto("https://api.ws.dpcmaps.toyota.com/v1/dealers?attributeKey=&searchMode=pmaProximityLayered&zipcode=90210")
                            #print("response_info.value.request.all_headers()", repr(response_info.value.request.all_headers()))
                            headers = mergeCookie(response_info.value.request.all_headers(), response_info.value.request.headers)
                            self.valid_headers = headers
                        
                    except Exception as inst:
                        print("Error: WAFBypass.get_headers: exception in code going to Dealer Info page: ", str(inst))
                    finally:
                        browser.close()
                if self.valid_headers is not None:
                    break
                else:
                    print("Error: WAFBypass.get_headers was None")
                    sleepTime = 60* 10
                    print("Waiting time ", sleepTime, "secs before retrying WAF Bypass")
                    getUserInput("Enter Cr to terminate wait early", sleepTime)
            except Exception as inst:
                print("Error: WAFBypass.get_headers exception", str(inst))
                sleepTime = 60* 10
                print("Waiting time ", sleepTime, "secs before retrying WAF Bypass")
                getUserInput("Enter Cr to terminate wait early", sleepTime)
    def run(self):
        """Return the valid headers to bypass the WAF."""
        self.get_headers()
        return self.valid_headers
