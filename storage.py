import json
import os
from datetime import datetime

STORAGE_FILE = 'data/reports.json'

# Initialize storage
if not os.path.exists('data'):
    os.makedirs('data')
if not os.path.exists(STORAGE_FILE) or os.path.getsize(STORAGE_FILE) == 0:
    with open(STORAGE_FILE, 'w') as f:
        json.dump([], f)

def store_report(crime_type, location, details, weapon=None, injury=None, suspect=None, mo=None, date=None):
    """Store a crime report with enhanced fields."""
    try:
        with open(STORAGE_FILE, 'r') as f:
            reports = json.load(f)
    except (json.JSONDecodeError, ValueError):
        reports = []

    report = {
        'id': str(len(reports) + 1),
        'crime_type': crime_type,
        'location': location,
        'details': details,
        'weapon': weapon or "Unknown",
        'injury': injury or "Unknown",
        'suspect': suspect or "Unknown",
        'mo': mo or "Unknown",
        'date': date or datetime.now().strftime('%Y-%m-%d'),
        'tags': {
            'App-Name': 'CrimeChain',
            'Crime-Type': crime_type,
            'Location': location,
            'Weapon': weapon or "Unknown",
            'Injury': injury or "Unknown",
            'Suspect': suspect or "Unknown",
            'MO': mo or "Unknown"
        }
    }

    reports.append(report)
    with open(STORAGE_FILE, 'w') as f:
        json.dump(reports, f, indent=2)

    return report['id']

def search_reports(query, start_date=None, end_date=None):
    """Search with filters for date range and tags."""
    try:
        with open(STORAGE_FILE, 'r') as f:
            reports = json.load(f)
    except (json.JSONDecodeError, ValueError):
        return []

    query = query.lower()
    results = [
        report for report in reports
        if (query in report['crime_type'].lower() or
            query in report['location'].lower() or
            query in report['details'].lower() or
            query in report['weapon'].lower() or
            query in report['injury'].lower() or
            query in report['suspect'].lower() or
            query in report['mo'].lower() or
            any(query in str(value).lower() for value in report['tags'].values()))
    ]

    # Filter by date range if provided
    if start_date:
        results = [r for r in results if r['date'] >= start_date]
    if end_date:
        results = [r for r in results if r['date'] <= end_date]

    return sorted(results, key=lambda x: x['date'])  # Sort by date