"""Collect in-production / in-transit Lexus inventory from dealer websites.

Why this exists
---------------
The Lexus inventory GraphQL API that vehicles.py uses does NOT publish factory to port
vehicles.  It returns only dealerCategory F (port to dealer) and G (at dealer), never A
(factory to port), and never a temporary vin.  Toyota publishes all three.  See the
"IMPORTANT LEXUS DATA LIMITATION" section of Invocation.txt for the evidence.

Individual Lexus dealer websites DO publish those vehicles, labelled "In Production".
They are vehicles that have been allocated to the dealer but not built or shipped yet, so
they carry a TEMPORARY vin, recognizable because the last 6 characters contain a letter
(2T2BBMCA5TC34C391) where a real vin's last 6 are all digits (2T2BBMCA4TC138242).  These
are the vehicles you can still call a dealer about and influence, for example to change the
port installed options, because they have not reached the port yet.

This program reads those dealer websites and writes what it finds to a csv.

Coverage
--------
Lexus dealers run several different website platforms and each needs its own reader.  The
platform for every dealer is reported by the lexus dealer service, so the program groups
dealers by platform and uses the matching reader.  Readers exist for DealerOn (26 of the 245
US Lexus dealers) and Dealer eProcess (33), so about 59 of 245 are covered.  Dealer Inspire
(88), Dealer.com (73) and MOTIVE (22) have no reader yet and are listed as unsupported in
the output so the gap is visible rather than silently missing.

The two readers do not give equally good data.  DealerOn exposes explicit
VehicleInProduction / VehicleInTransit / VehicleInStock flags and a clean InteriorColorLabel,
so its status and interior are reliable.  Dealer eProcess exposes neither, so status there is
inferred from the temporary vin and reported as "In Production (temp vin)", and the interior
has to be pulled out of a free text description, which does not always parse.  Check the
"interior known" count the program prints per dealer before trusting an interior search.

Usage
-----
py lexusDealerSiteInventory.py <output csv> [<state code> ...] [--model RX] [--all-status]

  no state codes    all US states
  --model           only keep vehicles whose name contains this text, for example
                    "RX 350h".  Repeatable.  Default keeps everything.
  --interior        only keep vehicles whose interior contains this text, for example
                    "Macadamia Semi-Aniline".  Repeatable.
  --all-status      keep every vehicle, not just the in production ones
"""
import base64
import collections
import json
import re
import sys
import time

import pandas as pd
import requests

LEXUS_DEALERS_URL = "https://www.lexus.com/rest/lexus/dealers?experience=dealer&state="
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/120.0 Safari/537.36")

US_STATE_CODES = ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA", "HI", "ID",
                  "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO",
                  "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA",
                  "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"]

# Wording the dealer sites use, mapped to the status this program reports.  Order matters,
# the first one found in a vehicle's markup wins, so the earlier entries must be the more
# specific ones.
STATUS_WORDS = [
    ("in production", "In Production"),
    ("in-production", "In Production"),
    ("in transit", "In Transit"),
    ("in-transit", "In Transit"),
    ("on order", "On Order"),
    ("arriving", "Arriving"),
    ("in stock", "In Stock"),
]

VIN_PATTERN = re.compile(r"\b[A-HJ-NPR-Z0-9]{17}\b")


def isPlausibleVin(candidate):
    # The 17 character pattern also matches marketing strings the sites embed, such as
    # DD365STAFFSUMMARY and CLASSLEADESH21MPG, so require at least 2 digits and reject
    # anything that is all letters.
    if not any(c.isdigit() for c in candidate):
        return False
    if sum(c.isdigit() for c in candidate) < 2:
        return False
    if candidate.isalpha():
        return False
    return True


def hasTemporaryVin(vin):
    # A not yet built vehicle carries a temporary vin whose last 6 characters contain a letter.
    return not vin[-6:].isdigit()


