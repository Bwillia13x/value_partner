from sqlalchemy.orm import Session

from . import database, schemas

def get_user_by_email(db: Session, email: str):
    print(f"Attempting to retrieve user with email: {email}")
    user = db.query(database.User).filter(database.User.email == email).first()
    if user:
        print(f"User found: {user.email}")
    else:
        print(f"User not found for email: {email}")
    return user

def create_user(db: Session, user: schemas.UserCreate, hashed_password: str):
    """Creates a new user in the database."""
    db_user = database.User(
        email=user.email,
        name=user.name,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
