import csv
import json
import re
from urllib.parse import urljoin, urlparse

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

QUESTION_WORDS = (
    "what", "why", "how", "when", "where", "who",
    "which", "can", "could", "does", "do", "is",
    "are", "should", "will"
)


def get_page(url):
    """Request a webpage using a standard browser-style user agent."""
    return requests.get(
        url,
        timeout=20,
        allow_redirects=True,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36"
            )
        },
    )


def get_robots_txt(url):
    """Retrieve robots.txt from the site's root."""
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

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


def parse_robots_groups(robots_text):
    """Parse basic robots.txt user-agent groups."""
    groups = []
    current_agents = []
    current_rules = []

    for raw_line in robots_text.splitlines():
        line = raw_line.split("#", 1)[0].strip()

        if not line or ":" not in line:
            continue

        directive, value = line.split(":", 1)
        directive = directive.strip().lower()
        value = value.strip()

        if directive == "user-agent":
            if current_rules:
                groups.append((current_agents, current_rules))
                current_agents = []
                current_rules = []

            current_agents.append(value.lower())

        elif directive in ("allow", "disallow"):
            if current_agents:
                current_rules.append(
                    (directive, value)
                )

    if current_agents:
        groups.append((current_agents, current_rules))

    return groups


def crawler_status(robots_text, crawler):
    """
    Return a simple robots.txt accessibility assessment.

    This checks explicit crawler groups and wildcard rules.
    It does not claim whether an AI platform will index, cite,
    train on, or surface the website.
    """
    if not robots_text:
        return "Could not verify"

    groups = parse_robots_groups(robots_text)
    crawler_lower = crawler.lower()

    relevant_groups = [
        rules
        for agents, rules in groups
        if crawler_lower in agents
    ]

    if not relevant_groups:
        relevant_groups = [
            rules
            for agents, rules in groups
            if "*" in agents
        ]

        if not relevant_groups:
            return "No specific directive"

        source = "Wildcard"
    else:
        source = "Explicit"

    rules = [
        rule
        for group in relevant_groups
        for rule in group
    ]

    root_disallow = any(
        directive == "disallow" and path.strip() == "/"
        for directive, path in rules
    )

    root_allow = any(
        directive == "allow" and path.strip() == "/"
        for directive, path in rules
    )

    if root_disallow and not root_allow:
        return f"Blocked ({source})"

    if rules:
        return f"Accessible / partial rules ({source})"

    return f"No blocking rule ({source})"


def extract_schema_types(soup):
    """Extract unique @type values from JSON-LD."""
    schema_types = set()

    def walk(data):
        if isinstance(data, dict):
            schema_type = data.get("@type")

            if isinstance(schema_type, list):
                for item in schema_type:
                    schema_types.add(str(item))

            elif schema_type:
                schema_types.add(str(schema_type))

            for value in data.values():
                walk(value)

        elif isinstance(data, list):
            for item in data:
                walk(item)

    scripts = soup.find_all(
        "script",
        attrs={"type": "application/ld+json"},
    )

    for script in scripts:
        raw = script.string or script.get_text()

        if not raw.strip():
            continue

        try:
            data = json.loads(raw)
            walk(data)

        except (json.JSONDecodeError, TypeError):
            continue

    return sorted(schema_types)


def find_author_signal(soup, schema_types):
    """Look for basic visible or structured author signals."""
    if "Person" in schema_types:
        return "Yes"

    if soup.find(
        attrs={
            "rel": lambda value: (
                value
                and (
                    "author" in value
                    if isinstance(value, list)
                    else "author" in str(value).lower()
                )
            )
        }
    ):
        return "Yes"

    author_selectors = [
        '[class*="author"]',
        '[id*="author"]',
        '[itemprop="author"]',
    ]

    for selector in author_selectors:
        if soup.select_one(selector):
            return "Yes"

    return "Not detected"


def count_question_headings(soup):
    """Count headings written in a question-oriented format."""
    count = 0

    for heading in soup.find_all(
        ["h2", "h3", "h4"]
    ):
        text = heading.get_text(
            " ",
            strip=True,
        ).lower()

        if not text:
            continue

        if text.endswith("?") or text.startswith(
            QUESTION_WORDS
        ):
            count += 1

    return count


