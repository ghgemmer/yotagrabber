# Gets list of inventory for the indicated vehicle makes for each model in the US
# and uploads this to a google drive

$Vehicle_Makes = 'toyota', 'lexus'

function Get-VehicleModels {
    # Gets a list of all models (fields modelCode, Title) and writes it to the json file output/models.json
    poetry run update_models
}

function Get-VehicleInventoryForModels {
    param (
        $DirectoryToRunIn,
        $PythonVENVPowershellActivateScript,
        $uploadInventory = "",
        $credentialsFileName = ""
    )
    # Use the following to log all console output as it is consistent in doing this over the inconsistent Start-Transcript
    # Note that the console output is redirected to the log file so if you want see it as it is running
    # use some linux like tail function on that log file, like the power shell 
    # Get-Content -Path filename -Tail 0 -Wait in another window to output the logfile contents as it is appended.
    $logfile = $DirectoryToRunIn + "\output\InventoryRunlog.txt"
    Get-VehicleInventoryForModelsA -DirectoryToRunIn $DirectoryToRunIn -PythonVENVPowershellActivateScript $PythonVENVPowershellActivateScript -uploadInventory $uploadInventory -credentialsFileName $credentialsFileName  *>> $logfile
}


function Get-VehicleInventoryForModelsA {
    param (
        $DirectoryToRunIn,
        $PythonVENVPowershellActivateScript,
        $uploadInventory = "",
        $credentialsFileName = ""
    )
    #Write-Host "uploadInventory is " $uploadInventory
    #Write-Host "credentialsFileName is " $credentialsFileName
    cd $DirectoryToRunIn
    $env:PYTHONUNBUFFERED = 1
    Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
    .$PythonVENVPowershellActivateScript
    $timeout = 60*3
    foreach ($vehicleMake in $Vehicle_Makes) {
        $env:VEHICLE_MAKE = $vehicleMake
        $curDate = Get-Date
        Write-Host $curDate "Started Vehicle Inventory search for Make" $vehicleMake
        # Get a list of all the current models first
        Write-Host "Getting list of Vehicle Models for Make" $vehicleMake
        Get-VehicleModels
        if ($LASTEXITCODE -eq 0) { 
            if ($vehicleMake -eq 'toyota') {
                $outputDir =  ".\output"
            }
            else {
                $outputDir =  ".\output\" + $vehicleMake
            }
            $modelFileName =  $outputDir + "\models.json"
            $models = Get-Content -Raw -Path $modelFileName | ConvertFrom-Json 
            $curDate = Get-Date
            Write-Host $curDate "Getting list of Vehicle Inventory for Make" $vehicleMake
            foreach ($model in $models) {
                Write-Host "Sleeping $timeout seconds before next operation"
                Start-Sleep -Seconds $timeout
                # set environment variable that update_vehicles uses
                $env:MODEL = $model.modelCode
                # Update that models inventory
                $curDate = Get-Date
                Write-Host $curDate "Getting inventory for $env:MODEL "
                poetry run update_vehicles
                if ($LASTEXITCODE -ne 0) { 
                    Write-Host "Error: Failed to get inventory for model $MODEL"
                }    
            }
            $curDate = Get-Date
            Write-Host $curDate "Vehicle Inventory search Completed" 
            if ($uploadInventory -eq "upload") {
                if ($credentialsFileName -eq "") {
                    $credentialsFileName = "inventory_credentials.json"
                }
                Write-Host "Uploading Inventory to Google Drive Started for Make" $vehicleMake
                if ($vehicleMake -eq 'toyota') {
                    $googleFolderName =  "Vehicle_Inventory"
                }
                else {
                    $googleFolderName =  "Vehicle_Inventory/" + $vehicleMake
                }
                py src\upload-files.py $outputDir  $googleFolderName  $credentialsFileName
                if ($LASTEXITCODE -ne 0) { 
                    Write-Host "Error: Failed to upload all inventory to google drive for Make" $vehicleMake
                } 
                else {
                    Write-Host "Uploading Inventory to Google Drive Completed"
                }   
            }
        }
        else
        {
            Write-Host "Error: Failed to get list of Vehicle Models.  Aborting Search"
        }
    }
    
}

$uploadInventory = ""
if ($args.Count -ge 3) {
    $uploadInventory = $args[2]
}
$credentialsFileName = ""
if ($args.Count -ge 4) {
    $credentialsFileName = $args[3]
}

Get-VehicleInventoryForModels -DirectoryToRunIn $args[0] -PythonVENVPowershellActivateScript $args[1] -uploadInventory $uploadInventory -credentialsFileName $credentialsFileName