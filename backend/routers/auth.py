"""
Auth Router — /api/auth/register and /api/auth/login
"""
from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from db.mysql import execute, fetch_one, get_db
from models.schemas import LoginRequest, RegisterRequest, TokenResponse

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: Session = Depends(get_db)) -> dict:
    # Check duplicate email or username
    existing = fetch_one(
        db,
        "SELECT id FROM users WHERE email = :email OR username = :username LIMIT 1",
        {"email": body.email, "username": body.username},
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or username already registered.",
        )

    hashed = pwd_context.hash(body.password)
    execute(
        db,
        """INSERT INTO users (username, email, password, full_name)
           VALUES (:username, :email, :password, :full_name)""",
        {
            "username": body.username,
            "email": body.email,
            "password": hashed,
            "full_name": body.full_name,
        },
    )
    return {"message": "Account created successfully."}


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = fetch_one(
        db,
        "SELECT * FROM users WHERE email = :email AND is_active = 1 LIMIT 1",
        {"email": body.email},
    )
    if not user or not pwd_context.verify(body.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    return TokenResponse(
        access_token=f"simple-token-{user['id']}",   # TODO: Replace with JWT
        user_id=user["id"],
        username=user["username"],
        full_name=user["full_name"],
        credits=user["credits"],
        language=user["language"],
    )
