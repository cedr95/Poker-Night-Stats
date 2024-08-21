
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

st.set_page_config(page_title="Poker Night Stats", page_icon="bar_chart", layout="wide")

st.title(" :bar_chart: Poker Stats ")

#fl = st.file_uploader("Upload a file", type=(["csv","txt","xls","xlsx"])) file upload if needed. Not needed for this since googlesheets has the data
#if fl is not None:
#    filename = fl.name
#    st.write(filename)
 #   df = pd.read_csv(filename)

#else:
#    os.chdir()
 #   df = pd.read_csv() '''

#Date Selection

col1, col2 = st.columns((2))
df["Session Date"] = pd.to_datetime(df["Session Date"])

#Get min and max dates
startDate = pd.to_datetime(df["Session Date"]).min()
endDate = pd.to_datetime(df["Session Date"]).max()

with col1:
    date1 = pd.to_datetime(st.date_input("Start Date", startDate))

with col2:
    date2 = pd.to_datetime(st.date_input("Start Date", endDate))

df = df[(df["Session Date"] >= date1) & (df["Session Date"] <= date2)].copy()


# Filter Creation at the sidebar
st.sidebar.header("Choose your filter")
player = st.sidebar.multiselect("Pick the person", df["Name"].unique())
if not player:
    df2 = df.copy()
else:
    df2 = df[df["Name"].isin(player)]

session = st.sidebar.multiselect("Pick Your Session type", df["Session Type"].unique())
if not session:
   df3 = df2.copy()
else:
   df3 = df2[df2["Session Type"].isin(session)]



# Convert Net Earnings column into numerical float
df3['Net Earnings'] = df3['Net Earnings'].replace('[\$,]', '', regex=True).astype(float)

# Group by 'Name' and sum the 'Net Earnings'
earnings_by_player = df3.groupby('Name')['Net Earnings'].sum().reset_index()

# Calculate the total money in play (sum of absolute net earnings)
earnings_by_player['Abs Net Earnings'] = earnings_by_player['Net Earnings'].abs()
total_money = earnings_by_player['Abs Net Earnings'].sum()

highest_session_per_player = df3.loc[df3.groupby('Name')['Net Earnings'].idxmax()].sort_values(by= "Net Earnings", ascending = False)

# Calculate each player's percentage share
earnings_by_player['Percentage Share'] = (earnings_by_player['Abs Net Earnings'] / total_money) * 100

 # Determine if each session is a win or loss
df3['Win/Loss'] = df3['Net Earnings'].apply(lambda x: 'Win' if x > 0 else 'Loss')

    # Group by 'Name' and count the number of wins and losses
win_loss_count = df3.groupby(['Name', 'Win/Loss']).size().unstack(fill_value=0)

    # Calculate the win-loss ratio
win_loss_count['Win-Loss Ratio'] = win_loss_count['Win'] / win_loss_count['Loss']

    # Replace infinities and NaNs (from players with only wins or only losses)
win_loss_count['Win-Loss Ratio'] = win_loss_count['Win-Loss Ratio'].replace([float('inf'), -float('inf'), float('nan')], 0)

    # Merge this with the existing earnings_by_player DataFrame
earnings_by_player = earnings_by_player.merge(win_loss_count[['Win-Loss Ratio']], on='Name', how='left')

earnings_by_player = earnings_by_player.sort_values(by = "Win-Loss Ratio", ascending = False)

# Session Count
session_counts = df3.groupby('Name')['Session Date'].count().reset_index()
session_counts.columns = ['Name', 'Number of Sessions']


with col1:
    # Create a bar chart using Plotly
    fig = px.bar(earnings_by_player, x='Name', y='Net Earnings', title='Net Earnings by Player')
    st.plotly_chart(fig, use_container_width=True)


with col2:
    # Display the bar chart for the number of sessions
    fig_sessions = px.bar(session_counts, x='Name', y='Number of Sessions',
                     title='Number of Sessions Played by Each Player',
                     labels={'Name': 'Player', 'Number of Sessions': 'Number of Sessions'})
    st.plotly_chart(fig_sessions, use_container_width=True)

    st.subheader("Top Earning Sessions Per Player")
    st.dataframe(highest_session_per_player[['Name', 'Session Date', 'Net Earnings']], hide_index=True)

with col1:
   
    # Display the win-loss ratio in your Streamlit dashboard
    st.subheader("Win-Loss Ratio by Player")
    st.dataframe(earnings_by_player[['Name', 'Win-Loss Ratio']], hide_index=True)
        

# Time Series Analysis 
df3['Session Date'] = pd.to_datetime(df3['Session Date'])
df3['Week Performance'] = df3['Session Date'].dt.to_period('W').astype(str)

# Calculate the net earnings for each player per week
weekly_performance = df3.groupby(['Week Performance', 'Name'])['Net Earnings'].sum().unstack(fill_value=0)

# Create the heatmap
heatmap_fig = px.imshow(weekly_performance, 
                        labels=dict(x="Player", y="Week", color="Net Earnings"),
                        x=weekly_performance.columns, 
                        y=weekly_performance.index,
                        title="Weekly Performance Heatmap",
                        color_continuous_scale='Viridis')

heatmap_fig.update_layout(
    width=2800,  # Adjust width as needed
    height=1000,  # Adjust height as needed
    title_text='Weekly Performance Heatmap',
    title_x=0.5  # Center title
)

heatmap_fig.update_xaxes(tickangle=-45)


# Display the heatmap in Streamlit
st.subheader("Weekly Performance Heatmap")
st.plotly_chart(heatmap_fig, use_container_width=True)

# Total earnings contributed as pie chart

fig2 = px.pie(earnings_by_player, names='Name', values='Abs Net Earnings', title='Percentage of Total Money Contributed by Each Person')
st.plotly_chart(fig2, use_container_width=True)


# Calculate cumulative earnings
df3 = df3.sort_values(by=['Session Date'])
df3['Cumulative Earnings'] = df3.groupby('Name')['Net Earnings'].cumsum()

# Plot the cumulative earnings line chart
st.subheader("Cumulative Earnings Over Time")
cumulative_earnings_chart = px.line(df3, x='Session Date', y='Cumulative Earnings', color='Name',
                                     title='Cumulative Earnings Over Time', markers=True)
st.plotly_chart(cumulative_earnings_chart, use_container_width=True)