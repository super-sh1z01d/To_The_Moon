from sqlalchemy.orm import Session
from src.adapters.db.models import User
from src.domain.users.schemas import UserCreate


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def get_user_by_google_id(db: Session, google_id: str) -> User | None:
    return db.query(User).filter(User.google_id == google_id).first()


def create_user(db: Session, user: UserCreate, hashed_password: str) -> User:
    db_user = User(email=user.email, hashed_password=hashed_password, auth_provider="email", role="user")
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def create_oauth_user(db: Session, email: str, google_id: str, profile_picture: str | None = None) -> User:
    db_user = User(
        email=email,
        google_id=google_id,
        auth_provider="google",
        profile_picture=profile_picture,
        hashed_password=None,
        role="user"
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
