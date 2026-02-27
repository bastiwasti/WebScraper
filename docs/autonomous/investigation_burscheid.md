# Burscheid - Investigation Report

## HTML Structure
- [x] Main event card structure documented
- [x] All data sources identified

## Hidden Data Sources
- [ ] "Mehr Infos" / "Show More" buttons found: YES
- [ ] Hidden divs with display:none: YES (via detail API)
- [x] ID mapping patterns identified: Link-based (API detail endpoint)

## Mapping Pattern
- [x] Mapping type: Link-based
- [x] Pattern documented: Event ID extracted from `<a name="123"></a>` anchor, detail fetched from `https://www.bergisch-live.de/events/client=burscheid.de;mode=utf8;what=detail;show={id}`

## API Parameters
- [x] API endpoint identified: https://www.bergisch-live.de/events/what=All;client=burscheid.de
- [x] Parameters tested:
  - `what=All` - Returns all events
  - `what=dyn` - Returns dynamic events
  - `client=burscheid.de` - Specifies city
- [x] Results: API returns HTML with event cards

## Pagination
- [x] Page 1 event count: 226 (all events returned in single API call)
- [x] Page 2 event count: N/A (no pagination - all events returned)
- [x] Is pagination real: NO - all events returned in single request

## Sample Events

### Event 1
- Name: Eltern-Kind-Gruppe Mäusegruppe
- Date: 16.02.2026
- Time: 09:00 - 10:30
- Location: Tri-Café
- Description source: Card (title + subtitle) / Detail page

### Event 2
- Name: Eltern-Kind-Gruppe Bienengruppe
- Date: 16.02.2026
- Time: 11:00 - 12:30
- Location: Tri-Café
- Description source: Card (title + subtitle) / Detail page

### Event 3
- Name: Kreativ am Dienstag - Malen & Zeichnen für alle
- Date: 17.02.2026
- Time: 14:00 - 16:00
- Location: SPD-Bürgertreff
- Description source: Card (title + subtitle) / Detail page

## Pattern Detected
**Pattern 1: REST API (JSON)** with HTML response

The site uses a custom API (`bergisch-live.de`) that returns HTML event data.
- Main API: `https://www.bergisch-live.de/events/what=All;client=burscheid.de`
- Detail API: `https://www.bergisch-live.de/events/client=burscheid.de;mode=utf8;what=detail;show={id}`
- No pagination required - all events returned in single request
- Level 2 extraction via detail page fetching for full descriptions
