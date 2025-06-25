echo off
echo This script tests various settings of the config items outputResultsMethod, alsoNotifyOnOnlyRemovals, and
echo showRemovalsWhenOutputStatusIsAll.  Testing is done with 4runnerhybrid Model files.
echo !!!! Currently we only have tests for when outputResultsMethod == outputAllSearchResultsOnChange but
echo more test to be added in the future for the other values outputResultsMethod can take on.
echo.
echo Step 1: Ensure you are in test directory (an output subdirectory will be made off of it)
echo Set up the PYTHONPATH environment variable if needed (to point to where  searchForVehiclesTest.py and associated python modules
echo as needed)
echo Set up the SEARCHFORVEHICLESPATH to point to the directory where  searchForVehiclesTest.py you want to test
echo is (no ending slash)
echo Get the gmail credentials.json file and place it in the test directory.
echo Warning!!!! SearchVehicles4runnerhybridTest.txt will be deleted in the current directory so if you want to save it
echo copy it somewhere or rename it before hitting return below. 
echo Hit return to continue after ensuring all the above or hit CTRL-C to abort  -------------------- 
pause
echo on
set MODEL=4runnerhybrid
set VEHICLE_MAKE=
set MODEL_SEARCH_ZIPCODE=
set MODEL_SEARCH_RADIUS=
set MODEL_UPDATE_VEHICLES_TEST_MODE=ON
mkdir output
echo off
echo Hit return to continue
pause
echo Step 2: Will run first test where the input inventory file contains 100 entries 
echo and the programs last user matches parquet file has been deleted
echo to show that all new inventory VINs have been added in the search results file when the program is run. 
echo config item settings are in SearchVehicles4runnerhybridTestCnfg0_config.yaml and contain the normal settings 
echo for these tests with the following changes:
echo outputResultsMethod: "outputAllSearchResultsOnChange"
echo alsoNotifyOnOnlyRemovals: False
echo showRemovalsWhenOutputStatusIsAll: False
echo Test_UserMatchCriteriaFilter0.py (no match criteria filtering done) is copied to Test_UserMatchCriteriaFilter.py which is 
echo called out by the config file.
echo Hit return to run the test
pause
echo on
del SearchVehicles4runnerhybridTest.txt
del SearchVehicles4runnerhybridTest.txt.lastUserMatches.parquet
del SearchVehicles4runnerhybridTest.txt.token.json
del output\4runnerhybrid_Lastraw.parquet
del output\4runnerhybrid_LastStatusInfo.json
del output\4runnerhybrid_????_Sold_raw.parquet
del output\4runnerhybrid_????_Sold.csv
copy modelsTest0.json output\models.json
copy modelsTest0_raw.json output\models_raw.json
copy 4runnerhybridTest0_raw.parquet output\4runnerhybrid_raw.parquet
copy 4runnerhybridTest0_StatusInfo.json output\4runnerhybrid_StatusInfo.json
copy Test_UserMatchCriteriaFilter0.py Test_UserMatchCriteriaFilter.py
py %SEARCHFORVEHICLESPATH%\searchForVehiclesTest.py SearchVehicles4runnerhybridTestCnfg0_config.yaml 
echo off
echo Step 3: Verify that SearchVehicles4runnerhybridTest.txt result file has after the last
echo "<timestamp of when started is close to when started> Started Up Search For Vehicles program ..."  line in the file
echo a "The following list of matching units was found on:" line somewhere below and then below that line a section 
echo containing exactly 100 inventory lines and that they all have  "***ADDED" prefix on them,  
echo AND that an email was sent with subject line "4runnerhybridTestSrchRslt: Vehicle Match Found"
echo and the contents of that email's attached file has a that same section of entries as indicated above 
echo Hit return to continue
pause
echo Step 4: Will run next test where the input inventory file and config file remain the same to show the program
echo does not add any inventory lines to the search results file
echo config item settings are in SearchVehicles4runnerhybridTestCnfg0_config.yaml 
echo Hit return to run the test
pause
echo on
py %SEARCHFORVEHICLESPATH%\searchForVehiclesTest.py SearchVehicles4runnerhybridTestCnfg0_config.yaml
echo off
echo Step 5: Verify that SearchVehicles4runnerhybridTest.txt result file has after the last
echo "<timestamp of when started is close to when started> Started Up Search For Vehicles program ..."  line in the file
echo no section with inventory entires after it
echo AND that an email was NOT sent
echo Hit return to continue
pause
echo Step 6: Will run next test where the input inventory file now only contains the first 50 entries of the file 
echo in the prior step, and the config file is the same as in prior step, so that
echo that when the program is run the search results file has those 50 entries of inventory added to it
echo with a blank prefix, and no email/text should have been sent since
echo showRemovalsWhenOutputStatusIsAll: False , outputResultsMethod: "outputAllSearchResultsOnChange",  and 
echo alsoNotifyOnOnlyRemovals: False
echo So even though entries were removed from the input inventory file we don't show them because of those config
echo file settings.
echo config item settings are in SearchVehicles4runnerhybridTestCnfg0_config.yaml 
echo Hit return to run the test
pause
echo on
copy 4runnerhybridTest3HalfEmpty_raw.parquet output\4runnerhybrid_raw.parquet
copy 4runnerhybridTest3HalfEmpty_StatusInfo.json output\4runnerhybrid_StatusInfo.json
py %SEARCHFORVEHICLESPATH%\searchForVehiclesTest.py SearchVehicles4runnerhybridTestCnfg0_config.yaml
echo off
echo Step 7: Verify that SearchVehicles4runnerhybridTest.txt result file has after the last
echo "<timestamp of when started is close to when started> Started Up Search For Vehicles program ..."  line in the file
echo a section that only has those 50 inventory lines in all with a blank prefix
echo AND that an email was NOT sent
echo Hit return to continue
pause
echo Step 8: Will run next test where the input inventory has no entries in it, the config file has modified normal settings of
echo outputResultsMethod: "outputAllSearchResultsOnChange"
echo alsoNotifyOnOnlyRemovals: True
echo showRemovalsWhenOutputStatusIsAll: True
echo to show that when the program is run the search results file has added the 50 entries from the last step
echo but now with a ***REMOVED prefix on them, and that an email is sent with an attached file containing that
echo same inventory information.
echo config file used is SearchVehicles4runnerhybridTestCnfg1_config.yaml
echo Hit return to run the test
pause
echo on
copy 4runnerhybridTest2Empty_raw.parquet output\4runnerhybrid_raw.parquet
copy 4runnerhybridTest2Empty_StatusInfo.json output\4runnerhybrid_StatusInfo.json
py %SEARCHFORVEHICLESPATH%\searchForVehiclesTest.py SearchVehicles4runnerhybridTestCnfg1_config.yaml
echo off
echo Step 9: Verify that SearchVehicles4runnerhybridTest.txt result file has after the last
echo "<timestamp of when started is close to when started> Started Up Search For Vehicles program ..."  line in the file
echo a "The following list of matching units was found on:" line somewhere below and then below that line a section 
echo containing exactly 50 inventory lines from the prior run and that they all have  "***REMOVED" prefix on them,  
echo AND that an email was sent with subject line "4runnerhybridTestSrchRslt: Vehicle Match Found"
echo and the contents of that email's attached file has a that same section of entries as indicated above 
echo Hit return to continue
pause
echo Step 10: Will run next test where the input inventory file contains the same entries as in Step2 (the 100 entries)
echo and config file settings are the same as in the prior step
echo to show that all 100 inventory entries have been added in the search results file with the ***ADDED prefix
echo when the program is run. 
echo SearchVehicles4runnerhybridTestCnfg1_config.yaml is the config file with all the normal settings and modifications of
echo outputResultsMethod: "outputAllSearchResultsOnChange"
echo alsoNotifyOnOnlyRemovals: True
echo showRemovalsWhenOutputStatusIsAll: True
echo Hit return to run the test
pause
echo on
copy 4runnerhybridTest0_raw.parquet output\4runnerhybrid_raw.parquet
copy 4runnerhybridTest0_StatusInfo.json output\4runnerhybrid_StatusInfo.json
py %SEARCHFORVEHICLESPATH%\searchForVehiclesTest.py SearchVehicles4runnerhybridTestCnfg1_config.yaml
echo off
echo Step 11: Verify that SearchVehicles4runnerhybridTest.txt result file has after the last
echo "<timestamp of when started is close to when started> Started Up Search For Vehicles program ..."  line in the file
echo a "The following list of matching units was found on:" line somewhere below and then below that line a section 
echo containing exactly 100 inventory lines and that they all have  "***ADDED" prefix on them,  
echo AND that an email was sent with subject line "4runnerhybridTestSrchRslt: Vehicle Match Found"
echo and the contents of that email's attached file has a that same section of entries as indicated above 
echo Hit return to continue
pause
echo Step 12: Will run next test where the input inventory file contains the same entries as in the prior step (the 100 entries)
echo but with 2 new unique VIN entries added at the start JTDAAAAA3RA01Add1, and JTDAAAAA3RA01Add2,
echo and the existing VIN JTEVB5BR0S111CQ36 entry modfied so that
echo "year" = 2051
echo "eta.currFromDate" = '2051-02-18' 
echo "eta.currToDate" = '2051-03-18'
echo "stockNum" = '116963'
echo and VIN JTEVB5BR0S111CI20 entry deleted. 
echo and config file settings are the same as in the prior step
echo to show that the new VINS show up in the search results file with the ***ADDED prefix,
echo the modified VIN shows up in the search results file with the ***MODED prefix and 
echo a List Of Changes sentence at the last tabbed field of that VINs line with each field that changed value and the previous and
echo current value  (except for the stockNum which is not field that is displayed in the results or modified names),
echo and the deleted VIN entry shows up with a ***REMOVED prefix at the very end of the section
echo SearchVehicles4runnerhybridTestCnfg1_config.yaml is the config file with all the normal settings and modifications of
echo outputResultsMethod: "outputAllSearchResultsOnChange"
echo alsoNotifyOnOnlyRemovals: True
echo showRemovalsWhenOutputStatusIsAll: True
echo Hit return to run the test
pause
echo on
copy 4runnerhybridTest1_raw.parquet output\4runnerhybrid_raw.parquet
copy 4runnerhybridTest1_StatusInfo.json output\4runnerhybrid_StatusInfo.json
py %SEARCHFORVEHICLESPATH%\searchForVehiclesTest.py SearchVehicles4runnerhybridTestCnfg1_config.yaml
echo off
echo Step 13: Verify that SearchVehicles4runnerhybridTest.txt result file has after the last
echo "<timestamp of when started is close to when started> Started Up Search For Vehicles program ..."  line in the file
echo a "The following list of matching units was found on:" line somewhere below and then below that line a section 
echo containing exactly 102 inventory lines with the values and prefixes indicated in the prior Step  
echo AND that an email was sent with subject line "4runnerhybridTestSrchRslt: Vehicle Match Found"
echo and the contents of that email's attached file has a that same section of entries as indicated above 
echo Hit return to continue
pause
echo off
echo Step 14: Will run next test where the input inventory file contains the same entries as in the prior step 
echo but with existing VIN JTEVB5BR0S111BE87 having its Selling Price changed from 73146.0 to 72000.
echo and calculated Markup changing from 4297.0 to 3151.0
echo The config file is the same as in the prior step, however 
echo the match criteria filter file Test_UserMatchCriteriaFilter1.py is used by copying it to 
echo Test_UserMatchCriteriaFilter.py which is called out by the config file. 
echo This filter is vin != "JTEVB5BR0S111BE87" or  Selling Price less than 70000)
echo to show that the VIN JTEVB5BR0S111BE87 shows up with a ***REMOVED prefix
echo and List of Changes sentence at the last tabbed field of that VINs line showing the Selling Price, and Markup as changing
echo and as indicated above to show the changes when the VIN is in inventory but the does not meet the match criteria fitler. 
echo All other 101 entries should have a blank prefix and have values as in the prior step results and no List Of Changes.
echo SearchVehicles4runnerhybridTestCnfg1_config.yaml is the config file with all the normal settings and modifications of
echo outputResultsMethod: "outputAllSearchResultsOnChange"
echo alsoNotifyOnOnlyRemovals: True
echo showRemovalsWhenOutputStatusIsAll: True
echo Test_UserMatchCriteriaFilter1.py is copied to Test_UserMatchCriteriaFilter.py which is called out by the config file
echo and has the above match criteria filtering.
echo Hit return to run the test
pause
echo on
copy 4runnerhybridTest8_raw.parquet output\4runnerhybrid_raw.parquet
copy 4runnerhybridTest8_StatusInfo.json output\4runnerhybrid_StatusInfo.json
copy Test_UserMatchCriteriaFilter1.py Test_UserMatchCriteriaFilter.py
py %SEARCHFORVEHICLESPATH%\searchForVehiclesTest.py SearchVehicles4runnerhybridTestCnfg1_config.yaml
echo off
echo Step 15: Verify that SearchVehicles4runnerhybridTest.txt result file has after the last
echo "<timestamp of when started is close to when started> Started Up Search For Vehicles program ..."  line in the file
echo a "The following list of matching units was found on:" line somewhere below and then below that line a section 
echo containing exactly 102 inventory lines with the values and prefixes indicated in the prior Step  
echo AND that an email was sent with subject line "4runnerhybridTestSrchRslt: Vehicle Match Found"
echo and the contents of that email's attached file has a that same section of entries as indicated above 
echo Hit return to continue
pause
echo  Completed Testing