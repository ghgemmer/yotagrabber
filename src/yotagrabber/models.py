"""Get a list of  models for the specified vehicle make (toyota, lexus, future makes) from the associated website.
which can be used later on to get inventory for
"""
import json
import datetime
import os
import pandas as pd
import random
import requests
from time import sleep
import sys
#print ("sys.path when in models.py is ", sys.path)

from yotagrabber import config, wafbypass, vehicleUtilities
#import importlib

#importlib.reload(config)
#importlib.reload(wafbypass)
#importlib.reload(sys)


# Set to True to use local data and skip requests to the Toyota website.
USE_LOCAL_DATA_ONLY = False

DEBUG_ENABLED = False

modelsObject = None

# what the list models request graphql brand field must be based on the vehicle Make
genericToyotaMakeToGraphqlBrandFieldStr = {vehicleUtilities.vehicleMakeLexus: "L", vehicleUtilities.vehicleMakeToyota: "T"} 

class modelsClass:
    #base Class for model collection and updating.  Needs certain methods overriden in superclass
    def __init__(self):
        self.vehicleMake = None
    def read_local_data(self):
        """Read local raw data from the disk instead of querying website."""
        fileName = vehicleUtilities.getVehicleMakeRelOutDirNoEndSlash(self.vehicleMake) + "/models_raw.json"
        with open(fileName, "r") as fileh:
            result = json.load(fileh)
        return result
        
    def query_for_models(self):
        """Send query for a list of models and return response as a json result."""
        print("Error: modelsClass.query_for_models method is abstract and  must be overriden by a superclass")
        return None
    def standardizeFields(self, df):
        # modifies the passed df in place so that it has at least modelCode (used in later inventory queries in another module), 
        # and title fields.  The assumption is that any vehicle make will have some code of some kind for each model
        # that we can use later on in another program to get inventory for it.
        # Also that there is some title of some kind that can be used later on by the inventory program to 
        # remove if needed the model name from the trim.
        print("Error: modelsClass.standardizeFields method is abstract and  must be overriden by a superclass")
    def addOtherModels(self, models):
        # adds on any other models we want to look for and returns the updated result
        return models
    def update_models(self):
        #print ("Vehicle Make for Models being collected for is ", self.vehicleMake)
        """Generate a raw JSON file containing the models."""
        # Get a dataframe of the models from the json result.
        if USE_LOCAL_DATA_ONLY:
            result = self.read_local_data()
        else:
            result = self.query_for_models()
            fileName = vehicleUtilities.getVehicleMakeRelOutDirNoEndSlash(self.vehicleMake) + "/models_raw.json"
            df = pd.json_normalize(result)
            df.to_json(
                fileName, orient="records", indent=2
            )
            
        self.standardizeFields(df)
        
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
        # Add in any models we can get inventory for that the website does not return
        # These could be models out of production, or new ones that for some reason are not yet shown, or other reasons
        models = self.addOtherModels(models)
        models.drop_duplicates(subset=["modelCode"], keep='last', inplace=True)
        fileName = vehicleUtilities.getVehicleMakeRelOutDirNoEndSlash(self.vehicleMake) + "/models.json"
        models.to_json(fileName, orient="records", indent=2)

class genericToyotaModelsClass(modelsClass):
    # base class for  toyota or lexus models
    def __init__(self):
        super().__init__()
    def get_models_query(self):
        """Read models query from a file."""
        print("config.BASE_DIRECTORY", config.BASE_DIRECTORY)
        with open(f"{config.BASE_DIRECTORY}/graphql/models.graphql", "r") as fileh:
            query = fileh.read()
            
        #print("genericToyotaModelsClass.get_models_query before replacement ", query)
        query = query.replace("VEHICLE_MAKE", genericToyotaMakeToGraphqlBrandFieldStr[self.vehicleMake])
        # Replace the zip code with some zip code.
        query = query.replace("ZIPCODE", "90210")
        #print("genericToyotaModelsClass.get_models_query after replacement ", query)
        
        return query
    def query_for_models(self):
        """Send query for a list of models and return response as a json result."""
        query = self.get_models_query()
        
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

