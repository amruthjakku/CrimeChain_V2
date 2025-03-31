import json
import os
from datetime import datetime
import hashlib
import random
import tempfile

# Define primary and fallback directories
PRIMARY_DATA_DIR = 'data'
FALLBACK_DATA_DIR = os.path.join(tempfile.gettempdir(), 'crimechain_data')

# Determine writable directory
DATA_DIR = PRIMARY_DATA_DIR
if not os.path.exists(PRIMARY_DATA_DIR):
    try:
        os.makedirs(PRIMARY_DATA_DIR, exist_ok=True)
    except PermissionError:
        print(f"Warning: Cannot create {PRIMARY_DATA_DIR}. Switching to fallback: {FALLBACK_DATA_DIR}")
        DATA_DIR = FALLBACK_DATA_DIR
        os.makedirs(FALLBACK_DATA_DIR, exist_ok=True)
elif not os.access(PRIMARY_DATA_DIR, os.W_OK):
    print(f"Warning: No write access to {PRIMARY_DATA_DIR}. Switching to fallback: {FALLBACK_DATA_DIR}")
    DATA_DIR = FALLBACK_DATA_DIR
    os.makedirs(FALLBACK_DATA_DIR, exist_ok=True)

# Define file paths
STORAGE_FILE = os.path.join(DATA_DIR, 'reports.json')
ACTIVITY_LOG = os.path.join(DATA_DIR, 'activity.json')
PROGRESS_FILE = os.path.join(DATA_DIR, 'progress.json')

# Initialize files
def initialize_file(file_path, default_content):
    """Initialize a file with default content if it doesn’t exist or is empty."""
    try:
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            with open(file_path, 'w') as f:
                json.dump(default_content, f)
    except PermissionError:
        print(f"Error: Cannot initialize {file_path}. Check permissions.")
        raise
    except Exception as e:
        print(f"Unexpected error initializing {file_path}: {e}")
        raise

# Initialize all files
for path, default in [
    (STORAGE_FILE, []),
    (ACTIVITY_LOG, []),
    (PROGRESS_FILE, {"milestones": [], "stats": {"reports_added": 0, "searches": 0}})
]:
    initialize_file(path, default)

def hash_report(report):
    return hashlib.sha256(json.dumps(report, sort_keys=True).encode()).hexdigest()

def extract_tags(details):
    tags = {}
    details = details.lower()
    if 'knife' in details: tags['Weapon'] = 'Knife'
    if 'stab' in details or 'cut' in details: tags['Injury'] = 'Stab Wound'
    if 'gun' in details or 'shot' in details: tags['Weapon'] = 'Gun'
    if 'night' in details: tags['MO'] = 'Night Ambush'
    return tags

def mock_sentiment(details):
    return 'negative' if any(w in details.lower() for w in ['violent', 'attack']) else 'neutral'

def cluster_reports(reports, new_report):
    for i, report in enumerate(reports):
        if (report.get('weapon') == new_report['weapon'] and
            report.get('injury') == new_report['injury'] and
            report.get('mo') == new_report['mo']):
            return report.get('cluster', f"Cluster {i+1}")
    return f"Cluster {len(reports) + 1}"

