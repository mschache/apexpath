"""
Strava API integration service.

Handles all interactions with the Strava API including OAuth authentication,
token management, and activity data retrieval.
"""

import asyncio
import logging
from typing import Any, Optional
from urllib.parse import urlencode

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class StravaAPIError(Exception):
    """Exception raised when Strava API returns an error."""

    def __init__(self, message: str, status_code: int = None, response_body: dict = None):
        self.message = message
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(self.message)


class StravaRateLimitError(StravaAPIError):
    """Exception raised when Strava API rate limit is exceeded."""

    def __init__(self, retry_after: int = 900):
        self.retry_after = retry_after
        super().__init__(
            f"Strava API rate limit exceeded. Retry after {retry_after} seconds.",
            status_code=429
        )


class StravaService:
    """
    Service for interacting with the Strava API.

    Provides methods for OAuth authentication, token management,
    and fetching athlete and activity data.

    Attributes:
        client_id: Strava OAuth client ID
        client_secret: Strava OAuth client secret
        auth_url: Strava authorization URL
        token_url: Strava token exchange URL
        api_base_url: Strava API base URL
    """

    # OAuth scopes required for the application
    SCOPES = "read,activity:read_all"

    # Rate limiting configuration
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # seconds

    def __init__(self):
        """Initialize the Strava service with configuration from settings."""
        self.client_id = settings.STRAVA_CLIENT_ID
        self.client_secret = settings.STRAVA_CLIENT_SECRET
        self.auth_url = settings.STRAVA_AUTH_URL
        self.token_url = settings.STRAVA_TOKEN_URL
        self.api_base_url = settings.STRAVA_API_BASE_URL

    def get_authorization_url(self, redirect_uri: str, state: Optional[str] = None) -> str:
        """
        Generate the Strava OAuth authorization URL.

        Creates a URL that the user should be redirected to in order to
        authorize the application to access their Strava data.

        Args:
            redirect_uri: The URI to redirect to after authorization
            state: Optional state parameter for CSRF protection

        Returns:
            str: The full authorization URL with query parameters

        Example:
            >>> service = StravaService()
            >>> url = service.get_authorization_url("http://localhost:8000/callback")
            >>> print(url)
            'https://www.strava.com/oauth/authorize?client_id=123&...'
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": self.SCOPES,
            "approval_prompt": "auto",
        }

        if state:
            params["state"] = state

        return f"{self.auth_url}?{urlencode(params)}"

    async def _make_request(
        self,
        method: str,
        url: str,
        headers: dict = None,
        params: dict = None,
        data: dict = None,
        timeout: float = 30.0,
    ) -> dict:
        """
        Make an HTTP request with retry logic and rate limit handling.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full URL to request
            headers: Optional request headers
            params: Optional query parameters
            data: Optional request body data
            timeout: Request timeout in seconds

        Returns:
            dict: Parsed JSON response

        Raises:
            StravaRateLimitError: If rate limit is exceeded after retries
            StravaAPIError: If the API returns an error
        """
        async with httpx.AsyncClient(timeout=timeout) as client:
            for attempt in range(self.MAX_RETRIES):
                try:
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=headers,
                        params=params,
                        data=data,
                    )

                    # Handle rate limiting
                    if response.status_code == 429:
                        retry_after = int(response.headers.get("Retry-After", 900))
                        logger.warning(
                            f"Strava rate limit hit. Attempt {attempt + 1}/{self.MAX_RETRIES}. "
                            f"Retry after {retry_after}s"
                        )

                        if attempt < self.MAX_RETRIES - 1:
                            # Wait a bit before retrying (exponential backoff)
                            wait_time = min(self.RETRY_DELAY * (2 ** attempt), 30)
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            raise StravaRateLimitError(retry_after=retry_after)

                    # Handle other errors
                    if response.status_code >= 400:
                        try:
                            error_body = response.json()
                        except Exception:
                            error_body = {"raw": response.text}

                        error_message = error_body.get("message", f"HTTP {response.status_code}")
                        logger.error(
                            f"Strava API error: {response.status_code} - {error_message}"
                        )
                        raise StravaAPIError(
                            message=error_message,
                            status_code=response.status_code,
                            response_body=error_body,
                        )

                    return response.json()

                except httpx.TimeoutException:
                    logger.warning(
                        f"Strava API timeout. Attempt {attempt + 1}/{self.MAX_RETRIES}"
                    )
                    if attempt < self.MAX_RETRIES - 1:
                        await asyncio.sleep(self.RETRY_DELAY)
                        continue
                    raise StravaAPIError("Request timed out", status_code=408)

                except httpx.RequestError as e:
                    logger.error(f"Strava API request error: {str(e)}")
                    if attempt < self.MAX_RETRIES - 1:
                        await asyncio.sleep(self.RETRY_DELAY)
                        continue
                    raise StravaAPIError(f"Request failed: {str(e)}")

    async def exchange_code(self, code: str) -> dict:
        """
        Exchange an authorization code for access and refresh tokens.

        This is called after the user authorizes the application on Strava
        and is redirected back with an authorization code.

        Args:
            code: The authorization code from the OAuth callback

        Returns:
            dict: Token response containing:
                - access_token: Bearer token for API requests
                - refresh_token: Token for refreshing access
                - expires_at: Unix timestamp when access_token expires
                - athlete: Athlete profile data

        Raises:
            StravaAPIError: If token exchange fails

        Example:
            >>> service = StravaService()
            >>> tokens = await service.exchange_code("abc123")
            >>> print(tokens["athlete"]["firstname"])
            'Jane'
        """
        logger.info("Exchanging authorization code for tokens")

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
        }

        response = await self._make_request(
            method="POST",
            url=self.token_url,
            data=data,
        )

        logger.info(f"Token exchange successful for athlete {response.get('athlete', {}).get('id')}")
        return response

    async def refresh_tokens(self, refresh_token: str) -> dict:
        """
        Refresh an expired access token using a refresh token.

        Strava access tokens expire after 6 hours. Use this method to
        obtain a new access token without requiring user re-authorization.

        Args:
            refresh_token: The refresh token from a previous token response

        Returns:
            dict: New token response containing:
                - access_token: New bearer token
                - refresh_token: New refresh token (may be the same)
                - expires_at: Unix timestamp when new access_token expires

        Raises:
            StravaAPIError: If token refresh fails

        Example:
            >>> service = StravaService()
            >>> new_tokens = await service.refresh_tokens("old_refresh_token")
            >>> print(new_tokens["access_token"])
            'new_access_token_here'
        """
        logger.info("Refreshing Strava access token")

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        response = await self._make_request(
            method="POST",
            url=self.token_url,
            data=data,
        )

        logger.info("Token refresh successful")
        return response

    async def get_athlete(self, access_token: str) -> dict:
        """
        Get the authenticated athlete's profile.

        Args:
            access_token: Valid Strava access token

        Returns:
            dict: Athlete profile containing:
                - id: Strava athlete ID
                - firstname: First name
                - lastname: Last name
                - profile: URL to profile picture
                - ftp: Functional Threshold Power (if set)
                - And other athlete fields...

        Raises:
            StravaAPIError: If request fails

        Example:
            >>> service = StravaService()
            >>> athlete = await service.get_athlete("access_token_here")
            >>> print(f"{athlete['firstname']} {athlete['lastname']}")
            'Jane Cyclist'
        """
        logger.debug("Fetching athlete profile")

        headers = {"Authorization": f"Bearer {access_token}"}

        response = await self._make_request(
            method="GET",
            url=f"{self.api_base_url}/athlete",
            headers=headers,
        )

        return response

    async def get_activities(
        self,
        access_token: str,
        after: Optional[int] = None,
        before: Optional[int] = None,
        page: int = 1,
        per_page: int = 30,
    ) -> list:
        """
        Fetch a list of activities for the authenticated athlete.

        Args:
            access_token: Valid Strava access token
            after: Only return activities after this Unix timestamp
            before: Only return activities before this Unix timestamp
            page: Page number for pagination (1-indexed)
            per_page: Number of activities per page (max 200)

        Returns:
            list: List of activity summaries, each containing:
                - id: Activity ID
                - name: Activity name
                - type: Activity type (Ride, Run, etc.)
                - start_date: ISO timestamp
                - distance: Distance in meters
                - moving_time: Moving time in seconds
                - average_watts: Average power (if available)
                - And other activity fields...

        Raises:
            StravaAPIError: If request fails

        Example:
            >>> service = StravaService()
            >>> activities = await service.get_activities(token, page=1, per_page=10)
            >>> for activity in activities:
            ...     print(f"{activity['name']}: {activity['distance']}m")
        """
        logger.debug(f"Fetching activities (page={page}, per_page={per_page})")

        headers = {"Authorization": f"Bearer {access_token}"}
        params = {
            "page": page,
            "per_page": min(per_page, 200),  # Strava max is 200
        }

        if after:
            params["after"] = after
        if before:
            params["before"] = before

        response = await self._make_request(
            method="GET",
            url=f"{self.api_base_url}/athlete/activities",
            headers=headers,
            params=params,
        )

        logger.debug(f"Fetched {len(response)} activities")
        return response

    async def get_activity(self, access_token: str, activity_id: int) -> dict:
        """
        Get detailed information about a specific activity.

        Args:
            access_token: Valid Strava access token
            activity_id: The Strava activity ID

        Returns:
            dict: Detailed activity data including segments and splits

        Raises:
            StravaAPIError: If request fails
        """
        logger.debug(f"Fetching activity {activity_id}")

        headers = {"Authorization": f"Bearer {access_token}"}

        response = await self._make_request(
            method="GET",
            url=f"{self.api_base_url}/activities/{activity_id}",
            headers=headers,
        )

        return response

    async def get_activity_streams(
        self,
        access_token: str,
        activity_id: int,
        stream_types: Optional[list[str]] = None,
    ) -> dict:
        """
        Get data streams for a specific activity.

        Streams contain time-series data like power, heart rate, cadence, etc.

        Args:
            access_token: Valid Strava access token
            activity_id: The Strava activity ID
            stream_types: List of stream types to fetch. Defaults to common types.
                Available types: time, distance, altitude, velocity_smooth,
                heartrate, cadence, watts, temp, moving, grade_smooth

        Returns:
            dict: Stream data keyed by stream type, each containing:
                - data: Array of data points
                - series_type: Type of stream
                - resolution: Data resolution

        Raises:
            StravaAPIError: If request fails

        Example:
            >>> service = StravaService()
            >>> streams = await service.get_activity_streams(token, 12345)
            >>> power_data = streams.get("watts", {}).get("data", [])
            >>> print(f"Power samples: {len(power_data)}")
        """
        if stream_types is None:
            stream_types = [
                "time",
                "distance",
                "altitude",
                "velocity_smooth",
                "heartrate",
                "cadence",
                "watts",
                "temp",
                "moving",
                "grade_smooth",
            ]

        logger.debug(f"Fetching streams for activity {activity_id}: {stream_types}")

        headers = {"Authorization": f"Bearer {access_token}"}
        params = {
            "keys": ",".join(stream_types),
            "key_by_type": "true",
        }

        response = await self._make_request(
            method="GET",
            url=f"{self.api_base_url}/activities/{activity_id}/streams",
            headers=headers,
            params=params,
        )

        # Convert list response to dict keyed by type
        if isinstance(response, list):
            streams_dict = {}
            for stream in response:
                stream_type = stream.get("type")
                if stream_type:
                    streams_dict[stream_type] = stream
            return streams_dict

        return response

    async def get_activity_zones(self, access_token: str, activity_id: int) -> list:
        """
        Get zone distributions for an activity (heart rate and power zones).

        Args:
            access_token: Valid Strava access token
            activity_id: The Strava activity ID

        Returns:
            list: Zone distribution data

        Raises:
            StravaAPIError: If request fails
        """
        logger.debug(f"Fetching zones for activity {activity_id}")

        headers = {"Authorization": f"Bearer {access_token}"}

        response = await self._make_request(
            method="GET",
            url=f"{self.api_base_url}/activities/{activity_id}/zones",
            headers=headers,
        )

        return response


# Singleton instance for use across the application
strava_service = StravaService()