def getLexusDealers(stateCodes):
    """Return a dataframe of lexus dealers for the passed states, with their website platform."""
    headers = {"User-Agent": USER_AGENT}
    rows = []
    for stateCode in stateCodes:
        try:
            resp = requests.get(LEXUS_DEALERS_URL + stateCode, headers=headers, timeout=30)
            result = resp.json()
        except Exception as inst:
            print("  %-3s dealer lookup failed: %s" % (stateCode, str(inst)[:70]))
            continue
        for dealer in (result.get("dealers") or []):
            address = dealer.get("dealerAddress") or {}
            rows.append({
                "dealerId": dealer.get("id"),
                "name": dealer.get("dealerName"),
                "platform": dealer.get("websiteVendor"),
                "url": dealer.get("dealerSiteUrl"),
                "newInventoryUrl": dealer.get("dealerNewInventoryUrl"),
                "phone": dealer.get("dealerPhone"),
                "city": address.get("city"),
                "state": address.get("state"),
            })
        time.sleep(1)
    return pd.DataFrame(rows)


def findStatusInMarkup(markup):
    low = markup.lower()
    for word, status in STATUS_WORDS:
        if word in low:
            return status
    return None


def cleanLabel(text):
    """Strip html tags and entities the dealer sites leave inside their colour labels."""
    if not text:
        return None
    text = re.sub(r"<[^>]+>", "", str(text))
    text = text.replace("&Ndash;", "-").replace("&ndash;", "-").replace("&amp;", "&")
    text = re.sub(r"&[a-zA-Z]+;", "", text)
    return re.sub(r"\s+", " ", text).strip()


class DealerOnReader:
    """Reads inventory from a DealerOn powered dealer site.

    DealerOn serves its search results page from a json api that returns vehicle cards.  The
    api url embeds two site specific numbers that have to be discovered by loading the page
    once and watching for the request, which is what findApiUrl does.  The cards carry
    explicit VehicleInProduction / VehicleInTransit / VehicleInStock flags and an
    InteriorColorLabel, so this reader uses those fields directly rather than guessing from
    the wording in the markup.
    """
    platformName = "DealerOn"
    apiPattern = re.compile(r"/api/vhcliaa/vehicle-pages/cosmos/srp/vehicles/\d+/\d+")

    def findApiUrl(self, siteUrl):
        """Load the dealer's new inventory page and capture the inventory api url it calls."""
        from playwright.sync_api import sync_playwright
        found = []

        def onResponse(response):
            if self.apiPattern.search(response.url) and not found:
                found.append(response.url)

        for path in ("/searchnew.aspx", "/new-inventory/index.htm"):
            try:
                with sync_playwright() as playwright:
                    browser = playwright.firefox.launch(headless=True)
                    try:
                        page = browser.new_context(viewport={"width": 1600, "height": 1000}).new_page()
                        page.on("response", onResponse)
                        page.goto(siteUrl.rstrip("/") + path, timeout=60000)
                        page.wait_for_timeout(9000)
                    finally:
                        browser.close()
            except Exception as inst:
                print("      page load failed: %s" % str(inst)[:80])
            if found:
                return found[0]
        return None

    def readInventory(self, siteUrl):
        """Return a list of dicts, one per vehicle, or None if the site could not be read."""
        apiUrl = self.findApiUrl(siteUrl)
        if not apiUrl:
            return None
        headers = {"User-Agent": USER_AGENT, "Accept": "application/json", "Referer": siteUrl}
        # pn is the page size.  Asking for a large page avoids having to paginate.
        url = apiUrl + ("&" if "?" in apiUrl else "?") + "pn=96"
        try:
            data = requests.get(url, headers=headers, timeout=60).json()
        except Exception as inst:
            print("      inventory api failed: %s" % str(inst)[:80])
            return None
        vehicles = []
        for card in (data.get("DisplayCards") or []):
            vehicleCard = card.get("VehicleCard") or {}
            vin = vehicleCard.get("VehicleVin")
            if not vin or not isPlausibleVin(vin):
                continue
            if vehicleCard.get("VehicleInProduction"):
                status = "In Production"
            elif vehicleCard.get("VehicleInTransit"):
                status = "In Transit"
            elif vehicleCard.get("VehicleInStock"):
                status = "In Stock"
            else:
                status = findStatusInMarkup(json.dumps(vehicleCard))
            vehicles.append({
                "vin": vin,
                "name": cleanLabel(vehicleCard.get("VehicleNameHtmlEncoded") or vehicleCard.get("VehicleName")),
                "trim": cleanLabel(vehicleCard.get("VehicleTrim")),
                "status": status,
                "interior": cleanLabel(vehicleCard.get("InteriorColorLabel")),
                "exterior": cleanLabel(vehicleCard.get("ExteriorColorLabel")),
                "msrp": vehicleCard.get("VehicleMsrp"),
                "detailUrl": vehicleCard.get("VehicleDetailUrl")
                             or (vehicleCard.get("VehicleImageModel") or {}).get("VehicleDetailUrl"),
            })
        return vehicles


