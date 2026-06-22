from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
from datetime import date

app = Flask(__name__)

CORS(app)

# DB CONFIG
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "Hanshii@10",
    "database": "conference_booking"
}

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

# ─────────────────────────────
# SIGNUP
# ─────────────────────────────
@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    email = (data.get('email') or '').strip().lower()
    password = (data.get('password') or '').strip()
    role = data.get('role', 'user')

    if not email or not password:
        return jsonify({"status": "fail", "msg": "Email and password required"}), 400

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT email FROM users WHERE email=%s", (email,))
        if cursor.fetchone():
            return jsonify({"status": "fail", "msg": "Email already exists"}), 409

        # 🔥 NO HASHING (important for your current setup)
        cursor.execute(
            "INSERT INTO users(email, password, role) VALUES(%s, %s, %s)",
            (email, password, role)
        )

        conn.commit()
        return jsonify({"status": "success"})

    finally:
        cursor.close()
        conn.close()

# ─────────────────────────────
# LOGIN
# ─────────────────────────────
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = (data.get('email') or '').strip().lower()
    password = (data.get('password') or '').strip()

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    try:
        # SIMPLE CHECK (no hashing)
        cursor.execute(
            "SELECT email, role FROM users WHERE email=%s AND password=%s",
            (email, password)
        )
        user = cursor.fetchone()

        if user:
            return jsonify({
                "status": "success",
                "user": {"email": user["email"], "role": user["role"]}
            })

        return jsonify({"status": "fail", "msg": "Invalid credentials"}), 401

    finally:
        cursor.close()
        conn.close()
# ─────────────────────────────
# BOOK ROOM
# ─────────────────────────────
@app.route('/book', methods=['POST'])
def book():
    data = request.json

    required = ['room', 'roomName', 'title', 'name', 'date', 'start', 'end', 'email']
    for f in required:
        if not str(data.get(f, '')).strip():
            return jsonify({"status": "fail", "msg": f"Missing {f}"}), 400

    if data['start'] >= data['end']:
        return jsonify({"status": "fail", "msg": "Invalid time"}), 400

    attendees = data.get('attendees', 1)

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    try:
        # conflict check
        cursor.execute("""
            SELECT id FROM bookings
            WHERE room_id = %s
              AND date = %s
              AND start_time < %s
              AND end_time > %s
        """, (data['room'], data['date'], data['end'], data['start']))

        if cursor.fetchone():
            return jsonify({"status": "fail", "msg": "Room already booked"}), 409

        # INSERT (fixed column name)
        cursor.execute("""
            INSERT INTO bookings
            (room_id, room_name, title, name, date, start_time, end_time, attendees, user_email)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            data['room'],
            data['roomName'],
            data['title'],
            data['name'],
            data['date'],
            data['start'],
            data['end'],
            attendees,
            data['email']
        ))

        conn.commit()
        return jsonify({"status": "success", "msg": "Booked!"})
    finally:
        cursor.close()
        conn.close()

# ─────────────────────────────
# GET USER BOOKINGS
# ─────────────────────────────
@app.route('/getBookings/<email>')
def get_bookings(email):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    try:
        # FIXED HERE
        cursor.execute(
            "SELECT * FROM bookings WHERE user_email = %s ORDER BY date DESC, start_time DESC",
            (email,)
        )

        rows = cursor.fetchall()
        result = []

        for r in rows:
            result.append({
                "id": r["id"],
                "room": r["room_id"],
                "roomName": r["room_name"],
                "title": r["title"],
                "name": r["name"],
                "date": str(r["date"]),
                "start": str(r["start_time"])[:5],
                "end": str(r["end_time"])[:5],
                "attendees": r["attendees"],
                "email": r["user_email"]   # FIXED HERE
            })

        return jsonify(result)
    finally:
        cursor.close()
        conn.close()

# ─────────────────────────────
# GET USERS (FIX)
# ─────────────────────────────
@app.route('/getUsers')
def get_users():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT email, role FROM users")
        return jsonify(cursor.fetchall())
    finally:
        cursor.close()
        conn.close()

@app.route('/getAllBookings')
def get_all_bookings():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM bookings ORDER BY date DESC, start_time DESC")
        rows = cursor.fetchall()

        result = []
        for r in rows:
            result.append({
                "id": r["id"],
                "room": r["room_id"],
                "roomName": r["room_name"],
                "title": r["title"],
                "name": r["name"],
                "date": str(r["date"]),
                "start": str(r["start_time"])[:5],
                "end": str(r["end_time"])[:5],
                "attendees": r["attendees"],
                "email": r["user_email"]   # IMPORTANT
            })

        return jsonify(result)

    finally:
        cursor.close()
        conn.close()
# ─────────────────────────────
# DELETE BOOKING
# ─────────────────────────────
@app.route('/delete/<int:id>', methods=['DELETE'])
def delete_booking(id):
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM bookings WHERE id=%s", (id,))
        conn.commit()
        return jsonify({"status": "deleted"})
    finally:
        cursor.close()
        conn.close()

# ─────────────────────────────
# DELETE USER (FIX)
# ─────────────────────────────
@app.route('/deleteUser/<email>', methods=['DELETE'])
def delete_user(email):
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM users WHERE email = %s", (email,))
        conn.commit()
        return jsonify({"status": "deleted"})
    finally:
        cursor.close()
        conn.close()        

# ─────────────────────────────
# GET ROOMS
# ─────────────────────────────
@app.route('/getRooms')
def get_rooms():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM rooms")
        return jsonify(cursor.fetchall())
    finally:
        cursor.close()
        conn.close()

# ─────────────────────────────
# STATS
# ─────────────────────────────
@app.route('/getStats')
def get_stats():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    try:
        today = str(date.today())

        cursor.execute("SELECT COUNT(*) AS c FROM users")
        u = cursor.fetchone()["c"]

        cursor.execute("SELECT COUNT(*) AS c FROM rooms")
        r = cursor.fetchone()["c"]

        cursor.execute("SELECT COUNT(*) AS c FROM bookings")
        b = cursor.fetchone()["c"]

        cursor.execute("SELECT COUNT(*) AS c FROM bookings WHERE date = %s", (today,))
        t = cursor.fetchone()["c"]

        return jsonify({"users": u, "rooms": r, "bookings": b, "today": t})
    finally:
        cursor.close()
        conn.close()

# ─────────────────────────────
# RUN
# ─────────────────────────────
if __name__ == '__main__':
    app.run(debug=True)