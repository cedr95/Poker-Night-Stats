
from googleapiclient.discovery import build
from google.oauth2 import service_account
import pandas as pd
import plotly.express as px
import streamlit as st
import plotly.graph_objects as go


# Authenticate and setup scope of project
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
#SERVICE_ACCOUNT_FILE = 'keys.json'


creds = None
creds = service_account.Credentials.from_service_account_info(
    st.secrets["google_credentials"], scopes=SCOPES
)

#creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE)

# The ID and range of a sample spreadsheet.
SAMPLE_SPREADSHEET_ID = "1JvAZOxj4qSp0NaU96tAX0qDB8Jk1p49VL8vlkxa43ck"
SAMPLE_RANGE_NAME = "Master Data!A1:D"

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

# Create a copy of the unfiltered DataFrame for leaderboard calculations

#st.logo(
 #   image=
 #   link="https://streamlit.io/gallery",
  #  icon_image=None
# )

unfiltered_df = df.copy()

# Convert Net Earnings column into numerical float
unfiltered_df['Net Earnings'] = pd.to_numeric(unfiltered_df['Net Earnings'].replace('[\$,]', '', regex=True), errors='coerce')

# Ensure 'Session Date' is in datetime format
unfiltered_df['Session Date'] = pd.to_datetime(unfiltered_df['Session Date'])

# Find the most recent session's earnings for each player
most_recent_sessions = (unfiltered_df
                        .sort_values(by=['Name', 'Session Date'], ascending=[True, False])
                        .groupby('Name')
                        .head(1)
                        .reset_index(drop=True))

# Calculate total earnings per player using the unfiltered DataFrame
unfiltered_earnings_by_player = unfiltered_df.groupby('Name')['Net Earnings'].sum().reset_index()

# Sort players by total net earnings to get the top 3 players
top_players = unfiltered_earnings_by_player.sort_values(by='Net Earnings', ascending=False).head(3)

# Merge the most recent session's earnings into the top players
top_3 = pd.merge(top_players, most_recent_sessions[['Name', 'Net Earnings']], on='Name', suffixes=('', '_Recent'))

# Calculate the delta as the most recent session's earnings
top_3['Delta'] = top_3['Net Earnings_Recent']  # Showing the most recent session's earnings

# Displaying the top 3 players in each column
st.header("Top 3 Players")

# Create 3 columns for displaying the metrics
col1, col2, col3 = st.columns(3)

# Assigning each player to a column
columns = [col1, col2, col3]
for i, (col, row) in enumerate(zip(columns, top_3.iterrows())):
    with col:
        st.metric(
            label=row[1]['Name'],  # row[1] accesses the row data since iterrows() returns (index, Series)
            value=f"${row[1]['Net Earnings']:.2f}", 
            delta=row[1]['Delta']  # Show delta as a formatted string with correct sign
        )



col1, col2 = st.columns((2)) # settiing up the 2 columns
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

net_earnings_by_player = earnings_by_player.sort_values(by = "Net Earnings", ascending= False)

# Session Count
session_counts = df3.groupby('Name')['Session Date'].count().reset_index()
session_counts.columns = ['Name', 'Number of Sessions']


with col1:
    # Create a bar chart using Plotly
    st.subheader("Net Earnings by Player")
    colors = ['green' if x > 0 else 'red' for x in net_earnings_by_player['Net Earnings']]
    fig = go.Figure(
    data=[
        go.Bar(
            x=net_earnings_by_player["Name"], 
            y=net_earnings_by_player["Net Earnings"], 
            marker_color=colors
        )
    ]
)
    fig.update_layout(
    title='',
    xaxis_title='Player',
    yaxis_title='Net Earnings'
)
    


    #fig = px.bar(net_earnings_by_player, x='Name', y='Net Earnings', title='Net Earnings by Player')
    st.plotly_chart(fig, use_container_width=True)
    



with col2:
   # Display the bar chart for the number of sessions
    st.subheader("Net Earnings by Player")
    st.dataframe(net_earnings_by_player[["Name","Net Earnings"]])



    st.subheader("Top Earning Sessions per Player")
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

st.subheader("Number of Sessions Played by Player")
fig_sessions = px.bar(session_counts, x='Name', y='Number of Sessions',
                     title='',
                     labels={'Name': 'Player', 'Number of Sessions': 'Number of Sessions'})
st.plotly_chart(fig_sessions, use_container_width=True)

# Create the heatmap
heatmap_fig = px.imshow(weekly_performance, 
                        labels=dict(x="Player", y="Week", color="Net Earnings"),
                        x=weekly_performance.columns, 
                        y=weekly_performance.index,
                        title="",
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
st.subheader("Percentage of Total Money Contributed by Each Person")
fig2 = px.pie(earnings_by_player, names='Name', values='Abs Net Earnings', title='')
st.plotly_chart(fig2, use_container_width=True)


# Calculate cumulative earnings
df3 = df3.sort_values(by=['Session Date'])
df3['Cumulative Earnings'] = df3.groupby('Name')['Net Earnings'].cumsum()

# Plot the cumulative earnings line chart
st.subheader("Cumulative Earnings Over Time")
cumulative_earnings_chart = px.line(df3, x='Session Date', y='Cumulative Earnings', color='Name',
                                     title='', markers=True)
st.plotly_chart(cumulative_earnings_chart, use_container_width=True)
with st.expander("Cumulative Earnings Data"):
         st.write(df3[["Cumulative Earnings","Name","Session Date"]].T)
         csv = df3[["Cumulative Earnings","Name","Session Date"]].to_csv(index = False).encode("utf-8")
         st.download_button("Download Data", data= csv, file_name= "Cumulative-Earnings.csv", mime = "text/csv")


