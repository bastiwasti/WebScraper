# Category System

Centralized, flexible category management for all WebScraper event sources.

---

## Overview

WebScraper uses a **10-category system** with standardized category IDs, German display names, and multi-language keyword inference.

**Files:**
- `rules/categories.py` - Category definitions and inference logic
- `rules/utils.py` - Date/time normalization utilities

---

## Categories

| ID | Name (DE) | Name (EN) | Priority | Description |
|----|-------------|-------------|----------|-------------|
| `family` | Familie | Family | 1 | Events for children, teens, parents |
| `education` | Bildung | Education | 2 | Courses, workshops, lectures, schools |
| `sport` | Sport | Sport | 3 | Sports, fitness, recreation |
| `culture` | Kultur | Culture | 4 | Theater, music, art, exhibitions, museums |
| `market` | Markt | Market | 5 | Markets, fairs, sales events |
| `festival` | Fest | Festival | 6 | Festivals, carnivals, celebrations |
| `adult` | Erwachsene | Adult | 7 | Events for adults, seniors, nightlife |
| `community` | Gemeinschaft | Community | 8 | Social events, meetings, clubs |
| `nature` | Natur | Nature | 9 | Outdoor, hiking, environment |
| `other` | Sonstiges | Other | 10 | Fallback for unmatched events |

---

## Category Inference

### How It Works

The category system uses **first-match priority** to infer categories from event text:

1. Searches German keywords (in priority order)
2. Searches English keywords (in priority order)
3. Returns `"other"` if no match

**Priority Order:** family → education → sport → culture → market → festival → adult → community → nature → other

### Example

```python
from rules import categories

# "Konzert für Kinder" → family (Kinder matches before Konzert)
cat = categories.infer_category("Konzert für Kinder")
# Returns: "family"

# "Fußballturnier" → sport
cat = categories.infer_category("Fußballturnier")
# Returns: "sport"

# "Bücherlesung" → culture
cat = categories.infer_category("Bücherlesung")
# Returns: "culture"
```

---

## Category Normalization

### Aliases to Standard IDs

The system normalizes common category variations to standard IDs:

| Raw Category | Standard Category |
|--------------|------------------|
| `sports` | `sport` |
| `kultur`, `musik`, `music` | `culture` |
| `vhs`, `volkshochschule` | `education` |
| `library`, `bibliothek`, `school` | `education` |
| `museum` | `culture` |
| `women`, `frauen`, `damen` | `adult` |
| `seniors`, `senioren` | `adult` |
| `familie`, `familien` | `family` |
| `karneval`, `fastnacht` | `festival` |

### Usage

```python
from rules import categories

# Normalize any category
normalized = categories.normalize_category("sports")
# Returns: "sport"

normalized = categories.normalize_category("kultur")
# Returns: "culture"

# Check if category is valid
is_valid = categories.is_valid_category("culture")
# Returns: True
```

---

## Helper Functions

### Get All Categories

```python
from rules import categories

all_cats = categories.get_all_categories()
# Returns: List of Category objects sorted by priority
```

### Get Category Display Name

```python
from rules import categories

# German (default)
name_de = categories.get_category_name("culture")
# Returns: "Kultur"

# English
name_en = categories.get_category_name("culture", language="en")
# Returns: "Culture"
```

### Get Default Category

```python
from rules import categories

default = categories.get_default_category()
# Returns: "other"
```

---

## Usage in Scrapers

### Example 1: Using Inference

```python
from rules import categories, utils

# Infer category from event text
category = categories.infer_category(event_description, event_name)

# Normalize to standard ID
category = categories.normalize_category(category)
```

### Example 2: Normalizing Dates and Times

```python
from rules import utils

# Normalize date to DD.MM.YYYY
date = utils.normalize_date("2026-02-16")
# Returns: "16.02.2026"

# Normalize time to HH:MM
time = utils.normalize_time("14:30 Uhr")
# Returns: "14:30"
```

### Example 3: Date Filtering

```python
from rules import utils

# Check if event is within 14 days
is_valid = utils.is_within_14_days("16.02.2026")
# Returns: True
```

---

## Category Keywords

### Family (Familie)

**German:** familie, kinder, jugend, kind, baby, schule, eltern, familien, schulkinder, schüler, familientag, kindertag, familienfest
**English:** family, children, kids, teens, school, parents

### Education (Bildung)

**German:** kurs, workshop, vhs, volkshochschule, bildung, schule, bibliothek, weiterbildung, unterricht, vortrag, seminar, schulung, ausbildung
**English:** course, workshop, school, library, education, training, lecture, seminar

### Sport (Sport)

