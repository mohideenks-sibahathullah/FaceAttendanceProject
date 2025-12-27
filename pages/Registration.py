import streamlit as st
import boto3
from PIL import Image
import io

# AWS Configuration
REGION = "ap-south-1"
COLLECTION_ID = "EmployeeFaces"
REGISTRY_TABLE = "EmployeeRegistry"

# Initialize AWS Clients
dynamodb = boto3.resource('dynamodb', region_name=REGION)
registry_table = dynamodb.Table(REGISTRY_TABLE)
rekognition = boto3.client('rekognition', region_name=REGION)

st.set_page_config(page_title="Self-Registration", page_icon="👤")

st.title("👤 Employee Self-Registration")
st.write("Enter your ID to unlock the biometric registration.")

# Step 1: Validation Check
emp_id = st.text_input("Enter your Employee ID (e.g., EMP2025):").strip()

if emp_id:
    try:
        # Check if ID exists in the Registry
        response = registry_table.get_item(Key={'EmployeeId': emp_id})
        
        if 'Item' in response:
            user_data = response['Item']
            st.success(f"✅ Verified: {user_data.get('Name')}")
            st.info(f"Department: {user_data.get('Department')}")
            
            # Step 2: Camera only unlocks for verified IDs
            img_file = st.camera_input("Capture your registration photo")

            if img_file:
                if st.button("Complete Biometric Link"):
                    image = Image.open(img_file)
                    img_byte_arr = io.BytesIO()
                    image.save(img_byte_arr, format='JPEG')
                    img_bytes = img_byte_arr.getvalue()

                    with st.spinner("Linking face to ID..."):
                        # Index the face and link to the verified ExternalImageId
                        rekognition.index_faces(
                            CollectionId=COLLECTION_ID,
                            Image={'Bytes': img_bytes},
                            ExternalImageId=emp_id,
                            DetectionAttributes=['ALL']
                        )
                    st.success(f"✅ Biometrics successfully linked to {emp_id}!")
                    st.balloons()
        else:
            # If ID is not in DynamoDB, they cannot register
            st.error("❌ This ID is not in our records. Please contact HR for onboarding.")
            
    except Exception as e:
        st.error(f"System Error: {e}")