class DealerEProcessReader:
    """Reads inventory from a Dealer eProcess powered dealer site.

    These sites are server rendered and embed one schema.org JSON-LD Vehicle block per
    vehicle.  The block carries the vin, the vehicle name and a description that contains the
    exterior colour and the interior, in the form
        "... , Caviar Exterior, Macadamia Leather And Ash Bamboo Trim Interior, 8AT"
    so the interior is recovered by pulling the text that sits before the word "Interior".

    These sites do not label vehicles as In Production.  A not yet built vehicle is still
    recognizable by its temporary vin, so that is what the status is derived from here, and
    the status is reported as "In Production (temp vin)" to make the weaker basis obvious.
    """
    platformName = "Dealer eProcess"
    ldJsonPattern = re.compile(
        r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', re.S | re.I)

    def readInventory(self, siteUrl):
        from playwright.sync_api import sync_playwright
        htmlPages = []
        try:
            with sync_playwright() as playwright:
                browser = playwright.firefox.launch(headless=True)
                try:
                    page = browser.new_context(viewport={"width": 1600, "height": 1100}).new_page()
                    page.goto(siteUrl.rstrip("/") + "/new-inventory/index.htm", timeout=60000)
                    page.wait_for_timeout(9000)
                    searchUrl = page.url
                    for pageNumber in range(1, 9):
                        if pageNumber > 1:
                            joiner = "&" if "?" in searchUrl else "?"
                            page.goto(searchUrl + "%spt=%d" % (joiner, pageNumber), timeout=60000)
                            page.wait_for_timeout(6000)
                        for _ in range(4):
                            page.mouse.wheel(0, 9000)
                            page.wait_for_timeout(1200)
                        html = page.content()
                        htmlPages.append(html)
                        if len(self.parseHtml(html)) == 0:
                            break
                finally:
                    browser.close()
        except Exception as inst:
            print("      page load failed: %s" % str(inst)[:80])
            return None
        vehicles = {}
        for html in htmlPages:
            for v in self.parseHtml(html):
                vehicles.setdefault(v["vin"], v)
        return list(vehicles.values())

    def parseHtml(self, html):
        vehicles = []
        for match in self.ldJsonPattern.finditer(html):
            try:
                data = json.loads(match.group(1))
            except Exception:
                continue
            if not isinstance(data, dict) or data.get("@type") != "Vehicle":
                continue
            vin = data.get("vehicleIdentificationNumber")
            if not vin or not isPlausibleVin(vin):
                continue
            description = data.get("description") or ""
            interior = None
            m = re.search(r",\s*([^,]+?)\s+Interior\b", description)
            if m:
                interior = cleanLabel(m.group(1))
            exterior = None
            m = re.search(r",\s*([^,]+?)\s+Exterior\b", description)
            if m:
                exterior = cleanLabel(m.group(1))
            vehicles.append({
                "vin": vin,
                "name": cleanLabel(data.get("name")),
                "trim": cleanLabel(data.get("model")),
                # these sites carry no explicit production flag, so fall back to the temp vin
                "status": "In Production (temp vin)" if hasTemporaryVin(vin) else "In Stock/Transit",
                "interior": interior,
                "exterior": exterior or cleanLabel(data.get("color")),
                "msrp": None,
                "detailUrl": data.get("url"),
            })
        return vehicles


READERS = {r.platformName: r() for r in [DealerOnReader, DealerEProcessReader]}


def collect(outputCsvFileName, stateCodes, modelFilters, interiorFilters, keepAllStatuses):
    print("Looking up lexus dealers for", len(stateCodes), "states")
    dealers = getLexusDealers(stateCodes)
    if dealers.empty:
        print("Error: no dealers found, nothing to do")
        return
    print("Found", len(dealers), "dealers")
    print()
    print("Website platforms present:")
    for platform, count in dealers["platform"].fillna("(unknown)").value_counts().items():
        supported = "reader available" if platform in READERS else "NO READER YET, skipped"
        print("   %-18s %4d   %s" % (platform, count, supported))
    print()

    rows = []
    supported = dealers[dealers["platform"].isin(READERS)]
    print("Reading", len(supported), "dealer sites")
    for _, dealer in supported.iterrows():
        reader = READERS[dealer["platform"]]
        print("   %-34s %s" % (dealer["name"], dealer["url"]))
        vehicles = reader.readInventory(dealer["url"])
        if vehicles is None:
            print("      could not read this site")
            continue
        inProduction = sum(1 for v in vehicles if v["status"] == "In Production")
        print("      %d vehicles, %d in production" % (len(vehicles), inProduction))
        for v in vehicles:
            v = dict(v)
            v.update({
                "dealer": dealer["name"], "dealerPhone": dealer["phone"],
                "dealerCity": dealer["city"], "dealerState": dealer["state"],
                "dealerUrl": dealer["url"], "platform": dealer["platform"],
                "isTempVin": hasTemporaryVin(v["vin"]),
            })
            rows.append(v)
        time.sleep(2)

    if not rows:
        print("No vehicles collected")
        return
    df = pd.DataFrame(rows)
    print()
    print("Collected", len(df), "vehicles in total")
    if not keepAllStatuses:
        df = df[df["status"].fillna("").str.startswith("In Production")]
        print("   of which in production:", len(df))
    if modelFilters:
        mask = False
        for text in modelFilters:
            mask = mask | df["name"].fillna("").str.contains(text, case=False, regex=False)
        df = df[mask]
        print("   matching model filter", modelFilters, ":", len(df))
    if interiorFilters:
        mask = False
        for text in interiorFilters:
            mask = mask | df["interior"].fillna("").str.contains(text, case=False, regex=False)
        df = df[mask]
        print("   matching interior filter", interiorFilters, ":", len(df))
    df = df[["status", "isTempVin", "name", "trim", "interior", "exterior", "msrp", "vin",
             "dealer", "dealerPhone", "dealerCity", "dealerState", "detailUrl", "platform",
             "dealerUrl"]]
    df.sort_values(by=["dealerState", "dealer", "name"], inplace=True)
    print()
    print("interior successfully parsed, by dealer (low numbers mean an unreliable interior search):")
    for dealerName, group in df.groupby("dealer"):
        print("   %-34s %3d of %3d" % (dealerName, group["interior"].notna().sum(), len(group)))
    # utf-8-sig so the registered trademark and other symbols in the colour labels survive
    # being opened in Excel instead of turning into mojibake
    df.to_csv(outputCsvFileName, index=False, encoding="utf-8-sig")
    print()
    print("Wrote", len(df), "vehicles to", outputCsvFileName)
    if len(df):
        print()
        print(df[["name", "interior", "dealer", "dealerPhone"]].to_string(index=False))


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    outputCsvFileName = args[0]
    modelFilters = []
    interiorFilters = []
    keepAllStatuses = False
    stateCodes = []
    i = 1
    while i < len(args):
        if args[i] == "--model":
            i += 1
            modelFilters.append(args[i])
        elif args[i] == "--interior":
            i += 1
            interiorFilters.append(args[i])
        elif args[i] == "--all-status":
            keepAllStatuses = True
        else:
            stateCodes.append(args[i].upper())
        i += 1
    collect(outputCsvFileName, stateCodes or US_STATE_CODES, modelFilters, interiorFilters, keepAllStatuses)
