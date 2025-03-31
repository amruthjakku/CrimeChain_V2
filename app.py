from flask import Flask, render_template, request
from storage import store_report, search_reports

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    report_id = None
    if request.method == 'POST' and 'crime_type' in request.form:
        crime_type = request.form['crime_type']
        location = request.form['location']
        details = request.form['details']
        weapon = request.form.get('weapon', '')
        injury = request.form.get('injury', '')
        suspect = request.form.get('suspect', '')
        mo = request.form.get('mo', '')
        date = request.form.get('date', '')
        
        report_id = store_report(crime_type, location, details, weapon, injury, suspect, mo, date)
    
    return render_template('index.html', report_id=report_id)

@app.route('/search', methods=['POST'])
def search():
    query = request.form['search_query']
    start_date = request.form.get('start_date', '')
    end_date = request.form.get('end_date', '')
    results = search_reports(query, start_date, end_date)
    return render_template('results.html', results=results, query=query)

if __name__ == '__main__':
    app.run(debug=True)