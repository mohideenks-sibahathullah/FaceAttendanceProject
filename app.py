import streamlit as st
import boto3
import pandas as pd
from datetime import datetime
from io import BytesIO

# --- CONFIGURATION ---
st.set_page_config(page_title="Enterprise Employee Tracking", page_icon="🏢", layout="wide")

# AWS Constants
REGION = "ap-south-1"
PROFILE_TABLE = "EmployeeProfile"
LOGS_TABLE = "AttendanceLogs"
COLLECTION_ID = "EmployeeFaces"

# Initialize AWS Clients
rek_client = boto3.client('rekognition', region_name=REGION)
dynamodb = boto3.resource('dynamodb', region_name=REGION)
profile_db = dynamodb.Table(PROFILE_TABLE)
logs_db = dynamodb.Table(LOGS_TABLE)

# --- CACHE: CONVERT DF TO CSV ---
@st.cache_data
def convert_df(df):
    return df.to_csv(index=False).encode('utf-8')

# --- NAVIGATION ---
page = st.sidebar.radio("Main Menu", ["📸 Mark Attendance", "👤 HR Onboarding", "📊 Admin Dashboard"])

# --- PAGE 1: HR ONBOARDING ---
if page == "👤 HR Onboarding":
    st.title("Employee Registration Portal")
    st.info("Enroll new employees into the biometric database.")
    
    with st.form("reg_form"):
        c1, c2 = st.columns(2)
        with c1:
            emp_id = st.text_input("Employee ID (Unique)")
            f_name = st.text_input("First Name")
            l_name = st.text_input("Last Name")
        with c2:
            city = st.text_input("City")
            state = st.text_input("State")
            pin = st.text_input("Pin Code")
        
        photo = st.camera_input("Enrollment Photo")
        submit = st.form_submit_button("Register New Employee")

    if submit and emp_id and photo:
        try:
            profile_db.put_item(Item={
                'EmployeeId': emp_id, 'FirstName': f_name, 'LastName': l_name,
                'City': city, 'State': state, 'Pincode': pin
            })
            rek_client.index_faces(
                CollectionId=COLLECTION_ID, Image={'Bytes': photo.getvalue()},
                ExternalImageId=emp_id, MaxFaces=1
            )
            st.success(f"✅ Success! {f_name} is now registered.")
        except Exception as e:
            st.error(f"Error: {str(e)}")

# --- PAGE 2: ATTENDANCE (FIXED BUG WITH MANUAL BUTTONS) ---
elif page == "📸 Mark Attendance":
    st.title("Smart Attendance Terminal")
    st.write("Capture your face and select your action (Login/Logout).")
    
    img = st.camera_input("Scan Face")
    col_in, col_out = st.columns(2)
    
    if img:
        try:
            search = rek_client.search_faces_by_image(
                CollectionId=COLLECTION_ID, Image={'Bytes': img.getvalue()},
                MaxFaces=1, FaceMatchThreshold=90
            )
            
            if not search.get('FaceMatches'):
                st.error("❌ Identity Not Found. Please register via HR first.")
            else:
                eid = search['FaceMatches'][0]['Face']['ExternalImageId']
                person = profile_db.get_item(Key={'EmployeeId': eid}).get('Item', {})
                name = person.get('FirstName', 'Employee')
                
                st.info(f"Identified: **{name}** (ID: {eid})")

                # Manual Buttons prevent the 'Auto-Toggle' bug
                with col_in:
                    if st.button("🚀 Punch LOGIN", use_container_width=True):
                        logs_db.put_item(Item={
                            'EmployeeId': eid,
                            'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'ActionType': 'LOGIN'
                        })
                        st.success(f"Welcome, {name}! LOGIN recorded.")
                        st.balloons()

                with col_out:
                    if st.button("🏠 Punch LOGOUT", use_container_width=True):
                        logs_db.put_item(Item={
                            'EmployeeId': eid,
                            'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'ActionType': 'LOGOUT'
                        })
                        st.warning(f"Goodbye, {name}! LOGOUT recorded.")

        except Exception as e:
            st.error(f"System Error: {str(e)}")

# --- PAGE 3: ADMIN DASHBOARD (DOWNLOAD REPORT) ---
elif page == "📊 Admin Dashboard":
    st.title("Attendance Records & Reports")
    
    if st.button("🔄 Refresh Data"):
        recs = logs_db.scan().get('Items', [])
        if recs:
            df = pd.DataFrame(recs)
            # Reorder columns for professional look
            df = df[['EmployeeId', 'Timestamp', 'ActionType']]
            st.dataframe(df, use_container_width=True)
            
            # Export to CSV feature
            csv = convert_df(df)
            st.download_button(
                label="📥 Download Attendance Report (CSV)",
                data=csv,
                file_name=f"Attendance_Report_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.info("No records found in the database.")
