# Bypass the AWS WAF in front of the GraphQL endpoint.
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

class WAFBypass:
    """Bypass the AWS WAF in front of the GraphQL endpoint."""
    def __init__(self):
        self.valid_headers = None

    def intercept_request(self, request):
        """Find the GraphQL request and save the headers."""
        if request.resource_type == "xhr" and request.url.endswith("/graphql"):
            self.valid_headers = request.headers
            # Just in case the request JSON is needed later.
            # pprint(request.post_data_json)
        return request

    def get_headers(self) -> None:
        """Run a browser to get valid headers for a WAF bypass."""
        while True:
            try:
                self.valid_headers = None
                with sync_playwright() as playwright:
                    browser = playwright.firefox.launch(headless=True)
                    try:
                        context = browser.new_context(viewport={"width": 1920, "height": 1080})
                        page = context.new_page()
                        page.on("request", self.intercept_request)
                        # pick a model that usually doesn't have much inventory to reduce response time and web page load time
                        page.goto("https://www.toyota.com/search-inventory/model/" + "corollahatchback" + "/?zipcode=90210")
                        #print("https://www.toyota.com/search-inventory/model/" + "corollahatchback" + "/?zipcode=90210")
                        page.wait_for_load_state("networkidle", timeout=60000)
                    except Exception as inst:
                        print("Error: WAFBypass.get_headers: exception in code going to inventory page: ", str(inst))
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
