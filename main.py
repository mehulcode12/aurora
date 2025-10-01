# main.py or routes/auth.py
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import redis
from firebase_admin import credentials, firestore, initialize_app
from typing import Optional
import os
from dotenv import load_dotenv
from jose import JWTError, jwt
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI()

# Initialize Firebase
cred = credentials.Certificate("serviceAccountKey.json")
initialize_app(cred)
db = firestore.client()

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

# Pydantic Models
class EmailRequest(BaseModel):
    email: EmailStr

class OTPResponse(BaseModel):
    success: bool
    message: str

# SMTP Configuration
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_EMAIL = os.getenv('SMTP_EMAIL')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')  # App password for Gmail

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
        admins_ref = db.collection('admins')
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