def detect_entity_signals(soup, schema_types):
    """Detect basic organization/person/entity signals."""
    score = 0
    signals = []

    entity_schema = {
        "Organization",
        "Corporation",
        "LocalBusiness",
        "Person",
        "Brand",
    }

    detected = entity_schema.intersection(
        set(schema_types)
    )

    if detected:
        score += 2
        signals.append(
            "Entity schema: "
            + ", ".join(sorted(detected))
        )

    same_as_found = False

    for script in soup.find_all(
        "script",
        attrs={"type": "application/ld+json"},
    ):
        raw = script.string or script.get_text()

        if '"sameAs"' in raw or "'sameAs'" in raw:
            same_as_found = True
            break

    if same_as_found:
        score += 1
        signals.append("sameAs references")

    og_site = soup.find(
        "meta",
        attrs={"property": "og:site_name"},
    )

    if og_site and og_site.get("content"):
        score += 1
        signals.append("Site/brand name metadata")

    if not signals:
        return 0, "Limited signals detected"

    return score, "; ".join(signals)


def classify_score(score, maximum):
    """Convert a component score into a readable assessment."""
    if maximum == 0:
        return "Not assessed"

    percentage = (score / maximum) * 100

    if percentage >= 80:
        return "Strong"

    if percentage >= 60:
        return "Good"

    if percentage >= 40:
        return "Moderate"

    return "Limited"


