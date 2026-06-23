"""imdbinfo-fetch – minimal CLI that returns raw IMDb HTML to stdout.

Usage
-----
    imdbinfo-fetch <url>

The HTTP request goes through the same ``request_handler`` used internally by
the library, so WAF cookie rotation and the browser-like headers are all
handled automatically – exactly what lets the library scrape IMDb reliably.

Your PHP app can then extract ``__NEXT_DATA__`` from the HTML however it likes,
for example with a regex:

    preg_match('/<script id="__NEXT_DATA__"[^>]*>(.*?)<\\/script>/s', $html, $m);
    $data = json_decode($m[1], true);

Exit codes
----------
    0  – success, HTML written to stdout
    1  – bad arguments or non-200 HTTP response
    2  – WAF blocked the request (HTTP 202)
"""

import sys
import argparse

from .services import request_handler
from .exceptions import HTTPError, WAFError


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="imdbinfo-fetch",
        description=(
            "Fetch a raw IMDb page and print its HTML to stdout.\n\n"
            "The request uses the same WAF-aware headers as the imdbinfo library,\n"
            "so the response is exactly what a real browser would receive."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  imdbinfo-fetch https://www.imdb.com/title/tt0166924/reference\n"
            "  imdbinfo-fetch https://www.imdb.com/lists/tt0166924\n"
            "  imdbinfo-fetch https://www.imdb.com/name/nm0000338/\n\n"
            "Pipe to a file:\n"
            "  imdbinfo-fetch https://www.imdb.com/title/tt0133093/reference > matrix.html\n"
        ),
    )
    p.add_argument(
        "url",
        help="Full IMDb URL to fetch (must start with https://www.imdb.com/)",
    )
    p.add_argument(
        "--check-domain",
        action="store_true",
        default=True,
        help="Warn (but do not abort) when the URL is not an IMDb domain (default: on)",
    )
    p.add_argument(
        "--no-check-domain",
        dest="check_domain",
        action="store_false",
        help="Skip the IMDb domain warning",
    )
    return p


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    url: str = args.url

    if not url.startswith(("http://", "https://")):
        parser.error(f"URL must start with http:// or https://  – got: {url!r}")

    if args.check_domain and "imdb.com" not in url:
        print(
            f"Warning: URL does not look like an IMDb URL: {url!r}",
            file=sys.stderr,
        )

    try:
        resp = request_handler(url)
    except WAFError as exc:
        print(f"Error: WAF blocked the request – {exc}", file=sys.stderr)
        sys.exit(2)
    except HTTPError as exc:
        print(f"Error: HTTP {exc.status_code} – {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:  # network error, DNS, etc.
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if resp.status_code != 200:
        print(
            f"Error: received HTTP {resp.status_code} from {url}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Write raw bytes to stdout so the encoding is preserved faithfully.
    # PHP reads bytes too, so this is the safest approach.
    sys.stdout.buffer.write(resp.content)


if __name__ == "__main__":
    main()
