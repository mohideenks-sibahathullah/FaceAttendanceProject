import streamlit as st
import boto3
import pandas as pd
from datetime import datetime

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

# --- NAVIGATION ---
page = st.sidebar.radio("Main Menu", ["📸 Mark Attendance", "👤 HR Onboarding", "📊 Admin Dashboard"])

# --- PAGE 1: HR ONBOARDING ---
if page == "👤 HR Onboarding":
    st.title("Employee Registration Portal")
    with st.form("reg_form"):
        c1, c2 = st.columns(2)
        with c1:
            emp_id = st.text_input("Employee ID")
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
            st.success(f"✅ Registered: {f_name}")
        except Exception as e:
            st.error(f"Error: {str(e)}")

# --- PAGE 2: ATTENDANCE (ONE-STEP PROCESS) ---
elif page == "📸 Mark Attendance":
    st.title("Smart Attendance Terminal")
    st.info("Stand in front of the camera and click your action button.")
    
    # The camera acts as a live feed
    img = st.camera_input("Camera Feed", label_visibility="collapsed")
    
    col_in, col_out = st.columns(2)
    
    # This function handles the "One-Step" logic
    def handle_click(action_type):
        if img:
            try:
                # 1. Identify the person from the current frame
                search = rek_client.search_faces_by_image(
                    CollectionId=COLLECTION_ID, 
                    Image={'Bytes': img.getvalue()},
                    MaxFaces=1, 
                    FaceMatchThreshold=90
                )
                
                if not search.get('FaceMatches'):
                    st.error("❌ Identity Not Found. Please see HR.")
                else:
                    eid = search['FaceMatches'][0]['Face']['ExternalImageId']
                    person = profile_db.get_item(Key={'EmployeeId': eid}).get('Item', {})
                    name = person.get('FirstName', 'Employee')
                    
                    # 2. Record the Attendance
                    logs_db.put_item(Item={
                        'EmployeeId': eid,
                        'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'ActionType': action_type
                    })
                    
                    if action_type == "LOGIN":
                        st.success(f"✅ Welcome, {name}! Clocked In.")
                        st.balloons()
                    else:
                        st.warning(f"✅ Goodbye, {name}! Clocked Out.")
            except Exception as e:
                st.error(f"System Error: {str(e)}")
        else:
            st.error("Please ensure your face is visible in the camera feed before clicking.")

    with col_in:
        if st.button("🚀 CLOCK IN", use_container_width=True, type="primary"):
            handle_click("LOGIN")

    with col_out:
        if st.button("🏠 CLOCK OUT", use_container_width=True):
            handle_click("LOGOUT")

# --- PAGE 3: ADMIN DASHBOARD ---
elif page == "📊 Admin Dashboard":
    st.title("Attendance Records")
    if st.button("Refresh Data"):
        recs = logs_db.scan().get('Items', [])
        if recs:
            df = pd.DataFrame(recs)
            st.dataframe(df[['EmployeeId', 'Timestamp', 'ActionType']], use_container_width=True)
