"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform
    """
    listings = load_listings()

    # ── Hard filters ──────────────────────────────────────────────────────────
    if max_price is not None:
        listings = [l for l in listings if l["price"] <= max_price]
    if size is not None:
        listings = [l for l in listings if size.lower() in l["size"].lower()]

    # ── Relevance scoring ─────────────────────────────────────────────────────
    def tokenize(text: str) -> set[str]:
        return {w.lower().strip(".,!?") for w in text.split() if w.strip()}

    keywords = tokenize(description)

    def score(listing: dict) -> int:
        searchable = " ".join([
            listing["title"],
            listing["description"],
            listing["category"],
            " ".join(listing["style_tags"] or []),
            " ".join(listing["colors"] or []),
            listing["brand"] or "",
        ])
        return len(keywords.intersection(tokenize(searchable)))

    scored = [(score(l), l) for l in listings]
    scored = [(s, l) for s, l in scored if s > 0]

    scored.sort(key=lambda x: x[0], reverse=True)
    return [l for _, l in scored[:3]]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict from search_listings(). Fields are read with
                  .get() so missing keys produce a degraded-but-valid prompt.
                  Returns an error string if new_item is not a dict.
        wardrobe: A wardrobe dict with an 'items' key. If the key is missing
                  or the list is empty, falls back to general styling advice.

    Returns:
        A non-empty string from the LLM.

        Empty wardrobe: asks the LLM for general styling advice — what kinds of
        pieces pair well with the item, what vibe it suits, and 1–2 outfit ideas
        using common wardrobe staples. Does not raise or return an empty string.

        Non-empty wardrobe: formats each wardrobe piece (name, category, colors,
        style tags, notes) into the prompt and asks the LLM to suggest 1–2
        outfits pairing the new item with named pieces from the wardrobe.
    """
    if not isinstance(new_item, dict):
        return "Please utilize search_listings to find a new valid item"

    client = _get_groq_client()
    items = wardrobe.get("items", [])

    colors = ", ".join(new_item.get("colors") or [])
    tags = ", ".join(new_item.get("style_tags") or [])
    item_summary = (
        f"Item: {new_item.get('title', 'Unknown item')}\n"
        f"Category: {new_item.get('category', 'unknown')}\n"
        f"Colors: {colors}\n"
        f"Style tags: {tags}\n"
        f"Size: {new_item.get('size', 'unknown')}\n"
        f"Condition: {new_item.get('condition', 'unknown')}\n"
        f"Price: ${new_item.get('price', '?')}"
    )

    if not items:
        prompt = (
            f"A user is considering buying the following thrifted item:\n\n"
            f"{item_summary}\n\n"
            f"They don't have a wardrobe on file yet. Give them general styling advice: "
            f"what kinds of pieces pair well with this item, what vibe or aesthetic it suits, "
            f"and 1–2 complete outfit ideas using common wardrobe staples."
        )
    else:
        wardrobe_lines = []
        for w in items:
            w_colors = ", ".join(w.get("colors") or [])
            w_tags = ", ".join(w.get("style_tags") or [])
            line = f"- {w.get('name', 'item')} ({w.get('category', '')}): colors [{w_colors}], tags [{w_tags}]"
            if w.get("notes"):
                line += f" — {w['notes']}"
            wardrobe_lines.append(line)

        prompt = (
            f"A user is considering buying the following thrifted item:\n\n"
            f"{item_summary}\n\n"
            f"Here is their current wardrobe:\n" + "\n".join(wardrobe_lines) + "\n\n"
            f"Suggest 1–2 complete outfits that pair the new item with specific pieces "
            f"from their wardrobe above. Name each wardrobe piece you include."
        )
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
        )
        suggestion =  response.choices[0].message.content
    except Exception:
        return "Cannot generate an outfit suggestion at this time"
    
    if not suggestion or not suggestion.strip():
        return "Cannot generate an outfit suggestion at this time"

    return suggestion

# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    """
    if not outfit or not outfit.strip():
        return "Please provide an outfit suggestion to create a fit card."

    title = new_item.get("title", "thrifted find")
    price = new_item.get("price", "?")
    platform = new_item.get("platform", "a thrift app")

    prompt = (
        f"Write a 2–4 sentence Instagram/TikTok caption for this thrifted outfit.\n\n"
        f"New item: {title} — ${price} from {platform}\n"
        f"Outfit: {outfit}\n\n"
        f"Guidelines:\n"
        f"- Sound casual and authentic, like a real OOTD post (not a product description)\n"
        f"- Mention the item name, price, and platform naturally — each only once\n"
        f"- Capture the specific vibe of the outfit\n"
        f"- Keep it to 2–4 sentences"
    )

    client = _get_groq_client()
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=1.2,
        )
        caption = response.choices[0].message.content
    except Exception:
        return "Cannot generate an outfit caption at this time"

    if not caption or not caption.strip():
        return "Cannot generate an outfit caption at this time"
    return caption
