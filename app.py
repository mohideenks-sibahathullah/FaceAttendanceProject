import streamlit as st
import boto3
import cv2
import numpy as np
from datetime import datetime
from decimal import Decimal

# --- CONFIGURATION ---
st.set_page_config(page_title="Employee Tracking System", page_icon="🏢", layout="wide")
st.title("🏢 Employee Attendance & Tracking System")

# AWS Constants
REGION = "ap-south-1"
TABLE_NAME = "StudentAttendanceLog"
COLLECTION_ID = "EmployeeFaces"

# Initialize AWS Clients
rek_client = boto3.client('rekognition', region_name=REGION)
dynamodb = boto3.resource('dynamodb', region_name=REGION)
table = dynamodb.Table(TABLE_NAME)

# --- APP LOGIC ---

def process_attendance(image_bytes):
    try:
        # 1. AI Face Search in Collection
        response = rek_client.search_faces_by_image(
            CollectionId=COLLECTION_ID,
            Image={'Bytes': image_bytes},
            MaxFaces=1,
            FaceMatchThreshold=90
        )
        
        face_matches = response.get('FaceMatches', [])
        
        if not face_matches:
            st.error("❌ Identity Not Recognized. Please Register first.")
            return

        # Extract Employee ID (Stored as ExternalImageId during registration)
        employee_id = face_matches[0]['Face']['ExternalImageId']
        confidence = face_matches[0]['Similarity']
        
        # 2. Check Today's History (Logic for Login/Logout)
        today_date = datetime.now().strftime('%Y-%m-%d')
        
        # Query database for this specific employee
        history = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('StudentId').eq(employee_id)
        )
        
        # Filter for today's entries
        today_entries = [item for item in history['Items'] if item['Timestamp'].startswith(today_date)]
        
        if len(today_entries) == 0:
            action = "LOGIN"
        elif len(today_entries) == 1:
            action = "LOGOUT"
        else:
            st.warning(f"⚠️ Employee {employee_id} has already completed their shift (Login & Logout) for today.")
            return

        # 3. Log the Event
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        table.put_item(Item={
            'StudentId': employee_id,
            'Timestamp': timestamp,
            'Action': action,
            'Confidence': Decimal(str(round(confidence, 2)))
        })
        
        st.success(f"✅ {action} Successful for Employee: {employee_id} at {timestamp}")

    except Exception as e:
        st.error(f"Error: {str(e)}")

# --- USER INTERFACE ---

col1, col2 = st.columns(2)

with col1:
    st.header("📸 Biometric Capture")
    img_file = st.camera_input("Position your face in the center")
    
    if img_file:
        bytes_data = img_file.getvalue()
        process_attendance(bytes_data)

with col2:
    st.header("📊 Today's Attendance Log")
    if st.button("🔄 Refresh Dashboard"):
        try:
            # For demonstration/Admin view, we scan the whole table
            resp = table.scan()
            items = resp.get('Items', [])
            if items:
                # Sort by timestamp latest first
                items = sorted(items, key=lambda x: x['Timestamp'], reverse=True)
                st.table(items)
            else:
                st.info("No records found.")
        except Exception as e:
            st.error(f"Table Read Error: {e}")

st.info("💡 Note: This system automatically detects if you are logging in or out based on your daily history.")
