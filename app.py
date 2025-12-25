import streamlit as st
import boto3
from datetime import datetime

# CONFIGURATION
REGION = "ap-south-1"
COLLECTION_ID = "StudentAttendanceCollection"
TABLE_NAME = "StudentAttendanceLog"

# AWS Clients
rek_client = boto3.client('rekognition', region_name=REGION)
db_client = boto3.resource('dynamodb', region_name=REGION)
table = db_client.Table(TABLE_NAME)

st.title("Cloud Face Attendance System")
st.write("M.Sc. Computer Science - Final Project")

# Live Camera Input
img_file_buffer = st.camera_input("Take a picture to mark attendance")

if img_file_buffer is not None:
    # Convert image to bytes for Rekognition
    bytes_data = img_file_buffer.getvalue()
    
    with st.spinner("Validating Face and Marking Attendance..."):
        try:
            # 1. Validation: MASK & QUALITY
            # We use DetectFaces with 'ALL' to get both quality and occlusion data
            detect_resp = rek_client.detect_faces(Image={'Bytes': bytes_data}, Attributes=['ALL'])
            
            if not detect_resp['FaceDetails']:
                st.error("No face detected. Please face the camera.")
            else:
                face = detect_resp['FaceDetails'][0]
                # Custom Validation Logic
                if face['FaceOccluded']['Value']:
                    st.warning("FAILED: Please remove your face mask to mark attendance.")
                elif face['Quality']['Sharpness'] < 30:
                    st.warning("FAILED: Image too blurry. Possibly a spoof or billboard.")
                else:
                    # 2. Recognition: Search in Collection
                    search_resp = rek_client.search_faces_by_image(
                        CollectionId=COLLECTION_ID,
                        Image={'Bytes': bytes_data},
                        MaxFaces=1,
                        FaceMatchThreshold=90
                    )

                    if search_resp['FaceMatches']:
                        student_id = search_resp['FaceMatches'][0]['Face']['ExternalImageId']
                        # LOG TO DATABASE
                        table.put_item(Item={
                            'StudentId': student_id,
                            'Timestamp': datetime.now().isoformat(),
                            'Status': 'Present'
                        })
                        st.success(f"SUCCESS: Attendance logged for {student_id}")
                    else:
                        st.error("FAILED: Identity not recognized. Please register first.")

        except Exception as e:
            st.error(f"Error: {str(e)}")

# --- ADD THIS TO THE BOTTOM OF app.py ---
st.divider()
st.subheader("Today's Attendance Log")

# Button to manually refresh the logs
if st.button("Refresh Log"):
    try:
        # Scan the table to get all records
        response = table.scan()
        items = response.get('Items', [])
        
        if items:
            # Sort by timestamp (latest first)
            sorted_items = sorted(items, key=lambda x: x['Timestamp'], reverse=True)
            # Display as a clean table
            st.table(sorted_items)
        else:
            st.info("No attendance records found for today.")
            
    except Exception as e:
        st.error(f"Error fetching logs: {str(e)}")
