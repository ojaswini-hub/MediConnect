import os
import sqlite3
from functools import wraps
from datetime import date, datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, g

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, "appointments.db")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key-before-deployment")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def table_columns(db, table):
    return [row["name"] for row in db.execute(f"PRAGMA table_info({table})").fetchall()]


def init_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")

    db.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('admin','doctor','patient')),
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS doctor_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        specialization TEXT NOT NULL,
        qualification TEXT DEFAULT '',
        phone TEXT DEFAULT '',
        availability TEXT DEFAULT 'Mon-Sat, 9:00 AM - 5:00 PM',
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_name TEXT NOT NULL,
        email TEXT NOT NULL,
        doctor TEXT NOT NULL,
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        patient_id INTEGER,
        doctor_id INTEGER,
        reason TEXT DEFAULT '',
        status TEXT DEFAULT 'Pending',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(patient_id) REFERENCES users(id),
        FOREIGN KEY(doctor_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        message TEXT NOT NULL,
        is_read INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    # Upgrade the earlier student project database without deleting existing appointments.
    columns = table_columns(db, "appointments")
    additions = {
        "patient_id": "INTEGER",
        "doctor_id": "INTEGER",
        "reason": "TEXT DEFAULT ''",
        "status": "TEXT DEFAULT 'Pending'",
        "created_at": "TEXT"
    }
    for column, definition in additions.items():
        if column not in columns:
            db.execute(f"ALTER TABLE appointments ADD COLUMN {column} {definition}")

    # Demo administrator
    admin = db.execute("SELECT id FROM users WHERE email = ?", ("admin@mediconnect.com",)).fetchone()
    if not admin:
        db.execute(
            "INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)",
            ("MediConnect Admin", "admin@mediconnect.com", "admin123", "admin")
        )

    # Demo doctor accounts. These are sample accounts for project demonstration.
    demo_doctors = [
        ("Dr. Asha Patil", "doctor1@mediconnect.com", "doc123", "General Medicine", "MBBS"),
        ("Dr. Rahul Sharma", "doctor2@mediconnect.com", "doc123", "Cardiology", "MBBS, MD"),
        ("Dr. Neha Deshmukh", "doctor3@mediconnect.com", "doc123", "Dermatology", "MBBS, DVD"),
        ("Dr. Amit Kulkarni", "doctor4@mediconnect.com", "doc123", "Orthopaedics", "MBBS, MS"),
        ("Dr. Priya Joshi", "doctor5@mediconnect.com", "doc123", "Paediatrics", "MBBS, DCH")
    ]
    for name, email, password, specialization, qualification in demo_doctors:
        user = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if not user:
            cur = db.execute(
                "INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)",
                (name, email, password, "doctor")
            )
            user_id = cur.lastrowid
        else:
            user_id = user["id"]
        profile = db.execute("SELECT id FROM doctor_profiles WHERE user_id = ?", (user_id,)).fetchone()
        if not profile:
            db.execute(
                """INSERT INTO doctor_profiles
                   (user_id,specialization,qualification,phone,availability)
                   VALUES (?,?,?,?,?)""",
                (user_id, specialization, qualification, "", "Monday-Saturday, 9:00 AM - 5:00 PM")
            )

    # Connect older appointments to doctor accounts when possible.
    old_rows = db.execute(
        "SELECT id, doctor FROM appointments WHERE doctor_id IS NULL"
    ).fetchall()
    for row in old_rows:
        doctor = db.execute("SELECT id FROM users WHERE name = ? AND role='doctor'", (row["doctor"],)).fetchone()
        if doctor:
            db.execute("UPDATE appointments SET doctor_id=? WHERE id=?", (doctor["id"], row["id"]))

    db.commit()
    db.close()


def login_required(role=None):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("user_id"):
                flash("Please log in to continue.", "warning")
                return redirect(url_for("login"))
            if role and session.get("role") != role:
                flash("You do not have permission to open that page.", "danger")
                return redirect(url_for("dashboard"))
            return view(*args, **kwargs)
        return wrapped
    return decorator


@app.context_processor
def inject_user():
    return {"current_user": session.get("name"), "current_role": session.get("role")}


@app.route("/")
def home():
    db = get_db()
    doctors = db.execute("""
        SELECT u.id,u.name,p.specialization,p.qualification
        FROM users u JOIN doctor_profiles p ON p.user_id=u.id
        WHERE u.role='doctor' ORDER BY u.name
    """).fetchall()
    return render_template("index.html", doctors=doctors)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or len(password) < 6:
            flash("Enter your name, a valid email and a password of at least 6 characters.", "danger")
            return render_template("register.html")
        db = get_db()
        try:
            db.execute(
                "INSERT INTO users (name,email,password,role) VALUES (?,?,?,'patient')",
                (name, email, password)
            )
            db.commit()
            flash("Your account has been created. Please log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("This email is already registered. Please log in.", "warning")
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE email=? AND password=?", (email, password)
        ).fetchone()
        if user:
            session.clear()
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]
            flash(f"Welcome, {user['name']}!", "success")
            return redirect(url_for("dashboard"))
        flash("Email or password is incorrect. Please try again.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))


@app.route("/dashboard")
@login_required()
def dashboard():
    role = session["role"]
    if role == "admin":
        return redirect(url_for("admin_dashboard"))
    if role == "doctor":
        return redirect(url_for("doctor_dashboard"))
    return redirect(url_for("patient_dashboard"))


@app.route("/patient")
@login_required("patient")
def patient_dashboard():
    db = get_db()
    appointments = db.execute("""
        SELECT * FROM appointments WHERE patient_id=?
        ORDER BY date DESC, time DESC
    """, (session["user_id"],)).fetchall()
    today = date.today().isoformat()
    upcoming = [a for a in appointments if a["date"] >= today and a["status"] not in ("Cancelled", "Rejected", "Completed")]
    reminders = [a for a in upcoming if a["date"] <= (date.today() + timedelta(days=2)).isoformat()]
    return render_template("patient_dashboard.html", appointments=appointments, upcoming=upcoming, reminders=reminders)


@app.route("/book", methods=["GET", "POST"])
@login_required("patient")
def book():
    db = get_db()
    doctors = db.execute("""
        SELECT u.id,u.name,p.specialization,p.qualification,p.availability
        FROM users u JOIN doctor_profiles p ON p.user_id=u.id
        WHERE u.role='doctor' ORDER BY p.specialization,u.name
    """).fetchall()

    if request.method == "POST":
        doctor_id = request.form.get("doctor_id", type=int)
        appointment_date = request.form.get("date", "")
        appointment_time = request.form.get("time", "")
        reason = request.form.get("reason", "").strip()

        doctor = db.execute("""
            SELECT u.id,u.name FROM users u
            JOIN doctor_profiles p ON p.user_id=u.id
            WHERE u.id=? AND u.role='doctor'
        """, (doctor_id,)).fetchone()

        try:
            chosen_date = date.fromisoformat(appointment_date)
            if chosen_date < date.today():
                raise ValueError()
        except ValueError:
            flash("Please select today or a future date.", "danger")
            return render_template("book.html", doctors=doctors, min_date=date.today().isoformat())

        if not doctor or not appointment_time:
            flash("Please select a doctor and an appointment time.", "danger")
            return render_template("book.html", doctors=doctors, min_date=date.today().isoformat())

        conflict = db.execute("""
            SELECT id FROM appointments
            WHERE doctor_id=? AND date=? AND time=?
            AND status NOT IN ('Cancelled','Rejected')
        """, (doctor_id, appointment_date, appointment_time)).fetchone()
        if conflict:
            flash("This time slot is already booked. Please choose another time.", "warning")
            return render_template("book.html", doctors=doctors, min_date=date.today().isoformat())

        patient = db.execute("SELECT name,email FROM users WHERE id=?", (session["user_id"],)).fetchone()
        db.execute("""
            INSERT INTO appointments
            (patient_name,email,doctor,date,time,patient_id,doctor_id,reason,status)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (patient["name"], patient["email"], doctor["name"], appointment_date,
              appointment_time, session["user_id"], doctor_id, reason, "Pending"))
        db.commit()
        flash("Your appointment request has been sent. You can track it on My Appointments.", "success")
        return redirect(url_for("patient_dashboard"))

    return render_template("book.html", doctors=doctors, min_date=date.today().isoformat())


@app.route("/appointments")
@login_required("patient")
def appointments():
    return redirect(url_for("patient_dashboard"))


@app.route("/cancel/<int:appointment_id>", methods=["POST"])
@login_required("patient")
def cancel_appointment(appointment_id):
    db = get_db()
    appointment = db.execute(
        "SELECT * FROM appointments WHERE id=? AND patient_id=?",
        (appointment_id, session["user_id"])
    ).fetchone()
    if not appointment:
        flash("Appointment not found.", "danger")
    elif appointment["status"] in ("Completed", "Rejected", "Cancelled"):
        flash("This appointment can no longer be cancelled.", "warning")
    else:
        db.execute("UPDATE appointments SET status='Cancelled' WHERE id=?", (appointment_id,))
        db.commit()
        flash("Appointment cancelled. Its reminder is no longer active.", "success")
    return redirect(url_for("patient_dashboard"))


@app.route("/doctor")
@login_required("doctor")
def doctor_dashboard():
    db = get_db()
    appointments = db.execute("""
        SELECT * FROM appointments WHERE doctor_id=?
        ORDER BY date ASC,time ASC
    """, (session["user_id"],)).fetchall()
    profile = db.execute("SELECT * FROM doctor_profiles WHERE user_id=?", (session["user_id"],)).fetchone()
    return render_template("doctor_dashboard.html", appointments=appointments, profile=profile)


@app.route("/doctor/appointment/<int:appointment_id>/<action>", methods=["POST"])
@login_required("doctor")
def doctor_update_appointment(appointment_id, action):
    allowed = {"accept": "Confirmed", "reject": "Rejected", "complete": "Completed"}
    if action not in allowed:
        flash("Invalid appointment action.", "danger")
        return redirect(url_for("doctor_dashboard"))
    db = get_db()
    result = db.execute("""
        UPDATE appointments SET status=?
        WHERE id=? AND doctor_id=?
    """, (allowed[action], appointment_id, session["user_id"]))
    db.commit()
    if result.rowcount:
        flash(f"Appointment marked as {allowed[action].lower()}.", "success")
    else:
        flash("Appointment not found.", "warning")
    return redirect(url_for("doctor_dashboard"))


@app.route("/admin")
@login_required("admin")
def admin_dashboard():
    db = get_db()
    stats = {
        "patients": db.execute("SELECT COUNT(*) FROM users WHERE role='patient'").fetchone()[0],
        "doctors": db.execute("SELECT COUNT(*) FROM users WHERE role='doctor'").fetchone()[0],
        "appointments": db.execute("SELECT COUNT(*) FROM appointments").fetchone()[0],
        "pending": db.execute("SELECT COUNT(*) FROM appointments WHERE status='Pending'").fetchone()[0]
    }
    doctors = db.execute("""
        SELECT u.id,u.name,u.email,p.specialization,p.qualification,p.availability
        FROM users u JOIN doctor_profiles p ON p.user_id=u.id
        WHERE u.role='doctor' ORDER BY u.name
    """).fetchall()
    appointments = db.execute("SELECT * FROM appointments ORDER BY date DESC,time DESC").fetchall()
    return render_template("admin_dashboard.html", stats=stats, doctors=doctors, appointments=appointments)


@app.route("/admin/doctor/add", methods=["POST"])
@login_required("admin")
def add_doctor():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    specialization = request.form.get("specialization", "").strip()
    qualification = request.form.get("qualification", "").strip()
    availability = request.form.get("availability", "").strip() or "Monday-Saturday, 9:00 AM - 5:00 PM"
    if not all([name, email, password, specialization]):
        flash("Please complete all required doctor details.", "danger")
        return redirect(url_for("admin_dashboard"))
    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO users (name,email,password,role) VALUES (?,?,?,'doctor')",
            (name, email, password)
        )
        db.execute("""
            INSERT INTO doctor_profiles (user_id,specialization,qualification,availability)
            VALUES (?,?,?,?)
        """, (cur.lastrowid, specialization, qualification, availability))
        db.commit()
        flash("Doctor account added successfully.", "success")
    except sqlite3.IntegrityError:
        flash("An account with this email already exists.", "warning")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/doctor/delete/<int:doctor_id>", methods=["POST"])
@login_required("admin")
def delete_doctor(doctor_id):
    db = get_db()
    # Keep appointment history; remove the doctor from the active doctor list.
    db.execute("UPDATE appointments SET status='Cancelled' WHERE doctor_id=? AND status NOT IN ('Completed','Rejected','Cancelled')", (doctor_id,))
    db.execute("UPDATE appointments SET doctor_id=NULL WHERE doctor_id=?", (doctor_id,))
    db.execute("DELETE FROM users WHERE id=? AND role='doctor'", (doctor_id,))
    db.commit()
    flash("Doctor account removed. Any active appointments were cancelled.", "info")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/appointment/<int:appointment_id>/<status>", methods=["POST"])
@login_required("admin")
def admin_update_appointment(appointment_id, status):
    if status not in ("Confirmed", "Cancelled", "Completed"):
        flash("Invalid status.", "danger")
    else:
        db = get_db()
        db.execute("UPDATE appointments SET status=? WHERE id=?", (status, appointment_id))
        db.commit()
        flash("Appointment status updated.", "success")
    return redirect(url_for("admin_dashboard"))


@app.errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404


# Initialize the database for both local runs and Gunicorn deployment.
init_db()

if __name__ == "__main__":
    app.run(debug=True)
