"""Fix city name variations in database.

Migration script to standardize city names:
- 'monheim' -> 'monheim_am_rhein'
- 'monheim am rhein' -> 'monheim_am_rhein'
- Other variations to underscore format

Usage:
    python scripts/fix_city_variations.py
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from storage import get_connection, _execute, rebuild_events_distinct

def fix_city_variations(conn=None):
    """Fix city name variations in events and events_distinct tables."""
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    
    try:
        print("Fixing city name variations in database...")
        print()
        
        # Fix 'monheim' -> 'monheim_am_rhein' in events table
        print("1. Fixing 'monheim' -> 'monheim_am_rhein' in events table...")
        _execute(conn,
            "UPDATE events SET city = 'monheim_am_rhein' WHERE city = 'monheim'"
        )
        conn.commit()
        cur = _execute(conn, "SELECT COUNT(*) AS cnt FROM events WHERE city = 'monheim_am_rhein' AND origin = 'monheim_marienburg_events'")
        count = cur.fetchone()['cnt']
        print(f"   Fixed {count} events in events table")
        
        # Fix 'monheim am rhein' -> 'monheim_am_rhein' in events table
        print()
        print("2. Fixing 'monheim am rhein' -> 'monheim_am_rhein' in events table...")
        _execute(conn,
            "UPDATE events SET city = 'monheim_am_rhein' WHERE city = 'monheim am rhein'"
        )
        conn.commit()
        cur = _execute(conn, "SELECT COUNT(*) AS cnt FROM events WHERE city = 'monheim_am_rhein' AND origin = 'rausgegangen_monheim_am_rhein'")
        count = cur.fetchone()['cnt']
        print(f"   Fixed {count} events in events table")
        
        # Fix 'monheim' -> 'monheim_am_rhein' in events_distinct table
        print()
        print("3. Fixing 'monheim' -> 'monheim_am_rhein' in events_distinct table...")
        _execute(conn,
            "UPDATE events_distinct SET city = 'monheim_am_rhein' WHERE city = 'monheim'"
        )
        conn.commit()
        cur = _execute(conn, "SELECT COUNT(*) AS cnt FROM events_distinct WHERE city = 'monheim_am_rhein' AND origin = 'monheim_marienburg_events'")
        count = cur.fetchone()['cnt']
        print(f"   Fixed {count} events in events_distinct table")
        
        # Fix 'monheim am rhein' -> 'monheim_am_rhein' in events_distinct table
        print()
        print("4. Fixing 'monheim am rhein' -> 'monheim_am_rhein' in events_distinct table...")
        _execute(conn,
            "UPDATE events_distinct SET city = 'monheim_am_rhein' WHERE city = 'monheim am rhein'"
        )
        conn.commit()
        cur = _execute(conn, "SELECT COUNT(*) AS cnt FROM events_distinct WHERE city = 'monheim_am_rhein' AND origin = 'rausgegangen_monheim_am_rhein'")
        count = cur.fetchone()['cnt']
        print(f"   Fixed {count} events in events_distinct table")
        
        # Fix other common variations (case-insensitive)
        print()
        print("5. Fixing other common variations (case-insensitive)...")
        
        # Monheim am Rhein (capital M)
        _execute(conn,
            "UPDATE events SET city = 'monheim_am_rhein' WHERE LOWER(city) = 'monheim am rhein'"
        )
        
        # Monheim am rhein (capital M, lowercase a)
        _execute(conn,
            "UPDATE events SET city = 'monheim_am_rhein' WHERE LOWER(city) = 'monheim am rhein'"
        )
        
        # Same for events_distinct
        _execute(conn,
            "UPDATE events_distinct SET city = 'monheim_am_rhein' WHERE LOWER(city) = 'monheim am rhein'"
        )
        conn.commit()
        print(f"   Fixed additional case variations")
        
        # Verify fixes
        print()
        print("6. Verifying fixes...")
        
        # Check remaining incorrect values
        cur = _execute(conn,
            "SELECT city, COUNT(*) AS cnt FROM events WHERE city ILIKE '%monheim%' AND city != 'monheim_am_rhein' GROUP BY city"
        )
        rows = cur.fetchall()
        
        if rows:
            print("   WARNING: Found remaining incorrect city values in events table:")
            for row in rows:
                print(f"     '{row['city']}': {row['cnt']} events")
        else:
            print("   ✓ All city names in events table are now correct")
        
        # Check events_distinct
        cur = _execute(conn,
            "SELECT city, COUNT(*) AS cnt FROM events_distinct WHERE city ILIKE '%monheim%' AND city != 'monheim_am_rhein' GROUP BY city"
        )
        rows = cur.fetchall()
        
        if rows:
            print("   WARNING: Found remaining incorrect city values in events_distinct table:")
            for row in rows:
                print(f"     '{row['city']}': {row['cnt']} events")
        else:
            print("   ✓ All city names in events_distinct table are now correct")
        
        # Summary
        print()
        print("Summary:")
        cur = _execute(conn, "SELECT COUNT(*) AS total FROM events WHERE city = 'monheim_am_rhein'")
        total_events = cur.fetchone()['total']
        print(f"  Total events with city = 'monheim_am_rhein': {total_events}")
        
        cur = _execute(conn, "SELECT COUNT(*) AS total FROM events_distinct WHERE city = 'monheim_am_rhein'")
        total_distinct = cur.fetchone()['total']
        print(f"  Total distinct events with city = 'monheim_am_rhein': {total_distinct}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        if own_conn:
            conn.rollback()
    finally:
        if own_conn:
            conn.close()


def main():
    """Main entry point."""
    import sys
    
    print("=" * 70)
    print("City Name Variations Fix Script")
    print("=" * 70)
    print()
    
    fix_city_variations()
    
    print()
    print("=" * 70)
    print("Migration complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
