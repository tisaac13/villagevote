"""
Authentication endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.core.database import get_db
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    encrypt_address,
    hash_address
)
from app.schemas import (
    UserSignup,
    UserLogin,
    TokenRefresh,
    SignupResponse,
    Tokens,
    UserResponse,
    LocationResolution
)
from app.models import User, UserProfile, UserPreferences

router = APIRouter()


@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    user_data: UserSignup,
    db: AsyncSession = Depends(get_db)
):
    """
    Create new user account (requires address)

    - Encrypts and stores address
    - Creates address hash for deduplication
    - Initiates background job for geocoding and division resolution
    """
    # Check if user already exists
    existing_user = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    if existing_user.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create user with basic info
    new_user = User(
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        provider="password",
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        birthday=user_data.birthday,
        state=user_data.state
    )
    db.add(new_user)
    await db.flush()  # Get the user ID

    # If address provided, create user profile with encrypted address
    if user_data.address:
        # Create address hash for deduplication
        addr_hash = hash_address(
            user_data.address.line1,
            user_data.address.city,
            user_data.address.state,
            user_data.address.postal_code,
            user_data.address.country
        )

        # Check if address hash already exists
        existing_profile = await db.execute(
            select(UserProfile).where(UserProfile.address_hash == addr_hash)
        )
        if existing_profile.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this address already exists"
            )

        user_profile = UserProfile(
            user_id=new_user.id,
            address_line1_enc=encrypt_address(user_data.address.line1),
            address_line2_enc=encrypt_address(user_data.address.line2) if user_data.address.line2 else None,
            city=user_data.address.city,
            state=user_data.address.state,
            postal_code=user_data.address.postal_code,
            country=user_data.address.country,
            address_hash=addr_hash
        )
        db.add(user_profile)

    # Create default preferences
    user_preferences = UserPreferences(
        user_id=new_user.id,
        topics=[],
        notify_enabled=True
    )
    db.add(user_preferences)

    # Commit all changes
    await db.commit()
    await db.refresh(new_user)

    # Create tokens
    access_token = create_access_token(data={"sub": str(new_user.id)})
    refresh_token = create_refresh_token(data={"sub": str(new_user.id)})

    # TODO: Trigger background job for geocoding
    # TODO: Trigger background job for division/official resolution

    return SignupResponse(
        user=UserResponse(
            id=new_user.id,
            email=new_user.email,
            first_name=new_user.first_name,
            last_name=new_user.last_name,
            state=new_user.state
        ),
        tokens=Tokens(access_token=access_token, refresh_token=refresh_token),
        location=LocationResolution(
            lat=None,
            lon=None,
            divisions_resolved=False
        )
    )


@router.post("/login", response_model=Tokens)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    Login with email and password

    Returns JWT access token and refresh token
    """
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == credentials.email)
    )
    user = result.scalar_one_or_none()

    # Verify user exists and password is correct
    if not user or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Update last login timestamp
    user.last_login_at = datetime.utcnow()
    await db.commit()

    # Create tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return Tokens(
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.post("/refresh", response_model=Tokens)
async def refresh(
    token_data: TokenRefresh,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token
    """
    payload = verify_token(token_data.refresh_token, token_type="refresh")

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    user_id = payload.get("sub")

    # Verify user still exists
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    # Create new tokens
    access_token = create_access_token(data={"sub": user_id})
    refresh_token = create_refresh_token(data={"sub": user_id})

    return Tokens(
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.post("/logout")
async def logout():
    """
    Logout user (client should discard tokens)
    """
    return {"message": "Logged out successfully"}
