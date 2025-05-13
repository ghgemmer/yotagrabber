echo off
echo This script tests various behaviors of the LastChangedDateTime 
echo Testing is done with 4runner Model files.
echo.
echo Step 1: Ensure you are in test directory (an output subdirectory will be made off of it)
echo Set up the PYTHONPATH environment variable if needed (to point to where vehiclesTest2LastChangedDate.py and associated python modules
echo as needed)
echo Set up the SEARCHFORVEHICLESPATH to point to the directory where vehiclesTest2LastChangedDate.py you want to test
echo is (no ending slash)
echo Also you need to enable the yotabrabber vitual environment before running this script.
echo Hit return to continue after ensuring all the above or hit CTRL-C to abort  -------------------- 
pause
echo on
set MODEL=4runner
set VEHICLE_MAKE=
set MODEL_SEARCH_ZIPCODE=
set MODEL_SEARCH_RADIUS=
set MODEL_UPDATE_VEHICLES_TEST_MODE=ON
set MODEL_UPDATE_VEHICLES_TEST_MODE_TODAY_DATE=2025-04-12 00:00:00

mkdir output
echo off
echo Hit return to continue
pause
echo Step 2: Will set the baseline data in this next test.
echo Hit return to run the test
pause
echo on
del output\4runner.csv
del output\4runner_Lastraw.parquet
del output\4runner_LastStatusInfo.json
del output\4runner_????_Sold_raw.parquet
del output\4runner_????_Sold.csv
del output\4runner_ChangeHistory.csv
del output\4runner_ChangeHistory.parquet
copy modelsTest0.json output\models.json
copy modelsTest0_raw.json output\models_raw.json
copy 4runner_Test0_raw.parquet output\4runner_raw.parquet
copy 4runner_Test0_StatusInfo.json output\4runner_StatusInfo.json
copy 4runner_Test0_raw.parquet output\4runner_Lastraw.parquet
copy 4runner_Test0_StatusInfo.json output\4runner_LastStatusInfo.json
pause
py %SEARCHFORVEHICLESPATH%\vehiclesTest2LastChangedDate.py
echo off
echo Step 3: Verify that all base files are created in the output and the FirstAddedDate,
echo and LastChangedDateTime and FirstAddedDate columns being blank in all files.
echo and the infoDateTime in the 4runner.csv file being 2025-03-31 21:xx:xx
echo Also verify that the Change History file has no entries in it.
echo 
echo Hit return to continue
pause
echo Step 4: Will run next test where we
echo Change all infoDateTime to '2025-04-01' for the inventory data gotten
echo Add a vin 'JTEKU5JR4R622Add1' by changing existing vin entry JTEKU5JR4R6223168 to that vin number,
echo and thus at the same time remove vin JTEKU5JR4R6223168
echo and for vin JTEEU5JR9R5314455 we change the following
echo Year is changed from 2024 to 2026 
echo Selling Price changed from 45870.0 to 46000
echo Markup changed from 895 to 1025
echo eta.currFromDate changed from 2025-03-26T00:00:00.000Z' to '2025-04-03 00:00:00'
echo eta.currToDat changed from  '2025-03-30T00:00:00.000Z' to '2025-04-10'
echo And for VIN JTEVA5AR0S5000269 we change the following options
echo Replace option Roof Rack Cross Bars with Silly Option 1
echo Replace option Rear Cargo Organizer with the duplicate option SILLY OPTION 1 (to test duplicate options later on)
echo So with those changes the new data should match those in 4runner.csv and
echo the LastChangedDateTime, and FirstAddedDate for vin JTEKU5JR4R622Add1
echo should be the same as infoDateTime which is '2025-04-01'.
echo For vin JTEEU5JR9R5314455, and JTEVA5AR0S5000269, the LastChangedDateTime should be the same as the
echo infoDateTime which is '2025-04-01'
echo The 2024 4runner sold file should have the JTEKU5JR4R6223168 entry in it now.
echo The Change History file should have an entry for the added vin, the removed vin, and the changed vin 
echo with the changed vin having the changes as indicated above and in the List of Changes column and the 
echo LastChangedDateTime for that changed vin being '2025-04-01' (same as in the 4runner.csv file)
echo and the added vin having the FirstAddedDate and LastChangedDateTime being '2025-04-01'

