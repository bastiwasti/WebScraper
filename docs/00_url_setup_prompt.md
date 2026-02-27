# URL Scraper Implementation Prompt

Implement a new event scraper for the WebScraper codebase.

## Input

User provides:
- Full URL (e.g., `https://www.duesseldorf.de/veranstaltungen`)
- City name (lowercase, no spaces, e.g., `duesseldorf`)

## Workflow

1. Read `docs/00_url_setup_prompt.md` for complete setup guide
2. Read `docs/14_categories.md` for category system reference
3. **Analyze URL to detect which of 7 proven patterns to use**
4. **Investigate HTML/API structure** (see Phase 2 below - MANDATORY)
5. Implement scraper using matching template from `rules/cities/` directory
6. Register URL in `rules/urls.py`
7. Test with `python3 main.py --url {url} --no-db --verbose`
8. Fix issues with up to 3 self-correction attempts
9. Create summary file: `docs/autonomous/2x_{city}_autonomous_{timestamp}.md` (ISO 8601 format)

## 7 Proven Patterns

| # | Pattern | Reference | When to Use | Critical Verification |
|---|---------|-----------|--------------|----------------------|
| 1 | REST API (JSON) | `rules/cities/leverkusen/lust_auf/` | URL has `/api/`, `/wp-json/`, `tribe/events` | Verify API returns event data |
| 2 | Static HTML | `rules/cities/langenfeld/city_events/` | Plain HTML, no JS | Verify event elements exist |
| 3 | Static + 2-Level | `rules/cities/langenfeld/schauplatz/` | Detail page links available | Verify detail pages load |
| 4 | Dynamic + Load More | `rules/cities/monheim/terminkalender/` | JavaScript + "Load More" button | **Verify new events load after clicking** |
| 5 | Static + Pagination | `rules/cities/dormagen/feste_veranstaltungen/` | URL parameters `?page=` in pagination | **CRITICAL: Verify page 1 ≠ page 2** |
| 6 | 2-Level Extraction | All Level 2 scrapers | Detail pages with richer data | Verify raw_data populates |
| 7 | Custom HTML Parsing | `rules/cities/monheim/terminkalender/regex.py` | Non-standard structures | Verify regex patterns match |

## Pagination Verification (CRITICAL)

Before implementing pagination (Patterns 4 or 5), you MUST verify it actually works:

### Why This Matters

Many sites have pagination URLs (`/page/2/`, `?page=2`) that return identical content to page 1. This causes:
- Duplicate events (770 "events" from 10 pages when there are only 77 unique events)
- Wasted scraping time
- Incorrect event counts in summaries

### Verification Steps

1. Fetch page 1 and page 2 content
2. Compare event count or titles:
   ```python
   # Simple check: count event elements
   page1_count = page1_html.count('<article')
   page2_count = page2_html.count('<article')

   if page1_count == page2_count:
       print("WARNING: Pagination returns identical content - set MAX_PAGES=1")
       print("All events are on page 1")
   ```

3. If content is identical → Use `MAX_PAGES = 1` (all events on first page)
4. If content differs → Implement pagination with appropriate `MAX_PAGES` setting

### Common False Positives

- WordPress sites with `/page/2/` URLs that return all events on every page
- Sites with "next" links in HTML but no actual page content changes
- Calendar themes that load all events on first page, pagination is for navigation only

### Example: Hitdorf Mistake

The Hitdorf kalender site appeared to have pagination:
- `<link rel="next" href="https://leben-in-hitdorf.de/kalender/page/2/" />` in HTML
- `/kalender/page/2/` returns HTTP 200
- But both pages contain identical 77 events

**Result**: Agent incorrectly set `MAX_PAGES = 10` and reported 770 events (77 × 10 duplicate pages).

**Fix**: Verification revealed identical content → Set `MAX_PAGES = 1` → Correct: 77 events.

## Phase 2: Investigation (MANDATORY)

**Before implementing ANY scraper code, you MUST thoroughly investigate the HTML/API structure.**

### Why Investigation is Mandatory

Many websites have hidden data sources that are not immediately visible:
- "Mehr Infos" / "Show More" buttons that expand content
- Hidden divs with `display:none` containing full descriptions
- JavaScript expansion mechanisms not visible in initial HTML
- API parameters that load additional data

