import csv
import json
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


AI_CRAWLERS = [
    "GPTBot",
    "ChatGPT-User",
    "OAI-SearchBot",
    "ClaudeBot",
    "PerplexityBot",
    "Google-Extended",
]


def get_robots_txt(url):
    """Retrieve robots.txt for the website."""
    robots_url = urljoin(url, "/robots.txt")

    try:
        response = requests.get(
            robots_url,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"},
        )

        if response.status_code == 200:
            return robots_url, response.text

        return robots_url, ""

    except requests.RequestException:
        return robots_url, ""


def check_ai_crawlers(robots_text):
    """Check whether common AI crawlers are mentioned or blocked."""

    results = {}

    lower_text = robots_text.lower()

    for crawler in AI_CRAWLERS:
        crawler_lower = crawler.lower()

        if crawler_lower not in lower_text:
            results[crawler] = "Not specifically mentioned"
            continue

        pattern = (
            r"user-agent:\s*"
            + re.escape(crawler_lower)
            + r"(.*?)(?=user-agent:|\Z)"
        )

        match = re.search(
            pattern,
            lower_text,
            flags=re.DOTALL,
        )

        if match:
            rules = match.group(1)

            if re.search(r"disallow:\s*/\s*(?:\n|$)", rules):
                results[crawler] = "Blocked"
            else:
                results[crawler] = "Mentioned / not fully blocked"
        else:
            results[crawler] = "Mentioned"

    return results


def extract_schema_types(soup):
    """Extract schema.org @type values from JSON-LD."""

    schema_types = []

    scripts = soup.find_all(
        "script",
        attrs={"type": "application/ld+json"},
    )

    def find_types(data):
        if isinstance(data, dict):

            if "@type" in data:
                value = data["@type"]

                if isinstance(value, list):
                    schema_types.extend(
                        [str(item) for item in value]
                    )
                else:
                    schema_types.append(str(value))

            for value in data.values():
                find_types(value)

        elif isinstance(data, list):

            for item in data:
                find_types(item)

    for script in scripts:

        try:
            data = json.loads(script.string or script.get_text())
            find_types(data)

        except (json.JSONDecodeError, TypeError):
            continue

    return sorted(set(schema_types))


def audit_url(url):
    """Run AI SEO, AEO and GEO readiness checks."""

    result = {
        "URL": url,
        "Status Code": "",
        "Final URL": "",
        "Title": "",
        "Meta Description": "",
        "Canonical": "",
        "H1": "",
        "H2 Count": 0,
        "Question Headings": 0,
        "Schema Types": "",
        "FAQ Schema": "No",
        "Organization Schema": "No",
        "Person Schema": "No",
        "Author Signal": "No",
        "Robots.txt": "",
        "GPTBot": "",
        "ChatGPT-User": "",
        "OAI-SearchBot": "",
        "ClaudeBot": "",
        "PerplexityBot": "",
        "Google-Extended": "",
        "AI SEO Score": 0,
    }

    try:
        response = requests.get(
            url,
            timeout=20,
            allow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; "
                    "AISEOAuditBot/1.0)"
                )
            },
        )

        result["Status Code"] = response.status_code
        result["Final URL"] = response.url

        soup = BeautifulSoup(response.text, "html.parser")

        # Title
        if soup.title:
            result["Title"] = soup.title.get_text(
                strip=True
            )

        # Meta description
        meta_description = soup.find(
            "meta",
            attrs={"name": re.compile(
                "^description$",
                re.I,
            )},
        )

        if meta_description:
            result["Meta Description"] = (
                meta_description.get("content", "")
            )

        # Canonical
        canonical = soup.find(
            "link",
            attrs={"rel": lambda value: (
                value and "canonical" in value
            )},
        )

        if canonical:
            result["Canonical"] = canonical.get(
                "href",
                "",
            )

        # Headings
        h1 = soup.find("h1")

        if h1:
            result["H1"] = h1.get_text(
                " ",
                strip=True,
            )

        h2_tags = soup.find_all("h2")
        result["H2 Count"] = len(h2_tags)

        question_words = (
            "what",
            "why",
            "how",
            "when",
            "where",
            "who",
            "which",
            "can",
            "does",
            "is",
            "are",
            "should",
        )

        question_count = 0

        for heading in soup.find_all(
            ["h2", "h3", "h4"]
        ):
            text = heading.get_text(
                " ",
                strip=True,
            ).lower()

            if (
                text.endswith("?")
                or text.startswith(question_words)
            ):
                question_count += 1

        result["Question Headings"] = question_count

        # Structured data
        schema_types = extract_schema_types(soup)

        result["Schema Types"] = ", ".join(
            schema_types
        )

        if "FAQPage" in schema_types:
            result["FAQ Schema"] = "Yes"

        if "Organization" in schema_types:
            result["Organization Schema"] = "Yes"

        if "Person" in schema_types:
            result["Person Schema"] = "Yes"

        # Author / expertise signals
        page_text = soup.get_text(
            " ",
            strip=True,
        ).lower()

        author_terms = [
            "author",
            "written by",
            "reviewed by",
            "expert",
            "editor",
        ]

        if any(
            term in page_text
            for term in author_terms
        ):
            result["Author Signal"] = "Yes"

        # Robots.txt and AI crawler checks
        robots_url, robots_text = get_robots_txt(
            response.url
        )

        result["Robots.txt"] = (
            robots_url if robots_text else "Not found"
        )

        crawler_results = check_ai_crawlers(
            robots_text
        )

        for crawler, status in crawler_results.items():
            result[crawler] = status

        # Simple readiness score
        score = 0

        if response.status_code == 200:
            score += 10

        if result["Title"]:
            score += 10

        if result["Meta Description"]:
            score += 10

        if result["Canonical"]:
            score += 10

        if result["H1"]:
            score += 10

        if result["H2 Count"] > 0:
            score += 10

        if result["Question Headings"] > 0:
            score += 10

        if schema_types:
            score += 10

        if result["Author Signal"] == "Yes":
            score += 10

        if robots_text:
            score += 10

        result["AI SEO Score"] = score

    except requests.RequestException as error:

        result["Status Code"] = "ERROR"
        result["Final URL"] = str(error)

    return result


def read_urls(filename):
    """Read URLs from a CSV file."""

    urls = []

    with open(
        filename,
        newline="",
        encoding="utf-8-sig",
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:

            url = (
                row.get("URL")
                or row.get("url")
                or ""
            ).strip()

            if url:
                urls.append(url)

    return urls


def save_results(results, filename):
    """Save audit results to CSV."""

    if not results:
        return

    with open(
        filename,
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=results[0].keys(),
        )

        writer.writeheader()
        writer.writerows(results)


def main():

    input_file = "sample_urls.csv"
    output_file = "ai_seo_audit_output.csv"

    urls = read_urls(input_file)

    results = []

    for url in urls:

        print(f"Auditing AI SEO readiness: {url}")

        result = audit_url(url)

        results.append(result)

    save_results(
        results,
        output_file,
    )

    print(
        "\nAI SEO audit complete. "
        f"Results saved to {output_file}"
    )


if __name__ == "__main__":
    main()
