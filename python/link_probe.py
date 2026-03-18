from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from urllib.parse import SplitResult, urlsplit, urlunsplit

import requests
from requests_cache import CachedSession
from tqdm import tqdm

CACHE_ROOT = Path("data/cache")
HTTP_CACHE_PATH = CACHE_ROOT / "http_responses"
REQUEST_TIMEOUT_SECONDS = 15
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/136.0.0.0 Safari/537.36"
    )
}


@dataclass(frozen=True)
class ProbeResult:
    probe_url: str
    page_exists: bool
    probe_status: str
    http_status_code: int | None
    final_url: str
    error: str


def _ensure_cache_root() -> None:
    CACHE_ROOT.mkdir(parents=True, exist_ok=True)


def get_cached_session() -> CachedSession:
    _ensure_cache_root()
    return CachedSession(
        cache_name=str(HTTP_CACHE_PATH),
        backend="sqlite",
        expire_after=timedelta(days=7),
        allowable_methods=("GET",),
        allowable_codes=(200, 203, 300, 301, 302, 307, 308, 401, 403, 404, 405, 410),
        cache_control=True,
        stale_if_error=True,
    )


def canonicalize_probe_url(url: str) -> str:
    parts = urlsplit(url)
    probe_parts = SplitResult(
        scheme=parts.scheme,
        netloc=parts.netloc,
        path=parts.path,
        query=parts.query,
        fragment="",
    )
    return urlunsplit(probe_parts)


def probe_urls(
    urls: list[str],
    session: CachedSession | None = None,
) -> dict[str, ProbeResult]:
    own_session = session is None
    active_session = session or get_cached_session()

    try:
        results: dict[str, ProbeResult] = {}
        unique_urls = list(dict.fromkeys(urls))
        for url in tqdm(unique_urls, desc="Probing links", unit="url"):
            results[url] = probe_url(
                url=url,
                session=active_session,
            )
        return results
    finally:
        if own_session:
            active_session.close()


def probe_url(
    url: str,
    session: CachedSession,
) -> ProbeResult:
    parsed = urlsplit(url)
    scheme = parsed.scheme.lower()
    hostname = parsed.hostname

    if scheme not in {"http", "https"}:
        return ProbeResult(
            url, False, "unsupported_scheme", None, url, "Unsupported URL scheme"
        )
    if not hostname:
        return ProbeResult(url, False, "invalid_url", None, url, "Missing hostname")

    try:
        response = session.get(
            url,
            allow_redirects=True,
            timeout=REQUEST_TIMEOUT_SECONDS,
            headers=DEFAULT_HEADERS,
            stream=True,
        )
    except requests.Timeout as error:
        return ProbeResult(url, False, "timeout", None, url, str(error))
    except requests.ConnectionError as error:
        error_message = str(error)
        probe_status = (
            "dns_error"
            if "NameResolutionError" in error_message
            or "Failed to resolve" in error_message
            or "getaddrinfo failed" in error_message
            else "connection_error"
        )
        return ProbeResult(url, False, probe_status, None, url, error_message)
    except requests.RequestException as error:
        return ProbeResult(url, False, "request_error", None, url, str(error))

    status_code = response.status_code
    page_exists = status_code not in {404, 410}
    probe_status = "ok" if page_exists else "missing"
    final_url = str(response.url)
    response.close()
    return ProbeResult(
        probe_url=url,
        page_exists=page_exists,
        probe_status=probe_status,
        http_status_code=status_code,
        final_url=final_url,
        error="",
    )
