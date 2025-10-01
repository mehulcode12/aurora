# main.py or routes/auth.py
from fastapi import FastAPI, HTTPException, status, Depends, File, UploadFile, Form, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import redis
import firebase_admin
from firebase_admin import credentials, firestore, db, initialize_app, auth
from typing import List, Optional
import os
from dotenv import load_dotenv
from jose import JWTError, jwt
from datetime import datetime, timedelta
from groq import Groq
import PyPDF2
import docx
import io
import requests



load_dotenv()

app = FastAPI()
security = HTTPBearer()

# Initialize Firebase
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': os.getenv('FIREBASE_DATABASE_URL')
})
firestore_db  = firestore.client()

# Firebase Web API Key
FIREBASE_WEB_API_KEY = os.getenv('FIREBASE_WEB_API_KEY')

# JWT Configuration
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here-change-in-production')
ALGORITHM = "HS256"
TEMP_TOKEN_EXPIRE_MINUTES = 15
ACCESS_TOKEN_EXPIRE_HOURS = 24

# Initialize Groq
groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))

# JWT Configuration
SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = "HS256"

# SMTP Configuration
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_EMAIL = os.getenv('SMTP_EMAIL')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')

# Initialize Redis client
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    db=0,
    decode_responses=True
)

# Test Redis connection
try:
    redis_client.ping()
    print("Connected to Redis successfully")
except redis.ConnectionError:
    print("Failed to connect to Redis")
    print("\n---------------------------------------------------------------------------------")
    print("Run Redis Server > cd C:\Redis-x64-3.0.504 && redis-server.exe redis.windows.conf")
    print("---------------------------------------------------------------------------------\n")


#------------------------------------------------------------------------------------------
#          1. GET /get-otp endpoint
#------------------------------------------------------------------------------------------


# Pydantic Models
class EmailRequest(BaseModel):
    email: EmailStr

class OTPResponse(BaseModel):
    success: bool
    message: str

# Helper Functions
def generate_otp() -> str:
    """Generate a 6-digit OTP"""
    return ''.join([str(random.randint(0, 9)) for _ in range(6)])

def send_otp_email(recipient_email: str, otp: str) -> bool:
    """Send OTP via SMTP email"""
    try:
        # Create message
        message = MIMEMultipart("alternative")
        message["Subject"] = "Your OTP for Aurora Admin Registration"
        message["From"] = SMTP_EMAIL
        message["To"] = recipient_email
        
        # Email body
        text = f"""
        Hello,
        
        Your OTP for Aurora Admin registration is: {otp}
        
        This OTP will expire in 10 minutes.
        
        If you did not request this OTP, please ignore this email.
        
        Best regards,
        Aurora Team
        """
        
        html = f"""
        <html>
          <body>
            <h2>Aurora Admin Registration</h2>
            <p>Hello,</p>
            <p>Your OTP for Aurora Admin registration is:</p>
            <h1 style="color: #4CAF50; font-size: 32px; letter-spacing: 5px;">{otp}</h1>
            <p>This OTP will expire in <strong>10 minutes</strong>.</p>
            <p>If you did not request this OTP, please ignore this email.</p>
            <br>
            <p>Best regards,<br>Aurora Team</p>
          </body>
        </html>
        """
        
        # Attach both plain text and HTML versions
        part1 = MIMEText(text, "plain")
        part2 = MIMEText(html, "html")
        message.attach(part1)
        message.attach(part2)
        
        # Connect to SMTP server and send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # Secure the connection
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, recipient_email, message.as_string())
        
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False

def check_email_exists(email: str) -> bool:
    """Check if email exists in Firestore admins collection"""
    try:
        admins_ref = firestore_db .collection('admins')
        query = admins_ref.where('email', '==', email).limit(1).get()
        return len(query) > 0
    except Exception as e:
        print(f"Error checking email in Firestore: {str(e)}")
        raise

def store_otp_in_redis(email: str, otp: str, ttl: int = 600) -> bool:
    """Store OTP in Redis with TTL (default 10 minutes = 600 seconds)"""
    try:
        redis_client.setex(f"otp:{email}", ttl, otp)
        return True
    except Exception as e:
        print(f"Error storing OTP in Redis: {str(e)}")
        return False

