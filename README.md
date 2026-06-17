# FitFindr — Starter Kit

This starter kit contains everything you need to begin Project 2.

## What's Included

```
ai201-project2-fitfindr-starter/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example wardrobe
├── utils/
│   └── data_loader.py         # Helper functions for loading the data
├── planning.md                # Your planning template — fill this out first
└── requirements.txt           # Python dependencies
```

## Setup

```bash
pip install -r requirements.txt
```

Set your Groq API key in a `.env` file (get a free key at [console.groq.com](https://console.groq.com)):
```
GROQ_API_KEY=your_key_here
```

## The Mock Listings Dataset

`data/listings.json` contains 40 mock secondhand listings across categories (tops, bottoms, outerwear, shoes, accessories) and styles (vintage, y2k, grunge, cottagecore, streetwear, and more).

Each listing has: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

Load it with:
```python
from utils.data_loader import load_listings
listings = load_listings()
```

## The Wardrobe Schema

`data/wardrobe_schema.json` defines the format your agent uses to represent a user's existing wardrobe. It includes:

- `schema`: field definitions for a wardrobe item
- `example_wardrobe`: a sample wardrobe with 10 items you can use for testing
- `empty_wardrobe`: a starting template for a new user

Load an example wardrobe with:
```python
from utils.data_loader import get_example_wardrobe
wardrobe = get_example_wardrobe()
```

## Where to Start

1. **Read `planning.md` and fill it out before writing any code.**
2. Verify the data loads correctly by running `python utils/data_loader.py`.
3. Build and test each tool individually before connecting them through your planning loop.

Your implementation files go in this same directory. There's no required file structure for your agent code — organize it however makes sense for your design.

---

## Tool Inventory

### Tool 1: `search_listings`

**Purpose:** Searches `listings.json` for items matching the user's description and optional hard filters. Uses keyword intersection scoring to rank results by relevance.

**Inputs:**

| Parameter | Type | Description |
|---|---|---|
| `description` | `str` | Keywords describing what the user wants (e.g. `"vintage graphic tee"`) |
| `size` | `str \| None` | Size string to filter by; case-insensitive substring match (`"M"` matches `"S/M"`). `None` skips size filtering. |
| `max_price` | `float \| None` | Maximum price inclusive. `None` skips price filtering. |

**Output:** `list[dict]` — up to 3 listing dicts sorted by relevance score (highest first). Returns `[]` if nothing matches.

Each listing dict has: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, `platform`.

---

### Tool 2: `suggest_outfit`

**Purpose:** Given the selected listing and the user's wardrobe, calls an LLM to suggest 1–2 complete outfits. Uses a different prompt depending on whether the wardrobe is populated or empty.

**Inputs:**

| Parameter | Type | Description |
|---|---|---|
| `new_item` | `dict` | A listing dict from `search_listings()`. Fields read with `.get()` so partial dicts produce a degraded-but-valid prompt. |
| `wardrobe` | `dict` | A wardrobe dict with an `"items"` key. Empty list triggers the general styling advice prompt. |

**Output:** `str` — a non-empty LLM-generated outfit suggestion. Returns `"Please utilize search_listings to find a new valid item"` if `new_item` is not a dict. Returns `"Cannot generate an outfit suggestion at this time"` if the LLM call fails.

---

### Tool 3: `create_fit_card`

**Purpose:** Takes the outfit suggestion and selected listing and generates a 2–4 sentence Instagram/TikTok-style caption. Uses a higher LLM temperature (1.2) so captions vary for different inputs.

**Inputs:**

| Parameter | Type | Description |
|---|---|---|
| `outfit` | `str` | The outfit suggestion string from `suggest_outfit()`. |
| `new_item` | `dict` | The listing dict for the thrifted item. `title`, `price`, and `platform` are pulled from it for the prompt. |

**Output:** `str` — a casual, shareable caption mentioning the item name, price, and platform. Returns `"Please provide an outfit suggestion to create a fit card."` if `outfit` is empty, whitespace-only, and `"Cannot generate an outfit caption at this time"` if the LLM call fails.

---

## How the Planning Loop Works

`run_agent(query, wardrobe)` in `agent.py` runs the full interaction as a linear pipeline with early-exit guards at each step.

**Step 1 — Parse the query.** Regex extracts `size` (pattern: `"size M"`) and `max_price` (pattern: `"under $30"`) from the natural language query. The full query string is also used as the `description` for keyword matching. Parsed values are stored in `session["parsed"]`.

**Step 2 — Search listings.** Calls `search_listings()` with the parsed parameters. If the result is an empty list, sets `session["error"]` and returns immediately — `suggest_outfit` is never called without a valid item.

**Step 3 — Select top result.** Picks `results[0]` as `session["selected_item"]`. The top-scored listing is always chosen.

**Step 4 — Guard empty wardrobe.** Checks `wardrobe["items"]` before calling `suggest_outfit`. If the wardrobe is empty, sets `session["error"]` and returns early.

**Step 5 — Generate outfit suggestion.** Calls `suggest_outfit()` with the selected item and wardrobe. If the result is empty or falsy, sets `session["error"]` and returns.

**Step 6 — Generate fit card.** Calls `create_fit_card()` with the suggestion and selected item. If the result is empty or falsy, sets `session["error"]` and returns.

**Step 7 — Return session.** If all steps succeed, returns the completed session with no error set.

---

## State Management

All state lives in a single session dict initialized by `_new_session()` before any tool runs:

```python
{
    "query": query,            # original user query string
    "parsed": {},              # regex-extracted description, size, max_price
    "search_results": [],      # list returned by search_listings()
    "selected_item": None,     # results[0]; passed into suggest_outfit and create_fit_card
    "wardrobe": wardrobe,      # user's wardrobe dict; passed into suggest_outfit
    "outfit_suggestion": None, # string returned by suggest_outfit
    "fit_card": None,          # string returned by create_fit_card
    "error": None,             # set to a string if the loop ends early
}
```

Every key is present from the start — `outfit_suggestion` and `fit_card` are `None` even if the loop exits at Step 2. The caller can always check `session["error"]` first and then safely read any key without a `KeyError`.

Tools do not share state directly. Each tool receives only the values it needs as function arguments: `search_listings` receives parsed parameters, `suggest_outfit` receives `selected_item` and `wardrobe`, and `create_fit_card` receives `outfit_suggestion` and `selected_item`. The session dict is the handoff layer — `run_agent` reads from it and writes to it between each call.

---

## Error Handling

| Tool | Failure mode | What the tool does | What the agent does |
|---|---|---|---|
| `search_listings` | No listings match the query | Returns `[]` | Sets `session["error"] = "No items match your criteria, please adjust your criteria"` and stops |
| `suggest_outfit` | `new_item` is not a dict | Returns `"Please utilize search_listings to find a new valid item"` | Stored in `outfit_suggestion`; agent checks for empty/falsy return |
| `suggest_outfit` | LLM API call fails | Returns `"Cannot generate an outfit suggestion at this time"` | Sets `session["error"]` and stops |
| `create_fit_card` | `outfit` is empty or whitespace | Returns `"Cannot generate an outfit caption at this time"` without calling LLM | Sets `session["error"]` and stops |
| `create_fit_card` | LLM API call fails | Returns `"Cannot generate an outfit caption at this time"` | Sets `session["error"]` and stops |

**Concrete examples from testing:**

- `search_listings("designer ballgown", size="XXS", max_price=5.0)` returns `[]`. No listing in the dataset is a ballgown, costs under $5, and comes in XXS — the no-match case hits cleanly. Covered by `TestSearchListings::test_returns_empty_list_for_no_matches`.

- `suggest_outfit("not a dict", get_example_wardrobe())` returns `"Please utilize search_listings to find a new valid item"` without calling the LLM. The type guard fires before any Groq client is created. Covered by `TestSuggestOutfit::test_invalid_new_item_returns_error_string`.

- `create_fit_card("", SAMPLE_ITEM)` returns `"Cannot generate an outfit caption at this time"`. The empty-string guard fires before the LLM prompt is built. Same result for `create_fit_card("   ", SAMPLE_ITEM)` since `.strip()` is checked. Covered by `TestCreateFitCard::test_empty_outfit_returns_error_string` and `test_whitespace_outfit_returns_error_string`.

---

## Spec Reflection

**One way the spec helped:** The Mermaid diagram in `planning.md` made the conditional branching concrete before any code was written. Each decision diamond (`len results == 0?`, `len suggestion == 0?`) had an explicit yes/no path with a labeled error, which translated directly into the `if not results` / `return session` pattern in `run_agent`. Having named error stops in the diagram meant the planning loop had no ambiguous fall-through cases.

**One way implementation diverged from the spec:** The original spec for `suggest_outfit` said an empty wardrobe should be treated as a hard failure — return an error string and stop. During implementation, this was changed: the tool calls the LLM with a general styling prompt when the wardrobe is empty, producing real outfit ideas based on common wardrobe staples rather than stopping. This was a deliberate tradeoff to keep the tool useful for new users who haven't built a wardrobe yet. The spec in `planning.md` was updated to reflect this decision.

---

## AI Usage

### Instance 1 — Implementing `search_listings`

**Input to Claude:** The Tool 1 spec from `planning.md` (purpose, 7 input parameters including `category`, `style_tags`, `colors`, `brand`, return value, and failure mode) plus the `load_listings()` function from `data_loader.py`.

**What it produced:** A function with all 7 parameters, each used as a dedicated hard filter against listing fields.

**What I overrode:** Rejected the expanded signature and reverted to 3 parameters (`description`, `size`, `max_price`). The keyword-based relevance scoring already handles category, style, color, and brand matching by scanning those fields across the listing text — adding dedicated filter params made the function rigid without improving results. The spec was updated to reflect the actual 3-parameter signature.

---

### Instance 2 — Implementing `suggest_outfit`

**Input to Claude:** The Tool 2 spec (inputs, return value, failure modes for empty wardrobe and invalid `new_item`) plus a sample wardrobe dict and a sample listing from `listings.json`.

**What it produced:** A single LLM prompt path regardless of whether the wardrobe was populated or empty.

**What I overrode:** Directed Claude to add two distinct prompt paths: one for a non-empty wardrobe (asks the LLM to name specific wardrobe pieces in the outfit) and one for an empty wardrobe (asks the LLM for general styling advice using common staples). The empty-wardrobe path changed the failure mode from "return error string" to "call LLM with general advice," which was then reflected back into the spec in `planning.md`.

---

### Instance 3 — Implementing `run_agent`

**Input to Claude:** The Planning Loop and State Management sections of `planning.md` plus the Mermaid flowchart showing each tool call and its yes/no decision branches.

**What it produced:** A complete `run_agent()` implementation following all 7 steps with correct session key names and early-return guards after each tool call.

**What I overrode:** Added regex-based query parsing (Step 2) since the spec left the parsing approach open. Chose regex over an LLM-based parser to keep query parsing deterministic and avoid an extra API call. The patterns `\bsize\s+([A-Za-z0-9/]+)` and `(?:under|max|below)\s*\$?\s*(\d+(?:\.\d+)?)` handle the formats shown in the spec's example queries without requiring a model call.