echo Hit return to run the test
pause
echo on
copy 4runner_Test1_raw.parquet output\4runner_raw.parquet
copy 4runner_Test1_StatusInfo.json output\4runner_StatusInfo.json
py %SEARCHFORVEHICLESPATH%\vehiclesTest2LastChangedDate.py
echo off
echo Step 5: Verify the information as detailed in the prior step.
echo Hit return to continue
pause
echo Step 6: Will run next test where 
echo Change all infoDateTime to '2025-04-03' for the inventory data gotten.
echo Change data for vin JTEVA5AR0S5000188 as follows:
echo eta.currToDate changed from '2025-03-02T00:00:00.000Z' to  '2025-04-15'
echo Engine Name changed from  'i-FORCE 2.4L 4-Cyl. Turbo Engine' to 'Silly Engine'
echo Base Msrp changed from 47250 to 47555`
echo and that the LastChangedDateTime for vin JTEVA5AR0S5000188 is '2025-04-03' 
echo and that the LastChangedDateTime for all other vins is the same as it was before in the prior step
echo Also that the Changed History file has the changes as indicated above and in the List of Changes column and the 
echo LastChangedDateTime for that changed vin being the infoDateTime which is '2025-04-03' (same as in the 4runner.csv file)
echo and all other entries in that Change History file being unchanged.
echo Hit return to run the test
pause
echo on
copy 4runner_Test2_raw.parquet output\4runner_raw.parquet
copy 4runner_Test2_StatusInfo.json output\4runner_StatusInfo.json
py %SEARCHFORVEHICLESPATH%\vehiclesTest2LastChangedDate.py
echo off
echo Step 7: Verify the changes detailed in the previous step.
echo Hit return to continue
pause
echo Step 8: Will run next test where
echo infoDateTime is changed to '2025-04-06' for all inventory entries gotten
echo vin JTEKU5JR4R622Add1 has the following changes
echo eta.currFromDate changed from blank to '2025-04-12'
echo eta.currToDate changed from '2023-12-08T00:00:00.000Z' to 2025-04-20'
echo LastChangedDateTime is now '2025-04-06'
echo And for VIN JTEVA5AR0S5000269 we change the following options back 
echo Replace option Silly Option 1 with Roof Rack Cross Bars
echo Replace option SILLY OPTION 1 with Rear Cargo Organizer
echo and the LastChangedDateTime is now '2025-04-06' for that vin( JTEVA5AR0S5000269)
echo and that the LastChangedDateTime remains unchanged for all other entries
echo Also that the Changed History file has the changes as indicated above and in the List of Changes column and the 
echo LastChangedDateTime for those two changed vins being the infoDateTime which is '2025-04-06' (same as in the 4runner.csv file)
echo and all other entries in that Change History file being unchanged.
echo Hit return to run the test
pause
echo on
copy 4runner_Test3_raw.parquet output\4runner_raw.parquet
copy 4runner_Test3_StatusInfo.json output\4runner_StatusInfo.json
py %SEARCHFORVEHICLESPATH%\vehiclesTest2LastChangedDate.py
echo off
echo Step 9: Verify the changes detailed in the previous step.
echo Hit return to continue
pause
echo Step 10: Will run next test where
echo infoDateTime is changed to '2025-04-07' for all inventory entries gotten
echo and nothing else is changed so that everything else in the files remains the same.
echo Hit return to run the test
pause
echo on
copy 4runner_Test4_raw.parquet output\4runner_raw.parquet
copy 4runner_Test4_StatusInfo.json output\4runner_StatusInfo.json
py %SEARCHFORVEHICLESPATH%\vehiclesTest2LastChangedDate.py
echo off
echo Step 11: Verify the changes detailed in the previous step.
echo Hit return to continue
pause
echo Step 12: Will run next test where 
echo infoDateTime is changed to '2025-04-08' for all inventory entries gotten
echo vin JTEEU5JR9R5314455 has the following changes:
echo eta.currToDate changed from '2025-04-10' to '2025-04-22'
echo LastChangedDateTime is now '2025-04-08'
echo and that the LastChangedDateTime remains unchanged for all other entries
echo Also that the Changed History file has the changes as indicated above and in the List of Changes column and the 
echo LastChangedDateTime for that changed vin being the infoDateTime which is '2025-04-08' (same as in the 4runner.csv file)
echo and all other entries in that Change History file being unchanged.
echo Hit return to run the test
pause
echo on
copy 4runner_Test5_raw.parquet output\4runner_raw.parquet
copy 4runner_Test5_StatusInfo.json output\4runner_StatusInfo.json
py %SEARCHFORVEHICLESPATH%\vehiclesTest2LastChangedDate.py
echo off
echo Step 13: Verify the changes detailed in the previous step.
echo Hit return to continue
pause
echo Step 14: Will run next test where 
echo infoDateTime is changed to '2025-04-09' for all inventory entries gotten
echo Add a vin 'JTEEU5JR9R531Add2' by changing existing vin entry JTEEU5JR9R5314455 to that vin number,
echo and thus at the same time remove vin JTEEU5JR9R5314455
echo So with those changes the new data should match those in 4runner.csv and
echo the LastChangedDateTime, and FirstAddedDate for vin JTEEU5JR9R531Add2
echo should be the same as infoDateTime which is '2025-04-09'.
echo The 2026 4runner sold file should have the JTEEU5JR9R5314455 entry in it now with all fields unchanged
echo The Change History file should have an entry for the added vin, and the removed vin, 
echo and the added vin having the FirstAddedDate and LastChangedDateTime being '2025-04-09'
echo Hit return to run the test
pause
echo on
copy 4runner_Test6_raw.parquet output\4runner_raw.parquet
copy 4runner_Test6_StatusInfo.json output\4runner_StatusInfo.json
py %SEARCHFORVEHICLESPATH%\vehiclesTest2LastChangedDate.py
echo off
echo Step 15: Verify the changes detailed in the previous step.
echo Hit return to continue
pause
echo Step 16: Will run next test where 
echo infoDateTime is changed to '2025-04-10' for all inventory entries gotten
echo Add sold vin JTEEU5JR9R5314455 by changing existing vin entry 'JTEEU5JR9R531Add2' to that vin number,
echo and thus at the same time removing vin JTEEU5JR9R531Add2
echo So with those changes the new data should match those in 4runner.csv and
echo the LastChangedDateTime, and FirstAddedDate for vin JTEEU5JR9R5314455
echo should be the same as infoDateTime which is '2025-04-10'.
echo The 2026 4runner sold file should have the JTEEU5JR9R531Add2 entry in it now with all fields unchanged
echo The Change History file should have an entry for the added vin, and the removed vin, 
echo and the added vin having the FirstAddedDate and LastChangedDateTime being '2025-04-10'
echo Hit return to run the test
pause
echo on
copy 4runner_Test7_raw.parquet output\4runner_raw.parquet
copy 4runner_Test7_StatusInfo.json output\4runner_StatusInfo.json
py %SEARCHFORVEHICLESPATH%\vehiclesTest2LastChangedDate.py
echo off
echo Step 17: Verify the changes detailed in the previous step.
echo Hit return to continue
pause
echo  Completed Testing