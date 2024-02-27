from hmac import new
import pickle
import os
from google_auth_oauthlib.flow import Flow, InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError
import streamlit as st
from streamlit_gsheets import GSheetsConnection


def Create_Service(client_secret_file, api_name, api_version, *scopes):
    CLIENT_SECRET_FILE = client_secret_file
    API_SERVICE_NAME = api_name
    API_VERSION = api_version
    SCOPES = [scope for scope in scopes[0]]

    conn = st.connection("gsheets", type=GSheetsConnection)

    df = conn.read(
        worksheet="Authtoken", 
        usecols=[0, 1],
        header=None )

    auth_tokens = {row[0]: row[1] for index, row in df.iterrows()}
    
    # client_id = auth_tokens["client_id"]
    # client_secret = auth_tokens["client_secret"]
    # refresh_token = auth_tokens["refresh_token"]
    # token_uri = auth_tokens["token_uri"]
    # scopes = auth_tokens["SCOPES"]
    client_id = auth_tokens.get("client_id", "")
    client_secret = auth_tokens.get("client_secret", "")
    refresh_token = auth_tokens.get("refresh_token", "")
    token_uri = auth_tokens.get("token_uri", "")
    scopes = auth_tokens.get("SCOPES", "")
    
    cred = None
    # client_id = st.secrets["AuthToken"]["client_id"]
    # client_secret = st.secrets["AuthToken"]["client_secret"]
    # refresh_token = st.secrets["AuthToken"]["refresh_token"]
    # token_uri = "https://oauth2.googleapis.com/token"  # Default token URI for Google

    # Create a Credentials object
    cred = Credentials.from_authorized_user_info({
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "token_uri": token_uri
    }, SCOPES)


    if not cred or not cred.valid:
        if cred and cred.expired and cred.refresh_token:
            cred.refresh(Request())
            print("token refreshed")
            new_credentials = {
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": cred.refresh_token,
                "token_uri": token_uri
            }
            conn.update(worksheet="Authtoken",
                        data = new_credentials)
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            cred = flow.run_local_server()
            print("token recreated")
            # cred1 = flow.redirect_uri()

        # with open(pickle_file, 'wb') as token:
            # pickle.dump(cred, token)
        # with open("token.json", "w") as token:
        #     token.write(cred.to_json())
    try:
        service = build(API_SERVICE_NAME, API_VERSION, credentials=cred)
        print(API_SERVICE_NAME, 'Cred valid. Service created successfully')
        return service
    except Exception as e:
        print('Unable to connect.')
        print(e)
        return None

