# Copyright (c) 2023-present Plane contributors
# SPDX-License-Identifier: AGPL-3.0-only
"""
AuthKitTokenAuthentication - DRF authentication backend for AuthKit tokens.

AuthKit issues JWT-like tokens that are validated against the AuthKit server.
This backend:
  1. Extracts the X-Api-Key / Bearer token from request headers
  2. Validates the token against the AuthKit server (or local cache)
  3. Returns the associated Plane User workspace membership

Settings (environment variables):
  AUTHKIT_API_URL        - Base URL of the AuthKit auth server
  AUTHKIT_API_KEY        - Server-side API key for AuthKit admin endpoints
  AUTHKIT_VERIFY_SSL     - Whether to verify SSL certs (default: True)
  AUTHKIT_CACHE_TTL_SEC  - How long to cache token validations (default: 300)
"""

import logging
from typing import Optional, Tuple

import requests
from django.conf import settings
from rest_framework import authentication, exceptions

from plane.db.models import User, WorkspaceMember

logger = logging.getLogger("plane.authentication")


class AuthKitTokenAuthentication(authentication.BaseAuthentication):
    """
    DRF authentication class that validates AuthKit-issued tokens.

    Matches Plane's APIKeyAuthentication pattern but validates against
    AuthKit's /auth/me endpoint instead of the database.

    Header: Authorization: Bearer <token>
            or  X-Api-Key: <token>
    """

    keyword = "Bearer"
    x_header_keyword = "X-Api-Key"

    def authenticate(self, request) -> Optional[Tuple[User, dict]]:
        """
        Returns (user, auth_info) if the token is valid, None otherwise.

        auth_info is a dict containing:
          authkit_token: the raw token
          authkit_user_id: user ID from AuthKit
          workspace_role: their role in the requested workspace
        """
        token = self._extract_token(request)
        if not token:
            return None

        auth_info = self._validate_token(token)
        if not auth_info:
            return None

        user = self._get_or_create_user(auth_info)
        if not user or not user.is_active:
            raise exceptions.AuthenticationFailed("User account is disabled.")

        return (user, auth_info)

    def _extract_token(self, request) -> Optional[str]:
        """Pull token from Authorization: Bearer or X-Api-Key header."""
        auth = request.META.get("HTTP_AUTHORIZATION", "")
        if auth.startswith(f"{self.keyword} "):
            return auth[len(self.keyword) + 1 :].strip()

        # Also support X-Api-Key for API clients
        api_key = request.META.get(f"HTTP_{self.x_header_keyword.upper().replace('-', '_')}", "")
        return api_key.strip() or None

    def _validate_token(self, token: str) -> Optional[dict]:
        """
        Validate token against AuthKit server.

        Returns auth_info dict on success, None on failure.
        Results are cached for AUTHKIT_CACHE_TTL_SEC seconds.
        """
        authkit_url = getattr(settings, "AUTHKIT_API_URL", None)
        if not authkit_url:
            logger.warning("AUTHKIT_API_URL not set — AuthKit auth disabled")
            return None

        cache_key = f"authkit:token:{token[:16]}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        try:
            response = requests.post(
                f"{authkit_url.rstrip('/')}/auth/me",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "X-Api-Key": getattr(settings, "AUTHKIT_API_KEY", ""),
                },
                timeout=10,
                verify=getattr(settings, "AUTHKIT_VERIFY_SSL", True),
            )

            if response.status_code == 401:
                return None
            if response.status_code != 200:
                logger.warning(
                    "AuthKit returned %s: %s", response.status_code, response.text[:200]
                )
                return None

            auth_info = response.json()
            self._set_cache(cache_key, auth_info)
            return auth_info

        except requests.Timeout:
            logger.error("AuthKit auth/me request timed out")
            return None
        except requests.RequestException as exc:
            logger.error("AuthKit auth/me request failed: %s", exc)
            return None

    def _get_or_create_user(self, auth_info: dict) -> Optional[User]:
        """
        Map AuthKit user info to a Plane User.

        AuthKit sends: { user_id, email, first_name, last_name, avatar_url }
        """
        try:
            user, _ = User.objects.update_or_create(
                {
                    "email": auth_info.get("email", ""),
                    "first_name": auth_info.get("first_name", "")[:50],
                    "last_name": auth_info.get("last_name", "")[:50],
                    "avatar": auth_info.get("avatar_url") or "",
                    "is_active": True,
                },
                id=auth_info.get("user_id"),
            )
            return user
        except Exception as exc:
            logger.error("Failed to get/create user from AuthKit info: %s", exc)
            return None

    def authenticate_header(self, request) -> str:
        """Return WWW-Authenticate header value for 401 responses."""
        return f'{self.keyword} realm="agileplus-plane"'

    # -------------------------------------------------------------------------
    # Simple in-memory cache (replace with Redis for multi-process deployments)
    # -------------------------------------------------------------------------

    _cache: dict = {}

    def _get_cache(self, key: str) -> Optional[dict]:
        import time

        entry = self._cache.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.time() > expires_at:
            del self._cache[key]
            return None
        return value

    def _set_cache(self, key: str, value: dict, ttl: int = None) -> None:
        import time

        if ttl is None:
            ttl = getattr(settings, "AUTHKIT_CACHE_TTL_SEC", 300)
        self._cache[key] = (value, time.time() + ttl)


def get_workspace_role_from_auth_info(
    user: User, workspace_slug: str, auth_info: dict
) -> Optional[str]:
    """
    Determine the user's role in a workspace based on AuthKit auth_info.

    Falls back to Plane's own WorkspaceMember table if AuthKit doesn't
    provide workspace role information.
    """
    # AuthKit can embed workspace roles in the token response
    workspace_roles = auth_info.get("workspace_roles", {})
    if workspace_slug in workspace_roles:
        return workspace_roles[workspace_slug]

    # Fall back to Plane's own membership table
    try:
        member = WorkspaceMember.objects.get(
            workspace__slug=workspace_slug, user=user, is_active=True
        )
        return member.role
    except WorkspaceMember.DoesNotExist:
        return None
