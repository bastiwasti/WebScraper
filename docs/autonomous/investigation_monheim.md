# Monheim - Investigation Report

## URL
https://marienburgmonheim.de/de/events

## HTML Structure
- [x] Main event card structure documented
- [x] All data sources identified

### Event Card Structure
```html
<div class="event-item col-12 col-sm-6 mb-4">
  <div class="card card-event h-100 animate-fade-top shadow">
    <picture>...</picture>
    <div class="card-body bg-primary">
      <p class="card-text text-dark text-sm d-flex text-nowrap justify-content-between">
        <span>Events</span>
        <time datetime="2026-03-03T10:00:00+01:00">
          03.03. – 30.06.2026
        </time>
      </p>
      <h2 class="card-title text-light text-xl mb-0">
        <a class="text-light" href="/de/events/details/vormittag-auf-dem-marienhof">
          Vormittag auf dem Marienhof
        </a>
      </h2>
    </div>
    <div class="card-footer bg-primary border-top border-primary-dark">
      <a class="text-light" href="/de/events/details/vormittag-auf-dem-marienhof">
        Details ansehen
      </a>
    </div>
  </div>
</div>
```

### Key Selectors
- Event cards: `div.event-item`
- Event title: `div.card-body h2.card-title a.text-light`
- Event date: `div.card-body time`
- Detail URL: `div.card-body h2.card-title a` or `div.card-footer a`
- Pagination: `ul.pagination li.page-item a.page-link`

## Hidden Data Sources
- [ ] "Mehr Infos" / "Show More" buttons found: NO
- [ ] Hidden divs with display:none: NO
- [ ] ID mapping patterns identified: N/A

## Mapping Pattern
- [x] Mapping type: [Link-based]
- [x] Pattern documented: Detail page URLs are extracted from event cards and fetched for additional data

Pattern:
1. Extract event detail URL from card: `/de/events/details/{slug}`
2. Fetch detail page for full description, location, and time
3. Extract enhanced data from detail page

## API Parameters
- [ ] API endpoint identified: NONE (Static HTML)
- [ ] Parameters tested: N/A
- [ ] Results: N/A

## Pagination
- [x] Page 1 event count: 12
- [x] Page 2 event count: 6
- [x] Is pagination real: YES

Pagination format:
- URL parameter: `?page_e8={page_number}`
- Example: `/de/events?page_e8=2`

## Sample Events

### Event 1
- Name: Vormittag auf dem Marienhof
- Date: 03.03.2026
- Time: 10:00 (from datetime attribute)
- Location: Parkplatz der Marienburg Monheim (Bleer Str. 33)
- Description source: Detail page
- Detail URL: https://marienburgmonheim.de/de/events/details/vormittag-auf-dem-marienhof

### Event 2
- Name: Spanischer Tag am OFYR Grill
- Date: 22.03.2026
- Time: 15:00 (from datetime attribute)
- Location: Not visible on card (detail page needed)
- Description source: Detail page
- Detail URL: https://marienburgmonheim.de/de/events/details/spanischer-tag-am-ofyr-grill-2

### Event 3
- Name: Führungen auf dem Marienhof
- Date: 29.03.2026
- Time: 11:00 (from datetime attribute)
- Location: Not visible on card (detail page needed)
- Description source: Detail page
- Detail URL: https://marienburgmonheim.de/de/events/details/fuehrungen-auf-dem-marienhof

## Pattern Detection
**Pattern 5: Static + Pagination** with **Pattern 3: Static + 2-Level**

Reasons:
1. Static HTML - no JavaScript required for page load
2. Real pagination - page 1 has 12 events, page 2 has 6 different events
3. Link-based mapping - detail pages available for enhanced data
4. Date format - HTML5 time datetime attribute provides start date/time
5. Some events have date ranges (start - end date)

## Data Fields Available

### Level 1 (List Page)
- Event name (from card)
- Start date (from datetime attribute, may include end date)
- Event URL (detail page link)

### Level 2 (Detail Page)
- Full description (from page content)
- Location (from Treffpunkt or card-location section)
- Time (from ⏰ markers or datetime)
- Multiple dates (for recurring events)
- End date (if applicable)
