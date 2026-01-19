"""
Authentication and user-related Pydantic schemas.

These schemas define the request/response models for authentication endpoints.
"""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserResponse(BaseModel):
    """
    User profile response schema.

    Returned when fetching the current user's profile or after authentication.

    Attributes:
        id: Internal user ID
        strava_id: Strava athlete ID
        name: Athlete's full name
        email: Athlete's email address (optional, may not be provided by Strava)
        ftp: Functional Threshold Power in watts (optional)
        profile_image: URL to athlete's profile picture (optional)
    """

    id: int = Field(..., description="Internal user ID")
    strava_id: int = Field(..., description="Strava athlete ID")
    name: Optional[str] = Field(None, description="Athlete's full name")
    email: Optional[str] = Field(None, description="Athlete's email address")
    ftp: Optional[int] = Field(None, description="Functional Threshold Power in watts")
    profile_image: Optional[str] = Field(None, description="URL to profile picture")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "strava_id": 12345678,
                "name": "Jane Cyclist",
                "email": "jane@example.com",
                "ftp": 250,
                "profile_image": "https://example.com/avatar.jpg"
            }
        }


class TokenResponse(BaseModel):
    """
    JWT token response schema.

    Returned after successful authentication or token refresh.

    Attributes:
        access_token: JWT access token for API authentication
        token_type: Token type, always "bearer"
    """

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer"
            }
        }


class AuthResponse(BaseModel):
    """
    Combined authentication response with user data and tokens.

    Returned after successful OAuth callback.

    Attributes:
        user: User profile data
        token: JWT token data
    """

    user: UserResponse = Field(..., description="User profile data")
    token: TokenResponse = Field(..., description="Authentication token")

    class Config:
        json_schema_extra = {
            "example": {
                "user": {
                    "id": 1,
                    "strava_id": 12345678,
                    "name": "Jane Cyclist",
                    "email": "jane@example.com",
                    "ftp": 250,
                    "profile_image": "https://example.com/avatar.jpg"
                },
                "token": {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer"
                }
            }
        }


class StravaCallbackRequest(BaseModel):
    """
    Strava OAuth callback request schema.

    Used when exchanging the authorization code for tokens.

    Attributes:
        code: Authorization code from Strava OAuth callback
    """

    code: str = Field(..., description="Authorization code from Strava OAuth")

    class Config:
        json_schema_extra = {
            "example": {
                "code": "abc123def456"
            }
        }


class UserUpdate(BaseModel):
    """
    User update request schema.

    Used for updating user profile fields like FTP.

    Attributes:
        ftp: Functional Threshold Power in watts (optional)
        name: User's display name (optional)
    """

    ftp: Optional[int] = Field(None, ge=50, le=500, description="FTP in watts (50-500)")
    name: Optional[str] = Field(None, max_length=255, description="Display name")

    class Config:
        json_schema_extra = {
            "example": {
                "ftp": 260,
                "name": "Jane Cyclist"
            }
        }


class StravaLoginResponse(BaseModel):
    """
    Response for the Strava login endpoint.

    Contains the authorization URL to redirect the user to.

    Attributes:
        authorization_url: Full Strava OAuth authorization URL
    """

    authorization_url: str = Field(..., description="Strava OAuth authorization URL")

    class Config:
        json_schema_extra = {
            "example": {
                "authorization_url": "https://www.strava.com/oauth/authorize?client_id=123&redirect_uri=..."
            }
        }