Skipping investigation leads to:
- Incomplete event data (missing descriptions, locations, etc.)
- Multiple re-implementation cycles
- Wasted time debugging avoidable issues

### Investigation Steps

#### Step 1: Fetch and Save Raw Content

```bash
# Fetch the URL and save to file for analysis
curl -o /tmp/{city}_raw.html "{target_url}"

# Or use Python to fetch
python3 -c "import requests; r = requests.get('{target_url}'); open('/tmp/{city}_raw.html', 'w').write(r.text)"
```

#### Step 2: Identify ALL Data Sources

Search the saved HTML for:

**a) Event Card Structure:**
```bash
grep -A 20 "event\|termin\|karte" /tmp/{city}_raw.html | head -50
```
- What HTML elements contain event data?
- Are there nested structures (cards within containers)?

**b) Hidden/Expansion Sections:**
```bash
grep -iE "mehr.*info|show.*more|expand|aufklapp" /tmp/{city}_raw.html | head -20
```
- Look for: "mehr Infos", "Show More", "Load More", "aufklappen"
- Are there hidden divs (`display:none`, `hidden`)?

**c) API Parameters:**
```bash
grep -oE 'what=|page=|limit=|count=' /tmp/{city}_raw.html | sort -u
```
- What parameters control data loading?
- Are there pagination parameters?

**d) JavaScript Loading:**
```bash
grep -iE "javascript|ajax|fetch|load" /tmp/{city}_raw.html | head -20
```
- Does the page load data via JavaScript?
- Are there API endpoints in the JavaScript?

#### Step 3: Document Data Relationships

Find how to map event cards to additional data:

**Common Mapping Patterns:**

1. **ID-Based Mapping** (e.g., Leichlingen):
   ```html
   <!-- In event card -->
   <a id="a411487" class="mehr-infos">+ mehr Infos</a>
   
   <!-- Hidden description -->
   <div id="termin411487" style="display:none">
       <div class="description">Full description here</div>
   </div>
   ```
   Pattern: Remove prefix from ID → Match to hidden div
   Example: `a411487` → `termin411487` (remove 'a', match event ID)

2. **Link-Based Mapping**:
   ```html
   <a href="event-detail-123.html">Event Title</a>
   <!-- Detail page at: https://site.com/event-detail-123.html -->
   ```
   Pattern: Extract URL from card → Fetch detail page

3. **Data Attributes**:
   ```html
   <div data-event-id="123" data-description="...">
       <!-- Description stored in data attribute -->
   </div>
   ```
   Pattern: Read data attributes directly

4. **Inline Expansion** (No hidden sections):
   ```html
   <div class="event-card">
       <p class="short-desc">Brief description</p>
       <p class="full-desc" style="display:none">Full description</p>
   </div>
   ```
   Pattern: Toggle display or read hidden content

#### Step 4: Test Extraction on Sample Data

Extract first 3 events and verify you can parse:
- Name
- Date
- Time
- Location
- Description (from all identified sources)
- Category

### Investigation Deliverable

Create analysis file: `investigation_{city}.md` containing:

```markdown
# {City Name} - Investigation Report

## HTML Structure
- [ ] Main event card structure documented
- [ ] All data sources identified

## Hidden Data Sources
- [ ] "Mehr Infos" / "Show More" buttons found: YES/NO
- [ ] Hidden divs with display:none: YES/NO
- [ ] ID mapping patterns identified: Describe pattern

## Mapping Pattern
- [ ] Mapping type: [ID-based / Link-based / Data attributes / Inline]
- [ ] Pattern documented: [Explain the pattern]

## API Parameters
- [ ] API endpoint identified: [URL]
- [ ] Parameters tested: [List tested parameters]
- [ ] Results: [What each parameter returns]

## Pagination
- [ ] Page 1 event count: [Number]
- [ ] Page 2 event count: [Number]
- [ ] Is pagination real: YES/NO

## Sample Events
### Event 1
- Name: [Event name]
- Date: [Date]
- Time: [Time]
- Location: [Location]
- Description source: [Card / Hidden section / Detail page]

### Event 2
- Name: [Event name]
- Date: [Date]
- Time: [Time]
- Location: [Location]
- Description source: [Card / Hidden section / Detail page]

### Event 3
- Name: [Event name]
- Date: [Date]
- Time: [Time]
- Location: [Location]
- Description source: [Card / Hidden section / Detail page]
```