# API Endpoint
@app.post("/get-otp", response_model=OTPResponse, status_code=status.HTTP_200_OK)
async def get_otp(request: EmailRequest):
    """
    Generate and send OTP to user's email
    
    - **email**: User's email address
    
    Returns success message if OTP sent successfully
    """
    try:
        email = request.email.lower().strip()
        
        # Step 1: Check if email already exists in Firestore admins collection
        if check_email_exists(email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Step 2: Generate 6-digit OTP
        otp = generate_otp()
        print(f"Generated OTP for {email}: {otp}")  # For debugging, remove in production
        
        # Step 3: Store OTP in Redis with 10-minute TTL
        if not store_otp_in_redis(email, otp, ttl=600):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to store OTP. Please try again."
            )
        
        # Step 4: Send OTP via email using SMTP
        if not send_otp_email(email, otp):
            # Clean up Redis if email fails
            redis_client.delete(f"otp:{email}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send OTP email. Please check your email address."
            )
        
        # Step 5: Return success response
        return OTPResponse(
            success=True,
            message="OTP sent to email"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error in get_otp: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )

# Additional utility endpoint to check Redis connection
@app.get("/health/redis")
async def check_redis():
    """Health check endpoint for Redis connection"""
    try:
        redis_client.ping()
        return {"status": "Redis is connected"}
    except redis.ConnectionError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis is not connected"
        )


#------------------------------------------------------------------------------------------
#          2. POST /verify-otp endpoint
#------------------------------------------------------------------------------------------


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str

class VerifyOTPResponse(BaseModel):
    success: bool
    temp_token: str
    expires_in: int

def create_temp_token(email: str) -> str:
    """Generate temporary JWT token valid for 15 minutes"""
    expire = datetime.utcnow() + timedelta(minutes=TEMP_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": email,
        "type": "temp",
        "exp": expire,
        "iat": datetime.utcnow()
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token

@app.post("/verify-otp", response_model=VerifyOTPResponse, status_code=status.HTTP_200_OK)
async def verify_otp(request: VerifyOTPRequest):
    """
    Verify OTP and generate temporary token
    
    - **email**: User's email address
    - **otp**: 6-digit OTP received via email
    """
    try:
        email = request.email.lower().strip()
        otp = request.otp.strip()
        
        stored_otp = redis_client.get(f"otp:{email}")
        
        if not stored_otp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP expired or invalid. Please request a new OTP."
            )
        
        if stored_otp != otp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OTP. Please check and try again."
            )
        
        redis_client.delete(f"otp:{email}")
        
        temp_token = create_temp_token(email)
        
        return VerifyOTPResponse(
            success=True,
            temp_token=temp_token,
            expires_in=900  # 15 minutes
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error in verify_otp: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )


#------------------------------------------------------------------------------------------
#          3. POST /sign-up endpoint
#------------------------------------------------------------------------------------------


class SignUpResponse(BaseModel):
    success: bool
    admin_id: str
    message: str

def verify_temp_token(token: str) -> str:
    """Verify temporary token and extract email"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        if payload.get("type") != "temp":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        email = payload.get("sub")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        return email
    
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired or invalid"
        )

def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from PDF file"""
    try:
        pdf_file = io.BytesIO(file_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        print(f"Error extracting PDF: {str(e)}")
        return ""

def extract_text_from_docx(file_content: bytes) -> str:
    """Extract text from DOCX file"""
    try:
        doc_file = io.BytesIO(file_content)
        doc = docx.Document(doc_file)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    except Exception as e:
        print(f"Error extracting DOCX: {str(e)}")
        return ""

def extract_text_from_txt(file_content: bytes) -> str:
    """Extract text from TXT file"""
    try:
        return file_content.decode('utf-8')
    except Exception as e:
        print(f"Error extracting TXT: {str(e)}")
        return ""

async def process_files_with_groq(files: List[UploadFile]) -> str:
    """Extract and process content from multiple files using Groq API"""
    all_text = ""
    
    for file in files:
        content = await file.read()
        filename = file.filename.lower()
        
        if filename.endswith('.pdf'):
            extracted_text = extract_text_from_pdf(content)
        elif filename.endswith('.docx'):
            extracted_text = extract_text_from_docx(content)
        elif filename.endswith('.txt'):
            extracted_text = extract_text_from_txt(content)
        else:
            continue
        
        all_text += f"\n--- {file.filename} ---\n{extracted_text}\n"
    
    # Use Groq to process and structure the extracted text
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at analyzing SOP manuals and documentation. Extract and organize key information, procedures, and guidelines from the provided text. Structure the content clearly and maintain important details."
                },
                {
                    "role": "user",
                    "content": f"Process and structure the following SOP manual content:\n\n{all_text}"
                }
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.3,
            max_tokens=8000
        )
        
        processed_content = chat_completion.choices[0].message.content
        return processed_content
    
    except Exception as e:
        print(f"Error processing with Groq: {str(e)}")
        return all_text