def store_report(crime_type, location, details, weapon=None, injury=None, suspect=None, mo=None, date=None, username=None):
    try:
        with open(STORAGE_FILE, 'r') as f:
            reports = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError, PermissionError):
        reports = []

    auto_tags = extract_tags(details)
    lat, lon = random.uniform(30, 40), random.uniform(-80, -70)  # Mock coordinates
    report = {
        'id': str(len(reports) + 1),
        'crime_type': crime_type,
        'location': location,
        'details': details,
        'weapon': weapon or auto_tags.get('Weapon', 'Unknown'),
        'injury': injury or auto_tags.get('Injury', 'Unknown'),
        'suspect': suspect or 'Unknown',
        'mo': mo or auto_tags.get('MO', 'Unknown'),
        'date': date or datetime.now().strftime('%Y-%m-%d'),
        'geo': {'lat': lat, 'lon': lon},  # Always include geo
        'sentiment': mock_sentiment(details),
        'tags': {
            'App-Name': 'CrimeChain',
            'Crime-Type': crime_type,
            'Location': location,
            'Weapon': weapon or auto_tags.get('Weapon', 'Unknown'),
            'Injury': injury or auto_tags.get('Injury', 'Unknown'),
            'Suspect': suspect or 'Unknown',
            'MO': mo or auto_tags.get('MO', 'Unknown')
        },
        'cluster': cluster_reports(reports, {'weapon': weapon, 'injury': injury, 'mo': mo}),
        'hash': hash_report({'crime_type': crime_type, 'location': location, 'details': details})
    }

    reports.append(report)
    try:
        with open(STORAGE_FILE, 'w') as f:
            json.dump(reports, f, indent=2)
    except PermissionError:
        print(f"Error: Cannot write to {STORAGE_FILE}. Check permissions.")
        raise

    log_activity(username, f"Submitted report {report['id']}")
    update_progress("reports_added", 1)

    return report['id'], auto_tags, report['cluster']

def search_reports(query, start_date=None, end_date=None):
    try:
        with open(STORAGE_FILE, 'r') as f:
            reports = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError, PermissionError):
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
    if start_date:
        results = [r for r in results if r['date'] >= start_date]
    if end_date:
        results = [r for r in results if r['date'] <= end_date]
    return sorted(results, key=lambda x: x['date'])

def get_analytics():
    try:
        with open(STORAGE_FILE, 'r') as f:
            reports = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError, PermissionError):
        return {"total_reports": 0, "weapon_counts": {}, "location_counts": {}, "cluster_counts": {}, "predictions": [], "heatmap": {}}

    analytics = {
        "total_reports": len(reports),
        "weapon_counts": {},
        "location_counts": {},
        "cluster_counts": {},
        "predictions": [],
        "heatmap": {}
    }
    for report in reports:
        analytics['weapon_counts'][report['weapon']] = analytics['weapon_counts'].get(report['weapon'], 0) + 1
        analytics['location_counts'][report['location']] = analytics['location_counts'].get(report['location'], 0) + 1
        cluster = report.get('cluster', 'Unclustered')
        analytics['cluster_counts'][cluster] = analytics['cluster_counts'].get(cluster, 0) + 1
        loc = report['location']
        analytics['heatmap'][loc] = analytics['heatmap'].get(loc, 0) + 1
    
    if analytics['weapon_counts'].get('Knife', 0) > 2:
        top_loc = max(analytics['location_counts'], key=analytics['location_counts'].get, default='Unknown')
        analytics['predictions'].append(f"High Knife crime in {top_loc} - Next likely soon.")
    
    return analytics

def log_activity(username, action):
    try:
        with open(ACTIVITY_LOG, 'r') as f:
            logs = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError, PermissionError):
        logs = []
    logs.append({'username': username or 'unknown', 'action': action, 'timestamp': datetime.now().isoformat()})
    try:
        with open(ACTIVITY_LOG, 'w') as f:
            json.dump(logs, f, indent=2)
    except PermissionError:
        print(f"Error: Cannot write to {ACTIVITY_LOG}. Check permissions.")

def update_progress(milestone=None, stat_increment=None):
    try:
        with open(PROGRESS_FILE, 'r') as f:
            progress = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError, PermissionError):
        progress = {"milestones": [], "stats": {"reports_added": 0, "searches": 0}}

    if milestone:
        progress['milestones'].append({"name": milestone, "date": datetime.now().isoformat()})
    if stat_increment and isinstance(stat_increment, tuple):
        key, value = stat_increment
        progress['stats'][key] = progress['stats'].get(key, 0) + value

    try:
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(progress, f, indent=2)
    except PermissionError:
        print(f"Error: Cannot write to {PROGRESS_FILE}. Check permissions.")
    return progress

def get_progress():
    try:
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError, PermissionError):
        return {"milestones": [], "stats": {"reports_added": 0, "searches": 0}}