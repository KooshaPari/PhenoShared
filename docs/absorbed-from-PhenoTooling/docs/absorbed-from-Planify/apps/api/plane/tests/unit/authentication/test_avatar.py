# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest

from plane.authentication.adapter.avatar import (
    get_pinned_avatar_response,
    get_avatar_url_policy,
    get_validated_avatar_response,
    validate_avatar_request_target,
    validate_avatar_url,
)

PUBLIC_TEST_IP = ".".join(("8", "8", "8", "8"))
GITLAB_PROVIDER_HOST = ".".join(("gitlab", "example", "com"))
GRAVATAR_SUFFIX = ".".join(("gravatar", "com"))


@pytest.mark.unit
class TestAvatarURLPolicy:
    """Test OAuth avatar URL policies."""

    def test_includes_provider_urls_as_exact_hosts(self):
        """Test self-hosted OAuth providers can serve avatars from their configured host."""
        token_url = f"https://{GITLAB_PROVIDER_HOST}/oauth/token"
        userinfo_url = f"https://{GITLAB_PROVIDER_HOST}/api/v4/user"
        allowed_hosts, allowed_suffixes = get_avatar_url_policy(
            "gitlab",
            (token_url, userinfo_url),
        )

        assert allowed_hosts.issuperset({GITLAB_PROVIDER_HOST})
        assert allowed_suffixes.issuperset({GRAVATAR_SUFFIX})

    def test_github_allows_githubusercontent_avatar_hosts(self, monkeypatch):
        """Test GitHub avatar hosts are allowed."""
        monkeypatch.setattr(
            "plane.utils.url.socket.getaddrinfo",
            lambda hostname, port: [(None, None, None, None, ("8.8.8.8", 0))],
        )

        assert (
            validate_avatar_url("github", "https://avatars.githubusercontent.com/u/1")
            == "https://avatars.githubusercontent.com/u/1"
        )

    def test_blocks_unlisted_avatar_hosts(self, monkeypatch):
        """Test provider avatar URLs must match the provider policy."""
        monkeypatch.setattr(
            "plane.utils.url.socket.getaddrinfo",
            lambda hostname, port: [(None, None, None, None, ("8.8.8.8", 0))],
        )

        with pytest.raises(ValueError, match="host is not allowed"):
            validate_avatar_url("github", "https://attacker.example/avatar.png")

    def test_blocks_private_provider_avatar_resolution(self, monkeypatch):
        """Test allowed provider hosts are rejected when DNS resolves internally."""
        monkeypatch.setattr(
            "plane.utils.url.socket.getaddrinfo",
            lambda hostname, port: [(None, None, None, None, ("127.0.0.1", 0))],
        )

        with pytest.raises(ValueError, match="non-public networks"):
            validate_avatar_url("github", "https://avatars.githubusercontent.com/u/1")


@pytest.mark.unit
class TestValidatedAvatarResponse:
    """Test avatar downloads validate every network target."""

    def test_validates_redirect_targets_before_following(self, monkeypatch):
        """Test redirects to disallowed hosts are blocked before the second request."""
        calls = []

        class RedirectResponse:
            is_redirect = True
            headers = {"Location": "https://metadata.google.internal/latest"}

        def fake_get(target, **kwargs):
            calls.append((target, kwargs))
            return RedirectResponse()

        monkeypatch.setattr(
            "plane.utils.url.socket.getaddrinfo",
            lambda hostname, port: [(None, None, None, None, ("8.8.8.8", 0))],
        )
        monkeypatch.setattr("plane.authentication.adapter.avatar.get_pinned_avatar_response", fake_get)

        with pytest.raises(ValueError, match="host is not allowed"):
            get_validated_avatar_response("github", "https://avatars.githubusercontent.com/u/1")

        assert len(calls) == 1
        assert calls[0][0].url == "https://avatars.githubusercontent.com/u/1"

    def test_returns_non_redirect_response(self, monkeypatch):
        """Test successful avatar downloads return the fetched response."""
        class OkResponse:
            is_redirect = False
            headers = {}

        response = OkResponse()

        monkeypatch.setattr(
            "plane.utils.url.socket.getaddrinfo",
            lambda hostname, port: [(None, None, None, None, ("8.8.8.8", 0))],
        )
        monkeypatch.setattr(
            "plane.authentication.adapter.avatar.get_pinned_avatar_response",
            lambda target, **kwargs: response,
        )

        assert get_validated_avatar_response("github", "https://avatars.githubusercontent.com/u/1") is response

    def test_pinned_fetch_uses_verified_ip_and_original_host_header(self, monkeypatch):
        """Test avatar fetches use the resolved public IP instead of resolving again."""
        calls = []

        class OkResponse:
            is_redirect = False
            headers = {}

        def fake_get(self, url, **kwargs):
            calls.append((url, kwargs))
            return OkResponse()

        monkeypatch.setattr(
            "plane.utils.url.socket.getaddrinfo",
            lambda hostname, port: [(None, None, None, None, (PUBLIC_TEST_IP, 0))],
        )
        monkeypatch.setattr("plane.authentication.adapter.avatar.requests.Session.get", fake_get)

        target = validate_avatar_request_target("github", "https://avatars.githubusercontent.com/u/1")
        response = get_pinned_avatar_response(target)

        assert response.is_redirect is False
        assert calls[0][0] == f"https://{PUBLIC_TEST_IP}/u/1"
        assert calls[0][1]["headers"]["Host"] == "avatars.githubusercontent.com"
        assert calls[0][1]["allow_redirects"] is False
