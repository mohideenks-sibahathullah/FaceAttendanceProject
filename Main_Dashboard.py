import streamlit as st
import boto3
import pandas as pd
from datetime import datetime

# AWS Configuration
REGION = "ap-south-1"
LOGS_TABLE = "AttendanceLogs"

# Initialize AWS Clients
dynamodb = boto3.resource('dynamodb', region_name=REGION)
table = dynamodb.Table(LOGS_TABLE)

st.set_page_config(page_title="HR Attendance Dashboard", page_icon="📈", layout="wide")

st.title("📈 HR Attendance Management Dashboard")
st.markdown("---")

# Sidebar for Refresh and Stats
st.sidebar.header("Dashboard Controls")
if st.sidebar.button("🔄 Refresh Data"):
    st.rerun()

# 1. Fetch Logs from DynamoDB
def fetch_attendance_logs():
    try:
        response = table.scan()
        data = response.get('Items', [])
        if not data:
            return pd.DataFrame(columns=["EmployeeId", "Timestamp", "ActionType"])
        
        df = pd.DataFrame(data)
        # Convert timestamp strings to datetime objects for sorting
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])
        return df.sort_values(by='Timestamp', ascending=False)
    except Exception as e:
        st.error(f"Error fetching logs: {e}")
        return pd.DataFrame()

df_logs = fetch_attendance_logs()

# 2. Key Metrics Display
if not df_logs.empty:
    col1, col2, col3 = st.columns(3)
    
    # Total unique employees logged today
    today = datetime.now().date()
    today_logs = df_logs[df_logs['Timestamp'].dt.date == today]
    active_now = today_logs.drop_duplicates('EmployeeId').shape[0]
    
    col1.metric("Active Employees (Today)", active_now)
    col2.metric("Total Logs (All Time)", len(df_logs))
    col3.metric("Last Activity", df_logs['Timestamp'].iloc[0].strftime('%H:%M:%S'))

# 3. Attendance Table
st.subheader("Recent Activity")
if df_logs.empty:
    st.info("No attendance logs found in DynamoDB.")
else:
    # Formatting for display
    display_df = df_logs.copy()
    display_df['Timestamp'] = display_df['Timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
    st.dataframe(display_df, use_container_width=True)

# 4. Filter by Employee ID
st.sidebar.markdown("---")
search_id = st.sidebar.text_input("Search Employee History (ID):")
if search_id:
    st.subheader(f"History for: {search_id}")
    filtered_df = df_logs[df_logs['EmployeeId'] == search_id]
    st.table(filtered_df[['Timestamp', 'ActionType']])

# Sidebar Navigation Note
st.sidebar.info("Use the sidebar to navigate to the 'Registration' page for existing employees.")