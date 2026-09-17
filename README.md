# AI SEO & LLM Visibility Audit

A practical Python-based audit toolkit for evaluating website signals related to **AI SEO, Answer Engine Optimization (AEO), Generative Engine Optimization (GEO), AI crawler accessibility, entity readiness, and technical search visibility**.

The toolkit combines traditional technical SEO checks with emerging AI-search considerations to help identify areas that may affect how easily search engines and AI-driven systems can access, understand, and interpret website content.

## 🔍 What This Toolkit Evaluates

### Technical SEO Signals

- HTTP status codes
- Final destination URLs
- Indexability signals
- Canonical URLs
- Meta robots directives
- Page titles
- Meta descriptions
- H1 and H2 structure
- Robots.txt availability

### 🤖 AI Crawler Accessibility

The audit reviews robots.txt directives associated with crawlers and user agents such as:

- GPTBot
- ChatGPT-User
- OAI-SearchBot
- ClaudeBot
- PerplexityBot
- Google-Extended

This helps identify whether observable robots.txt directives appear to allow or restrict access for these user agents.

### 💬 AEO — Answer Engine Optimization Signals

The toolkit reviews page-level signals that may support answer-oriented content, including:

- Question-based headings/content
- FAQ-related structured data
- Content structure
- Heading organization
- Answer-focused page elements

These checks are intended to highlight opportunities for making important information easier for search and answer systems to interpret.

### 🌐 GEO — Generative Engine Optimization Signals

The audit also reviews observable signals relevant to generative-search readiness, including:

- Structured content
- Schema markup
- Entity-related signals
- Organization and Person schema
- Author signals
- Canonicalization
- Crawl accessibility
- Content structure
- Technical accessibility

### 🧩 Entity & Structured Data Signals

The toolkit checks for signals such as:

- Schema markup
- FAQ schema
- Organization schema
- Person schema
- Author signals
- Entity-related page elements

These signals can help search systems better understand the entities and relationships represented on a website.

## 📊 Audit Output

Results are exported to a CSV file for further analysis.

Example fields include:

- URL
- Status Code
- Final URL
- Indexability
- Title
- Meta Description
- Canonical
- H1
- H2 Count
- Question Signals
- Schema Type
- Article Schema
- FAQ Schema
- Organization Schema
- Person Schema
- Author Signals
- Robots.txt
- GPTBot Accessibility
- ChatGPT-User Accessibility
- OAI-SearchBot Accessibility
- ClaudeBot Accessibility
- PerplexityBot Accessibility
- Google-Extended Accessibility
- Technical Signals
- AEO Signals
- Entity Readiness
- AI Crawler Status
- Custom Readiness Score

A sample audit output is included in:

`sample_output.csv`

## 📈 Custom Readiness Score

The toolkit generates a **Custom Readiness Score** based on observable signals detected during the audit.

The score is designed to help organize findings and identify areas that may require further investigation.

**Important:** This is a diagnostic score created by this toolkit. It does not predict Google rankings, AI citations, traffic, or inclusion in AI-generated answers.

Crawler accessibility also does not guarantee that content will be indexed, cited, retrieved, or surfaced by any AI system.

## 🚀 How to Use

### 1. Install Python

Python 3 is required.

### 2. Install dependencies

```bash
py -m pip install -r requirements.txt
```

### 3. Add URLs

Add the URLs you want to audit to:

```text
sample_urls.csv
```

### 4. Run the audit

```bash
py ai_seo_audit.py
```

### 5. Review the results

The audit generates:

```text
ai_seo_audit_output.csv
```

Open the CSV in Excel, Google Sheets, or another spreadsheet application for analysis.

## 🛠 Technologies Used

- Python
- Requests
- BeautifulSoup
- CSV processing
- HTML parsing
- Robots.txt analysis
- Schema/structured-data analysis

## 🎯 Use Cases

This toolkit can support:

- AI SEO audits
- Technical SEO audits
- AEO audits
- GEO audits
- AI crawler accessibility reviews
- Structured data reviews
- Entity signal analysis
- Content-structure analysis
- Pre-audit website research

It is intended to complement professional tools and manual analysis rather than replace platforms such as Screaming Frog SEO Spider, Google Search Console, Ahrefs, or Semrush.

## ⚠️ Limitations

AI search visibility cannot be determined from website signals alone.

Results may also be affected by network restrictions, robots.txt availability, JavaScript rendering, anti-bot systems, authentication, geographic restrictions, and other technical factors.

A failed request should therefore not automatically be interpreted as poor AI-search readiness.

## 👤 About

Created as a practical Technical SEO and AI Search Optimization project covering **Technical SEO, AI SEO, AEO, GEO, structured data, entity analysis, and AI crawler accessibility**.