**This analysis file MUST be completed BEFORE writing any scraper code.**

### Common Mistakes to Avoid

❌ **Not searching for hidden content**: Assuming all data is visible in event cards
- **Fix**: Always search for "mehr Infos", "Show More", `display:none` elements

❌ **Not verifying pagination**: Assuming `/page/2/` works without checking
- **Fix**: Always fetch page 1 and page 2, compare content

❌ **Not checking ID patterns**: Trying to implement without understanding mapping
- **Fix**: Document how card IDs map to descriptions before coding

❌ **Skipping API parameters**: Not testing available parameters
- **Fix**: Test `what=All`, `limit=100`, etc. to understand behavior

## Investigation Checklist (Complete BEFORE Implementation)

- [ ] Main event card structure documented
- [ ] All data sources identified (cards + hidden sections + API parameters)
- [ ] Hidden/expansion sections found ("mehr Infos", "Show More", etc.)
- [ ] ID mapping patterns identified (how to link card → description)
- [ ] API parameters tested (what=, page=, limit=, etc.)
- [ ] Pagination verified (page 1 ≠ page 2)
- [ ] Sample extraction tested on 3+ events
- [ ] Investigation file created with findings (`investigation_{city}.md`)

**Only proceed to implementation after all items are checked.**

## Implementation Rules

- Each URL gets own subfolder: `rules/cities/{city}/{subfolder}/`
- Class names: `{SubfolderNameCamelCase}Scraper` and `{SubfolderNameCamelCase}Regex`
- Import `from rules import categories, utils`
- Use `categories.infer_category()` and `categories.normalize_category()`
- Use `utils.normalize_date()` and `utils.normalize_time()`
- Set `needs_browser` property correctly
- Register URL in `CITY_URLS` dictionary
- **Pagination Verification**: If using Pattern 4 or 5, verify pages contain different content before implementing
- **Set `MAX_PAGES = 1`** if all events appear on first page (same content on `/page/2/`)

## Required Event Fields

- name (required): Event title
- description (required): Event description
- location (required): Venue/address
- date (required): DD.MM.YYYY format
- time (required): HH:MM format
- source (required): Source URL
- category (inferred): Use category system
- event_url (optional): Detail page URL
- end_time (optional): End time if available
- raw_data (optional): Level 2 data

## Testing

Test 1: Module imports
```bash
python3 -c "from rules import categories, utils; print('✓ Imported')"
```
✓ Imported

Test 2: Single URL
```bash
python3 main.py --url {target_url} --no-db --verbose
```

**IMPORTANT: Check log files for actual progress**
The scraper redirects all output to log files after the initial "Logging to:" message:
```bash
# View log file while script is running
tail -f logs/scrape_*.log

# After completion, view full log
cat logs/scrape_2026-02-16_*.log

# Find the most recent log file
ls -lt logs/ | head -2
```

**Why check logs instead of bash output?**
- Bash stdout only shows: `Logging to: logs/scrape_2026-02-16_XX-XX-XX.log`
- All progress, errors, and results are written to the log file
- Scripts often continue running after bash timeouts
- Log files contain the true status (success/failure, event counts, errors)
- Example log output shows: `✓ https://example.com - 77 events (167.24s)`

**Common pitfall**: Seeing only "Logging to: ..." message and assuming script timed out
- Script is likely still running in background
- All progress is being written to the log file
- Check the log file to see actual status and progress

Verify: events extracted count > 0, all required fields present

## Final Verification Workflow

After implementing and testing the scraper, follow this final verification process:

### Step 1: Run with Database Write

Test the scraper with database writing enabled:
```bash
python3 main.py --url {target_url} --verbose
```

**What this does:**
- Fetches events from URL using your scraper
- Writes events to database (events table)
- Creates a run record in the database

**Verify:**
- Check log file for success: `✓ https://example.com - X events (Y.YYs)`
- Confirm events were written to database
- No critical errors in log file

### Step 2: Verify Database Records

