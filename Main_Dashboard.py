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
        st.dataframe(df_logs, use_container_width=True)
    else:
        st.info("No activity recorded yet.")

# --- PAGE 2: HR ONBOARDING (THE FOOLPROOF STEP) ---
elif page == "HR Onboarding":
    st.title("👤 New Employee Onboarding")
    st.write("Adding to Registry: " + REGISTRY_TABLE)
    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        new_emp_id = st.text_input("Assign Employee ID:")
        new_emp_name = st.text_input("Full Name:")
        new_emp_dept = st.selectbox("Department:", ["IT", "HR", "Operations", "Sales"])
    
    with col2:
        onboard_img = st.camera_input("Capture Official Photo")

    if st.button("🚀 Complete Onboarding"):
        if new_emp_id and new_emp_name and onboard_img:
            try:
                # 1. Image preparation
                image = Image.open(onboard_img)
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='JPEG')
                img_bytes = img_byte_arr.getvalue()

                with st.spinner("Writing to AWS..."):
                    # 2. EXPLICIT WRITE TO DYNAMODB
                    db_response = registry_table.put_item(
                        Item={
                            'EmployeeId': str(new_emp_id).strip(),
                            'Name': str(new_emp_name).strip(),
                            'Department': new_emp_dept,
                            'Status': 'Active',
                            'OnboardedDate': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                    )
                    
                    # DEBUG OUTPUTS
                    st.write(f"DEBUG: AWS Request ID: {db_response['ResponseMetadata']['RequestId']}")
                    st.success(f"DEBUG: HTTP Status: {db_response['ResponseMetadata']['HTTPStatusCode']}")

                    # 3. INDEX IN REKOGNITION
                    rek_response = rekognition.index_faces(
                        CollectionId=COLLECTION_ID,
                        Image={'Bytes': img_bytes},
                        ExternalImageId=str(new_emp_id).strip(),
                        DetectionAttributes=['ALL']
                    )
                    st.info(f"DEBUG: Face ID Indexed: {rek_response['FaceRecords'][0]['Face']['FaceId']}")

                st.success(f"✅ Onboarding Complete for {new_emp_id}!")
                st.balloons()
            except Exception as e:
                st.error(f"❌ CRITICAL ERROR: {str(e)}")
        else:
            st.warning("Please fill all fields.")
