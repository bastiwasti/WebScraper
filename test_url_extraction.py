"""Test URL extraction from Monheim calendar page."""

import sys
from rules.cities.monheim_am_rhein.terminkalender.regex import TerminkalenderRegex

# Mock HTML with event detail URLs (matches actual Monheim structure)
MOCK_CALENDAR_HTML = '''
<html>
<head><title>Monheim - Terminkalender</title></head>
<body>
    <h1>Terminkalender</h1>

    <div class="event-item">
        <p>
            <a class="url date" title="Wochenmarkt in Monheim Mitte" href="/freizeit-tourismus/terminkalender/termin/wochenmarkt-in-monheim-mitte-2884">
                <span class="more-link">mehr</span>
            </a>
        </p>
    </div>

    <div class="event-item">
        <p>
            <a class="url date" title="Die Sprachbar" href="/freizeit-tourismus/terminkalender/termin/die-sprachbar-2-8866">
                <span class="more-link">mehr</span>
            </a>
        </p>
    </div>

    <div class="event-item">
        <p>
            <a class="url date" title="Chorproben für Kinder, Jugendliche und Erwachsene" href="/freizeit-tourismus/terminkalender/termin/chorproben-fur-kinder-jugendliche-und-erwachsene-8756">
                <span class="more-link">mehr</span>
            </a>
        </p>
    </div>
</body>
</html>
'''

# Mock detail page HTML (matches actual Monheim structure)
MOCK_DETAIL_HTML = '''
<html>
<head><title>Termin - Stadt Monheim am Rhein</title></head>
<body>
    <h1>Wochenmarkt in Monheim Mitte</h1>

    <dl>
        <dt>Termin:</dt>
        <dd>Jeden Mittwoch</dd>
        <dt>Beginn:</dt>
        <dd>08:00 Uhr</dd>
        <dt>Ende:</dt>
        <dd>13:00 Uhr</dd>
    </dl>

    <h3>Ort: Eierplatz</h3>

    <p>Mittwochs und samstags ist Wochenmarkt im Stadtteil Monheim. An Feiertagen können die Termine abweichen. Der Markt bietet ein reichhaltiges Angebot von Fisch, Fleisch, Eier und Käse über Obst und Gemüse bis zu Blumen und Brot. Daneben bieten Händlerinnen und Händler Textilien, Haushalts- und Kurzwaren an.</p>

    <p>Kategorie: Markt</p>
</body>
</html>
'''

def test_url_extraction():
    """Test URL extraction from Monheim calendar page."""
    parser = TerminkalenderRegex("https://www.monheim.de/freizeit-tourismus/terminkalender")
    urls = parser.get_event_urls_from_html(MOCK_CALENDAR_HTML)

    print(f"✅ Found {len(urls)} event detail URLs:")
    for url in urls:
        print(f"  {url}")

    assert len(urls) == 3, f"Expected 3 URLs, got {len(urls)}"
    assert urls[0] == "/freizeit-tourismus/terminkalender/termin/wochenmarkt-in-monheim-mitte-2884"
    assert urls[1] == "/freizeit-tourismus/terminkalender/termin/die-sprachbar-2-8866"

    return urls


def test_detail_page_parsing():
    """Test detail page parsing."""
    parser = TerminkalenderRegex("https://www.monheim.de/freizeit-tourismus/terminkalender")
    detail_data = parser.parse_detail_page(MOCK_DETAIL_HTML)

    print(f"\n✅ Parsed detail page data:")
    for key, value in detail_data.items():
        print(f"  {key}: {value}")

    assert detail_data is not None, "Failed to parse detail page"
    assert detail_data['detail_title'] == "Wochenmarkt in Monheim Mitte"
    assert detail_data['detail_date'] == "Jeden Mittwoch"
    assert detail_data['detail_time'] == "08:00 Uhr"
    assert detail_data['detail_end_time'] == "13:00 Uhr"
    assert detail_data['detail_location'] == "Eierplatz"

    if 'detail_category' in detail_data:
        assert detail_data['detail_category'] == "Markt"
    else:
        print("  ⚠️  Category not found in detail page")

    assert "Wochenmarkt" in detail_data['detail_description']

    return detail_data


if __name__ == '__main__':
    print("=" * 60)
    print("Test 1: URL Extraction")
    print("=" * 60)
    urls = test_url_extraction()
    print(f"\n✅ URL Extraction Test: PASSED")

    print("\n" + "=" * 60)
    print("Test 2: Detail Page Parsing")
    print("=" * 60)
    detail_data = test_detail_page_parsing()
    print(f"\n✅ Detail Page Parsing Test: PASSED")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)
