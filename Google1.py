import pickle
import os
from google_auth_oauthlib.flow import Flow, InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.auth.transport.requests import Request
import json

def Initiate_Service(client_secret_data, api_name, api_version, *scopes, cred):
    # print(client_secret_file, api_name, api_version, scopes, sep='-')
    print(client_secret_data, api_name, api_version, scopes, sep='-')
    # CLIENT_SECRET_FILE = client_secret_file
    if isinstance(client_secret_data, str):
        client_secret_data = json.loads(client_secret_data)
    API_SERVICE_NAME = api_name
    API_VERSION = api_version
    SCOPES = [scope for scope in scopes[0]]
    print(SCOPES)

    if not cred or not cred.valid:
        if cred and cred.expired and cred.refresh_token:
            cred.refresh(Request())
        else:
            pickle_file = f'token_{API_SERVICE_NAME}_{API_VERSION}.pickle'
            auth_url, _ = InstalledAppFlow.authorization_url()