Query the database to verify events were saved correctly:
```bash
# Check most recent runs
python3 main.py --list-runs

# Or query database directly (if you have access)
# SELECT * FROM events WHERE source LIKE '%{target_url}%';
```

**Verify:**
- Event count matches scraper output
- Required fields are populated (name, date, location, description, time)
- Categories are inferred correctly
- No duplicate events

### Step 3: Final Verification Test

Run the scraper again to verify consistency:
```bash
python3 main.py --url {target_url} --verbose
```

**Verify:**
- Event count remains consistent
- No new errors appear
- Same events retrieved (no drift in website structure)

### Step 4: Debug if Unsuccessful

If any step fails:

1. **Check log file** for specific errors:
   ```bash
   cat logs/scrape_2026-02-16_*.log | grep -i error
   ```

2. **Common issues and fixes:**
   - Database connection errors: Check config.py database settings
   - No events extracted: Check regex patterns in regex.py
   - Duplicate events: Verify pagination (page 1 ≠ page 2)
   - **Missing descriptions / incomplete data:**
     **Symptoms**: Events only have titles, no descriptions or locations
     **Cause**: Did not investigate HTML structure for hidden data sources ("mehr Infos", "Show More", hidden divs)
     **Fix**: 
       1. Return to Phase 2: Investigation
       2. Search for hidden data sources: `grep -iE "mehr.*info|show.*more|expand" /tmp/{city}_raw.html`
       3. Find ID mapping patterns: Look for button IDs matching hidden div IDs (e.g., `a{event_id}` → `termin{event_id}`)
       4. Re-extract with updated logic to capture hidden descriptions
   - Timeout errors: Increase timeout in detail page requests

3. **Debug steps:**
   - Print fetched content: Add `print(content[:5000])` after fetch
   - Test regex patterns manually: Copy HTML to regex tester
   - Verify selectors: Check if HTML structure changed
   - Check event URLs: Ensure detail pages exist

4. **Retest after fixes:**
   ```bash
   python3 main.py --url {target_url} --verbose
   ```

**Success criteria for final verification:**
- ✅ Events saved to database
- ✅ All required fields populated
- ✅ No duplicate events
- ✅ Consistent results on re-run
- ✅ No critical errors in logs

## Self-Correction

Maximum 3 attempts. For each:
1. Diagnose issue from error output
2. **CHECK LOG FILE** - all progress and errors are logged to `logs/scrape_*.log`
3. Apply appropriate fix from common issues
4. Retest
5. Document attempt (issue, fix, result)

**Critical: Always check log files during troubleshooting**
```bash
# View the log file from your test run
cat logs/scrape_2026-02-16_XX-XX-XX.log

# Monitor logs in real-time while testing
tail -f logs/scrape_*.log
```

Common fixes: selector issues, date parsing, pagination (verify page 1 ≠ page 2), timeout, anti-bot

## Summary File

After completion, create: `2x_{city}_autonomous_{timestamp}.md`

Content includes:
- Task info (user input, pattern detected)
- Implementation details (files created, URL registered)
- Test results (all validations)
- Self-correction attempts (up to 3)
- Issues encountered (table format)
- Final status (✅ SUCCESS or ❌ FAILED)
- Recommendations (2-3 items)
- Next steps (if any)

Timestamp format: `YYYY-MM-DDTHH:MM:SS`

## Success Criteria

- URL registered in `rules/urls.py`
- Both `scraper.py` and `regex.py` created
- Class names match subfolder format
- `can_handle()` returns True for target URL
- Events extracted (count > 0)
- All required fields populated
- Category inferred correctly
- Test run successful
- Registry auto-discovers new scraper
- Summary file created with correct naming

## Resources

- `docs/00_url_setup_prompt.md` - Complete setup guide (380 lines)
- `14_categories.md` - Category system (480 lines)
- `01_setup_guide.md` - Detailed setup guide (1,800 lines)
- `rules/categories.py` - 10 categories, keywords
- `rules/utils.py` - Date/time normalization
- `rules/cities/*/` - All working implementations (7 patterns)

## Final Output

After task completion, provide:
1. Summary file path
2. Events extracted count
3. Pattern used
4. Files created
5. Issues encountered (if any)
6. Final status

Time estimate: 30-60 minutes per URL.
