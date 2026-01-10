# Bypass the AWS WAF in front of the GraphQL endpoint.
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from inputimeout import inputimeout, TimeoutOccurred
from typing import Dict, Optional, Tuple, Any, List
import random
from yotagrabber import config

def getUserInput(promptStr: str, sleepTime: float) -> Tuple[bool, str]:
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
    
    valid_headers: Optional[Dict[str, str]]

    def __init__(self, vehicle_make: str = "toyota"):
        self.vehicle_make = vehicle_make
        self.valid_headers = None

    def intercept_request(self, request: Any):
        """Find the GraphQL request and save the headers."""
        if request.resource_type == "xhr" and request.url.endswith("/graphql"):
            self.valid_headers = request.headers
        return request

    def get_headers(self) -> None:
        """Run a browser to get valid headers for a WAF bypass."""
        
        # Define models to try: [Primary, Fallback 1, Fallback 2]
        # We prefer low-inventory models to speed up page load.
        # Fallback #2 is a higher-inventory model to maximize chances of success.
        lexus_models = ["txphev", "lc", "is"] 
        toyota_models = ["mirai", "supra", "corollahatchback"]
        
        target_models = lexus_models if self.vehicle_make.lower() == "lexus" else toyota_models

        # Define a pool of safe, continental US zip codes
        # 90210 (CA), 10001 (NY), 33101 (FL), 75001 (TX), 60007 (IL)
        safe_zips = ["90210", "10001", "33101", "75001", "60007"]

        while True:
            try:
                self.valid_headers = None
                with sync_playwright() as playwright:
                    # 1. Random User Agent from config
                    user_agent_str = config.random_user_agent()
                    
                    browser = playwright.firefox.launch(headless=True)
                    try:
                        context = browser.new_context(
                            viewport={"width": 1920, "height": 1080},
                            user_agent=user_agent_str
                        )
                        page = context.new_page()
                        page.on("request", self.intercept_request)
                        
                        # 2. Pick a Random Safe Zip
                        # This varies the geolocation to avoid static fingerprinting
                        safe_zip = random.choice(safe_zips)
                        print(f"WAFBypass: Using Safe Zip Code: {safe_zip}")

                        # 3. Try models in order until one works
                        for model in target_models:
                            print(f"WAFBypass: Attempting to load inventory page for model '{model}'...")
                            try:
                                if self.vehicle_make.lower() == "lexus":
                                    url = f"https://www.lexus.com/search-inventory/model/{model}/?zipcode={safe_zip}"
                                else:
                                    url = f"https://www.toyota.com/search-inventory/model/{model}/?zipcode={safe_zip}"
                                
                                page.goto(url, timeout=45000)
                                page.wait_for_load_state("networkidle", timeout=45000)

                                # Check if we successfully captured headers
                                if self.valid_headers is not None:
                                    print(f"WAFBypass: Successfully captured headers using model '{model}'.")
                                    break # Exit the model loop
                                else:
                                    print(f"WAFBypass: Page loaded for '{model}' but headers were not captured. Trying next model...")

                            except Exception as e:
                                print(f"WAFBypass: Failed to load model '{model}': {str(e)}")
                                print("WAFBypass: Retrying with next fallback model...")
                                continue
                        
                        if self.valid_headers is None:
                            print("Error: All fallback models failed to produce valid headers.")

                    except Exception as inst:
                        print("Error: WAFBypass.get_headers: exception in browser session: ", str(inst))
                    finally:
                        browser.close()

                if self.valid_headers is not None:
                    break
                else:
                    print("Error: WAFBypass.get_headers was None")
                    sleepTime = 60 * 10
                    print("Waiting time ", sleepTime, "secs before retrying WAF Bypass")
                    getUserInput("Enter Cr to terminate wait early", sleepTime)

            except Exception as inst:
                print("Error: WAFBypass.get_headers exception", str(inst))
                sleepTime = 60 * 10
                print("Waiting time ", sleepTime, "secs before retrying WAF Bypass")
                getUserInput("Enter Cr to terminate wait early", sleepTime)
    
    def run(self) -> Optional[Dict[str, str]]:
        """Return the valid headers to bypass the WAF."""
        self.get_headers()
        return self.valid_headers