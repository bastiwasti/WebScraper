# URL Investigation Results and Scraper Configuration

## Investigation Summary

This document summarizes the investigation of all event URLs per city and the recommended scraping approach.

## Working URLs (可直接提取事件信息)

### Monheim
| URL | Status | Scraper | Method |
|-----|--------|---------|--------|
| `https://www.monheim.de/freizeit-tourismus/terminkalender` | ✅ Working | `monheim.py` | Playwright + specialized extraction |
| `https://www.monheimer-kulturwerke.de/de/kalender/` | ✅ Working | `monheim.py` | Playwright |

**Findings:**
- The terminkalender uses TYPO3 Extbase events framework
- Requires specific parameter-based fetching for search results
- Content is dynamically loaded
- Events include date, title, location, and description

**Recommended Actions:**
- Use existing `MonheimScraper` with terminkalender-specific method
- Click selectors: 'button:has-text("Mehr laden")', '.ews-dwh-events button[class*="load"]'
- Wait selectors: '.ews-dwh-events .event-item', '[class*="event"][class*="item"]'

### Solingen
| URL | Status | Scraper | Method |
|-----|--------|---------|--------|
| `https://www.solingen-live.de/` | ✅ Working | `solingen.py` | Static HTML |

**Findings:**
- Calendar-based UI with date navigation
- Events displayed with date, time, venue, artist/band, and ticket info
- Static HTML, no JavaScript required for basic content
- Some events require clicking calendar days to see listings

**Recommended Actions:**
- Use `SolingenScraper._fetch_static()` for basic content
- If more events needed, consider Playwright to click through calendar days
- Click selectors: '.calendar-day', '.event-item a'
- Wait selectors: '.event-list', '.calendar'

### Haan
| URL | Status | Scraper | Method |
|-----|--------|---------|--------|
| `https://www.haan.de/Kultur-Freizeit/Veranstaltungen` | ✅ Working | `haan.py` | Static HTML |

**Findings:**
- Event listings directly in HTML
- Events organized by month with date, time, venue, and category
- Static HTML, no JavaScript required
- Clear structure with event cards

**Recommended Actions:**
- Use `HaanScraper._fetch_kulturkalender()` for optimized extraction
- No browser needed
- Content includes: date, time, venue, category, title

### Rausgegangen (Aggregator)
| URL | Status | Scraper | Method |
|-----|--------|---------|--------|
| `https://rausgegangen.de/` | ✅ Working | `aggregators.py` | Static HTML |

**Findings:**
- Major event aggregator for Germany
- Shows popular events with venue, date, price, and category
- City-specific filtering available
- Some content is sponsored/promoted

**Recommended Actions:**
- Use `RausgegangenScraper._fetch_static()` for basic content
- Consider adding city filter to URL for specific locations
- Good source for discovering events in the region

### Meetup (Aggregator)
| URL | Status | Scraper | Method |
|-----|--------|---------|--------|
| `https://www.meetup.com/de-DE/find/?location=de--Nordrhein-Westfalen&source=EVENTS` | ✅ Working | `aggregators.py` | Static HTML |

**Findings:**
- Community-driven event platform
- Shows meetups and events in NRW
- Includes attendee counts and venue information
- Some events are online/hybrid

**Recommended Actions:**
- Use `MeetupScraper._fetch_static()` for basic content
- Consider adding more specific location filters
- Good for community-based events

## Broken URLs (需要验证)

### Langenfeld
| URL | Status | Issue |
|-----|--------|-------|
| `https://www.langenfeld.de/freizeit-kultur/veranstaltungen` | ❌ 404 | URL not found |
| `https://www.kultur-langenfeld.de/` | ❌ Connection Error | Website unavailable |

**Recommended Actions:**
- Manually verify the correct URLs on the city website
- Look for "Veranstaltungen" or "Events" sections
- Update `langenfeld.py` once correct URLs are found