@app.post("/sign-up", response_model=SignUpResponse, status_code=status.HTTP_201_CREATED)
async def sign_up(
    temp_token: str = Form(...),
    name: str = Form(...),
    email: EmailStr = Form(...),
    password: str = Form(...),
    company_name: str = Form(...),
    designation: str = Form(...),
    files: List[UploadFile] = File(...)
    ):
    """
    Admin sign-up with SOP manual upload
    
    - **temp_token**: Temporary token from verify-otp
    - **name**: Admin full name
    - **email**: Admin email address
    - **password**: Admin password
    - **company_name**: Company name
    - **designation**: Job designation
    - **files**: SOP manual files (PDF, DOCX, TXT)
    """
    try:
        email = email.lower().strip()
        
        # Verify temp token and extract email
        token_email = verify_temp_token(temp_token)
        
        # Validate email matches token payload
        if token_email != email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email does not match token"
            )
        
        # Check if admin already exists
        admins_ref = firestore_db .collection('admins')
        existing_admin = admins_ref.where('email', '==', email).limit(1).get()
        if len(existing_admin) > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admin already exists"
            )
        
        # Extract content from files using Groq API
        processed_content = await process_files_with_groq(files)
        
        # Create document in sops_manuals collection
        sops_ref = firestore_db .collection('sops_manuals')
        sop_doc_ref = sops_ref.add({
            'sop_manual_guidelines': processed_content,
        })
        sop_manual_id = sop_doc_ref[1].id
        
        # Create Firebase Auth user
        firebase_user = auth.create_user(
            email=email,
            password=password,
            display_name=name
        )
        
        # Store admin details in admins collection using firebase_user.uid as document ID
        admin_doc_ref = admins_ref.document(firebase_user.uid)
        admin_doc_ref.set({
            'email': email,
            'name': name,
            'company_name': company_name,
            'designation': designation,
            'sop_manuals_id': sop_manual_id,
            'created_at': firestore.SERVER_TIMESTAMP,
            'last_login': None
        })
        admin_id = firebase_user.uid
        
        return SignUpResponse(
            success=True,
            admin_id=admin_id,
            message="Admin registered successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error in sign_up: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


#------------------------------------------------------------------------------------------
#          4. POST /login endpoint
#------------------------------------------------------------------------------------------


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class AdminProfile(BaseModel):
    admin_id: str
    email: str
    name: str
    company_name: str
    designation: str

class LoginResponse(BaseModel):
    success: bool
    access_token: str
    admin: AdminProfile

def authenticate_with_firebase(email: str, password: str) -> dict:
    """Authenticate user with Firebase Auth REST API"""
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}"
    
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }
    
    response = requests.post(url, json=payload)
    
    if response.status_code != 200:
        error_data = response.json()
        error_message = error_data.get('error', {}).get('message', 'Authentication failed')
        
        if error_message == "EMAIL_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email not found"
            )
        elif error_message == "INVALID_PASSWORD":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid password"
            )
        elif error_message == "USER_DISABLED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account has been disabled"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed"
            )
    
    return response.json()

def create_access_token(admin_id: str, email: str) -> str:
    """Generate JWT access token valid for 24 hours"""
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": admin_id,
        "email": email,
        "type": "access",
        "exp": expire,
        "iat": datetime.utcnow()
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token

