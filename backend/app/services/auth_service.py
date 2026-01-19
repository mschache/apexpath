"""
JWT authentication service.

Handles JWT token creation, verification, and user authentication.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User

logger = logging.getLogger(__name__)

# Security scheme for Bearer token authentication
security = HTTPBearer(auto_error=False)


class AuthenticationError(Exception):
    """Exception raised when authentication fails."""
    pass


def create_access_token(
    user_id: int,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT access token for a user.

    The token contains the user ID as the subject claim and an expiration time.

    Args:
        user_id: The database user ID to encode in the token
        expires_delta: Optional custom expiration time. Defaults to settings value.

    Returns:
        str: Encoded JWT token string

    Example:
        >>> token = create_access_token(user_id=1)
        >>> print(token[:20])
        'eyJhbGciOiJIUzI1NiIs'
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )

    logger.debug(f"Created access token for user {user_id}")
    return encoded_jwt


def verify_token(token: str) -> int:
    """
    Verify a JWT token and extract the user ID.

    Validates the token signature, expiration, and required claims.

    Args:
        token: The JWT token string to verify

    Returns:
        int: The user ID extracted from the token

    Raises:
        AuthenticationError: If the token is invalid, expired, or missing required claims

    Example:
        >>> user_id = verify_token("eyJhbGci...")
        >>> print(user_id)
        1
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )

        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            logger.warning("Token missing 'sub' claim")
            raise AuthenticationError("Invalid token: missing subject")

        # Verify token type
        token_type = payload.get("type")
        if token_type != "access":
            logger.warning(f"Invalid token type: {token_type}")
            raise AuthenticationError("Invalid token type")

        user_id = int(user_id_str)
        logger.debug(f"Token verified for user {user_id}")
        return user_id

    except JWTError as e:
        logger.warning(f"JWT verification failed: {str(e)}")
        raise AuthenticationError(f"Invalid token: {str(e)}")
    except ValueError as e:
        logger.warning(f"Invalid user ID in token: {str(e)}")
        raise AuthenticationError("Invalid token: malformed subject")


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency to get the current authenticated user.

    Extracts the bearer token from the Authorization header, verifies it,
    and returns the corresponding user from the database.

    Args:
        credentials: The Authorization header credentials (injected by FastAPI)
        db: Database session (injected by FastAPI)

    Returns:
        User: The authenticated user object

    Raises:
        HTTPException: 401 if not authenticated or token is invalid
        HTTPException: 404 if user not found in database

    Example:
        >>> @app.get("/profile")
        ... async def get_profile(user: User = Depends(get_current_user)):
        ...     return {"name": user.name}
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        logger.debug("No credentials provided")
        raise credentials_exception

    token = credentials.credentials

    try:
        user_id = verify_token(token)
    except AuthenticationError as e:
        logger.warning(f"Authentication failed: {str(e)}")
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        logger.warning(f"User {user_id} not found in database")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    FastAPI dependency to optionally get the current user.

    Similar to get_current_user but returns None instead of raising
    an exception if no valid authentication is provided.

    Args:
        credentials: The Authorization header credentials (injected by FastAPI)
        db: Database session (injected by FastAPI)

    Returns:
        Optional[User]: The authenticated user object, or None if not authenticated

    Example:
        >>> @app.get("/activities")
        ... async def get_activities(user: Optional[User] = Depends(get_current_user_optional)):
        ...     if user:
        ...         return {"user_activities": ...}
        ...     return {"public_activities": ...}
    """
    if credentials is None:
        return None

    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


def create_refresh_token(user_id: int) -> str:
    """
    Create a long-lived refresh token for a user.

    Refresh tokens have a longer expiration and can be used to obtain
    new access tokens without re-authentication.

    Args:
        user_id: The database user ID to encode in the token

    Returns:
        str: Encoded JWT refresh token string
    """
    expire = datetime.now(timezone.utc) + timedelta(days=30)

    to_encode = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
    }

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )

    logger.debug(f"Created refresh token for user {user_id}")
    return encoded_jwt


def verify_refresh_token(token: str) -> int:
    """
    Verify a refresh token and extract the user ID.

    Args:
        token: The JWT refresh token string to verify

    Returns:
        int: The user ID extracted from the token

    Raises:
        AuthenticationError: If the token is invalid or not a refresh token
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )

        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise AuthenticationError("Invalid token: missing subject")

        token_type = payload.get("type")
        if token_type != "refresh":
            raise AuthenticationError("Invalid token: not a refresh token")

        return int(user_id_str)

    except JWTError as e:
        raise AuthenticationError(f"Invalid refresh token: {str(e)}")
    except ValueError:
        raise AuthenticationError("Invalid token: malformed subject")
