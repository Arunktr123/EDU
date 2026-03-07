"""
SUPERNATURAL - Authentication Routes
JWT-based register & login for mentors and students
"""

import os
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials

from app.database import get_db
from app.models.user import User, UserRole
from app.models.mentor import Mentor
from app.models.student import Student
from app.config import settings

logger = logging.getLogger(__name__)

# Google OAuth scopes for Calendar/Meet
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
]

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ── Pydantic Schemas ──────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: UserRole


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: int


# ── Helpers ───────────────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    payload = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    payload.update({"exp": expire})
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: int = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


# ── Routes ────────────────────────────────────────────────────────────────────
@router.post("/register", status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new mentor or student. Creates base profile automatically."""
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.flush()

    # Auto-create profile based on role
    if payload.role == UserRole.MENTOR:
        db.add(Mentor(user_id=user.id))
    elif payload.role == UserRole.STUDENT:
        db.add(Student(user_id=user.id))

    db.commit()
    db.refresh(user)
    return {"message": "Registration successful", "user_id": user.id, "role": user.role}


@router.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login and receive JWT access token."""
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": user.id, "role": user.role})
    return TokenResponse(access_token=token, role=user.role, user_id=user.id)


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "is_active": current_user.is_active,
    }


# ── Google OAuth Helpers ──────────────────────────────────────────────────────
def _get_google_client_config() -> dict:
    """Load Google OAuth client config from env var or file.

    On Render (production), set GOOGLE_CREDENTIALS_JSON env var with the full
    contents of google_credentials.json.  Locally, the file is used directly.
    """
    # 1. Try env var first (Render / production)
    json_str = settings.GOOGLE_CREDENTIALS_JSON
    if json_str:
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=500,
                detail=f"GOOGLE_CREDENTIALS_JSON env var contains invalid JSON: {exc}",
            )

    # 2. Fall back to file (local development)
    creds_file = settings.GOOGLE_CALENDAR_CREDENTIALS_FILE
    if os.path.exists(creds_file):
        with open(creds_file) as f:
            return json.load(f)

    raise HTTPException(
        status_code=500,
        detail="Google credentials not found. Either set the GOOGLE_CREDENTIALS_JSON "
               "env var (for Render) or place google_credentials.json in credentials/.",
    )


# ── Google OAuth (Calendar/Meet) ─────────────────────────────────────────────
@router.get("/google/login")
def google_login():
    """Redirect user to Google consent screen to authorize Calendar access."""
    client_config = _get_google_client_config()

    flow = Flow.from_client_config(
        client_config,
        scopes=GOOGLE_SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
    )
    authorization_url, _state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return RedirectResponse(authorization_url)


@router.get("/google/callback")
def google_callback(code: str = None, error: str = None, state: str = None):
    """Handle Google OAuth callback — exchange code for tokens and save token.json."""
    if error:
        raise HTTPException(status_code=400, detail=f"Google OAuth error: {error}")
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    try:
        # Google may return more scopes than requested (incremental auth).
        # Tell oauthlib to accept the wider set instead of raising.
        os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

        client_config = _get_google_client_config()

        flow = Flow.from_client_config(
            client_config,
            scopes=GOOGLE_SCOPES,
            redirect_uri=settings.GOOGLE_REDIRECT_URI,
        )
        flow.fetch_token(code=code)
        creds = flow.credentials
    except Exception as exc:
        logger.error(f"Google token exchange failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Google token exchange failed: {exc}",
        )

    # Serialise token so it can be saved / returned
    token_json_str = creds.to_json()

    # Try saving token.json to disk (works locally, may be ephemeral on Render)
    token_path = settings.GOOGLE_TOKEN_FILE
    try:
        os.makedirs(
            os.path.dirname(token_path) if os.path.dirname(token_path) else ".",
            exist_ok=True,
        )
        with open(token_path, "w") as f:
            f.write(token_json_str)
        logger.info(f"✅ Google token saved to {token_path}")
    except OSError as exc:
        logger.warning(f"Could not write token file ({exc}). Return token in response instead.")

    # Always return the token JSON so the user can store it as GOOGLE_TOKEN_JSON env var
    return {
        "status": "success",
        "message": (
            "Google Calendar authorized! Copy the 'token_json' value below "
            "and set it as the GOOGLE_TOKEN_JSON environment variable on Render "
            "so the token persists across deploys."
        ),
        "token_file": token_path,
        "token_json": json.loads(token_json_str),
    }

