from tools import search_listings, suggest_outfit, create_fit_card
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe


# ═══════════════════════════════════════════════════════════════════════════════
#  Tool 1 — search_listings
# ═══════════════════════════════════════════════════════════════════════════════

class TestSearchListings:

    def test_returns_results_for_matching_query(self):
        """'vintage graphic tee' should hit several listings (lst_002, lst_006, lst_033, etc.)."""
        results = search_listings("vintage graphic tee")
        assert isinstance(results, list)
        assert len(results) > 0

    def test_returns_error_string_for_no_matches(self):
        """No listing is a 'designer ballgown' under $5 in XXS — must return the no-match error string."""
        results = search_listings("designer ballgown", size="XXS", max_price=5.0)
        assert results == "No items match your criteria, please adjust your criteria"

    def test_multiple_filters_size_and_price(self):
        """
        'denim' in size 'M' at or under $30 should return lst_038 (Denim Vest, $27, size M).
        Verifies both filters are applied together, not independently.
        """
        results = search_listings("denim", size="M", max_price=30.0)
        assert len(results) > 0
        for item in results:
            assert item["price"] <= 30.0, f"{item['title']} costs ${item['price']}, over max"
            assert "m" in item["size"].lower(), f"Size '{item['size']}' doesn't contain 'M'"

    def test_results_capped_at_three(self):
        """'vintage streetwear' matches many listings — result must still be at most 3."""
        results = search_listings("vintage streetwear")
        assert len(results) <= 3

    def test_price_filter_excludes_over_budget_items(self):
        """Every returned item must cost at or below max_price=$20."""
        results = search_listings("vintage", max_price=20.0)
        for item in results:
            assert item["price"] <= 20.0, f"{item['title']} costs ${item['price']}, over $20 cap"

    def test_size_filter_is_case_insensitive(self):
        """
        Passing size='s/m' (lowercase) should match listings with size 'S/M'.
        lst_002 (Y2K Baby Tee, S/M) is the primary expected match.
        """
        results = search_listings("vintage", size="s/m")
        assert len(results) > 0
        for item in results:
            assert "s/m" in item["size"].lower(), f"Size '{item['size']}' doesn't contain 's/m'"


# ═══════════════════════════════════════════════════════════════════════════════
#  Tool 2 — suggest_outfit
# ═══════════════════════════════════════════════════════════════════════════════

# Sample new_item drawn from lst_006 in listings.json
SAMPLE_ITEM = {
    "id": "lst_006",
    "title": "Graphic Tee — 2003 Tour Bootleg Style",
    "description": "Vintage-style bootleg tee with faded graphic. Slightly boxy fit.",
    "category": "tops",
    "style_tags": ["graphic tee", "vintage", "grunge", "streetwear", "band tee"],
    "size": "L",
    "condition": "good",
    "price": 24.00,
    "colors": ["black"],
    "brand": None,
    "platform": "depop",
}


class TestSuggestOutfit:

    def test_valid_wardrobe_returns_suggestion(self):
        """With a real wardrobe, should return a non-empty LLM-generated string."""
        result = suggest_outfit(SAMPLE_ITEM, get_example_wardrobe())
        assert isinstance(result, str)
        assert len(result.strip()) > 0

    def test_empty_wardrobe_returns_general_advice(self):
        """Empty wardrobe triggers the general styling advice path — still a non-empty string."""
        result = suggest_outfit(SAMPLE_ITEM, get_empty_wardrobe())
        assert isinstance(result, str)
        assert len(result.strip()) > 0

    def test_invalid_new_item_returns_error_string(self):
        """Passing a non-dict new_item should return the validation error string, not raise."""
        result = suggest_outfit("not a dict", get_example_wardrobe())
        assert result == "Please utilize search_listings to find a new valid item"


# ═══════════════════════════════════════════════════════════════════════════════
#  Tool 3 — create_fit_card
# ═══════════════════════════════════════════════════════════════════════════════

# Realistic outfit suggestion built from SAMPLE_ITEM + a typical wardrobe
SAMPLE_OUTFIT = (
    "Pair the Graphic Tee — 2003 Tour Bootleg Style with your high-waisted "
    "baggy jeans and white chunky sneakers for a relaxed vintage streetwear "
    "look. Tuck the front of the tee slightly to add shape while keeping the "
    "silhouette loose."
)


class TestCreateFitCard:

    def test_valid_inputs_returns_non_empty_caption(self):
        """Valid outfit + valid new_item should return a non-empty LLM-generated string."""
        result = create_fit_card(SAMPLE_OUTFIT, SAMPLE_ITEM)
        assert isinstance(result, str)
        assert len(result.strip()) > 0

    def test_caption_references_new_item(self):
        """LLM is prompted to mention item title, price, and platform — at least one should appear."""
        result = create_fit_card(SAMPLE_OUTFIT, SAMPLE_ITEM)
        lower = result.lower()
        assert (
            SAMPLE_ITEM["title"].lower() in lower
            or str(SAMPLE_ITEM["price"]) in result
            or SAMPLE_ITEM["platform"].lower() in lower
        ), f"Caption doesn't reference the new item: {result!r}"

    def test_empty_outfit_returns_error_string(self):
        """Empty outfit string should return the error string without calling the LLM."""
        result = create_fit_card("", SAMPLE_ITEM)
        assert result == "Cannot generate an outfit caption at this time"

    def test_whitespace_outfit_returns_error_string(self):
        """Whitespace-only outfit string should also return the error string."""
        result = create_fit_card("   ", SAMPLE_ITEM)
        assert result == "Cannot generate an outfit caption at this time"
