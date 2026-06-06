# Problem Statement: Mutual Fund FAQ Assistant (Facts-Only Q&A)

## Overview

The objective of this project is to build a facts-only FAQ assistant for mutual fund schemes, using Groww as the reference product context. For this phase, the assistant answers objective, verifiable queries about **five HDFC Mutual Fund schemes** by retrieving information from their public Groww scheme pages. AMFI and SEBI links may be used only for educational refusal responses—not as answer corpus.

The system must strictly avoid providing investment advice, opinions, or recommendations. Every response must include a single, clear source link and adhere to defined constraints around clarity, accuracy, and compliance.

## Objective

Design and implement a lightweight Retrieval-Augmented Generation (RAG)-based assistant that:

- Answers factual queries about mutual fund schemes
- Uses a curated corpus of five Groww scheme pages (HDFC AMC)
- Provides concise, source-backed responses

## Target Users

- Retail investors comparing mutual fund schemes
- Customer support and content teams handling repetitive mutual fund queries

## Scope of Work

### 1. Corpus Definition

- **AMC:** HDFC Mutual Fund
- **Corpus size:** Five public Groww scheme pages (fixed for this phase):

| Scheme | Source URL |
|--------|------------|
| HDFC Mid Cap Fund Direct Growth | https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth |
| HDFC Small Cap Fund Direct Growth | https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth |
| HDFC Large Cap Fund Direct Growth | https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth |
| HDFC Gold ETF Fund of Fund Direct Plan Growth | https://groww.in/mutual-funds/hdfc-gold-etf-fund-of-fund-direct-plan-growth |
| HDFC Defence Fund Direct Growth | https://groww.in/mutual-funds/hdfc-defence-fund-direct-growth |

- Content extracted from each page should include scheme overview, expense ratio, exit load, minimum investment, benchmark, tax (factual), **fund management** (manager name, tenure, education, experience), investment objective, and fund house details—as published on the corresponding Groww page.
- Queries about schemes **not** in this list are out of scope; the assistant should explain the limited corpus politely.

### 2. FAQ Assistant Requirements

The assistant must:

**Answer facts-only queries**, such as:

- Expense ratio of a scheme
- Exit load details
- Minimum SIP amount (and minimum lumpsum where shown)
- Riskometer / risk classification
- Benchmark index
- **Fund management** — fund manager name(s), tenure, education, and experience as listed on the scheme page
- Tax implications stated on the scheme page (factual wording only; no personalized tax advice)

**Ensure:**

- Each response is limited to a maximum of 3 sentences
- Each response includes exactly one citation link
- Each response includes a footer: `Last updated from sources: <date>`

### 3. Refusal Handling

The assistant must refuse non-factual or advisory queries, such as:

- “Should I invest in this fund?”
- “Which fund is better?”

Refusal responses should:

- Be polite and clearly worded
- Reinforce the facts-only limitation
- Provide a relevant educational link (e.g., AMFI or SEBI resource)

### 4. User Interface (Minimal)

The solution should include a simple interface with:

- A welcome message
- Three example questions (including at least one **fund management** example), e.g.:
  - What is the expense ratio of HDFC Mid Cap Fund Direct Growth?
  - What is the exit load on HDFC Defence Fund Direct Growth?
  - Who manages HDFC Gold ETF Fund of Fund Direct Plan Growth?
- A visible disclaimer: **“Facts-only. No investment advice.”**

## Constraints

### Data and Sources

- **Answer corpus:** Only the five Groww HDFC scheme URLs listed in §1 (Corpus Definition)
- **Refusal / education links:** AMFI or SEBI resources when declining advisory or comparison queries
- Do not use third-party blogs, news sites, or other aggregator pages outside this corpus
- Groww pages are used as the reference source for this phase; primary AMC documents (KIM/SID/factsheets) are out of scope unless added in a future phase

### Privacy and Security

Do not collect, store, or process:

- PAN or Aadhaar numbers
- Account numbers
- OTPs
- Email addresses or phone numbers

### Content Restrictions

- No investment advice or recommendations
- No performance comparisons or return calculations
- For performance-related queries, refuse return calculations and comparisons; provide a link to the relevant scheme page only

### Transparency

- Responses must be short, factual, and verifiable
- Every answer must include a source link and last updated date

## Expected Deliverables

### README Document

- Setup instructions
- Selected AMC (HDFC) and the five scheme URLs
- Architecture overview (RAG approach)
- Known limitations

### Disclaimer Snippet

> “Facts-only. No investment advice.”

## Success Criteria

- Accurate retrieval of factual mutual fund information, including fund management details, for the five supported schemes
- Strict adherence to facts-only responses
- Consistent inclusion of valid source citations
- Proper refusal of advisory queries
- Clean, minimal, and user-friendly interface

## Summary

The goal is to build a trustworthy, transparent, and compliant mutual fund FAQ assistant that prioritizes accuracy over intelligence. Scoped to five HDFC schemes on Groww, the system should ensure that users receive only verified, source-backed factual information—including fund manager details—without any advisory bias or speculative content.
