
from googleapiclient.discovery import build
from google.oauth2 import service_account
import pandas as pd
import plotly.express as px
import streamlit as st


# Authenticate and setup scope of project
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
SERVICE_ACCOUNT_FILE = 'keys.json'


creds = None
creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes = SCOPES)

# The ID and range of a sample spreadsheet.
SAMPLE_SPREADSHEET_ID = "1JvAZOxj4qSp0NaU96tAX0qDB8Jk1p49VL8vlkxa43ck"
SAMPLE_RANGE_NAME = "Master Data!A1:D500"

service = build("sheets", "v4", credentials=creds)

 # Call the Sheets API
sheet = service.spreadsheets()
result = ( sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID, range=SAMPLE_RANGE_NAME).execute())
values = result.get('values', [])

if values:
    df = pd.DataFrame(values[1:], columns=values[0]) # values[1:] skips first row in this case headers, cloumns=values[0] is using the headers as cloumn names
    print(df)
else:
    print("No data")

player_earnings = df.groupby('Name')['Net Earnings'].sum().reset_index()
fig = px.bar(player_earnings, x='Name', y='Net Earnings', title='Total Net Earnings by Player')
st.plotly_chart(fig)