@app.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(request: LoginRequest):
    """
    Admin login endpoint
    
    - **email**: Admin email address
    - **password**: Admin password
    """
    try:
        email = request.email.lower().strip()
        
        firebase_response = authenticate_with_firebase(email, request.password)
        firebase_uid = firebase_response.get('localId')
        
        # Verify user exists in admins collection
        admins_ref = firestore_db .collection('admins')
        admin_query = admins_ref.where('email', '==', email).limit(1).get()
        
        if len(admin_query) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Admin profile not found"
            )
        
        admin_doc = admin_query[0]
        admin_data = admin_doc.to_dict()
        admin_id = admin_doc.id
        
        # Update last_login
        admins_ref.document(admin_id).update({
            'last_login': firestore.SERVER_TIMESTAMP
        })
        
        access_token = create_access_token(admin_id, email)
        
        admin_profile = AdminProfile(
            admin_id=admin_id,
            email=admin_data['email'],
            name=admin_data['name'],
            company_name=admin_data['company_name'],
            designation=admin_data['designation']
        )
        
        return LoginResponse(
            success=True,
            access_token=access_token,
            admin=admin_profile
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error in login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed. Please try again."
        )


#------------------------------------------------------------------------------------------
#          5. GET /get-active-calls endpoint
#------------------------------------------------------------------------------------------


class ActiveCall(BaseModel):
    call_id: str
    worker_id: str
    mobile_no: str
    conversation_id: str
    urgency: str
    status: str
    timestamp: str
    medium: str
    last_message_at: str
    admin_id: Optional[str] = None

class GetActiveCallsResponse(BaseModel):
    success: bool
    active_calls: List[ActiveCall]

def verify_access_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Verify JWT access token and extract payload"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        admin_id = payload.get("sub")
        if not admin_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        return {"admin_id": admin_id, "email": payload.get("email")}
    
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

def get_admin_company(admin_id: str) -> str:
    """Get company name for admin from Firestore"""
    try:
        admin_doc = firestore_db.collection('admins').document(admin_id).get()
        if not admin_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Admin not found"
            )
        return admin_doc.to_dict().get('company_name')
    except Exception as e:
        print(f"Error fetching admin company: {str(e)}")
        raise

def convert_timestamp(timestamp_value) -> str:
    """Convert Firebase timestamp to ISO format string"""
    try:
        if isinstance(timestamp_value, (int, float)):
            return datetime.fromtimestamp(timestamp_value / 1000).isoformat() + "Z"
        elif isinstance(timestamp_value, str):
            return timestamp_value
        else:
            return datetime.utcnow().isoformat() + "Z"
    except:
        return datetime.utcnow().isoformat() + "Z"

@app.get("/get-active-calls", response_model=GetActiveCallsResponse, status_code=status.HTTP_200_OK)
async def get_active_calls(token_data: dict = Depends(verify_access_token)):
    """
    Get active calls for logged-in admin
    
    Returns active calls that are:
    - Taken over by the logged-in admin (admin_id matches)
    - Unassigned calls from workers in the same company
    """
    try:
        admin_id = token_data["admin_id"]
        
        # Get admin's company name
        company_name = get_admin_company(admin_id)
        
        # Get all workers under this admin's company
        workers_ref = firestore_db.collection('workers')
        workers_query = workers_ref.where('admin_id', '==', admin_id).get()
        worker_ids = [worker.id for worker in workers_query]
        
        # Query Realtime Database for active calls
        active_calls_ref = db.reference('active_calls')
        all_calls = active_calls_ref.get()
        
        filtered_calls = []
        
        if all_calls:
            for call_id, call_data in all_calls.items():
                # Filter: admin_id matches OR admin_id is null/empty and worker belongs to admin's company
                if (call_data.get('admin_id') == admin_id or 
                    (not call_data.get('admin_id') and call_data.get('worker_id') in worker_ids)):
                    
                    active_call = ActiveCall(
                        call_id=call_id,
                        worker_id=call_data.get('worker_id', ''),
                        mobile_no=call_data.get('mobile_no', ''),
                        conversation_id=call_data.get('conversation_id', ''),
                        urgency=call_data.get('urgency', 'NORMAL'),
                        status=call_data.get('status', 'ACTIVE'),
                        timestamp=convert_timestamp(call_data.get('timestamp')),
                        medium=call_data.get('medium', 'Text'),
                        last_message_at=convert_timestamp(call_data.get('last_message_at')),
                        admin_id=call_data.get('admin_id')
                    )
                    filtered_calls.append(active_call)
        
        # Sort by urgency: CRITICAL > URGENT > NORMAL
        urgency_priority = {'CRITICAL': 0, 'URGENT': 1, 'NORMAL': 2}
        filtered_calls.sort(key=lambda x: urgency_priority.get(x.urgency, 3))
        
        return GetActiveCallsResponse(
            success=True,
            active_calls=filtered_calls
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error in get_active_calls: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve active calls"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

