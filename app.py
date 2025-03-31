from flask import Flask, render_template, request, session, redirect, url_for, send_file, jsonify, make_response
from functools import wraps
from storage import store_report, search_reports, get_analytics, log_activity, update_progress, get_progress, STORAGE_FILE
import json
import os
import csv
from io import StringIO

app = Flask(__name__)
app.secret_key = 'crimechain_secret'

USERS = {
    'police': {'password': 'secure123', 'role': 'police'},
    'analyst': {'password': 'data456', 'role': 'analyst'}
}

cached_analytics = None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in', False):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def extract_form_data(form, fields):
    return {field: form.get(field, '') for field in fields}

def validate_date(date_str):
    if not date_str:
        return None
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return date_str
    except ValueError:
        return None

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        user = USERS.get(username)
        if user and user['password'] == password:
            session['logged_in'] = True
            session['username'] = username
            session['role'] = user['role']
            log_activity(username, "Logged in")
            return redirect(url_for('index'))
        return render_template('login.html', error="Invalid credentials")
    return render_template('login.html', error=None)

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    global cached_analytics
    report_id, suggested_tags, cluster = None, {}, None
    role = session.get('role', 'analyst')
    username = session.get('username', 'unknown')

    if request.method == 'POST' and role == 'police':
        fields = ['crime_type', 'location', 'details', 'weapon', 'injury', 'suspect', 'mo', 'date']
        data = extract_form_data(request.form, fields)
        if data['crime_type'] and data['location'] and data['details']:
            report_id, suggested_tags, cluster = store_report(
                data['crime_type'], data['location'], data['details'],
                data['weapon'], data['injury'], data['suspect'], data['mo'], data['date'], username
            )
            cached_analytics = None
    
    cached_analytics = cached_analytics or get_analytics()
    return render_template('index.html', report_id=report_id, suggested_tags=suggested_tags, 
                          cluster=cluster, analytics=cached_analytics, role=role)

@app.route('/search', methods=['POST'])
@login_required
def search():
    role = session.get('role', 'analyst')
    username = session.get('username', 'unknown')
    fields = ['search_query', 'start_date', 'end_date']
    data = extract_form_data(request.form, fields)
    query = data['search_query']
    start_date = validate_date(data['start_date'])
    end_date = validate_date(data['end_date'])
    
    if not query:
        return render_template('results.html', results=[], query=query, role=role)
    
    results = search_reports(query, start_date, end_date)
    log_activity(username, f"Searched for '{query}'")
    update_progress(stat_increment=("searches", 1))
    
    if 'export_json' in request.form:
        export_data = json.dumps(results, indent=2)
        export_path = 'export.json'
        with open(export_path, 'w') as f:
            f.write(export_data)
        return send_file(export_path, as_attachment=True, download_name=f'search_results_{query}.json')
    
    if 'export_csv' in request.form:
        si = StringIO()
        writer = csv.writer(si)
        writer.writerow(['ID', 'Crime Type', 'Location', 'Date', 'Weapon', 'Injury', 'Suspect', 'MO', 'Details', 'Sentiment', 'Cluster', 'Lat', 'Lon'])
        for r in results:
            writer.writerow([
                r['id'], r['crime_type'], r['location'], r['date'], r['weapon'], r['injury'], 
                r['suspect'], r['mo'], r['details'], r.get('sentiment', 'N/A'), r.get('cluster', 'N/A'),
                r.get('geo', {}).get('lat', 'N/A'), r.get('geo', {}).get('lon', 'N/A')
            ])
        response = make_response(si.getvalue())
        response.headers['Content-Disposition'] = f'attachment; filename=search_results_{query}.csv'
        response.headers['Content-type'] = 'text/csv'
        return response
    
    return render_template('results.html', results=results, query=query, role=role)

@app.route('/progress')
@login_required
def progress():
    role = session.get('role', 'analyst')
    progress_data = get_progress()
    return render_template('progress.html', progress=progress_data, role=role)

@app.route('/api/reports', methods=['GET'])
@login_required
def api_reports():
    try:
        with open(STORAGE_FILE, 'r') as f:
            reports = json.load(f)
        return jsonify(reports), 200
    except (FileNotFoundError, json.JSONDecodeError):
        return jsonify({'error': 'No reports available'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/logout')
def logout():
    username = session.get('username', 'unknown')
    log_activity(username, "Logged out")
    session.clear()
    return redirect(url_for('login'))

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', message="Something went wrong."), 500

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', message="Page not found."), 404

if __name__ == '__main__':
    update_progress("App Started")
    app.run(debug=True, host='0.0.0.0', port=5000)