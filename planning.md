# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
search_listings extracts the items in listings.json utilizing the data_loader.py function: load_listings(). It filters against the fields that make up a listing and if it returns nothing, the app should communicate with the user about they need to do differently and stop.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `description` (str): contains key words about a user's desired attributes for an article of clothing that are not captured in other fields
- `category` (str): specifies the type of article of clothing for faster filtering (outerwear, top, shoes, etc.)
- `style_tags` (str): keywords that filter based on style keywords (vintage, grunge, flowy, etc.)
- `size` (str): keyword that filter based on size, default includes all sizes
- `max_price` (float): a number that represents the max price for an item, will filter items priced above this number
- `colors` (str): will filter out items that don't match the specified colors the user is searching for, default to include all colors
- `brand` (str): will filter out items that don't match the brand specified by the user, default to include all brands

**What it returns:**
<!-- Describe the return value -->
Returns 3 listings that follow the listing schema, sorted by relevance. FitFindr picks the top result.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the outfit data is incomplete? -->
- Returns no matching listings: return null. Notify user = "Items matching criteria were not found, try again with different criteria."

---

### Tool 2: suggest_outfit

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
suggest_outfit needs an existing wardrobe and a new item (output from search_listings). It should take any additional context provided by the user to search for the rest of an outfit (if the new item is a top, this function should have shoes and bottoms to create an outfit).

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `new_item` (dict): an item from the listings.json
- `wardrobe` (dict): a non-empty wardrobe that follows the wardrobe schema

**What it returns:**
<!-- Describe the return value -->
The output is a generated string that pairs existing items in a user's wardrobe with the new item passed into the function and how to style them together.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the outfit data is incomplete? -->
- Empty wardrobe: "Please add an item to your wardrobe to generate an outfit suggestion"
- Wrong input type for new_item: "Please utilize search_listings to find a new valid item"


---

### Tool 3: create_fit_card

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
create_fit_card takes a suggestion (output from suggest_outfit()) and a new item (output from search_listings()) and generates a caption for a post that follows the suggestion and assumes the user bought the item.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `outfit` (str): the generated outfit suggestion that the user is following
- `new_item` (dict): the new_item and all the metadata associated with it to highlight the new item in the generated caption.

**What it returns:**
<!-- Describe the return value -->
The output is a generated string that shares the suggestion and new item with an audience that may be interested in replicating the outfit.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the outfit data is incomplete? -->
- If we don't have an outfit suggestion, or a new_item, the error should have surfaced in an earlier function output. If it fails for any reason: "Cannot generate an outfit caption at this time"

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**
<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->

After search_listings runs, check whether results is empty. If it is empty, save an error message in the session and return early. If it has results, choose the first listing with session.new_item = results[0].

Then call suggest_outfit using the selected item and the user’s wardrobe. Before generating the suggestion, check whether the wardrobe is empty. If it is, save an error message and stop. If not, generate the suggestion. If the suggestion is empty, save an error and stop. Otherwise, save it as session.fit_suggestion.

Finally, call create_fit_card using the outfit suggestion and selected item. Generate the caption, then check whether the caption is empty. If it is empty, save an error and stop. Otherwise, save it as session.fit_caption and return the completed session.

---

## State Management

**How does information from one tool get passed to the next?**
<!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? -->

After search_listings runs, its returned listings are stored as results. If results is not empty, the agent saves the top listing as session.new_item = results[0].

That new_item is then passed into suggest_outfit(new_item, wardrobe). If a suggestion is successfully generated, it is saved as session.fit_suggestion.

Then fit_suggestion and new_item are passed into create_fit_card(fit_suggestion, new_item). If a caption is created, it is saved as session.fit_caption.

If any step fails, the agent saves an error message in session.error and returns early instead of calling the next tool.

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Set session.error = "No listings found" and stop the planning loop. Do not call suggest_outfit because there is no selected item to recommend.|
| suggest_outfit | Wardrobe is empty | Set session.error = "Add an item to wardrobe for suggestion" and stop the planning loop. Do not attempt to generate an outfit suggestion.|
| create_fit_card | Outfit input is missing or incomplete | Set session.error = "Cannot generate a caption at this time" and stop the planning loop. Return the session with the selected item and outfit suggestion, but without a fit caption.|

---

## Architecture