class lexusModelsClass(genericToyotaModelsClass):
    # class for lexus model colletion and updating
    def __init__(self):
        #print("lexusModelsClass __init__ ")
        super().__init__()
        # vehicle make is the internal vehicleMake after the user input vehicle make has been validated.
        self.vehicleMake = vehicleUtilities.vehicleMakeLexus
    def standardizeFields(self, df):
        # modifies the passed df in place so that it has at least modelCode (used in later inventory queries in another module), 
        # and title fields.  The assumption is that any vehicle make will have some code of some kind for each model
        # that we can use later on in another program to get inventory for it.
        # Also that there is some title of some kind that can be used later on by the inventory program to 
        # remove if needed the model name from the trim.
        
        # for lexus the title field is returned as Null in the query response, so use modelCode as title for now
        df["title"] = df["modelCode"]
        
class toyotaModelsClass(genericToyotaModelsClass):
    # class for toyota model colletion and updating
    def __init__(self):
        super().__init__()
        # vehicle make is the internal vehicleMake after the user input vehicle make has been validated.
        self.vehicleMake = vehicleUtilities.vehicleMakeToyota
    def standardizeFields(self, df):
        # modifies the passed df in place so that it has at least modelCode (used in later inventory queries in another module), 
        # and title fields.  The assumption is that any vehicle make will have some code of some kind for each model
        # that we can use later on in another program to get inventory for it.
        # Also that there is some title of some kind that can be used later on by the inventory program to 
        # remove if needed the model name from the trim field.
        #
        # Toyota uses different names for some models when you query the graphQL API, so rename them here
        # https://github.com/major/yotagrabber/issues/32
        df.drop_duplicates(subset=["modelCode"], keep='last', inplace=True)
        df.loc[df["modelCode"] == "gr86", "modelCode"] = "86"
        df.loc[df["modelCode"] == "grsupra", "modelCode"] = "supra"
        df.drop_duplicates(subset=["modelCode"], keep='last', inplace=True)
        
    def addOtherModels(self, models):
        # adds on any other models we want to look for and returns the updated result
        # drop any duplicate model codes.
        updatedModels = models
        new_model_row = pd.DataFrame({'modelCode': ['rav4prime'], 'title': ['RAV4 Prime']})
        updatedModels = pd.concat([updatedModels, new_model_row], ignore_index=True)
        new_model_row1 = pd.DataFrame({'modelCode': ['venza'], 'title': ['Venza']})
        updatedModels = pd.concat([updatedModels, new_model_row1], ignore_index=True)
        new_model_row2 = pd.DataFrame({'modelCode': ['4runnerhybrid'], 'title': ['4Runner Hybrid']})
        updatedModels = pd.concat([updatedModels, new_model_row2], ignore_index=True)
        
        updatedModels.drop_duplicates(subset=["modelCode"], keep='last', inplace=True)
        return updatedModels


def update_models():
    global modelsObject
    modelsObject = None
    # Get the vehicleMake that we should be searching models for.
    VEHICLE_MAKE = os.environ.get("VEHICLE_MAKE")
    #print("User entered VEHICLE_MAKE environment variable is ", VEHICLE_MAKE)
    # validate user input vehicle make and return internal vehicle make
    ok, vehicleMake = vehicleUtilities.validateVehicleMake(VEHICLE_MAKE)
    if not ok:
        print("update_models aborting due to invalid Vehicle Make")
        return
    else:
        print("vehicleMake specified is", vehicleMake )
    if vehicleMake == vehicleMakeLexus:
        modelsObject = lexusModelsClass()
    elif vehicleMake == vehicleMakeToyota:
        modelsObject = toyotaModelsClass()
    else:
        print("Error: No modelsObject made for vehicleMake", vehicleMake, ". Terminating update_models()")
        return
    modelsObject.update_models()
    
if __name__ == "__main__":
    update_models()

