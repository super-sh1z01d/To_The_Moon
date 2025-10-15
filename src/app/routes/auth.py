from datetime import timedelta
import os

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth

from src.adapters.db.deps import get_db
from src.adapters.repositories import user_repo
from src.domain.users import auth_service, schemas

router = APIRouter(prefix="/auth", tags=["auth"])

# Google OAuth configuration
oauth = OAuth()
oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)


@router.post("/register", response_model=schemas.User)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = user_repo.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = auth_service.get_password_hash(user.password)
    return user_repo.create_user(db=db, user=user, hashed_password=hashed_password)


@router.post("/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = user_repo.get_user_by_email(db, email=form_data.username) # form uses 'username' field for email
    if not user or not auth_service.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth_service.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/users/me", response_model=schemas.User)
def read_users_me(current_user: schemas.User = Depends(auth_service.get_current_active_user)):
    return current_user


@router.get("/google")
async def google_login(request: Request):
    """Redirect to Google OAuth login page"""
    redirect_uri = os.getenv('GOOGLE_REDIRECT_URI', 'https://tothemoon.sh1z01d.ru/auth/google/callback')
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """Handle Google OAuth callback"""
    try:
        # Get access token from Google
        token = await oauth.google.authorize_access_token(request)

        # Get user info from Google
        user_info = token.get('userinfo')
        if not user_info:
            raise HTTPException(status_code=400, detail="Failed to get user info from Google")

        google_id = user_info.get('sub')
        email = user_info.get('email')
        profile_picture = user_info.get('picture')

        if not google_id or not email:
            raise HTTPException(status_code=400, detail="Missing required user information")

        # Check if user exists by google_id
        user = user_repo.get_user_by_google_id(db, google_id)

        # If not, check by email (maybe they registered with email before)
        if not user:
            user = user_repo.get_user_by_email(db, email)
            if user and user.auth_provider == "email":
                # User exists with email auth, link Google account
                user.google_id = google_id
                user.profile_picture = profile_picture
                db.commit()
                db.refresh(user)
            elif not user:
                # Create new user with Google auth
                user = user_repo.create_oauth_user(db, email, google_id, profile_picture)

        # Create JWT token for the user
        access_token_expires = timedelta(minutes=auth_service.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = auth_service.create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )

        # Redirect to frontend with token in fragment (more secure than query param)
        frontend_url = os.getenv('FRONTEND_URL', 'https://tothemoon.sh1z01d.ru')
        return RedirectResponse(
            url=f"{frontend_url}/app/#token={access_token}",
            status_code=status.HTTP_303_SEE_OTHER
        )

    except Exception as e:
        # Redirect to frontend with error
        frontend_url = os.getenv('FRONTEND_URL', 'https://tothemoon.sh1z01d.ru')
        return RedirectResponse(
            url=f"{frontend_url}/?error=auth_failed",
            status_code=status.HTTP_303_SEE_OTHER
        )