**German:** sport, fitness, laufen, schwimmen, rad, fußball, tennis, yoga, wandern, turnier, sportveranstaltung, sportart, sportstätte, turnhalle, schwimmbad, jogging, radfahren, fahrrad
**English:** sport, sports, fitness, running, swimming, cycling, football, tennis, yoga, hiking, tournament

### Culture (Kultur)

**German:** ausstellung, konzert, theater, film, kino, lesung, buch, vortrag, führung, tour, kunst, museum, kultur, opera, orchester, chor, jazz, musik, galerie, vernissage, kulturveranstaltung, kunstausstellung
**English:** exhibition, concert, theater, film, cinema, reading, book, lecture, tour, art, museum, culture, opera, orchestra, choir, jazz, music, gallery

### Market (Markt)

**German:** markt, markttag, messe, flohmarkt, verkauf, verkaufsmarkt, weihnachtsmarkt, frühlingsmarkt, floßmarkt, bauernmarkt, handwerkermarkt
**English:** market, fair, sale, flea market

### Festival (Fest)

**German:** fest, festival, karneval, fastnacht, kirmes, volksfest, weihnachtsmarkt, stadtfest, dorfest, sommerfest, kirmes, schützenfest
**English:** festival, carnival, fair, christmas market, street festival

### Adult (Erwachsene)

**German:** erwachsen, adult, senior, senioren, abend, nacht, bar, club, party, frauen, damen, damenabend, herren, nachtleben, diskothek, tanzabend
**English:** adult, seniors, women, ladies, night, party, club, bar

### Community (Gemeinschaft)

**German:** treffen, verein, club, gruppe, nachbarschaft, soziales, gemeinschaft, bürgerverein, sportverein, musikverein, gesangsverein, chorverein
**English:** meeting, club, group, neighborhood, social, community, association

### Nature (Natur)

**German:** natur, wanderung, spaziergang, umwelt, garten, park, wald, see, landschaft, naturschutz, grünanlagen, stadtpark
**English:** nature, hike, walk, environment, garden, park, forest, lake, landscape

---

## Migration Guide

### Updating Scrapers

To update an existing scraper to use the centralized category system:

**Before (custom category inference):**
```python
category = self._infer_category(description, name)
```

**After (centralized system):**
```python
from rules import categories, utils

# Infer and normalize category
category = categories.infer_category(description, name)
category = categories.normalize_category(category)

# Also normalize dates and times
date = utils.normalize_date(date_str)
time = utils.normalize_time(time_str)
```

### Removing Custom Methods

Remove these custom methods from scrapers:
- `_infer_category()` - Use `categories.infer_category()` instead
- `_infer_category_from_card()` - Use centralized inference instead
- Custom category keyword dictionaries - Use system keywords instead

---

## Design Decisions

### Why 10 Categories?

- **Flexible**: Covers all use cases from current scrapers
- **Not Overwhelming**: Easy to understand and maintain
- **Extensible**: Easy to add new categories if needed

### Why First-Match Priority?

- **Fast**: Returns immediately on first match
- **Predictable**: Always checks family first, then education, etc.
- **Sufficient**: High-priority categories (family, education) checked first

### Why German Display Names?

- **Primary Audience**: German cities → German events
- **User Interface**: All displays in German
- **Database**: Category IDs (EN) for storage, display names (DE) for UI

### No Database Migration?

- **Reason**: Existing categories preserved, only normalized going forward
- **Approach**: Gradual migration as scrapers are updated
- **Benefits**: No breaking changes, smooth transition

---

## Testing

### Test Inference

```python
# Test category inference
from rules import categories

test_cases = [
    ("Konzert für Kinder", "family"),
    ("Fußballturnier", "sport"),
    ("Bücherlesung", "culture"),
    ("Weihnachtsmarkt", "festival"),
]

for text, expected in test_cases:
    result = categories.infer_category(text)
    assert result == expected, f"Expected {expected}, got {result}"
```

### Test Normalization

```python
# Test category normalization
from rules import categories

test_cases = [
    ("sports", "sport"),
    ("kultur", "culture"),
    ("familie", "family"),
]

for raw, expected in test_cases:
    result = categories.normalize_category(raw)
    assert result == expected, f"Expected {expected}, got {result}"
```

### Test Date/Time Utils

```python
# Test date normalization
from rules import utils

test_dates = [
    ("2026-02-16", "16.02.2026"),
    ("16.02.2026", "16.02.2026"),
    ("5.3.2026", "05.03.2026"),
    ("16. Februar 2026", "16.02.2026"),
]

for input_date, expected in test_dates:
    result = utils.normalize_date(input_date)
    assert result == expected, f"Expected {expected}, got {result}"
```

---

## Reference

- **Category Module**: `rules/categories.py`
- **Utils Module**: `rules/utils.py`
- **Base Class**: `rules/base.py` (uses category inference)
- **Related Docs**: `11_architecture.md`, `01_setup_guide.md`
