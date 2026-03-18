from pathlib import Path
from urllib.parse import urljoin, urlsplit

import pandas as pd
import tldextract
from bs4 import BeautifulSoup
from python.link_probe import canonicalize_probe_url, get_cached_session, probe_urls

URL = "https://www.un.org/en/site-index"
LINK_CONTAINER_SELECTOR = "#node-133272 > div > div > div > div"
OUTPUT_PATH = Path("data/output/site-index-links.csv")
TIMEOUT_SECONDS = 30
TLD_EXTRACTOR = tldextract.TLDExtract(suffix_list_urls=())


def normalize_hostname(value: str) -> str:
    return value.strip().lower().rstrip(".")


def extract_domain_parts(hostname: str) -> tuple[str, str, str]:
    normalized_hostname = normalize_hostname(hostname)
    if not normalized_hostname:
        return "", "", ""

    extracted = TLD_EXTRACTOR(normalized_hostname)
    registered_domain = extracted.top_domain_under_public_suffix
    cname = extracted.subdomain
    suffix = extracted.suffix
    return registered_domain, cname, suffix


def fetch_html(url: str) -> str:
    with get_cached_session() as session:
        response = session.get(
            url,
            timeout=TIMEOUT_SECONDS,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/136.0.0.0 Safari/537.36"
                )
            },
        )
    response.raise_for_status()
    return response.text


def classify_un_link(hostname: str, cname: str, path: str) -> tuple[bool, str]:
    if hostname == "un.org" and cname:
        return True, "subdomain"
    if hostname == "un.org":
        normalized_path = path.strip("/")
        if normalized_path:
            return False, "path"
        return False, "root"
    return False, "external"


def build_dataframe(html: str, base_url: str) -> pd.DataFrame:
    soup = BeautifulSoup(html, "html.parser")
    container = soup.select_one(LINK_CONTAINER_SELECTOR)
    if container is None:
        raise ValueError(f"Could not find link container: {LINK_CONTAINER_SELECTOR}")

    rows: list[dict[str, object]] = []

    for index, anchor in enumerate(container.select("a[href]"), start=1):
        href_value = anchor.get("href")
        href = href_value.strip() if isinstance(href_value, str) else ""
        if not href:
            continue

        absolute_url = urljoin(base_url, href)
        parsed = urlsplit(absolute_url)
        full_hostname = normalize_hostname(parsed.hostname or "")
        registered_domain, cname, suffix = extract_domain_parts(full_hostname)
        effective_cname = "" if cname == "www" else cname
        hostname = registered_domain or full_hostname
        link_text = " ".join(anchor.stripped_strings)
        is_cname, un_link_type = classify_un_link(
            hostname, effective_cname, parsed.path
        )

        rows.append(
            {
                "source_url": base_url,
                "link_index": index,
                "text": link_text,
                "href": href,
                "absolute_url": absolute_url,
                "probe_url": canonicalize_probe_url(absolute_url),
                "scheme": parsed.scheme,
                "full_hostname": full_hostname,
                "hostname": hostname,
                "cname": effective_cname,
                "public_suffix": suffix,
                "path": parsed.path,
                "query": parsed.query,
                "fragment": parsed.fragment,
                "is_cname": is_cname,
                "un_link_type": un_link_type,
            }
        )

    return pd.DataFrame(rows)


def attach_probe_results(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.assign(
            page_exists=pd.Series(dtype="boolean"),
            probe_status=pd.Series(dtype="string"),
            http_status_code=pd.Series(dtype="Int64"),
            final_url=pd.Series(dtype="string"),
            probe_error=pd.Series(dtype="string"),
        )

    probe_targets = df["probe_url"].dropna().drop_duplicates().tolist()
    probe_result_map = probe_urls(probe_targets)
    probe_frame = pd.DataFrame(
        [
            {
                "probe_url": probe_url,
                "page_exists": result.page_exists,
                "probe_status": result.probe_status,
                "http_status_code": result.http_status_code,
                "final_url": result.final_url,
                "probe_error": result.error,
            }
            for probe_url, result in probe_result_map.items()
        ]
    )

    if probe_frame.empty:
        return df

    return df.merge(probe_frame, on="probe_url", how="left")


def main() -> None:
    html = fetch_html(URL)
    df = build_dataframe(html, URL)
    df = attach_probe_results(df)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)

    print(f"Saved {len(df)} links to {OUTPUT_PATH}")
    print(f"Tagged {int(df['is_cname'].sum())} links as CNAMEs")
    if "page_exists" in df:
        print(df["probe_status"].value_counts(dropna=False).to_string())
    print(df["un_link_type"].value_counts(dropna=False).to_string())
    if not df.empty:
        preview = df[
            [
                "link_index",
                "text",
                "absolute_url",
                "cname",
                "is_cname",
                "page_exists",
                "probe_status",
            ]
        ].head(10)
        print(preview.to_string(index=False))


if __name__ == "__main__":
    main()
