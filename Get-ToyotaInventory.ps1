# Gets list of Toyota models, current inventory for each model in the US
# and commits all this to git

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
    # Note that the console output is redirected to the log file so you want see it as it is running unless
    # you use some linux like tail function, like the power shell 
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
    $curDate = Get-Date
    Write-Host "Started Vehicle Inventory search at" $curDate
    #Write-Host "uploadInventory is " $uploadInventory
    #Write-Host "credentialsFileName is " $credentialsFileName
    cd $DirectoryToRunIn
    $env:PYTHONUNBUFFERED = 1
    Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
    .$PythonVENVPowershellActivateScript
    $timeout = 60*3
    # Get a list of all the current models first
    Write-Host "Getting list of Vehicle Models"
    Get-VehicleModels
    if ($LASTEXITCODE -eq 0) {     
        $models = Get-Content -Raw -Path "output/models.json" | ConvertFrom-Json       
        Write-Host "Getting list of Vehicle Inventory"
        foreach ($model in $models) {
            Write-Host "Sleeping $timeout seconds before next operation"
            Start-Sleep -Seconds $timeout
            # set environment variable that update_vehicles uses
            $env:MODEL = $model.modelCode
            # Update that models inventory
            Write-Host "Getting inventory for $env:MODEL "
            poetry run update_vehicles
            if ($LASTEXITCODE -ne 0) { 
                Write-Host "Error: Failed to get inventory for model $MODEL"
            }    
        }
        $curDate = Get-Date
        Write-Host "Vehicle Inventory search Completed" $curDate
        if ($uploadInventory -eq "upload") {
            if ($credentialsFileName -eq "") {
                $credentialsFileName = "inventory_credentials.json"
            }
            Write-Host "Uploading Inventory to Google Drive Started"
            py src\upload-files.py ".\output"  "Vehicle_Inventory"  $credentialsFileName
            if ($LASTEXITCODE -ne 0) { 
                Write-Host "Error: Failed to upload all inventory to google drive"
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

$uploadInventory = ""
if ($args.Count -ge 3) {
    $uploadInventory = $args[2]
}
$credentialsFileName = ""
if ($args.Count -ge 4) {
    $credentialsFileName = $args[3]
}

Get-VehicleInventoryForModels -DirectoryToRunIn $args[0] -PythonVENVPowershellActivateScript $args[1] -uploadInventory $uploadInventory -credentialsFileName $credentialsFileName