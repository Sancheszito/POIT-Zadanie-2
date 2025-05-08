import serial
import MySQLdb
from flask_socketio import SocketIO, emit, disconnect
from datetime import datetime
import configparser as ConfigParser
import socketio

# SocketIO klient
sio = socketio.Client()
sio.connect('http://localhost:80')  # pripojenie na SocketIO server

arduino = serial.Serial('/dev/ttyS0', 9600)
config = ConfigParser.ConfigParser()
config.read('config.cfg')
myhost = config.get('mysqlDB', 'host')
myuser = config.get('mysqlDB', 'user')
mypasswd = config.get('mysqlDB', 'passwd')
mydb = config.get('mysqlDB', 'db')
db = MySQLdb.connect(host=myhost, user=myuser, passwd=mypasswd, db=mydb)
cursor = db.cursor()

session_id = 0
recording = False


while True:
    line = arduino.readline().decode().strip()
    if line == "START":
        session_id += 1
        recording = True
        print(f"Zaznamenávam session {session_id}")
    elif line == "STOP":
        recording = False
        print(f"Stop zaznamenávania")
    elif recording:
        try:
            distance = float(line)
            ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("INSERT INTO measurements (session_id, timestamp, distance) VALUES (%s, %s, %s)", (session_id, ts, distance))
            db.commit()            
            print(f"Uložené: {distance} cm")
            # Posielanie cez socket
            sio.emit('new_data', {'session_id': session_id, 'timestamp': ts, 'distance': distance})
        except ValueError:
            pass
