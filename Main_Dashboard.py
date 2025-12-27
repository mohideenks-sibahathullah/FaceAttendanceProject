import streamlit as st
import boto3
import pandas as pd
from datetime import datetime
from PIL import Image
import io

# AWS Configuration
REGION = "ap-south-1"
LOGS_TABLE = "AttendanceLogs"
REGISTRY_TABLE = "EmployeeRegistry"
COLLECTION_ID = "EmployeeFaces"

# Initialize AWS Clients
dynamodb = boto3.resource('dynamodb', region_name=REGION)
logs_table = dynamodb.Table(LOGS_TABLE)
registry_table = dynamodb.Table(REGISTRY_TABLE)
rekognition = boto3.client('rekognition', region_name=REGION)

st.set_page_config(page_title="HR Admin Portal", page_icon="🛡️", layout="wide")

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to:", ["Attendance Dashboard", "HR Onboarding"])

# --- PAGE 1: ATTENDANCE DASHBOARD ---
if page == "Attendance Dashboard":
    st.title("📈 HR Attendance Management Dashboard")
    st.markdown("---")

    def fetch_logs():
        try:
            response = logs_table.scan()
            data = response.get('Items', [])
            return pd.DataFrame(data) if data else pd.DataFrame(columns=["EmployeeId", "Timestamp", "ActionType"])
        except Exception as e:
            st.error(f"Error fetching logs: {e}")
            return pd.DataFrame()

    df_logs = fetch_logs()

    if not df_logs.empty:
        df_logs['Timestamp'] = pd.to_datetime(df_logs['Timestamp'])
        df_logs = df_logs.sort_values(by='Timestamp', ascending=False)
        
        col1, col2 = st.columns(2)
        col1.metric("Total Logs", len(df_logs))
        col2.metric("Last Activity", df_logs['Timestamp'].iloc[0].strftime('%H:%M:%S'))

        st.subheader("Recent Activity Logs")
        st.dataframe(df_logs, use_container_width=True)
    else:
        st.info("No attendance activity recorded yet.")

# --- PAGE 2: HR ONBOARDING (FOOLPROOF LOGIC) ---
elif page == "HR Onboarding":
    st.title("👤 New Employee Onboarding")
    st.write("Link biometric data to the master Employee Registry.")
    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        new_emp_id = st.text_input("Assign Employee ID (Primary Key):")
        new_emp_name = st.text_input("Full Name:")
        new_emp_dept = st.selectbox("Department:", ["IT", "HR", "Operations", "Sales"])
    
    with col2:
        onboard_img = st.camera_input("Capture Official Photo")

    if st.button("🚀 Complete Onboarding"):
        if new_emp_id and new_emp_name and onboard_img:
            try:
                # Image processing
                image = Image.open(onboard_img)
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='JPEG')
                img_bytes = img_byte_arr.getvalue()

                with st.spinner("Processing..."):
                    # 1. ATTEMPT Write to DynamoDB
                    db_response = registry_table.put_item(
                        Item={
                            'EmployeeId': str(new_emp_id).strip(), 
                            'Name': str(new_emp_name).strip(),
                            'Department': new_emp_dept,
                            'Status': 'Active',
                            'OnboardedDate': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                    )
                    st.info(f"✅ DB Status: {db_response['ResponseMetadata']['HTTPStatusCode']}")

                    # 2. ATTEMPT Index in Rekognition
                    rekognition.index_faces(
                        CollectionId=COLLECTION_ID,
                        Image={'Bytes': img_bytes},
                        ExternalImageId=str(new_emp_id).strip(),
                        DetectionAttributes=['ALL']
                    )
                    st.info("✅ Biometrics Linked.")

                st.success(f"✅ Registered: {new_emp_name}")
                st.balloons()
            except Exception as e:
                st.error(f"Onboarding halted: {str(e)}")
        else:
            st.warning("Please provide ID, Name, and a Photo.")

st.sidebar.markdown("---")
st.sidebar.info(f"Connected to ARN: {REGION}")