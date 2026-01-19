"""
Authentication router for Strava OAuth and JWT management.

Provides endpoints for:
- Initiating Strava OAuth flow
- Handling OAuth callbacks
- Retrieving current user profile
- Refreshing JWT tokens
- Logout
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    StravaCallbackRequest,
    StravaLoginResponse,
    TokenResponse,
    UserResponse,
    UserUpdate,
)
from app.services.auth_service import (
    AuthenticationError,
    create_access_token,
    create_refresh_token,
    get_current_user,
    verify_refresh_token,
)
from app.services.strava_service import StravaAPIError, strava_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Authentication"])


@router.get(
    "/strava/login",
    response_model=StravaLoginResponse,
    summary="Get Strava OAuth URL",
    description="Returns the Strava OAuth authorization URL. Redirect the user to this URL to initiate authentication.",
)
async def strava_login(
    redirect_uri: Optional[str] = Query(
        None,
        description="Custom redirect URI. Defaults to configured STRAVA_REDIRECT_URI.",
    ),
) -> StravaLoginResponse:
    """
    Get the Strava OAuth authorization URL.

    This endpoint generates the URL where users should be redirected to
    authorize the application to access their Strava data.

    The default redirect URI is configured in settings but can be overridden
    for different environments (e.g., mobile apps).

    Args:
        redirect_uri: Optional custom redirect URI

    Returns:
        StravaLoginResponse: Contains the authorization URL

    Example:
        GET /auth/strava/login
        Response: {"authorization_url": "https://www.strava.com/oauth/authorize?..."}
    """
    callback_uri = redirect_uri or settings.STRAVA_REDIRECT_URI
    authorization_url = strava_service.get_authorization_url(redirect_uri=callback_uri)

    logger.info(f"Generated Strava OAuth URL with redirect to {callback_uri}")

    return StravaLoginResponse(authorization_url=authorization_url)


@router.get(
    "/strava/login/redirect",
    response_class=RedirectResponse,
    summary="Redirect to Strava OAuth",
    description="Directly redirects the user to Strava for OAuth authorization.",
)
async def strava_login_redirect() -> RedirectResponse:
    """
    Redirect directly to Strava OAuth.

    This is a convenience endpoint that immediately redirects the user
    to Strava's authorization page instead of returning the URL.

    Returns:
        RedirectResponse: 302 redirect to Strava OAuth
    """
    authorization_url = strava_service.get_authorization_url(
        redirect_uri=settings.STRAVA_REDIRECT_URI
    )
    return RedirectResponse(url=authorization_url, status_code=302)


@router.get(
    "/strava/callback",
    response_model=AuthResponse,
    summary="Handle Strava OAuth callback",
    description="Handles the OAuth callback from Strava, exchanges the code for tokens, and creates/updates the user.",
)
async def strava_callback(
    code: str = Query(..., description="Authorization code from Strava"),
    scope: Optional[str] = Query(None, description="Granted scopes"),
    state: Optional[str] = Query(None, description="State parameter for CSRF validation"),
    error: Optional[str] = Query(None, description="Error code if authorization failed"),
    db: Session = Depends(get_db),
) -> AuthResponse:
    """
    Handle the Strava OAuth callback.

    This endpoint is called by Strava after the user authorizes (or denies)
    the application. It exchanges the authorization code for tokens,
    creates or updates the user in the database, and returns a JWT token.

    Args:
        code: The authorization code from Strava
        scope: The scopes that were granted
        state: Optional CSRF state parameter
        error: Error code if the user denied authorization
        db: Database session

    Returns:
        AuthResponse: User profile and JWT token

    Raises:
        HTTPException: 400 if authorization was denied or code exchange fails

    Example:
        GET /auth/strava/callback?code=abc123&scope=read,activity:read_all
        Response: {
            "user": {"id": 1, "strava_id": 12345, ...},
            "token": {"access_token": "eyJ...", "token_type": "bearer"}
        }
    """
    # Handle authorization errors
    if error:
        logger.warning(f"Strava OAuth error: {error}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Strava authorization failed: {error}",
        )

    try:
        # Exchange code for tokens
        logger.info("Exchanging Strava authorization code")
        token_response = await strava_service.exchange_code(code)

        # Extract data from response
        access_token = token_response["access_token"]
        refresh_token = token_response["refresh_token"]
        expires_at = token_response["expires_at"]
        athlete = token_response["athlete"]

        strava_id = athlete["id"]
        firstname = athlete.get("firstname", "")
        lastname = athlete.get("lastname", "")
        name = f"{firstname} {lastname}".strip() or None
        profile_image = athlete.get("profile")
        ftp = athlete.get("ftp")
        weight = athlete.get("weight")  # Weight in kg from Strava

        # Find or create user
        user = db.query(User).filter(User.strava_id == strava_id).first()

        if user:
            # Update existing user
            logger.info(f"Updating existing user {user.id} (strava_id={strava_id})")
            user.name = name
            user.profile_image = profile_image
            user.strava_access_token = access_token
            user.strava_refresh_token = refresh_token
            user.strava_token_expires_at = expires_at
            # Sync FTP and weight from Strava (only if set in Strava)
            if ftp:
                user.ftp = ftp
            if weight:
                user.weight_kg = weight
        else:
            # Create new user
            logger.info(f"Creating new user for strava_id={strava_id}")
            user = User(
                strava_id=strava_id,
                name=name,
                profile_image=profile_image,
                ftp=ftp,
                weight_kg=weight,
                strava_access_token=access_token,
                strava_refresh_token=refresh_token,
                strava_token_expires_at=expires_at,
            )
            db.add(user)

        db.commit()
        db.refresh(user)

        # Create JWT token
        jwt_token = create_access_token(user_id=user.id)

        logger.info(f"Authentication successful for user {user.id}")

        return AuthResponse(
            user=UserResponse.model_validate(user),
            token=TokenResponse(
                access_token=jwt_token,
                token_type="bearer",
            ),
        )

    except StravaAPIError as e:
        logger.error(f"Strava API error during callback: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to authenticate with Strava: {e.message}",
        )
    except KeyError as e:
        logger.error(f"Missing field in Strava response: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid response from Strava",
        )


@router.post(
    "/strava/callback",
    response_model=AuthResponse,
    summary="Handle Strava OAuth callback (POST)",
    description="Alternative POST endpoint for OAuth callback, useful for frontend applications.",
)
async def strava_callback_post(
    request: StravaCallbackRequest,
    db: Session = Depends(get_db),
) -> AuthResponse:
    """
    Handle the Strava OAuth callback via POST.

    This is an alternative endpoint for frontend applications that prefer
    to send the authorization code via POST body instead of query parameters.

    Args:
        request: Request body containing the authorization code
        db: Database session

    Returns:
        AuthResponse: User profile and JWT token
    """
    return await strava_callback(code=request.code, db=db)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Returns the profile of the currently authenticated user.",
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """
    Get the current authenticated user's profile.

    Requires a valid JWT token in the Authorization header.

    Args:
        current_user: The authenticated user (injected by dependency)

    Returns:
        UserResponse: The user's profile data

    Example:
        GET /auth/me
        Authorization: Bearer eyJ...
        Response: {"id": 1, "strava_id": 12345, "name": "Jane Cyclist", ...}
    """
    return UserResponse.model_validate(current_user)


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update current user",
    description="Update the current user's profile including physical attributes and training preferences.",
)
async def update_current_user(
    updates: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    Update the current user's profile.

    Allows updating fields like FTP, physical attributes, and training preferences.

    Args:
        updates: Fields to update
        current_user: The authenticated user
        db: Database session

    Returns:
        UserResponse: The updated user profile
    """
    # Core fields
    if updates.ftp is not None:
        current_user.ftp = updates.ftp
    if updates.name is not None:
        current_user.name = updates.name

    # Physical attributes
    if updates.weight_kg is not None:
        current_user.weight_kg = updates.weight_kg
    if updates.age is not None:
        current_user.age = updates.age
    if updates.max_hr is not None:
        current_user.max_hr = updates.max_hr
    if updates.resting_hr is not None:
        current_user.resting_hr = updates.resting_hr

    # Training profile
    if updates.experience_level is not None:
        current_user.experience_level = updates.experience_level
    if updates.primary_discipline is not None:
        current_user.primary_discipline = updates.primary_discipline
    if updates.default_weekly_hours is not None:
        current_user.default_weekly_hours = updates.default_weekly_hours

    # Equipment
    if updates.has_power_meter is not None:
        current_user.has_power_meter = updates.has_power_meter
    if updates.has_indoor_trainer is not None:
        current_user.has_indoor_trainer = updates.has_indoor_trainer

    db.commit()
    db.refresh(current_user)

    logger.info(f"Updated user {current_user.id}")

    return UserResponse.model_validate(current_user)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh JWT token",
    description="Exchange a refresh token for a new access token.",
)
async def refresh_token(
    refresh_token: str = Query(..., description="Refresh token"),
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    Refresh an expired JWT access token.

    Uses a long-lived refresh token to obtain a new access token
    without requiring re-authentication.

    Args:
        refresh_token: The refresh token
        db: Database session

    Returns:
        TokenResponse: New access token

    Raises:
        HTTPException: 401 if refresh token is invalid
    """
    try:
        user_id = verify_refresh_token(refresh_token)
    except AuthenticationError as e:
        logger.warning(f"Invalid refresh token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    # Verify user still exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    # Create new access token
    new_token = create_access_token(user_id=user_id)

    logger.info(f"Refreshed token for user {user_id}")

    return TokenResponse(access_token=new_token, token_type="bearer")


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout",
    description="Logout the current user. Note: JWT tokens are stateless, so this is primarily for client-side token removal.",
)
async def logout(
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Logout the current user.

    Since JWT tokens are stateless, this endpoint doesn't invalidate
    the token server-side. It's primarily a signal to the client to
    remove the token from storage.

    For enhanced security, consider implementing a token blacklist
    or using short-lived tokens with refresh tokens.

    Args:
        current_user: The authenticated user

    Returns:
        None: Returns 204 No Content on success
    """
    logger.info(f"User {current_user.id} logged out")
    # In a production system, you might want to:
    # - Add the token to a blacklist
    # - Invalidate refresh tokens
    # - Clear server-side sessions
    return None


@router.post(
    "/strava/sync",
    response_model=UserResponse,
    summary="Sync profile from Strava",
    description="Fetch the latest athlete data from Strava and update the user's profile (weight, FTP).",
)
async def sync_from_strava(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    Sync profile data from Strava.

    Fetches the authenticated user's athlete profile from Strava and updates
    their local profile with weight and FTP (if available in Strava).

    Args:
        current_user: The authenticated user
        db: Database session

    Returns:
        UserResponse: The updated user profile

    Raises:
        HTTPException: 500 if Strava API call fails
    """
    try:
        # Ensure we have a valid access token
        access_token = current_user.strava_access_token
        if current_user.is_token_expired:
            logger.info(f"Refreshing expired Strava token for user {current_user.id}")
            token_response = await strava_service.refresh_tokens(
                current_user.strava_refresh_token
            )
            access_token = token_response["access_token"]
            current_user.strava_access_token = token_response["access_token"]
            current_user.strava_refresh_token = token_response["refresh_token"]
            current_user.strava_token_expires_at = token_response["expires_at"]

        # Fetch athlete data from Strava
        logger.info(f"Syncing Strava data for user {current_user.id}")
        athlete = await strava_service.get_athlete(access_token)

        # Update profile with Strava data
        updated_fields = []

        ftp = athlete.get("ftp")
        if ftp:
            current_user.ftp = ftp
            updated_fields.append(f"ftp={ftp}")

        weight = athlete.get("weight")
        if weight:
            current_user.weight_kg = weight
            updated_fields.append(f"weight_kg={weight}")

        # Update name if changed
        firstname = athlete.get("firstname", "")
        lastname = athlete.get("lastname", "")
        name = f"{firstname} {lastname}".strip() or None
        if name and name != current_user.name:
            current_user.name = name
            updated_fields.append(f"name={name}")

        # Update profile image if changed
        profile_image = athlete.get("profile")
        if profile_image and profile_image != current_user.profile_image:
            current_user.profile_image = profile_image
            updated_fields.append("profile_image")

        db.commit()
        db.refresh(current_user)

        if updated_fields:
            logger.info(f"Synced Strava data for user {current_user.id}: {', '.join(updated_fields)}")
        else:
            logger.info(f"No new data to sync from Strava for user {current_user.id}")

        return UserResponse.model_validate(current_user)

    except StravaAPIError as e:
        logger.error(f"Failed to sync from Strava: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync from Strava: {e.message}",
        )


@router.get(
    "/strava/refresh",
    response_model=TokenResponse,
    summary="Refresh Strava tokens",
    description="Refresh the user's Strava access token if expired.",
)
async def refresh_strava_tokens(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    Refresh the user's Strava access token.

    Checks if the current Strava token is expired and refreshes it
    if necessary. Returns a new JWT token.

    Args:
        current_user: The authenticated user
        db: Database session

    Returns:
        TokenResponse: New JWT token (Strava tokens stored in DB)

    Raises:
        HTTPException: 500 if Strava token refresh fails
    """
    if not current_user.is_token_expired:
        logger.debug(f"Strava token for user {current_user.id} is still valid")
        return TokenResponse(
            access_token=create_access_token(current_user.id),
            token_type="bearer",
        )

    try:
        logger.info(f"Refreshing Strava token for user {current_user.id}")
        token_response = await strava_service.refresh_tokens(
            current_user.strava_refresh_token
        )

        # Update user's Strava tokens
        current_user.strava_access_token = token_response["access_token"]
        current_user.strava_refresh_token = token_response["refresh_token"]
        current_user.strava_token_expires_at = token_response["expires_at"]

        db.commit()

        logger.info(f"Strava token refreshed for user {current_user.id}")

        return TokenResponse(
            access_token=create_access_token(current_user.id),
            token_type="bearer",
        )

    except StravaAPIError as e:
        logger.error(f"Failed to refresh Strava token: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh Strava token. Please re-authenticate.",
        )
