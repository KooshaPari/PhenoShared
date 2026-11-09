# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from urllib.parse import urljoin, urlparse

import requests
from requests.adapters import HTTPAdapter

from plane.utils.url import ValidatedExternalURL, validate_resolved_external_url


MAX_AVATAR_REDIRECTS = 3

PROVIDER_AVATAR_HOSTS = {
    "github": ("avatars.githubusercontent.com",),
    "gitlab": ("secure.gravatar.com", "www.gravatar.com"),
}

PROVIDER_AVATAR_DOMAIN_SUFFIXES = {
    "google": ("googleusercontent.com",),
    "github": ("githubusercontent.com",),
    "gitlab": ("gravatar.com",),
}


def _hostname_from_url(url: str | None) -> str | None:
    if not url:
        return None
    return urlparse(url).hostname


def get_avatar_url_policy(provider: str, provider_urls: tuple[str | None, ...] = ()) -> tuple[set[str], set[str]]:
    """Build the exact-host and suffix policy for provider avatar downloads."""
    allowed_hosts = set(PROVIDER_AVATAR_HOSTS.get(provider, ()))
    allowed_suffixes = set(PROVIDER_AVATAR_DOMAIN_SUFFIXES.get(provider, ()))

    for url in provider_urls:
        hostname = _hostname_from_url(url)
        if hostname:
            allowed_hosts.add(hostname)

    return allowed_hosts, allowed_suffixes


def validate_avatar_url(provider: str, avatar_url: str, provider_urls: tuple[str | None, ...] = ()) -> str:
    """Validate an OAuth avatar URL before fetching it from the server."""
    return validate_avatar_request_target(provider, avatar_url, provider_urls).url


def validate_avatar_request_target(
    provider: str,
    avatar_url: str,
    provider_urls: tuple[str | None, ...] = (),
) -> ValidatedExternalURL:
    """Validate an OAuth avatar URL and keep its verified public IP."""
    allowed_hosts, allowed_suffixes = get_avatar_url_policy(provider, provider_urls)
    return validate_resolved_external_url(
        avatar_url,
        allowed_hosts=allowed_hosts,
        allowed_domain_suffixes=allowed_suffixes,
    )


class PinnedDNSHTTPAdapter(HTTPAdapter):
    """Requests adapter that preserves TLS hostname checks while connecting to a pinned IP."""

    def __init__(self, hostname: str, *args, **kwargs):
        self.hostname = hostname
        super().__init__(*args, **kwargs)

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        pool_kwargs.setdefault("assert_hostname", self.hostname)
        pool_kwargs.setdefault("server_hostname", self.hostname)
        return super().init_poolmanager(connections, maxsize, block=block, **pool_kwargs)


def _netloc_with_host(host: str, port: int | None) -> str:
    if ":" in host:
        host = f"[{host}]"
    return f"{host}:{port}" if port else host


def _request_url_for_verified_ip(target: ValidatedExternalURL) -> str:
    parsed_url = urlparse(target.url)
    return parsed_url._replace(netloc=_netloc_with_host(target.ip_address, parsed_url.port)).geturl()


def _host_header_for_target(target: ValidatedExternalURL) -> str:
    parsed_url = urlparse(target.url)
    return _netloc_with_host(target.hostname, parsed_url.port)


def get_pinned_avatar_response(
    target: ValidatedExternalURL,
    *,
    headers: dict | None = None,
    timeout: int = 10,
) -> requests.Response:
    """Fetch a validated avatar URL through its already-verified public IP."""
    request_headers = {**(headers or {}), "Host": _host_header_for_target(target)}
    request_url = _request_url_for_verified_ip(target)

    session = requests.Session()
    parsed_url = urlparse(target.url)
    if parsed_url.scheme == "https":
        session.mount(
            f"{parsed_url.scheme}://{_netloc_with_host(target.ip_address, parsed_url.port)}",
            PinnedDNSHTTPAdapter(target.hostname),
        )
    return session.get(
        request_url,
        timeout=timeout,
        headers=request_headers,
        stream=True,
        allow_redirects=False,
    )


def get_validated_avatar_response(
    provider: str,
    avatar_url: str,
    *,
    provider_urls: tuple[str | None, ...] = (),
    headers: dict | None = None,
    timeout: int = 10,
) -> requests.Response:
    """Fetch a provider avatar after validating the initial URL and each redirect."""
    current_target = validate_avatar_request_target(provider, avatar_url, provider_urls)

    for _ in range(MAX_AVATAR_REDIRECTS + 1):
        response = get_pinned_avatar_response(current_target, timeout=timeout, headers=headers)

        if not response.is_redirect:
            return response

        redirect_url = response.headers.get("Location")
        if not redirect_url:
            return response

        current_target = validate_avatar_request_target(
            provider,
            urljoin(current_target.url, redirect_url),
            provider_urls,
        )

    raise ValueError("Too many avatar download redirects")