<!-- Draw a diagram of your agent showing how the components connect:
     User input → Planning Loop → Tools (search_listings, suggest_outfit, create_fit_card) ↕ State / Session
     
     Show what triggers each tool, how state flows between them, and where error paths branch off.
     ASCII art, a Mermaid diagram (https://mermaid.js.org/syntax/flowchart.html), or an embedded
     sketch are all fine. You'll share this diagram with an AI tool when asking it to implement
     the planning loop and each individual tool. -->

     ```mermaid
     flowchart TD
     A([user query]) --> B

     subgraph LOOP ["Initiate Planning Loop"]
          B["search_listings(args)\nresults = []"]
          B --> C["find_matches(args)\n→ results = [item1, item2, item3]"]
          C --> D{len results == 0?}
          D -- yes --> STOP1(["[ERROR] No listings found\nSTOP LOOP"])
          D -- no --> E["session: new_item = results[0]"]

          E --> F["suggest_outfit(new_item, wardrobe)\nsuggestion = ''"]
          F --> G{len wardrobe == 0?}
          G -- yes --> STOP2(["[ERROR] Add an item to wardrobe\nfor suggestion\nSTOP LOOP"])
          G -- no --> H["generate_suggestion(new_item, wardrobe)\n→ suggestion = '...'"]
          H --> I{len suggestion == 0?}
          I -- yes --> STOP3(["[ERROR] Cannot generate a\nsuggestion at this time\nSTOP LOOP"])
          I -- no --> J["session: fit_suggestion = suggestion"]

          J --> K["create_fit_card(fit_suggestion, new_item)\ncaption = ''"]
          K --> L["create_caption(fit_suggestion, new_item)\n→ caption = '...'"]
          L --> M{len caption == 0?}
          M -- yes --> STOP4(["[ERROR] Cannot generate a\ncaption at this time\nSTOP LOOP"])
          M -- no --> N["session: fit_caption = caption"]
     end

     N --> O([return session])
     ```

---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

**Milestone 3 — Individual tool implementations:**

For Milestone 3, I plan to use Claude to help implement and test each tool one at a time. I will give ChatGPT the specific tool spec from this `planning.md`, including the tool’s purpose, input parameters, expected return value, and failure modes. I will also provide the relevant project files, such as `data_loader.py`, `listings.json`, and any wardrobe schema files, so the implementation matches the existing data structure.

For `search_listings()`, I will ask Claude to implement the function using `load_listings()` from `data_loader.py`. I expect it to produce a function that filters listings by description, category, style tags, size, max price, colors, and brand, then returns the top 3 relevant results. I will verify it by testing at least 3 queries: one that should return matches, one that should return no matches, and one with multiple filters such as size and max price.

For `suggest_outfit()`, I will give Claude the tool spec, an example `new_item` from `search_listings()`, and a sample wardrobe. I expect it to produce a function that validates the wardrobe and new item, then generates a styling suggestion using the new item and compatible wardrobe pieces. I will verify it by testing with a valid wardrobe, an empty wardrobe, and an invalid `new_item` input.

For `create_fit_card()`, I will give Claude the tool spec, a sample outfit suggestion, and the selected listing. I expect it to produce a function that generates a short social-style caption highlighting the new item and outfit. I will verify it by checking that the caption references the new item, reflects the outfit suggestion, and returns the correct error message if caption generation fails.

**Milestone 4 — Planning loop and state management:**

For Milestone 4, I plan to use ChatGPT to help implement the planning loop based on my agent diagram and the Mermaid diagram in this `planning.md`. I will provide the full planning loop description, including the exact conditional branches after each tool call.

I expect ChatGPT to produce a session-based control flow where the agent stores intermediate state such as `results`, `new_item`, `fit_suggestion`, `fit_caption`, and `error`.

First, the planning loop calls `search_listings()` using the user’s search criteria. After `search_listings()` runs, the loop checks whether `results` is empty or null. If results are empty, it sets `session.error = "Items matching criteria were not found, try again with different criteria."` and returns early. If results exist, it sets `session.results = results`, selects the top result with `session.new_item = results[0]`, and continues.

Next, before calling `suggest_outfit()`, the loop checks whether `session.new_item` exists and is a valid listing dictionary. If not, it sets `session.error = "Please utilize search_listings to find a new valid item"` and returns early. Then it checks whether the user’s wardrobe exists and is non-empty. If the wardrobe is empty, it sets `session.error = "Please add an item to your wardrobe to generate an outfit suggestion"` and returns early. Only after both checks pass does the loop call `suggest_outfit(new_item=session.new_item, wardrobe=wardrobe)`.

After `suggest_outfit()` runs, the loop checks whether a suggestion was generated. If no suggestion is returned, it sets `session.error` to the appropriate outfit-generation error and returns early. If a suggestion exists, it stores it as `session.fit_suggestion` and continues.

Next, before calling `create_fit_card()`, the loop checks that both `session.fit_suggestion` and `session.new_item` exist. In the expected flow, these errors should already have been caught earlier, but this check protects against invalid session state. If either value is missing, the loop sets `session.error` and returns early. If both values exist, the loop calls `create_fit_card(outfit=session.fit_suggestion, new_item=session.new_item)`.

After `create_fit_card()` runs, the loop checks whether a caption was successfully generated. If caption generation fails, likely because the LLM or caption generator is unavailable, it sets `session.error = "Cannot generate an outfit caption at this time"` and returns the session. If successful, it stores the caption as `session.fit_caption` and returns the completed session.

I will verify the planning loop by running end-to-end tests for both the successful path and each error path. The successful path should call all three tools in order and return a selected listing, outfit suggestion, and fit card caption. The error paths should stop early and avoid calling downstream tools with missing or invalid input.

---


## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

### Step 1: Search for listings

The agent extracts the user's search criteria and calls `search_listings()`.

**Tool call:**

```python
search_listings(
    description="graphic tee",
    category="top",
    style_tags="vintage",
    max_price=30.0
)
```

**Tool output:**

```python
[
    {
        "name": "Faded Band Tee",
        "price": 22.0,
        "platform": "Depop",
        "condition": "Good",
        "category": "top",
        "style_tags": ["vintage", "grunge"],
        "size": "M"
    },
    {
        "name": "Vintage Racing Tee",
        "price": 25.0,
        "platform": "Grailed",
        "condition": "Good",
        "category": "top",
        "style_tags": ["vintage"]
    },
    {
        "name": "Retro Tour Tee",
        "price": 28.0,
        "platform": "Depop",
        "condition": "Fair",
        "category": "top",
        "style_tags": ["vintage", "streetwear"]
    }
]
```

The planning loop checks whether the results are empty.

```python
if len(results) == 0:
    session.error = "Items matching criteria were not found, try again with different criteria."
    return session
```

Since results exist, the agent stores the results and selects the top listing.

```python
session.results = results
session.new_item = results[0]
```

---

### Step 2: Generate an outfit suggestion

The planning loop verifies that:

- `session.new_item` exists and is a valid listing
- the wardrobe follows the wardrobe schema
- `len(wardrobe["items"]) > 0`

The agent calls `suggest_outfit()` using the selected listing and the user's wardrobe.

**Tool call:**

```python
suggest_outfit(
    new_item=session.new_item,
    wardrobe={
        "items": [
            {
                "id": "w_001",
                "name": "Baggy straight-leg jeans, dark wash",
                "category": "bottoms",
                "colors": ["dark blue", "indigo"],
                "style_tags": ["denim", "streetwear", "baggy"],
                "notes": "High-waisted, sits above the hip"
            },
            {
                "id": "w_007",
                "name": "Chunky white sneakers",
                "category": "shoes",
                "colors": ["white"],
                "style_tags": ["sneakers", "chunky", "streetwear"],
                "notes": None
            }
        ]
    }
)
```

The tool examines the new item and the wardrobe metadata to identify compatible pieces. It uses categories, colors, style tags, and notes to create a complete outfit recommendation.

**Tool output:**

```python
"Pair the Faded Band Tee with your baggy straight-leg jeans and chunky white sneakers for a relaxed vintage streetwear look. The dark-wash denim balances the faded graphic, while the chunky sneakers reinforce the 90s-inspired silhouette. Slightly tuck the front of the tee to add shape while keeping the outfit casual."
```

The planning loop verifies that a suggestion was generated.

```python
if suggestion is None or suggestion == "":
    session.error = "Unable to generate outfit suggestion"
    return session
```

If successful, the agent stores the result:

```python
session.fit_suggestion = suggestion
```

---

### Step 3: Generate a fit card caption

The planning loop verifies that:

- `session.new_item` exists
- `session.fit_suggestion` exists

Since both values are present, the agent calls `create_fit_card()`.

**Tool call:**

```python
create_fit_card(
    outfit=session.fit_suggestion,
    new_item=session.new_item
)
```

**Tool output:**

```python
"thrifted this faded band tee off Depop for $22 and styled it with baggy jeans + chunky sneakers for the easiest vintage streetwear fit 🖤"
```

The planning loop stores the generated caption.

```python
session.fit_caption = caption
```

---

### Step 4: Return the completed response

The planning loop returns the completed session.

```python
return {
    "new_item": session.new_item,
    "fit_suggestion": session.fit_suggestion,
    "fit_caption": session.fit_caption
}
```

---

## Final output to user

```text
I found a match for you:

Faded Band Tee — $22 on Depop
Condition: Good

How to style it:
Pair the Faded Band Tee with your baggy jeans and chunky sneakers for a relaxed vintage streetwear look. Slightly tuck the front of the tee to add shape while keeping the outfit casual.

Fit Card Caption:
thrifted this faded band tee off Depop for $22 and styled it with baggy jeans + chunky sneakers for the easiest vintage streetwear fit 🖤
```