### Leverkusen
| URL | Status | Issue |
|-----|--------|-------|
| `https://www.leverkusen.de/leben-in-lev/veranstaltungen.php` | ❌ 404 | URL not found |
| `https://www.kulturstadtlev.de/veranstaltungen` | ❌ 404 | URL not found |

**Recommended Actions:**
- Verify the correct URLs on leverkusen.de
- Check if there's a new event calendar system
- Update `leverkusen.py` once correct URLs are found

### Hilden
| URL | Status | Issue |
|-----|--------|-------|
| `https://www.hilden.de/kultur-freizeit/veranstaltungen` | ❌ 404 | URL not found |

**Recommended Actions:**
- Verify the correct URL on hilden.de
- Look for event calendar or news section
- Update `hilden.py` once correct URLs are found

### Dormagen
| URL | Status | Issue |
|-----|--------|-------|
| `https://www.dormagen.de/leben-in-dormagen/veranstaltungen` | ❌ 404 | URL not found |

**Recommended Actions:**
- Verify the correct URL on dormagen.de
- Check for events or calendar section
- Update `dormagen.py` once correct URLs are found

### Ratingen
| URL | Status | Issue |
|-----|--------|-------|
| `https://www.ratingen.de/freizeit-kultur/veranstaltungen` | ❌ 404 | URL not found |

**Recommended Actions:**
- Verify the correct URL on ratingen.de
- Look for event calendar or news section
- Update `ratingen.py` once correct URLs are found

### Eventbrite (Aggregator)
| URL | Status | Issue |
|-----|--------|-------|
| `https://www.eventbrite.de/d/germany--nrw/events/` | ❌ 405 | Blocks automated requests |

**Recommended Actions:**
- Eventbrite actively blocks automated scraping
- Consider using Eventbrite API (requires registration)
- Or rely on other aggregators like Rausgegangen
- `EventbriteScraper` returns a message explaining the limitation

## Scraper Configuration

### Priority Order (highest to lowest)
1. **City-specific scrapers** (Monheim, Solingen, Haan)
2. **Placeholder scrapers** (Langenfeld, Leverkusen, Hilden, Dormagen, Ratingen) - URLs need verification
3. **Aggregator scrapers** (Rausgegangen, Meetup)
4. **Eventbrite scraper** - Limited functionality
5. **StaticScraper** - Fallback for any HTTP/HTTPS URL

### When to Use Browser (Playwright)

Use browser-based scraping when:
- Content is dynamically loaded via JavaScript
- Events require clicking buttons/links to load
- Calendar interfaces need navigation
- "Load more" buttons exist

**Don't use browser when:**
- Static HTML contains all needed information
- Page is simple and loads all content immediately
- Resource usage is a concern (browser is heavier)

## Next Steps

1. **Verify broken URLs**: Manually visit each city website to find correct event URLs
2. **Update placeholder scrapers**: Modify `langenfeld.py`, `leverkusen.py`, `hilden.py`, `dormagen.py`, `ratingen.py` once correct URLs are found
3. **Test all scrapers**: Run `python main.py` with each city to verify data extraction
4. **Monitor for changes**: Websites change frequently; update scrapers as needed
5. **Consider API access**: Some sites offer APIs (Eventbrite) that may be more reliable

## URL Update Template

When finding correct URLs, update `agents/scraper_agent.py`:

```python
CITY_EVENT_URLS = {
    "monheim": [
        "https://www.monheim.de/freizeit-tourismus/terminkalender",
        "https://www.monheimer-kulturwerke.de/de/kalender/",
    ],
    "langenfeld": [
        "https://www.langenfeld.de/[CORRECT-PATH]",  # Update this
        # "https://www.kultur-langenfeld.de/",  # Remove if broken
    ],
    # ... update other cities
}
```

## Resources

- **Playwright Documentation**: https://playwright.dev/python/
- **BeautifulSoup Documentation**: https://www.crummy.com/software/BeautifulSoup/bs4/doc/
- **Requests Documentation**: https://requests.readthedocs.io/
