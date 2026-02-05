# Analyzer Guide

This guide explains how the analyzer agent works and how to customize its behavior.

## Table of Contents

- [How the Analyzer Works](#how-the-analyzer-works)
- [LLM Prompts](#llm-prompts)
- [Customizing Prompts](#customizing-prompts)
- [Event Categories](#event-categories)
- [Output Format](#output-format)
- [Performance Optimization](#performance-optimization)
- [Debugging](#debugging)

---

## How the Analyzer Works

The analyzer agent (`agents/analyzer_agent.py`) is the second agent in the pipeline. Its job is to:

1. **Receive raw event text** from the scraper agent
2. **Parse the text** into structured event data using an LLM
3. **Validate events** ensuring required fields are present
4. **Save events** to the database
5. **Track metrics** (events found, valid events, duration)

### Flow

```
1. Receive raw summary from scraper
2. Split into chunks (if too large)
3. For each chunk:
   a. Send to LLM with extraction prompt
   b. Parse JSON response
   c. Extract events into structured format
4. Merge all events from chunks
5. Validate each event (name, date, location, source)
6. Infer category from description/name
7. Save to database (events table)
8. Update run status with metrics
```

### Key Components

- **Analyzer Agent** (`agents/analyzer_agent.py:30`): Orchestrates event extraction
- **LLM Prompts**: System and user prompts for extraction
- **JSON Parser**: Handles LLM output parsing with fallbacks
- **Category Inference**: Assigns categories based on keywords
- **Chunking**: Splits large texts to avoid token limits

---

## LLM Prompts

### System Prompt

```python
SYSTEM_PROMPT = """You are a data analyst. You receive a text that describes local events (from web search/summaries).
Your task is to extract every event and output a single JSON array of objects. Each object must have exactly these fields:
- "name": string (event title)
- "description": string (short summary or category)
- "location": string (venue or place)
- "date": string (e.g. "2025-02-01" or "Samstag 1. Februar")
- "time": string (e.g. "14:00" or "all day") or empty string if unknown
- "source": string (URL or website name where the event was found; required)
- "category": string - Categorize as one of: "family", "adult", "sport", "other" (based on event type, target audience, and content)
Output only the JSON array, no markdown code fence, no extra text. If there are no events, output []."""
```

### User Prompt

```python
USER_PROMPT = """Extract all events from this text into a JSON array (include source for each event):

{raw_event_text}
"""
```

### Prompt Design Principles

1. **Explicit format requirements**: Specifies exact JSON structure
2. **Required fields**: Lists all mandatory fields
3. **Category constraints**: Limits to allowed categories
4. **Source requirement**: Ensures event provenance is tracked
5. **Fallback handling**: Instructs what to do when no events found

---

## Customizing Prompts

### Modify Existing Prompts

Edit `agents/analyzer_agent.py` directly:

```python
# Change system prompt
SYSTEM_PROMPT = """You are an event data extractor..."""

# Change user prompt
USER_PROMPT = """Extract events from: {raw_event_text}"""
```

### Add Custom Categories

Extend the category inference in `_infer_category()`:

```python
def _infer_category(self, description: str, name: str = "") -> str:
    """Infer category from event description and name."""
    text = (description + " " + name).lower()

    category_keywords = {
        "family": ["familie", "kinder", "jugend", "kind", "baby", "schule", "eltern", "familien"],
        "adult": ["erwachsen", "adult", "senior", "abend", "nacht", "bar", "club", "party"],
        "sport": ["sport", "fitness", "laufen", "schwimmen", "rad", "fußball", "tennis", "yoga"],
        # Add new categories
        "music": ["musik", "konzert", "band", "dj", "festival", "jazz", "rock"],
        "theater": ["theater", "schauspiel", "oper", "ballett", "musical"],
        "culture": ["kunst", "ausstellung", "museum", "galerie", "kultur"],
    }

    for category, keywords in category_keywords.items():
        if any(kw in text for kw in keywords):
            return category

    return "other"
```

Then update the system prompt to include new categories:

```python
SYSTEM_PROMPT = """...
- "category": string - Categorize as one of: "family", "adult", "sport", "music", "theater", "culture", "other"
..."""
```

### Custom Prompt Templates

Create a custom analyzer with different prompts:

```python
from agents.analyzer_agent import AnalyzerAgent

class CustomAnalyzer(AnalyzerAgent):
    def __init__(self, model: str | None = None, base_url: str | None = None):
        super().__init__(model, base_url)

        # Override prompts
        custom_system = """You specialize in family-friendly events..."""
        custom_user = """Extract family events from: {raw_event_text}"""

        self._prompt = ChatPromptTemplate.from_messages([
            ("system", custom_system),
            ("human", custom_user),
        ])
```

---

## Event Categories

### Default Categories

| Category | Description | Keywords |
|----------|-------------|----------|
| `family` | Family and children events | familie, kinder, jugend, kind, baby, schule, eltern |
| `adult` | Adult-oriented events | erwachsen, adult, senior, abend, nacht, bar, club, party |
| `sport` | Sports and fitness events | sport, fitness, laufen, schwimmen, rad, fußball, tennis, yoga |
| `other` | Uncategorized events | Default category |

### Category Inference Logic

Categories are inferred from both the event name and description:

```python
text = (description + " " + name).lower()

# Check each category's keywords
for category, keywords in category_keywords.items():
    if any(kw in text for kw in keywords):
        return category

return "other"  # Default if no match
```

### Validating Events

Events are considered valid if they have all required fields:

```python
def is_valid_event(event: dict) -> bool:
    return all([
        event.get("name"),
        event.get("date"),
        event.get("location"),
        event.get("source"),
    ])
```

---

## Output Format

### Event Object Structure

```python
{
    "name": "Jazz Concert at City Hall",
    "description": "Open air jazz performance with local bands",
    "location": "City Hall, Main Square",
    "date": "2025-02-15",
    "time": "19:00",
    "source": "https://www.monheim.de/termine",
    "category": "other"
}
```

### JSON Array Format

LLM must output a valid JSON array:

```json
[
  {
    "name": "Event 1",
    "description": "Description 1",
    "location": "Location 1",
    "date": "2025-02-01",
    "time": "14:00",
    "source": "https://example.com",
    "category": "family"
  },
  {
    "name": "Event 2",
    "description": "Description 2",
    "location": "Location 2",
    "date": "2025-02-02",
    "time": "",
    "source": "https://example.com",
    "category": "sport"
  }
]
```

### Parsing Robustness

The analyzer handles various LLM output formats:

```python
def _parse_json_array(self, text: str) -> list[dict]:
    """Try to extract a JSON array from the model output."""
    text = text.strip()

    # Remove markdown code fences
    if "```" in text:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if match:
            text = match.group(1).strip()

    try:
        data = json.loads(text)

        # Handle different formats
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "events" in data:
            return data["events"]
        if isinstance(data, dict):
            return [data]

        return []
    except json.JSONDecodeError:
        return []
```

---

## Performance Optimization

### Chunking Strategy

Large texts are split into chunks to avoid token limits:

```python
def _split_into_chunks(self, raw_event_text: str, events_per_chunk: int = 5) -> list[str]:
    """Split raw event text into chunks of events."""
    events_pattern = r'\*\s+\*\*Event:\*\*'
    event_blocks = re.split(events_pattern, raw_event_text)

    # Group events into chunks
    chunks = []
    for i in range(1, len(event_blocks), events_per_chunk):
        batch = event_blocks[i:i+events_per_chunk]
        chunk = '\n*   **Event:**'.join([''] + batch)
        chunks.append(chunk.strip())

    return chunks
```

### Adjusting Chunk Size

```bash
# Run analyzer with custom chunk size
python -c "
from agents import AnalyzerAgent

analyzer = AnalyzerAgent()
events = analyzer.run(raw_text, chunk_size=10)  # Default: 5
"
```

### LLM Configuration

Adjust temperature for deterministic output:

```python
# In analyzer_agent.py
self.llm = ChatOpenAI(
    model=model,
    temperature=0.1,  # Lower = more consistent
    # ...
)
```

### Batch Processing

For large datasets, process in batches:

```python
# Run scraper only
python main.py --agent scraper --cities monheim solingen

# Run analyzer later on saved summaries
python main.py --agent analyzer
# Paste summary or load from DB
```

---

## Debugging

### Enable Verbose Output

```bash
python main.py --cities monheim -v
```

### Inspect LLM Output

```python
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from config import LLM_PROVIDER, DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL

if LLM_PROVIDER == "deepseek":
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(model=DEEPSEEK_MODEL, api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

# Test extraction
chain = prompt | llm | StrOutputParser()
result = chain.invoke({"raw_event_text": "Sample text with events"})
print(result)
```

### Check Database

```bash
# View recent runs
python main.py --list-runs

# Query events
sqlite3 data/events.db "SELECT * FROM events ORDER BY id DESC LIMIT 10"

# Check validation stats
sqlite3 data/events.db "
SELECT
    r.id,
    r.agent,
    s.events_found,
    s.valid_events
FROM runs r
JOIN status s ON s.run_id = r.id
ORDER BY r.id DESC
LIMIT 5"
```

### Common Issues

| Issue | Solution |
|-------|----------|
| No events extracted | Check LLM is working, verify prompt format |
| Invalid JSON output | Use `--verbose` to see raw LLM output |
| Missing required fields | Improve prompt to emphasize required fields |
| Wrong categories | Add keywords to `_infer_category()` |
| Token limit exceeded | Reduce `chunk_size` or use larger LLM |

### Debug Categories

```python
from agents import AnalyzerAgent

analyzer = AnalyzerAgent()

# Test category inference
print(analyzer._infer_category("Kinderfest im Park", ""))
# Output: family

print(analyzer._infer_category("Fitness im Park", ""))
# Output: sport
```

### Test JSON Parsing

```python
import json
from agents.analyzer_agent import AnalyzerAgent

analyzer = AnalyzerAgent()

# Test parsing
test_outputs = [
    '[{"name": "Event 1"}]',
    '```json\n[{"name": "Event 1"}]\n```',
    '{"events": [{"name": "Event 1"}]}',
    '{"name": "Event 1"}',
]

for output in test_outputs:
    events = analyzer._parse_json_array(output)
    print(f"Input: {output[:30]}... -> {len(events)} events")
```

---

## Advanced Usage

### Custom Validator

```python
class CustomAnalyzer(AnalyzerAgent):
    def _validate_event(self, event: dict) -> bool:
        """Custom validation logic."""
        # Require date to be in the future
        from datetime import datetime
        date_str = event.get("date", "")

        try:
            event_date = datetime.strptime(date_str, "%Y-%m-%d")
            return event_date >= datetime.now()
        except ValueError:
            return False

    def run(self, raw_event_text: str, ...):
        # Override to use custom validation
        all_events = []
        # ... extraction logic ...

        # Filter with custom validator
        valid_events = [e for e in all_events if self._validate_event(e)]

        return valid_events
```

### Post-Processing

```python
# After running analyzer
events = analyzer.run(raw_text)

# Add custom fields
for event in events:
    event['city'] = 'Monheim'
    event['country'] = 'Germany'
    event['created_by'] = 'analyzer_agent'

# Save to DB
from storage import insert_events, create_run
run_id = create_run("analyzer")
insert_events(events, run_id)
```

---

## Resources

- **Analyzer Agent**: `agents/analyzer_agent.py`
- **Base Classes**: `rules/base.py`
- **Storage**: `storage.py`
- **Config**: `config.py`
