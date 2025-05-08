from flask import Flask, render_template, request, Response, redirect, url_for
from flask_socketio import SocketIO, emit
from threading import Lock
import os
import time 
import datetime 
from werkzeug.utils import secure_filename
import MySQLdb
import configparser as ConfigParser
import csv
import io
import subprocess
from flask import flash
latest_uploaded_csv = []
# === Flask & SocketIO setup ===
async_mode = None
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode, cors_allowed_origins="*")  # Dôležité pre frontend aj reader.py

thread = None
thread_lock = Lock()

# === Load DB config ===
config = ConfigParser.ConfigParser()
config.read('config.cfg')
myhost = config.get('mysqlDB', 'host')
myuser = config.get('mysqlDB', 'user')
mypasswd = config.get('mysqlDB', 'passwd')
mydb = config.get('mysqlDB', 'db')
# === Folder config ===
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# === DB connection function ===
def get_db_connection():
    return MySQLdb.connect(host=myhost, user=myuser, passwd=mypasswd, db=mydb)
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# === Routes ===
@app.route('/')
def index():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT session_id FROM measurements ORDER BY session_id DESC")
    sessions = cur.fetchall()
    conn.close()
    return render_template('index.html', sessions=sessions)

@app.route('/session/<int:session_id>')
def show_session(session_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT timestamp, distance FROM measurements WHERE session_id = %s", (session_id,))
    data = cur.fetchall()
    conn.close()
    return render_template('session.html', data=data, session_id=session_id)

@app.route('/delete-session/<int:session_id>', methods=['POST'])
def delete_session(session_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM measurements WHERE session_id = %s", (session_id,))
        conn.commit()
        conn.close()
        return redirect('/')
    except Exception as e:
        return f"Chyba pri mazaní merania: {e}"

@app.route('/download/<int:session_id>')
def download_csv(session_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT timestamp, distance FROM measurements WHERE session_id = %s", (session_id,))
    data = cur.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['timestamp', 'distance'])

    for row in data:
        writer.writerow(row)

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename=session_{session_id}.csv'}
    )

@app.route('/start')
def start_measurement():
    try:
        # Spusti reader.py na pozadí
        subprocess.Popen(["python3", "reader.py"])
        return redirect(url_for('live'))
    except Exception as e:
        return f"Chyba pri spúšťaní: {e}"

@app.route('/stop')
def stop_measurement():
    global measuring
    measuring = False  # alebo iný mechanizmus na ukončenie vlákna
    print("Meranie ukončené.")
    return redirect('/')

@app.route('/live')
def live():
    return render_template('live.html')
    
@app.route('/upload_csv', methods=['POST'])
def upload_csv():
    global latest_uploaded_csv

    if 'csv_file' not in request.files:
        return "Nebyl vybratý žiadny súbor"

    file = request.files['csv_file']
    if file.filename == '':
        return "Nebyl vybratý žiadny súbor"

    try:
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_input = csv.DictReader(stream)

        uploaded_data = []
        for row in csv_input:
            try:
                dt = datetime.datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S")
                ts = int(time.mktime(dt.timetuple()))
                dist = float(row['distance'])
                uploaded_data.append((ts, dist))
            except Exception as e:
                print("Chyba pri parsovaní riadku:", e)

        if uploaded_data:
            latest_uploaded_csv = uploaded_data
            return redirect('/session_csv')
        else:
            return "CSV neobsahuje žiadne platné dáta."

    except Exception as e:
        return f"Chyba pri nahrávaní: {e}"

@app.route('/session_csv')
def session_csv():
    global latest_uploaded_csv
    if not latest_uploaded_csv:
        return "Žiadne dáta neboli nahrané."

    return render_template('session.html', data=latest_uploaded_csv, session_id="CSV")
#prevod cisla na timestamp na datumovy format pri upload CSV
@app.template_filter('datetimeformat')
def datetimeformat(value):
    try:
        return datetime.datetime.fromtimestamp(int(value)).strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return value  # Ak sa nedá previesť, vráti pôvodnú hodnotu
    
# === SocketIO Events ===
@socketio.on('new_data')
def handle_new_data(data):
    print(f"Prijaté nové dáta: {data}")
    emit('broadcast_data', data, broadcast=True)

@socketio.on('connect')
def handle_connect():
    print('Klient pripojený')

@socketio.on('disconnect')
def handle_disconnect():
    print('Klient odpojený')

# === Main ===
if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=80, debug=True)
