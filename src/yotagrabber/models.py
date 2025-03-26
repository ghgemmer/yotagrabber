"""Get a list of Toyota models from the Toyota website."""
import json
import datetime

import pandas as pd
import random
import requests
from time import sleep

from yotagrabber import config, wafbypass

# Set to True to use local data and skip requests to the Toyota website.
USE_LOCAL_DATA_ONLY = False

DEBUG_ENABLED = False

def get_models_query():
    """Read models query from a file."""
    with open(f"{config.BASE_DIRECTORY}/graphql/models.graphql", "r") as fileh:
        query = fileh.read()

    # Replace the zip code with a random zip code.
    # query = query.replace("ZIPCODE", config.random_zip_code())
    query = query.replace("ZIPCODE", "90210")

    return query


def read_local_data():
    """Read local raw data from the disk instead of querying Toyota."""
    with open("output/models_raw.json", "r") as fileh:
        result = json.load(fileh)

    return result


def query_toyota():
    """Query Toyota for a list of models."""
    query = get_models_query()
    
    # Get headers by bypassing the WAF.
    print("Bypassing WAF")
    headers = wafbypass.WAFBypass().run()
    print("Getting list of models")
    tryCount = 4
    result = None
    # TODO: still getting many query failures even with this retry method (goes through all retires withuot success)
    # and not sure why?  Printed resp.text does not seem to contain any readable ascii text.
    while tryCount:
        # Make request.
        json_post = {"query": query}
        url = "https://api.search-inventory.toyota.com/graphql"
        resp = requests.post(
            url,
            json=json_post,
            headers=headers,
            timeout=60,
        )
        if DEBUG_ENABLED:
            if resp is None:
                print("query_toyota: models query resp is None")
            else:
                print("query_toyota: models query request headers: ", repr(resp.request.headers))
                print("query_toyota: models query request.body: " + str(resp.request.body))
                print("query_toyota: models query resp", repr (resp.headers), repr(resp))
        try:
            result = resp.json()["data"]["models"]
            break
        except (requests.exceptions.JSONDecodeError) as inst:
            print ("query_toyota: Exception occurred with accessing json models list response:", str(type(inst)) + " "  + str(inst))
            print("resp.status_code", resp.status_code)
            print("resp.headers", resp.headers)
            #print("resp.text", resp.text)
            #print("resp.content", resp.content)
            #return None
        tryCount -= 1
        print("query_toyota: Trying models list query again" ,  ", tryCount = " + str(tryCount))
        tm = 7 + (6 * random.random())
        print("sleeping", tm, " secs")
        sleep(tm)
        
    return result


def update_models():
    """Generate a JSON file containing Toyota models."""
    result = read_local_data() if USE_LOCAL_DATA_ONLY else query_toyota()

    # Get the models from the result.
    df = pd.json_normalize(result)

    df.sort_values("modelCode").to_json(
        "output/models_raw.json", orient="records", indent=2
    )

    # Build a view and write it out as JSON.
    models = (
        df[
            [
                "modelCode",
                "title",
            ]
        ]
        .sort_values("title", ascending=True)
        .reset_index(drop=True)
    )
    # Add in any old models we can still get which are not in the current models list
    #if datetime.date.today().year <= 2025
    new_model_row = pd.DataFrame({'modelCode': ['rav4prime'], 'title': ['RAV4 Prime']})
    models = pd.concat([models, new_model_row], ignore_index=True)
    models.drop_duplicates(subset=["modelCode"], inplace=True)
    new_model_row1 = pd.DataFrame({'modelCode': ['venza'], 'title': ['Venza']})
    models = pd.concat([models, new_model_row1], ignore_index=True)
    models.drop_duplicates(subset=["modelCode"], inplace=True)
    new_model_row2 = pd.DataFrame({'modelCode': ['4runnerhybrid'], 'title': ['4Runner Hybrid']})
    models = pd.concat([models, new_model_row2], ignore_index=True)
    new_model_row3 = pd.DataFrame({'modelCode': ['priusprime'], 'title': ['Prius Prime']})
    models = pd.concat([models, new_model_row3], ignore_index=True)
    models.drop_duplicates(subset=["modelCode"], inplace=True)
    
    # Toyota uses different names for some models when you query the graphQL API.
    # https://github.com/major/yotagrabber/issues/32
    models.loc[models["modelCode"] == "gr86", "modelCode"] = "86"
    models.loc[models["modelCode"] == "grsupra", "modelCode"] = "supra"

    models.to_json("output/models.json", orient="records", indent=2)
