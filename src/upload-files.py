import sys
import json
import os
from pathlib import Path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaFileUpload
import mimetypes

# If modifying these scopes, delete the file inventory_token.json.
SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly',
          'https://www.googleapis.com/auth/drive.file']

def get_credentials(credentialsFileName):
    global authenticationAuthorizationPath
    global resultsFileName
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    tokenFileName = 'inventory_token.json'
    if os.path.exists(tokenFileName):
        creds = Credentials.from_authorized_user_file(tokenFileName, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing authorization/authentication token")
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                Path(credentialsFileName), SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(tokenFileName, 'w') as token:
            token.write(creds.to_json())
    return creds


def get_gdrive_service(credentialsFileName):
    creds = get_credentials(credentialsFileName)
    return build('drive', 'v3', credentials= creds)

def findGoogleDriveFolder(service, name):
    # find the first level that has that a folder with that name and return that folder Id, name, type as a tuple or
    # None if not found
    filetype = "application/vnd.google-apps.folder"
    #filetype = "folder"
    query=f"mimeType='{filetype}' and name='{name}'"
    #print("query is", query)
    result = None
    page_token = None    
    # pylint: disable=maybe-no-member
    response = (
        service.files()
        .list(
            q=query,
            spaces="drive",
            fields="nextPageToken, files(id, name, mimeType)",
            pageToken=page_token,
        )
        .execute()
        )
    for file in response.get("files", []):
        result = (file["id"], file["name"], file["mimeType"])
        break
    return result

def fileIsInDriveFolder(service, folder_id, filename):
    # returns the file id of the file if it is in the drive folder, otherwise blank
    response = service.files().list(pageSize=1,fields="files(id, name, mimeType)",q="'" + folder_id + "' in parents and trashed=false and name='" + filename + "'" ).execute()
    results = response.get("files", [])
    #print("fileIsInDriveFolder results", results)
    if results:
        return results[0]["id"]
    else:
        return ""

def upload_inventory_files(directory, googleDriveFolderName, credentialsFileName = "inventory_credentials.json", onlyForModel = ""):
    """
    uploads the vehicle inventory files and logs from directory to the googleDriveFolderName 
    """
    # authenticate account
    service = get_gdrive_service(credentialsFileName)
    
    # get inventory folder Id
    folderName = googleDriveFolderName
    info = findGoogleDriveFolder(service, folderName)
    if info is None:
        print("Error:  Google Drive Folder", folderName, "does not exist")
        return
    folder_id = info[0]
    print("Google Drive Folder", folderName, "ID is", folder_id)
    # create or replace the files in that folder
    files = os.listdir( directory )
    for filename in files:
        # when onlyForModel is blank  we want to upload all files of the form
        # *.csv  (gets the current and sold ones), *_Lastraw.parquet, *_Sold_raw.parquet, *_LastStatusInfo.json
        # "InventoryRunlog.txt", "models.json", "models_raw.json"
        # when onlyForModel is not blank, and thus specifies a model we want to upload files of the form
        # <onlyForModel>.csv ,  <onlyForModel>_*_Sold.csv, <onlyForModel>_Lastraw.parquet, <onlyForModel>_*_Sold_raw.parquet, , <onlyForModel>_LastStatusInfo.json
        if  (
              ( (onlyForModel == "") and (os.path.isfile(Path(directory + "/" + filename))) and 
                (  filename.endswith(".csv") or 
                   filename.endswith("_Lastraw.parquet") or 
                   filename.endswith("_Sold_raw.parquet") or
                   filename.endswith("_LastStatusInfo.json") or 
                   filename.endswith("_ChangeHistory.parquet") or 
                   (filename in ["InventoryRunlog.txt", "models.json", "models_raw.json"] )
                )
              ) 
            or
              ( (onlyForModel != "") and (os.path.isfile(Path(directory + "/" + filename))) and 
                (  (filename.endswith("_Sold.csv") and filename.startswith(onlyForModel + "_")  ) or 
                   (filename.endswith("_Sold_raw.parquet")  and filename.startswith(onlyForModel + "_")) or 
                   (filename in [onlyForModel + ".csv", onlyForModel + "_Lastraw.parquet", onlyForModel + "_LastStatusInfo.json", 
                                 onlyForModel + "_ChangeHistory.csv", onlyForModel + "_ChangeHistory.parquet"]
                   )
                )
              ) 
            ):
            fileid = fileIsInDriveFolder(service, folder_id, filename)
            if fileid:
                # filename already exists in that google drive folder
                file_metadata = {}
                # update the file
                media = MediaFileUpload(Path(directory + "/" + filename), resumable=True)
                fileInfo = service.files().update(fileId=fileid, body=file_metadata, media_body=media, fields="id").execute()
                print("Replaced existing google drive file", filename, "having ID", fileid )
            else:
                # first, define file metadata, such as the name and the parent folder ID
                file_metadata = {
                    "name": filename,
                    "parents": [folder_id]
                }
                # create that file in the google drive folder
                media = MediaFileUpload(Path(directory + "/" + filename), resumable=True)
                file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
                print("File:", filename, "with ID", file.get("id") , "did not exist in drive folder and was created/uploaded")

if __name__ == '__main__':
    directory = sys.argv[1]
    googleDriveFolderName = sys.argv[2]
    credentialsFileName = sys.argv[3]
    onlyForModel = ""
    if len(sys.argv) > 4:
        onlyForModel = sys.argv[4]
    upload_inventory_files(directory, googleDriveFolderName, credentialsFileName, onlyForModel)