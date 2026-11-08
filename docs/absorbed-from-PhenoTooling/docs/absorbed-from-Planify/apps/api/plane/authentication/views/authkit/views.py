# AuthKit Token Exchange Views
# These views bridge AuthKit token management with Plane's session auth.
#
# AuthKit flow:
# 1. /auth/sign-in → POST email+password → calls AuthKit API → returns tokens + user
# 2. /auth/me     → GET with Bearer token → validates token → returns user
# 3. /auth/refresh → POST refresh token → calls AuthKit API → returns new tokens
# 4. /auth/sign-out → POST → clears session cookies

from datetime import datetime, timezone
from typing import Any

import httpx
from django.conf import settings
from django.http import JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

AGILEPLUS_AUTHKIT_URL = getattr(settings, "AUTHKIT_API_URL", "http://localhost:8001")
AGILEPLUS_AUTHKIT_KEY = getattr(settings, "AUTHKIT_API_KEY", "")
VERIFY_TLS = getattr(settings, "AUTHKIT_VERIFY_TLS", True)


def get_authkit_client() -> httpx.Client:
    """HTTPX client configured for AuthKit API calls."""
    return httpx.Client(
        base_url=AGILEPLUS_AUTHKIT_URL,
        headers={
            "X-API-Key": AGILEPLUS_AUTHKIT_KEY,
            "Content-Type": "application/json",
        },
        timeout=15.0,
        verify=VERIFY_TLS,
    )


def authkit_request(method: str, path: str, **kwargs) -> httpx.Response:
    """Make an authenticated request to AuthKit API."""
    with get_authkit_client() as client:
        return getattr(client, method)(path, **kwargs)


@api_view(["POST"])
@permission_classes([AllowAny])
def sign_in(request: Request) -> Response:
    """
    Exchange credentials for AuthKit tokens.
    
    Body: { "email": str, "password": str }
    Returns: { "user": User, "tokens": { "access_token", "refresh_token", "expires_at" } }
    """
    email = request.data.get("email", "").strip()
    password = request.data.get("password", "")

    if not email or not password:
        return Response(
            {"error": "email and password are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        resp = authkit_request(
            "post",
            "/auth/token",
            json={"email": email, "password": password},
        )
    except httpx.TimeoutException:
        return Response(
            {"error": "AuthKit service unavailable (timeout)"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except httpx.ConnectError:
        return Response(
            {"error": "AuthKit service unavailable (connection failed)"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except Exception as exc:
        return Response(
            {"error": f"AuthKit request failed: {exc}"},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    if resp.status_code == 401:
        return Response(
            {"error": "Invalid credentials"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if resp.status_code >= 400:
        return Response(
            {"error": resp.json().get("detail", "AuthKit error")},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    data = resp.json()

    # Transform AuthKit response to our format
    tokens = data.get("tokens", {})
    user = data.get("user", {})

    # Set httpOnly session cookie as a convenience
    response = Response({
        "user": user,
        "tokens": tokens,
    })

    access_token = tokens.get("access_token", "")
    if access_token:
        response.set_cookie(
            key="authkit_access_token",
            value=access_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=tokens.get("expires_in", 3600),
        )
        refresh_token = tokens.get("refresh_token")
        if refresh_token:
            response.set_cookie(
                key="authkit_refresh_token",
                value=refresh_token,
                httponly=True,
                secure=True,
                samesite="lax",
                max_age=60 * 60 * 24 * 7,  # 7 days
            )

    return response


@api_view(["GET"])
@permission_classes([AllowAny])
def me(request: Request) -> Response:
    """
    Validate an AuthKit token and return the associated user.
    
    Auth header: Bearer <access_token>
    OR Cookie: authkit_access_token
    """
    auth_header = request.headers.get("Authorization", "")
    token = None

    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    else:
        token = request.COOKIES.get("authkit_access_token")

    if not token:
        return Response({"error": "No token provided"}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        resp = authkit_request("get", "/auth/me", headers={"Authorization": f"Bearer {token}"})
    except httpx.TimeoutException:
        return Response({"error": "AuthKit service unavailable"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except Exception as exc:
        return Response(
            {"error": f"AuthKit request failed: {exc}"},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    if resp.status_code == 401:
        return Response({"error": "Invalid or expired token"}, status=status.HTTP_401_UNAUTHORIZED)

    if resp.status_code >= 400:
        return Response({"error": "Token validation failed"}, status=status.HTTP_502_BAD_GATEWAY)

    return Response(resp.json())


@api_view(["POST"])
@permission_classes([AllowAny])
def refresh(request: Request) -> Response:
    """
    Refresh an AuthKit access token using a refresh token.
    
    Body: { "refresh_token": str }
    OR Cookie: authkit_refresh_token
    """
    refresh_token = request.data.get("refresh_token") or request.COOKIES.get("authkit_refresh_token")

    if not refresh_token:
        return Response(
            {"error": "No refresh token provided"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        resp = authkit_request(
            "post",
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        )
    except httpx.TimeoutException:
        return Response({"error": "AuthKit service unavailable"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except Exception as exc:
        return Response(
            {"error": f"AuthKit request failed: {exc}"},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    if resp.status_code == 401:
        return Response({"error": "Invalid or expired refresh token"}, status=status.HTTP_401_UNAUTHORIZED)

    if resp.status_code >= 400:
        return Response({"error": "Token refresh failed"}, status=status.HTTP_502_BAD_GATEWAY)

    tokens = resp.json().get("tokens", {})
    response = Response({"tokens": tokens})

    access_token = tokens.get("access_token", "")
    if access_token:
        response.set_cookie(
            key="authkit_access_token",
            value=access_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=tokens.get("expires_in", 3600),
        )

    return response


@api_view(["POST"])
@permission_classes([AllowAny])
def sign_out(request: Request) -> Response:
    """
    Sign out - revoke AuthKit tokens and clear cookies.
    
    Auth header: Bearer <access_token>
    """
    auth_header = request.headers.get("Authorization", "")
    token = None
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]

    # Try to revoke token with AuthKit (best-effort)
    if token:
        try:
            authkit_request(
                "post",
                "/auth/revoke",
                json={"token": token},
            )
        except Exception:
            pass  # Best-effort: don't fail if AuthKit is unreachable

    # Clear cookies regardless
    response = Response({"message": "Signed out"})
    response.delete_cookie("authkit_access_token")
    response.delete_cookie("authkit_refresh_token")
    return response


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request: Request) -> Response:
    """Health check for AuthKit integration."""
    try:
        resp = authkit_request("get", "/health")
        authkit_ok = resp.status_code == 200
    except Exception:
        authkit_ok = False

    return Response({
        "status": "ok",
        "authkit": "connected" if authkit_ok else "unavailable",
        "configured": bool(AGILEPLUS_AUTHKIT_URL),
    })
