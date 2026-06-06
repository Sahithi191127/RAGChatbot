# Data directories

| Path | Purpose |
|------|---------|
| `raw/` | Fetched HTML or markdown per Groww scheme URL (`{slug}.html`) |
| `processed/` | Parsed sections (`{slug}.json`) and chunk artifacts (`{slug}.chunks.json`) |
| `index/` | ChromaDB (`chroma/`) + `metadata.json` (gitignored) |

Regenerate index: `python ingestion/run.py` (Phase 2+).

## Chunk ID format (Phase 1)

Vector store document IDs follow `config/chunk_ids.py`:

| Type | Pattern | Example |
|------|---------|---------|
| General section | `{slug}#{section}#{index}` | `hdfc-mid-cap-fund-direct-growth#expense_ratio#0` |
| Fund management | `{slug}#fund_management#{manager-slug}` | `hdfc-defence-fund-direct-growth#fund_management#priya-ranjan` |

Section tags are defined in `config/corpus.yaml` (`overview`, `expense_ratio`, `exit_load`, `minimum_investment`, `benchmark`, `tax`, `fund_management`, `investment_objective`, `fund_house`).

## Chunking (Phase 2.3)

**Section-first:** one chunk per section when text fits ~400 tokens; split with overlap only inside oversized sections; **one chunk per fund manager** for `fund_management`. See [implementationplan.md](../DOCS/implementationplan.md) Phase 2.3.

## Corpus configuration

Scheme URLs and aliases: `config/corpus.yaml` (five HDFC Groww pages). Load in Python:

```python
from config import get_corpus_config, get_groww_citation_allowlist
```
