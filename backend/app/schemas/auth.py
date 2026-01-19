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
        weight_kg: Athlete's weight in kilograms (optional)
        age: Athlete's age in years (optional)
        max_hr: Maximum heart rate in bpm (optional)
        resting_hr: Resting heart rate in bpm (optional)
        experience_level: Training experience level (optional)
        primary_discipline: Primary cycling discipline (optional)
        default_weekly_hours: Default weekly training hours (optional)
        has_power_meter: Whether athlete has a power meter (optional)
        has_indoor_trainer: Whether athlete has an indoor trainer (optional)
    """

    id: int = Field(..., description="Internal user ID")
    strava_id: int = Field(..., description="Strava athlete ID")
    name: Optional[str] = Field(None, description="Athlete's full name")
    email: Optional[str] = Field(None, description="Athlete's email address")
    ftp: Optional[int] = Field(None, description="Functional Threshold Power in watts")
    profile_image: Optional[str] = Field(None, description="URL to profile picture")

    # Physical attributes
    weight_kg: Optional[float] = Field(None, description="Weight in kilograms")
    age: Optional[int] = Field(None, description="Age in years")
    max_hr: Optional[int] = Field(None, description="Maximum heart rate in bpm")
    resting_hr: Optional[int] = Field(None, description="Resting heart rate in bpm")

    # Training profile
    experience_level: Optional[str] = Field(None, description="Experience level: beginner/intermediate/advanced/elite")
    primary_discipline: Optional[str] = Field(None, description="Primary discipline: road/mtb/gravel/track/indoor")
    default_weekly_hours: Optional[int] = Field(None, description="Default weekly training hours")

    # Equipment
    has_power_meter: Optional[bool] = Field(None, description="Has power meter")
    has_indoor_trainer: Optional[bool] = Field(None, description="Has indoor trainer")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "strava_id": 12345678,
                "name": "Jane Cyclist",
                "email": "jane@example.com",
                "ftp": 250,
                "profile_image": "https://example.com/avatar.jpg",
                "weight_kg": 70.5,
                "age": 35,
                "max_hr": 185,
                "resting_hr": 52,
                "experience_level": "intermediate",
                "primary_discipline": "road",
                "default_weekly_hours": 8,
                "has_power_meter": True,
                "has_indoor_trainer": True
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

    Used for updating user profile fields like FTP, physical attributes, and training preferences.

    Attributes:
        ftp: Functional Threshold Power in watts (optional)
        name: User's display name (optional)
        weight_kg: Weight in kilograms (optional)
        age: Age in years (optional)
        max_hr: Maximum heart rate in bpm (optional)
        resting_hr: Resting heart rate in bpm (optional)
        experience_level: Training experience level (optional)
        primary_discipline: Primary cycling discipline (optional)
        default_weekly_hours: Default weekly training hours (optional)
        has_power_meter: Whether athlete has a power meter (optional)
        has_indoor_trainer: Whether athlete has an indoor trainer (optional)
    """

    # Core fields
    ftp: Optional[int] = Field(None, ge=50, le=500, description="FTP in watts (50-500)")
    name: Optional[str] = Field(None, max_length=255, description="Display name")

    # Physical attributes
    weight_kg: Optional[float] = Field(None, ge=30.0, le=200.0, description="Weight in kg (30-200)")
    age: Optional[int] = Field(None, ge=13, le=99, description="Age in years (13-99)")
    max_hr: Optional[int] = Field(None, ge=100, le=220, description="Max HR in bpm (100-220)")
    resting_hr: Optional[int] = Field(None, ge=30, le=100, description="Resting HR in bpm (30-100)")

    # Training profile
    experience_level: Optional[str] = Field(None, pattern="^(beginner|intermediate|advanced|elite)$", description="Experience level")
    primary_discipline: Optional[str] = Field(None, pattern="^(road|mtb|gravel|track|indoor)$", description="Primary discipline")
    default_weekly_hours: Optional[int] = Field(None, ge=3, le=30, description="Weekly training hours (3-30)")

    # Equipment
    has_power_meter: Optional[bool] = Field(None, description="Has power meter")
    has_indoor_trainer: Optional[bool] = Field(None, description="Has indoor trainer")

    class Config:
        json_schema_extra = {
            "example": {
                "ftp": 260,
                "name": "Jane Cyclist",
                "weight_kg": 70.5,
                "age": 35,
                "max_hr": 185,
                "resting_hr": 52,
                "experience_level": "intermediate",
                "primary_discipline": "road",
                "default_weekly_hours": 8,
                "has_power_meter": True,
                "has_indoor_trainer": True
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
