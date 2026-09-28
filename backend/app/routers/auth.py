"""Authentication routes: register, login, current user."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

from app.db import get_session
from app.deps import get_current_user
from app.models import Customer, Role
from app.schemas import LoginRequest, RegisterRequest, Token, UserOut
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, session: Session = Depends(get_session)) -> Token:
    existing = session.exec(
        select(Customer).where(Customer.email == data.email)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )
    user = Customer(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        role=Role.customer,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    token = create_access_token(str(user.id), extra={"role": user.role.value})
    return Token(access_token=token)


@router.post("/login", response_model=Token)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
) -> Token:
    # OAuth2 form uses `username` for the email.
    user = session.exec(
        select(Customer).where(Customer.email == form.username)
    ).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    token = create_access_token(str(user.id), extra={"role": user.role.value})
    return Token(access_token=token)


@router.post("/login-json", response_model=Token)
def login_json(data: LoginRequest, session: Session = Depends(get_session)) -> Token:
    """JSON login convenience endpoint for the SPA frontend."""
    user = session.exec(select(Customer).where(Customer.email == data.email)).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    token = create_access_token(str(user.id), extra={"role": user.role.value})
    return Token(access_token=token)


@router.get("/me", response_model=UserOut)
def me(user: Customer = Depends(get_current_user)) -> Customer:
    return user
