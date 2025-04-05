echo off
echo This batch file is for running multiple vehicles searches.
echo Verify you are in the appropriate directory to start this series of user search for vehicles.
echo Each search is run with the desired YAML file indicating to run once and exit
echo If multiple searches are run on the same model then the model inventory is gotten once from the website
echo by setting the MODEL and then running
echo py vehicles.py
echo and then each of the searches on that model is run with a YAML config file that
echo specifies to use local data ( useLocalInventoryFile: True) and runOnceAndExit:True
echo That way we are getting the inventory only once for that model and then running multiple searches on it
echo Thus avoiding taking extra time to get inventory multiple times from the website, as well as avoiding
echo overloading the website with more inventory request traffic
echo After each search is run a delay occurs to reduce traffic to the website.
echo This delay can be terminated by entering return
echo After all searches are completed a much longer delay is performed and then the 
echo sequence repeats.
echo Assumes there is an output sub directory with models.json and models_raw.json in it.
echo Also assumes you have activated the appropriate python virtual environment
echo Hit return to continue or Ctrl-C to abort
pause
:loopstart
echo -----------
set MODEL=rav4pluginhybrid
echo Model is %MODEL%
echo config file is SearchVehiclesRav4pluginhybrid-AdhesivenessNo4140_config.yaml
py searchForVehicles.py SearchVehiclesRav4pluginhybrid-AdhesivenessNo4140_config.yaml
py waitForSeconds.py 180
echo -----------
set MODEL=priuspluginhybrid
echo Model is %MODEL%
echo config file is SearchVehiclesPriuspluginhybridExact_Soup6927_config.yaml
py searchForVehicles.py SearchVehiclesPriuspluginhybridExact_Soup6927_config.yaml
echo Waiting before next series of searches.
py waitForSeconds.py 7200
goto loopstart