def audit_url(url):
    """Run Technical SEO + AEO/GEO/AI crawler readiness checks."""

    result = {
        "URL": url,
        "Status Code": "",
        "Final URL": "",
        "Indexability": "",
        "Title": "",
        "Meta Description": "",
        "Canonical": "",
        "H1": "",
        "H2 Count": 0,
        "Question Headings": 0,
        "Schema Types": "",
        "Article Schema": "No",
        "FAQ Schema": "No",
        "Organization Schema": "No",
        "Person Schema": "No",
        "Author Signal": "",
        "Entity Signals": "",
        "Robots.txt": "",
        "GPTBot": "",
        "ChatGPT-User": "",
        "OAI-SearchBot": "",
        "ClaudeBot": "",
        "PerplexityBot": "",
        "Google-Extended": "",
        "Technical Readiness": "",
        "AEO Signals": "",
        "Entity Readiness": "",
        "AI Crawler Access": "",
        "Custom Readiness Score": 0,
    }

    try:
        response = get_page(url)

        result["Status Code"] = response.status_code
        result["Final URL"] = response.url

        soup = BeautifulSoup(
            response.text,
            "html.parser",
        )

        # -------------------------
        # Basic Technical SEO
        # -------------------------

        if soup.title:
            result["Title"] = soup.title.get_text(
                " ",
                strip=True,
            )

        meta_description = soup.find(
            "meta",
            attrs={
                "name": re.compile(
                    r"^description$",
                    re.I,
                )
            },
        )

        if meta_description:
            result["Meta Description"] = (
                meta_description.get(
                    "content",
                    "",
                ).strip()
            )

        canonical = soup.find(
            "link",
            rel=lambda value: (
                value
                and (
                    "canonical" in value
                    if isinstance(value, list)
                    else "canonical"
                    in str(value).lower()
                )
            ),
        )

        if canonical:
            result["Canonical"] = canonical.get(
                "href",
                "",
            )

        h1 = soup.find("h1")

        if h1:
            result["H1"] = h1.get_text(
                " ",
                strip=True,
            )

        result["H2 Count"] = len(
            soup.find_all("h2")
        )

        result["Question Headings"] = (
            count_question_headings(soup)
        )

        robots_meta = soup.find(
            "meta",
            attrs={
                "name": re.compile(
                    r"^robots$",
                    re.I,
                )
            },
        )

        robots_content = ""

        if robots_meta:
            robots_content = robots_meta.get(
                "content",
                "",
            ).lower()

        if response.status_code != 200:
            result["Indexability"] = (
                "Non-200 response"
            )

        elif "noindex" in robots_content:
            result["Indexability"] = "Noindex"

        else:
            result["Indexability"] = (
                "No meta noindex detected"
            )

        # -------------------------
        # Structured Data
        # -------------------------

        schema_types = extract_schema_types(soup)

        result["Schema Types"] = (
            ", ".join(schema_types)
            if schema_types
            else "None detected"
        )

        article_types = {
            "Article",
            "NewsArticle",
            "BlogPosting",
        }

        if article_types.intersection(
            set(schema_types)
        ):
            result["Article Schema"] = "Yes"

        if "FAQPage" in schema_types:
            result["FAQ Schema"] = "Yes"

        organization_types = {
            "Organization",
            "Corporation",
            "LocalBusiness",
        }

        if organization_types.intersection(
            set(schema_types)
        ):
            result["Organization Schema"] = "Yes"

        if "Person" in schema_types:
            result["Person Schema"] = "Yes"

        result["Author Signal"] = (
            find_author_signal(
                soup,
                schema_types,
            )
        )

        entity_score, entity_text = (
            detect_entity_signals(
                soup,
                schema_types,
            )
        )

        result["Entity Signals"] = entity_text

        # -------------------------
        # AI Crawler Accessibility
        # -------------------------

        robots_url, robots_text = (
            get_robots_txt(response.url)
        )

        if robots_text:
            result["Robots.txt"] = robots_url

        else:
            result["Robots.txt"] = (
                "Could not retrieve"
            )

        crawler_results = {}

        for crawler in AI_CRAWLERS:
            status = crawler_status(
                robots_text,
                crawler,
            )

            crawler_results[crawler] = status
            result[crawler] = status

        # -------------------------
        # Component Assessments
        # -------------------------

        technical_score = 0
        technical_max = 6

        if response.status_code == 200:
            technical_score += 1

        if result["Title"]:
            technical_score += 1

        if result["Meta Description"]:
            technical_score += 1

        if result["Canonical"]:
            technical_score += 1

        if result["H1"]:
            technical_score += 1

        if result["Indexability"] == (
            "No meta noindex detected"
        ):
            technical_score += 1

        result["Technical Readiness"] = (
            classify_score(
                technical_score,
                technical_max,
            )
        )

        aeo_score = 0
        aeo_max = 4

        if result["H2 Count"] > 0:
            aeo_score += 1

        if result["Question Headings"] > 0:
            aeo_score += 1

        if schema_types:
            aeo_score += 1

        if (
            result["Article Schema"] == "Yes"
            or result["FAQ Schema"] == "Yes"
        ):
            aeo_score += 1

        result["AEO Signals"] = classify_score(
            aeo_score,
            aeo_max,
        )

        result["Entity Readiness"] = (
            classify_score(
                entity_score,
                4,
            )
        )

        accessible_count = 0
        verified_count = 0

        for status in crawler_results.values():

            if status != "Could not verify":
                verified_count += 1

            if (
                "Accessible" in status
                or "No blocking rule" in status
                or "No specific directive" in status
            ):
                accessible_count += 1

        if verified_count == 0:
            result["AI Crawler Access"] = (
                "Could not verify"
            )

        elif accessible_count == len(
            AI_CRAWLERS
        ):
            result["AI Crawler Access"] = (
                "No full blocks detected"
            )

        elif accessible_count > 0:
            result["AI Crawler Access"] = (
                "Mixed"
            )

        else:
            result["AI Crawler Access"] = (
                "Restricted"
            )

        # -------------------------
        # Custom Readiness Score
        # -------------------------
        #
        # This is a portfolio diagnostic score based
        # only on observable website signals.
        # It is NOT a ranking or citation probability.
        #

        total = 0

        total += round(
            (technical_score / technical_max) * 40
        )

        total += round(
            (aeo_score / aeo_max) * 25
        )

        total += round(
            (entity_score / 4) * 20
        )

        if verified_count:
            total += round(
                (
                    accessible_count
                    / len(AI_CRAWLERS)
                )
                * 15
            )

        result["Custom Readiness Score"] = min(
            total,
            100,
        )

    except requests.RequestException as error:

        result["Status Code"] = "ERROR"
        result["Final URL"] = str(error)
        result["Indexability"] = (
            "Could not assess"
        )
        result["Technical Readiness"] = (
            "Could not assess"
        )
        result["AEO Signals"] = (
            "Could not assess"
        )
        result["Entity Readiness"] = (
            "Could not assess"
        )
        result["AI Crawler Access"] = (
            "Could not assess"
        )

    return result


def read_urls(filename):
    """Read URLs from a CSV containing a URL column."""
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
    """Save audit results as CSV."""
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

    if not urls:
        print(
            "No URLs found in sample_urls.csv"
        )
        return

    results = []

    print(
        f"Starting AI SEO audit for "
        f"{len(urls)} URL(s)...\n"
    )

    for url in urls:
        print(
            f"Auditing AI SEO readiness: {url}"
        )

        results.append(
            audit_url(url)
        )

    save_results(
        results,
        output_file,
    )

    print(
        "\nAI SEO audit complete."
    )

    print(
        f"Results saved to {output_file}"
    )

    print(
        "\nNote: Custom Readiness Score is a "
        "diagnostic score based on observable "
        "website signals. It does not predict "
        "rankings, AI citations, or inclusion "
        "in AI-generated answers."
    )


if __name__ == "__main__":
    main()
