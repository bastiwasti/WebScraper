# Graph Report - WebScraper  (2026-05-04)

## Corpus Check
- Corpus is ~47,216 words - fits in a single context window. You may not need a graph.

## Summary
- 889 nodes · 1182 edges · 103 communities (61 shown, 42 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 155 edges (avg confidence: 0.7)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8539976`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Location Storage Layer|Location Storage Layer]]
- [[_COMMUNITY_Monheim Terminkalender Scraper|Monheim Terminkalender Scraper]]
- [[_COMMUNITY_Langenfeld Schauplatz Scraper|Langenfeld Schauplatz Scraper]]
- [[_COMMUNITY_Scraper Agent|Scraper Agent]]
- [[_COMMUNITY_Leverkusen Stadt-Erleben Scraper|Leverkusen Stadt-Erleben Scraper]]
- [[_COMMUNITY_Rausgegangen Aggregator Scraper|Rausgegangen Aggregator Scraper]]
- [[_COMMUNITY_Rules Framework Core|Rules Framework Core]]
- [[_COMMUNITY_Event Rating System|Event Rating System]]
- [[_COMMUNITY_Location Data Sources|Location Data Sources]]
- [[_COMMUNITY_Event Analysis Agent|Event Analysis Agent]]
- [[_COMMUNITY_Rules Utilities|Rules Utilities]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Leverkusen Lust-auf Scraper|Leverkusen Lust-auf Scraper]]
- [[_COMMUNITY_Location Management CLI|Location Management CLI]]
- [[_COMMUNITY_Rules Framework Core|Rules Framework Core]]
- [[_COMMUNITY_Dormagen Feste Scraper|Dormagen Feste Scraper]]
- [[_COMMUNITY_Hilden Veranstaltungen Scraper|Hilden Veranstaltungen Scraper]]
- [[_COMMUNITY_Hitdorf Kalender Scraper|Hitdorf Kalender Scraper]]
- [[_COMMUNITY_Burscheid Veranstaltungskalender Scraper|Burscheid Veranstaltungskalender Scraper]]
- [[_COMMUNITY_Duesseldorf Schloss-Benrath Scraper|Duesseldorf Schloss-Benrath Scraper]]
- [[_COMMUNITY_Langenfeld Schauplatz Scraper|Langenfeld Schauplatz Scraper]]
- [[_COMMUNITY_Monheim Kulturwerke Scraper|Monheim Kulturwerke Scraper]]
- [[_COMMUNITY_Location Data Sources|Location Data Sources]]
- [[_COMMUNITY_Eventim Aggregator Scraper|Eventim Aggregator Scraper]]
- [[_COMMUNITY_Langenfeld City Events Scraper|Langenfeld City Events Scraper]]
- [[_COMMUNITY_Monheim Terminkalender Scraper|Monheim Terminkalender Scraper]]
- [[_COMMUNITY_Leichlingen Freizeit Scraper|Leichlingen Freizeit Scraper]]
- [[_COMMUNITY_Monheim Marienburg Scraper|Monheim Marienburg Scraper]]
- [[_COMMUNITY_Monheim Kulturwerke Scraper|Monheim Kulturwerke Scraper]]
- [[_COMMUNITY_Hitdorf Kalender Scraper|Hitdorf Kalender Scraper]]
- [[_COMMUNITY_Langenfeld City Events Scraper|Langenfeld City Events Scraper]]
- [[_COMMUNITY_Leichlingen Freizeit Scraper|Leichlingen Freizeit Scraper]]
- [[_COMMUNITY_Monheim Marienburg Scraper|Monheim Marienburg Scraper]]
- [[_COMMUNITY_Rules Framework Core|Rules Framework Core]]
- [[_COMMUNITY_Agent Tools|Agent Tools]]
- [[_COMMUNITY_Rausgegangen Aggregator Scraper|Rausgegangen Aggregator Scraper]]
- [[_COMMUNITY_Eventim Aggregator Scraper|Eventim Aggregator Scraper]]
- [[_COMMUNITY_Test Suite|Test Suite]]
- [[_COMMUNITY_Test Suite|Test Suite]]
- [[_COMMUNITY_Configuration|Configuration]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Event Rating System|Event Rating System]]
- [[_COMMUNITY_Event Rating System|Event Rating System]]
- [[_COMMUNITY_Rausgegangen Aggregator Scraper|Rausgegangen Aggregator Scraper]]
- [[_COMMUNITY_Rausgegangen Aggregator Scraper|Rausgegangen Aggregator Scraper]]
- [[_COMMUNITY_Rausgegangen Aggregator Scraper|Rausgegangen Aggregator Scraper]]
- [[_COMMUNITY_Rules Framework Core|Rules Framework Core]]
- [[_COMMUNITY_Rules Framework Core|Rules Framework Core]]
- [[_COMMUNITY_Rules Framework Core|Rules Framework Core]]
- [[_COMMUNITY_Rules Framework Core|Rules Framework Core]]
- [[_COMMUNITY_Rules Framework Core|Rules Framework Core]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Duesseldorf Schloss-Benrath Scraper|Duesseldorf Schloss-Benrath Scraper]]
- [[_COMMUNITY_Duesseldorf Schloss-Benrath Scraper|Duesseldorf Schloss-Benrath Scraper]]
- [[_COMMUNITY_Community 68|Community 68]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 72|Community 72]]
- [[_COMMUNITY_Community 73|Community 73]]
- [[_COMMUNITY_Community 76|Community 76]]
- [[_COMMUNITY_Community 77|Community 77]]
- [[_COMMUNITY_Community 79|Community 79]]
- [[_COMMUNITY_Community 80|Community 80]]
- [[_COMMUNITY_Community 83|Community 83]]
- [[_COMMUNITY_Community 84|Community 84]]
- [[_COMMUNITY_Community 86|Community 86]]
- [[_COMMUNITY_Community 87|Community 87]]
- [[_COMMUNITY_Community 88|Community 88]]
- [[_COMMUNITY_Community 89|Community 89]]
- [[_COMMUNITY_Community 90|Community 90]]
- [[_COMMUNITY_Community 93|Community 93]]
- [[_COMMUNITY_Community 94|Community 94]]
- [[_COMMUNITY_Community 95|Community 95]]
- [[_COMMUNITY_Community 97|Community 97]]
- [[_COMMUNITY_Community 98|Community 98]]
- [[_COMMUNITY_Community 100|Community 100]]
- [[_COMMUNITY_Community 101|Community 101]]
- [[_COMMUNITY_Community 102|Community 102]]

## God Nodes (most connected - your core abstractions)
1. `Event` - 38 edges
2. `_execute()` - 37 edges
3. `get_connection()` - 33 edges
4. `BaseRule` - 28 edges
5. `BaseScraper` - 23 edges
6. `init_db()` - 23 edges
7. `RausgegangenScraper` - 17 edges
8. `main()` - 16 edges
9. `AnalyzerAgent` - 15 edges
10. `LustAufRegex` - 15 edges

## Surprising Connections (you probably didn't know these)
- `main()` --calls--> `AnalyzerAgent`  [INFERRED]
  main.py → agents/analyzer_agent.py
- `run_pipeline()` --calls--> `AnalyzerAgent`  [INFERRED]
  pipeline.py → agents/analyzer_agent.py
- `main()` --calls--> `RatingAgent`  [INFERRED]
  main.py → agents/rating_agent.py
- `main()` --calls--> `ScraperAgent`  [INFERRED]
  main.py → agents/scraper_agent.py
- `run_pipeline()` --calls--> `ScraperAgent`  [INFERRED]
  pipeline.py → agents/scraper_agent.py

## Communities (103 total, 42 thin omitted)

### Community 0 - "Location Storage Layer"
Cohesion: 0.05
Nodes (89): enrich_locations(), Enrich existing locations with Google Places data (ratings).      Searches Googl, get_location_stats(), get_location_summary(), get_locations(), get_locations_with_urls(), init_locations_db(), PostgreSQL storage for the locations/Ausflüge feature.  Uses the same webscraper (+81 more)

### Community 1 - "Monheim Terminkalender Scraper"
Cohesion: 0.05
Nodes (27): ABC, BaseRule, BaseScraper, _clean_text(), get_regex_patterns(), Unified base classes for URL rules - handles fetching and parsing.  Each rule co, Fetch content using Playwright for dynamic pages., Abstract base class for URL-specific regex parsers (parsing only).      Each par (+19 more)

### Community 2 - "Langenfeld Schauplatz Scraper"
Cohesion: 0.05
Nodes (28): BaseScraper, FesteVeranstaltungenScraper, Scraper for Dormagen feste-veranstaltungen website., Fetch events from datefix.de calendar system.                  The Dormagen webs, Fetch raw HTML content from datefix.de calendar system for Level 2 scraping., Fetch raw HTML content from datefix.de calendar system.                  The Dor, Scraper for Dormagen feste-veranstaltungen page.          Uses requests to fetch, Scraper for Schauplatz Langenfeld URL. (+20 more)

### Community 3 - "Scraper Agent"
Cohesion: 0.07
Nodes (28): Agent 1: Scrapes the internet for local events using search and fetch tools.  In, Print live table of URL status (updates as they complete)., Print Rich table with event counts by city and per-URL breakdown., Run multiple searches and scrape fixed URLs for events with Rich progress tracki, Search for events, fetch pages from fixed URLs, and return a summarized event te, Configure logging to timestamped file in logs/ directory., Scrape URLs one at a time and yield events for each URL.                  This i, Finds local events via web search and page fetch, then summarizes with LLM. (+20 more)

### Community 4 - "Leverkusen Stadt-Erleben Scraper"
Cohesion: 0.07
Nodes (18): Stadt-Erleben-Leverkusen calendar scraper., HTML-based parser for Leverkusen Stadt_Erleben events., HTML parser for Leverkusen Stadt_Erleben events.          Extracts these fields:, Parse ISO 8601 datetime to DD.MM.YYYY., Extract event detail URLs from calendar page raw HTML.                  Returns:, Parse internal leverkusen.de detail page.                  Args:             det, Parse detail page (handles both internal and external pages)., Fetch Level 2 detail data for events.                  For each event, fetches d (+10 more)

### Community 5 - "Rausgegangen Aggregator Scraper"
Cohesion: 0.08
Nodes (16): Rausgegangen aggregator rule package., Minimal regex parser for rausgegangen.de aggregator.  Since rausgegangen uses a, Hybrid scraper for rausgegangen.de aggregator.  Uses Level 1 + Level 2 approach:, Fetch events using hybrid approach.                  This method is overridden t, Extract event detail page URLs from city page (Level 1).                  Uses P, Fetch single event detail page with timeout handling.                  Args:, Fetch event detail pages concurrently and extract structured data (Level 2)., Hybrid scraper for rausgegangen.de aggregator.          Focuses on Monheim with (+8 more)

### Community 6 - "Rules Framework Core"
Cohesion: 0.09
Nodes (27): create_regex(), create_scraper(), _discover_rules(), _ensure_initialized(), get_regex_for_url(), get_rule(), get_rule_or_raise(), get_scraper_for_url() (+19 more)

### Community 7 - "Event Rating System"
Cohesion: 0.11
Nodes (18): _parse_json_array(), RatingAgent, Agent 3: Rates events based on family-friendliness for a family with 2 kids unde, Rates events based on family-friendliness for a family with 2 kids under 6., Extract and accumulate token usage from a LangChain response., Execute the get_unrated_events tool call., Execute the submit_ratings tool call., Route a tool call to the appropriate handler. (+10 more)

### Community 8 - "Location Data Sources"
Cohesion: 0.09
Nodes (24): Location, Data models for the locations/Ausflüge feature., A family-friendly location/Ausflugsziel., Calculate haversine distance in km from a reference point., _check_api_key(), discover_all_categories(), _parse_place(), Google Places API (New) source for location discovery and enrichment.  Uses the (+16 more)

### Community 9 - "Event Analysis Agent"
Cohesion: 0.1
Nodes (14): AnalyzerAgent, Agent 2: Analyzes raw event text and structures it (name, description, location,, Try to extract a JSON array from the model output., Split raw event text into chunks with event and character limits., Infer category from event description and name., Normalize German field names to English database schema.                  Maps:, Infer city from event source URL., Validate city format and warn if not standard.                  Args: (+6 more)

### Community 10 - "Rules Utilities"
Cohesion: 0.09
Nodes (23): extract_city_from_address(), extract_end_time(), extract_start_time(), is_within_14_days(), is_within_date_range(), map_aggregator_city(), normalize_city(), normalize_city_name() (+15 more)

### Community 11 - "Community 11"
Cohesion: 0.12
Nodes (11): LustAufRegex, Parse ISO datetime to DD.MM.YYYY., Parse ISO datetime to HH:MM format., Check if event date is within 30 days from today., Fallback HTML parser (not used with API)., Extract event detail URLs from HTML (not used with API)., Parse event detail page for Level 2 data.                  Extracts full descrip, JSON parser for Leverkusen Lust-Auf events.          Extracts events from REST A (+3 more)

### Community 12 - "Leverkusen Lust-auf Scraper"
Cohesion: 0.11
Nodes (10): Lust-Auf-Leverkusen events scraper., JSON parser for Leverkusen Lust-Auf website.  Extracts ALL events from REST API, LustAufScraper, Scraper for Leverkusen Lust-Auf website.  Uses REST API to fetch all events with, Convert API response dictionary to Event object.                  Args:, Scraper for Leverkusen Lust-Auf website.          Uses REST API to fetch all eve, Fetch content from Lust-Auf URL.                  Uses standard requests for sta, Fetch using requests. (+2 more)

### Community 13 - "Location Management CLI"
Cohesion: 0.13
Nodes (18): _cmd_check_urls(), _cmd_discover(), _cmd_enrich(), _cmd_list(), _cmd_stats(), handle_command(), CLI command handling for the locations feature., Run location discovery. (+10 more)

### Community 14 - "Rules Framework Core"
Cohesion: 0.11
Nodes (18): Infer category from event description and name.          Uses centralized catego, Category, get_all_categories(), get_category_by_id(), get_category_name(), get_default_category(), infer_category(), is_valid_category() (+10 more)

### Community 15 - "Dormagen Feste Scraper"
Cohesion: 0.12
Nodes (10): FesteVeranstaltungenRegex, Regex parser for Dormagen feste-veranstaltungen website.  Event structure: - Pag, Clean and normalize time string., Parse detail page HTML to extract enhanced data.                  Args:, HTML parser for Dormagen feste-veranstaltungen events.          Uses BeautifulSo, Fetch Level 2 detail data for Dormagen events.                  For each event,, Extract events with method tracking., Return regex patterns (fallback only). (+2 more)

### Community 16 - "Hilden Veranstaltungen Scraper"
Cohesion: 0.13
Nodes (9): HildenRegex, JSON parser for Hilden veranstaltungen website.  Extracts events from JSON API e, Fetch Level 2 detail data from Hilden detail pages.                  For each ev, JSON parser for Hilden veranstaltungen events.          Hilden uses a JSON API t, Parse Hilden detail page for event information.                  Args:, Extract events using regex (JSON parsing).                  Args:             ra, Extract events with method tracking.                  Args:             raw_cont, Return empty list - JSON parsing is used instead. (+1 more)

### Community 17 - "Hitdorf Kalender Scraper"
Cohesion: 0.13
Nodes (9): KalenderRegex, Regex parser for Hitdorf kalender website.  Event structure: - Pagination-based, Parse detail page HTML to extract enhanced data.                  Args:, Fetch Level 2 detail data for Hitdorf events.                  For each event, f, HTML parser for Hitdorf kalender events.          Uses BeautifulSoup to parse Wo, Extract events with method tracking., Return regex patterns (fallback only)., Parse content using BeautifulSoup (primary method). (+1 more)

### Community 18 - "Burscheid Veranstaltungskalender Scraper"
Cohesion: 0.13
Nodes (9): HTML-based parser for Burscheid Veranstaltungskalender API., HTML parser for Burscheid event calendar via bergisch-live.de API.      IMPORTAN, Map rubrik text to standard category.          Args:             rubrik: Rubrik, Extract event IDs from calendar HTML.          Args:             raw_html: Raw H, Fetch Level 2 detail data for Burscheid events.          For each event, fetches, Parse event detail HTML to extract enhanced information.          Args:, Return regex patterns for Burscheid events.          These patterns are fallback, Parse content using HTML parsing (primary method).          Override BaseRule me (+1 more)

### Community 19 - "Duesseldorf Schloss-Benrath Scraper"
Cohesion: 0.14
Nodes (9): HTML-based parser for Schloss Benrath event pages., Parse date and time from German format.          Args:             date_time_str, Extract event detail URLs from calendar page raw HTML.          Args:, Parse event detail page to extract enhanced information.          Args:, Fetch Level 2 detail data for Schloss Benrath events.          For each event, f, Return regex patterns for Schloss Benrath events.          These patterns are fa, Parse content using HTML parsing (primary method).          Override BaseRule me, HTML parser for Schloss Benrath events.      IMPORTANT: HTML parsing is PRIMARY (+1 more)

### Community 20 - "Langenfeld Schauplatz Scraper"
Cohesion: 0.13
Nodes (9): HTML-based parser for Schauplatz event pages., Normalize date format from DD.MM.YYYY to DD.MM.YYYY., Extract event detail URLs from calendar page raw HTML.                  Args:, Parse event detail page to extract enhanced information.                  Args:, Fetch Level 2 detail data for Schauplatz events.                  For each event, Return regex patterns for Schauplatz events.                  These patterns are, Parse content using HTML parsing (primary method).                  Override Bas, HTML parser for Schauplatz events.          IMPORTANT: HTML parsing is PRIMARY e (+1 more)

### Community 21 - "Monheim Kulturwerke Scraper"
Cohesion: 0.12
Nodes (9): KulturwerkeRegex, Regex parser for Monheimer Kulturwerke event pages., Regex parser for Monheimer Kulturwerke events.          IMPORTANT: HTML parsing, Extract event detail URLs from calendar page raw HTML.                  Args:, Parse event detail page to extract enhanced information.                  Args:, Fetch Level 2 detail data for Monheimer Kulturwerke events (CONCURRENT)., Return regex patterns for Kulturwerke events.                  These patterns ar, Check if event date is within 1 month from current date. (+1 more)

### Community 22 - "Location Data Sources"
Cohesion: 0.16
Nodes (14): _deduplicate(), discover_locations(), _haversine_m(), _is_duplicate(), _print_summary(), Locations/Ausflüge feature — discover and manage family-friendly locations., Print a summary table of discovered locations., Remove duplicates by coordinate proximity + name similarity.      Two entries ma (+6 more)

### Community 23 - "Eventim Aggregator Scraper"
Cohesion: 0.15
Nodes (7): EventimScraper, API-based scraper for eventim.de aggregator.  Uses the public eventim API to fet, Extract city_names parameter from the API URL., Create an Event from an eventim API product object., API-based scraper for eventim.de.      Fetches events per city using the public, Not used — fetch_events_from_api() takes over., Fetch events from the eventim public API.          Note: The API returns max 50

### Community 24 - "Langenfeld City Events Scraper"
Cohesion: 0.15
Nodes (8): CityEventsRegex, HTML-based parser for Langenfeld city events pages., Extract event detail URLs from calendar page raw HTML.                  Args:, Parse event detail page to extract enhanced information.                  Args:, Fetch Level 2 detail data for Langenfeld city events.                  For each, Return regex patterns for Langenfeld city events.                  These pattern, Parse content using HTML parsing (primary method).                  Override Bas, HTML parser for Langenfeld city events.          IMPORTANT: HTML parsing is PRIM

### Community 25 - "Monheim Terminkalender Scraper"
Cohesion: 0.15
Nodes (7): FreizeitUndTourismusRegex, HTML-based parser for Leichlingen city events pages., Extract event detail URLs from calendar page raw HTML.                  For berg, Parse event detail page to extract enhanced information.                  Args:, Fetch Level 2 detail data for Leichlingen city events.          IMPORTANT: Level, Return regex patterns for Leichlingen city events.                  These patter, HTML parser for Leichlingen city events.          IMPORTANT: HTML parsing is PRI

### Community 26 - "Leichlingen Freizeit Scraper"
Cohesion: 0.18
Nodes (7): MarienburgEventsRegex, HTML-based parser for Marienburg Monheim events pages., Extract event detail URLs from calendar page raw HTML.          Args:, HTML parser for Marienburg Monheim events.      IMPORTANT: HTML parsing is PRIMA, Parse event detail page to extract enhanced information.          Args:, Fetch Level 2 detail data for Marienburg Monheim events.          For each event, Return regex patterns for Marienburg Monheim events.          These patterns are

### Community 27 - "Monheim Marienburg Scraper"
Cohesion: 0.17
Nodes (7): Regex parser for Monheim terminkalender event pages., Regex parser for Monheim terminkalender events., Return regex patterns for Monheim events.          Matches cleaned text format:, Extract event detail URLs from calendar page raw HTML.          Args:, Parse event detail page to extract enhanced information.          Args:, Fetch Level 2 detail data for Monheim terminkalender events.                  Fo, TerminkalenderRegex

### Community 28 - "Monheim Kulturwerke Scraper"
Cohesion: 0.2
Nodes (6): KulturwerkeScraper, Scraper for Monheimer Kulturwerke calendar URL., Scraper for Monheimer Kulturwerke event pages., Fetch content using requests and return raw HTML.                  Returns raw H, Fetch content from Kulturwerke URL.          Uses HTTP requests (faster, no Java, Fetch raw HTML content from Kulturwerke URL.                  This is used by th

### Community 29 - "Hitdorf Kalender Scraper"
Cohesion: 0.22
Nodes (6): KalenderScraper, Scraper for Hitdorf kalender website., Fetch events from Hitdorf WordPress site.                  The Hitdorf website u, Fetch raw HTML content from Hitdorf kalender for Level 2 scraping., Fetch raw HTML content from Hitdorf kalender.                  The Hitdorf websi, Scraper for Hitdorf kalender page.          Uses requests to fetch HTML from Wor

### Community 30 - "Langenfeld City Events Scraper"
Cohesion: 0.22
Nodes (6): CityEventsScraper, Scraper for Langenfeld city events URL., Scraper for Langenfeld city event pages., Fetch content from Langenfeld city events URL.          Uses standard requests f, Fetch raw HTML content from URL.                  Returns full HTML with all ele, Fetch raw HTML content from URL.                  This is used by regex parser f

### Community 31 - "Leichlingen Freizeit Scraper"
Cohesion: 0.22
Nodes (6): FreizeitUndTourismusScraper, Scraper for Leichlingen city events URL., Scraper for Leichlingen city event pages.          The Leichlingen page uses a J, Fetch content from Leichlingen city events URL.          The Leichlingen page us, Fetch raw HTML content from bergisch-live.de API.                  The Leichling, Fetch raw HTML content from URL.                  This is used by regex parser f

### Community 32 - "Monheim Marienburg Scraper"
Cohesion: 0.22
Nodes (6): MarienburgEventsScraper, Scraper for Marienburg Monheim events URL., Scraper for Marienburg Monheim events pages., Fetch content from Marienburg Monheim events URL.          Uses standard request, Fetch raw HTML content from URL with pagination.          Returns full HTML with, Fetch raw HTML content from URL.          This is used by regex parser for Level

### Community 33 - "Rules Framework Core"
Cohesion: 0.2
Nodes (6): Parse content using HTML parsing (primary method).                  Override Bas, Parse content using HTML parsing (primary method).          Override BaseRule me, Event, Structured event data., Create Event from Monheim regex match.          Format: HH.MM Uhr<br>Event Name, Parse content using HTML parsing (not regex).                  Override BaseRule

### Community 34 - "Agent Tools"
Cohesion: 0.25
Nodes (7): fetch_page(), fetch_page_with_browser_check(), Tools for the scraper agent: search and fetch web content., Search the web for information. Use this to find local events, event calendars,, Fetch and extract main text from a web page. Use this to get event details from, Fetch a page, returning additional info about whether browser was needed., search_web()

### Community 35 - "Rausgegangen Aggregator Scraper"
Cohesion: 0.29
Nodes (3): EventimRule, Minimal regex parser for eventim.de aggregator.  Since eventim uses an API-based, Stub regex parser for eventim.de (not used).      All data extraction happens in

### Community 36 - "Eventim Aggregator Scraper"
Cohesion: 0.29
Nodes (5): BaseRule, Minimal regex parser for rausgegangen.de (fallback only).          The primary d, Return empty list - scraper provides all data.                  Returns:, Return empty events - scraper already provides data.                  This metho, RausgegangenRule

### Community 37 - "Test Suite"
Cohesion: 0.33
Nodes (5): Test URL extraction from Monheim calendar page., Test URL extraction from Monheim calendar page., Test detail page parsing., test_detail_page_parsing(), test_url_extraction()

## Knowledge Gaps
- **422 isolated node(s):** `Multi-agent pipeline: scraper -> analyzer -> rating.`, `Agent 2: Analyzes raw event text and structures it (name, description, location,`, `Takes raw event summary text and returns structured event list (list of dicts) w`, `Extract JSON events from pre-structured text (from scraper LLM fallback).`, `Try to extract a JSON array from the model output.` (+417 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **42 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.