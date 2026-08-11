import os
import secrets
from datetime import datetime, date, timedelta
import cv2
import re

# scheduler and HTTP client for exit notifications
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import requests

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_from_directory
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import or_

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")  # Change this to a random secret key
app.config["ESP_API_KEY"] = os.environ.get(
    "ESP_API_KEY",
    "ESP32_SECRET_KEY"
) # Use a secure key in production

# configuration for scheduler and ESP32 exit gate
app.config['ESP32_IP'] = os.environ.get('ESP32_IP', '10.177.179.251')
# the scheduler will call this URL when a booking expires
app.config['ESP32_EXIT_URL'] = f"http://{app.config['ESP32_IP']}/open_exit_gate"
app.config['BOOKING_EXPIRY_INTERVAL'] = 30  # seconds between checks

# Upload folders
app.config['UPLOAD_FOLDER'] = os.path.join(app.instance_path, 'uploads')
app.config['PROCESSED_FOLDER'] = os.path.join('static', 'processed')

# Ensure folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PROCESSED_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# ---------------- MODELS ----------------

class Slot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slot_number = db.Column(db.Integer)
    location = db.Column(db.String(200), nullable=False, default="Default Location")
    price_per_hour = db.Column(db.Float, nullable=False, default=5.0)
    status = db.Column(db.String(20))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    slot_type = db.Column(db.String(50), nullable=False, default="regular")  # 'regular', 'ev', 'handicapped'

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    slot_id = db.Column(db.Integer, db.ForeignKey('slot.id'))
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    status = db.Column(db.String(20), default="active")  # 'active' or 'cancelled'
    vehicle_number = db.Column(db.String(20), nullable=True)
    slot = db.relationship('Slot', backref='bookings')
    user = db.relationship('User', backref='bookings')

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    gender = db.Column(db.String(50))
    role = db.Column(db.String(50), nullable=False)  # 'admin' or 'user'


class PlateImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    slot_id = db.Column(db.Integer, db.ForeignKey('slot.id'), nullable=True)
    original_path = db.Column(db.String(500))
    processed_path = db.Column(db.String(500))
    plate_text = db.Column(db.String(200))
    confidence = db.Column(db.Float)
    notes = db.Column(db.String(500))

    slot = db.relationship('Slot', backref='plate_images')

@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except Exception:
        return None

# ================= GATE CONTROL HELPERS =================

def clean_plate_text(text):
    """
    Clean extracted plate text:
    - Remove spaces and special characters (keep alphanumeric only)
    - Convert to uppercase
    """
    if not text:
        return None
    # Remove spaces, dashes, and special chars - keep only alphanumeric
    cleaned = re.sub(r'[^A-zA-Z0-9]', '', text)
    return cleaned.upper()


def verify_booking_for_plate(plate_number):
    """
    Check if a plate number has an active booking for TODAY.
    
    Query logic:
    - Find booking where vehicle_number matches (case-insensitive)
    - booking_date (start_time) is TODAY
    - current_time is between start_time and end_time
    - status is 'active'
    
    Returns: (is_authorized, booking_details)
    """
    if not plate_number:
        return False, {"error": "Invalid plate number"}
    
    try:
        now = datetime.now()
        today_start = datetime.combine(now.date(), datetime.min.time())
        today_end = datetime.combine(now.date(), datetime.max.time())
        
        # Query for active bookings matching plate and date/time
        booking = Booking.query.filter(
            Booking.vehicle_number.ilike(plate_number),  # Case-insensitive match
            Booking.status == "active",
            Booking.start_time >= today_start,  # Booking started today
            Booking.start_time <= today_end,    # Confirmation: within today
            Booking.start_time <= now,          # Booking has started
            Booking.end_time > now              # Booking hasn't ended yet
        ).first()
        
        if booking:
            return True, {
                "booking_id": booking.id,
                "slot_number": booking.slot.slot_number,
                "start_time": booking.start_time.isoformat(),
                "end_time": booking.end_time.isoformat(),
                "vehicle_number": booking.vehicle_number
            }
        else:
            return False, {
                "error": "No active booking found",
                "searched_plate": plate_number
            }
    
    except Exception as e:
        print(f"Database error during plate verification: {e}")
        return False, {"error": f"Database error: {str(e)}"}


# ---------------- INIT ----------------

# ---------------- ROUTES ----------------

@app.route("/")
@login_required
def index():
    return render_template("index.html", today=date.today().isoformat())

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            # Redirect admins to admin dashboard, users to regular index
            if user.role == "admin":
                return redirect(url_for("admin"))
            else:
                return redirect(url_for("index"))
        else:
            flash("Invalid email or password")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        username = request.form.get("username")
        gender = request.form.get("gender")
        role = request.form.get("role", "user")
        if User.query.filter_by(email=email).first():
            flash("Email already exists")
        elif User.query.filter_by(username=username).first():
            flash("Username already exists")
        else:
            hashed_password = generate_password_hash(password, method="pbkdf2:sha256")
            new_user = User(email=email, password=hashed_password, username=username, gender=gender, role=role)
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            flash("Account created successfully")
            if new_user.role == "admin":
                return redirect(url_for("admin"))
            else:
                return redirect(url_for("index"))
    return render_template("register.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html")

@app.route("/admin")
@login_required
def admin():
    if current_user.role != "admin":
        return redirect(url_for("index"))
    slots = Slot.query.all()
    bookings = Booking.query.all()
    plate_images = PlateImage.query.order_by(PlateImage.created_at.desc()).limit(12).all()
    # Normalize paths/URLs for template
    plate_entries = []
    for p in plate_images:
        proc_fname = None
        orig_fname = None
        if p.processed_path:
            proc_fname = os.path.basename(p.processed_path.replace('\\', '/'))
        if p.original_path:
            orig_fname = os.path.basename(p.original_path.replace('\\', '/'))
        proc_url = url_for('static', filename=f'processed/{proc_fname}') if proc_fname else None
        orig_url = url_for('uploaded_file', filename=orig_fname) if orig_fname else None
        plate_entries.append({
            'id': p.id,
            'created_at': p.created_at,
            'slot_id': p.slot_id,
            'plate_text': p.plate_text,
            'confidence': p.confidence,
            'notes': p.notes,
            'processed_url': proc_url,
            'original_url': orig_url
        })

    return render_template("admin.html", slots=slots, bookings=bookings, plate_images=plate_entries, now=datetime.now())

@app.route("/book")
@login_required
def book():
    return render_template("book.html", today=date.today().isoformat())

@app.route("/book/datetime")
@login_required
def book_datetime():
    return render_template("book_datetime.html", today=date.today().isoformat())

@app.route("/book/payment")
@login_required
def book_payment():
    return render_template("book_payment.html")

@app.route("/my_bookings")
@login_required
def my_bookings_page():
    return render_template("my_bookings.html")

# ---------------- APIs ----------------

@app.route("/api/slots")
def get_slots():
    try:
        from math import radians, sin, cos, sqrt, atan2
        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)
        slot_filter = request.args.get('filter', default=None)  # 'ev', 'handicapped', or None
        
        slots = Slot.query.all()
        now = datetime.now()
        
        slot_data = []
        for s in slots:
            # Apply filter
            if slot_filter == 'ev' and s.slot_type != 'ev':
                continue
            if slot_filter == 'handicapped' and s.slot_type != 'handicapped':
                continue
            
            # Check if currently booked (exclude cancelled bookings and NULL status)
            # Only check for bookings that are currently ongoing (now is between start and end)
            current_booking = Booking.query.filter(
                Booking.slot_id == s.id,
                or_(Booking.status == "active", Booking.status.is_(None)),
                Booking.start_time <= now,
                Booking.end_time > now
            ).first()
            in_use = current_booking is not None
            
            # Check physical occupancy from ESP32 sensor (case-insensitive)
            physically_occupied = s.status and s.status.lower() == "occupied"
            
            # Slot is available only if it's not being booked AND not physically occupied
            available = not in_use and not physically_occupied
            
            data = {
                "id": s.id,
                "slot_number": s.slot_number,
                "location": s.location,
                "price_per_hour": s.price_per_hour,
                "available": available,
                "in_use": in_use,
                "physically_occupied": physically_occupied,
                "latitude": s.latitude,
                "longitude": s.longitude,
                "slot_type": s.slot_type
            }
            
            if lat is not None and lng is not None and s.latitude and s.longitude:
                # Calculate distance
                R = 6371  # Earth's radius in km
                dlat = radians(s.latitude - lat)
                dlng = radians(s.longitude - lng)
                a = sin(dlat/2)**2 + cos(radians(lat)) * cos(radians(s.latitude)) * sin(dlng/2)**2
                c = 2 * atan2(sqrt(a), sqrt(1-a))
                distance = R * c
                data["distance"] = distance
            
            slot_data.append(data)
        
        # Sort by distance if location provided
        if lat is not None:
            slot_data.sort(key=lambda x: x.get("distance", float('inf')))
        
        return jsonify(slot_data)
    except Exception as e:
        print(f"⚠️ Error fetching slots: {e}")
        return jsonify([]), 200  # Return empty list to prevent frontend errors

@app.route("/api/my_bookings")
@login_required
def my_bookings():
    bookings = Booking.query.filter_by(user_id=current_user.id).join(Slot, Booking.slot_id == Slot.id).all()
    return jsonify([
        {
            "id": b.id,
            "slot_number": b.slot.slot_number,
            "start_time": b.start_time.isoformat(),
            "end_time": b.end_time.isoformat(),
            "latitude": b.slot.latitude,
            "longitude": b.slot.longitude,
            "status": b.status,
            "vehicle_number": b.vehicle_number  # include vehicle number for display
        }
        for b in bookings
    ])

@app.route("/api/update_slot", methods=["POST"])
def update_slot():
    """
    Endpoint for ESP32 or other hardware to update slot status.
    Expects JSON: {"slot_id": <int>, "status": <str>}
    """
    data = request.get_json()
    slot_id = data.get("slot_id")
    status = data.get("status")
    if slot_id is None or status is None:
        return jsonify({"error": "Missing slot_id or status"}), 400
    slot = Slot.query.get(slot_id)
    if not slot:
        return jsonify({"error": "Slot not found"}), 404
    slot.status = status
    db.session.commit()
    return jsonify({"message": "Slot status updated", "slot_id": slot_id, "status": status})

@app.route("/api/book", methods=["POST"])
@login_required
def book_slot():
    data = request.json
    start = datetime.fromisoformat(data["start"])
    end = datetime.fromisoformat(data["end"])
    vehicle_number = data.get("vehicle_number")

    # Check for conflicts: only with active bookings that overlap in time
    # Overlap occurs when: new_start < existing_end AND new_end > existing_start
    conflict = Booking.query.filter(
        Booking.slot_id == data["slot_id"],
        or_(Booking.status == "active", Booking.status.is_(None)),
        Booking.start_time < end,
        Booking.end_time > start
    ).first()

    if conflict:
        return jsonify({"error": "Slot already booked for this time"}), 409

    booking = Booking(
        user_id=current_user.id,
        slot_id=data["slot_id"],
        start_time=start,
        end_time=end,
        status="active",
        vehicle_number=vehicle_number
    )
    db.session.add(booking)
    db.session.commit()
    return jsonify({"message": "Booked"})

@app.route("/api/cancel_booking", methods=["POST"])
@login_required
def cancel_booking():
    data = request.json
    booking_id = data.get("booking_id")
    
    booking = Booking.query.get(booking_id)
    
    if not booking:
        return jsonify({"error": "Booking not found"}), 404
    
    if booking.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403
    
    booking.status = "cancelled"
    db.session.commit()
    return jsonify({"message": "Booking cancelled successfully"})


# helper route used during development/testing to fire the expiry check manually
@app.route("/api/trigger_expiry")
def trigger_expiry():
    try:
        _expire_bookings_job()
        return jsonify({"status": "success", "message": "expiry job executed"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

# ================= GATE CONTROL ENDPOINT =================

@app.route("/api/verify_plate", methods=["POST"])
def verify_plate():
    """
    Endpoint for ESP32-CAM to verify if a vehicle can pass through the gate.
    
    Accepts multipart/form-data or raw image bytes
    Form fields: file (image) or raw image bytes
    
    Returns:
    {
        "status": "AUTHORIZED" or "DENIED",
        "vehicle_number": <extracted_plate>,
        "booking_details": {...},  # if authorized
        "error": "..."  # if denied or error
    }
    """
    
    # Accept API key or allow without authentication for gate system
    api_key = request.headers.get('X-API-Key')
    if api_key and api_key != app.config['ESP_API_KEY']:
        return jsonify({
            "status": "DENIED",
            "error": "Invalid API key"
        }), 401
    
    # Get image from request
    image_data = None
    
    if 'file' in request.files:
        # Multipart/form-data with file
        f = request.files['file']
        if f.filename == '':
            return jsonify({
                "status": "DENIED",
                "error": "No file selected"
            }), 400
        
        if not _allowed_file(f.filename):
            return jsonify({
                "status": "DENIED",
                "error": "Unsupported file type"
            }), 400
        
        image_data = f.read()
    
    elif request.data and request.headers.get('Content-Type', '').startswith('image/'):
        # Raw image bytes
        image_data = request.data
    
    else:
        return jsonify({
            "status": "DENIED",
            "error": "No image data provided"
        }), 400
    
    # Save image temporarily
    try:
        nparr = cv2.imdecode(__import__('numpy').frombuffer(image_data, __import__('numpy').uint8), cv2.IMREAD_COLOR)
        if nparr is None:
            return jsonify({
                "status": "DENIED",
                "error": "Could not decode image"
            }), 400
        
        token = secrets.token_hex(8)
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        temp_filename = f"{timestamp}_{token}_gate_verify.jpg"
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)
        cv2.imwrite(temp_path, nparr)
        
    except Exception as e:
        print(f"Error processing image: {e}")
        return jsonify({
            "status": "DENIED",
            "error": f"Image processing error: {str(e)}"
        }), 500
    
    # Extract plate using OCR
    plate_number = None
    ocr_confidence = None
    
    try:
        from plate_processor import process_image as process_ocr
        processed_path, ocr_text, confidence, notes = process_ocr(temp_path, output_dir=app.config['PROCESSED_FOLDER'])
        
        if ocr_text:
            plate_number = clean_plate_text(ocr_text)
            ocr_confidence = confidence
            print(f"✅ Extracted plate: {ocr_text} → Cleaned: {plate_number}")
        else:
            print(f"⚠️ OCR failed to extract text. Notes: {notes}")
        
    except Exception as e:
        print(f"❌ OCR Error: {e}")
        return jsonify({
            "status": "DENIED",
            "error": f"OCR failed: {str(e)}"
        }), 500
    
    finally:
        # Clean up temporary image
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except:
            pass
    
    if not plate_number:
        return jsonify({
            "status": "DENIED",
            "error": "Could not extract valid plate number",
            "confidence": ocr_confidence
        }), 400
    
    # Verify booking for extracted plate
    is_authorized, booking_info = verify_booking_for_plate(plate_number)
    
    response = {
        "status": "AUTHORIZED" if is_authorized else "DENIED",
        "vehicle_number": plate_number,
        "ocr_confidence": ocr_confidence
    }
    
    if is_authorized:
        response["booking_details"] = booking_info
    else:
        response["error"] = booking_info.get("error")
    
    return jsonify(response), 200

# ================== IMAGE UPLOAD & PROCESSING ================

with app.app_context():
    try:
        db.create_all()
        # Only create slots if the database is completely empty (first run)
        if Slot.query.count() == 0 and User.query.count() == 0:
            print("Initializing database with default data...")
            # 6 slots as per new layout:
            # P1: Handicapped
            db.session.add(Slot(slot_number=1, status="empty", location="P1", price_per_hour=5.0,
                        latitude=17.6868, longitude=83.2185, slot_type="handicapped"))
            # P2: Handicapped
            db.session.add(Slot(slot_number=2, status="empty", location="P2", price_per_hour=5.0,
                        latitude=17.6870, longitude=83.2187, slot_type="handicapped"))
            # P3: Normal
            db.session.add(Slot(slot_number=3, status="empty", location="P3", price_per_hour=4.0,
                        latitude=17.6880, longitude=83.2170, slot_type="regular"))
            # P4: Normal
            db.session.add(Slot(slot_number=4, status="empty", location="P4", price_per_hour=4.0,
                        latitude=17.6875, longitude=83.2175, slot_type="regular"))
            # P5: EV
            db.session.add(Slot(slot_number=5, status="empty", location="P5", price_per_hour=8.0,
                        latitude=17.6865, longitude=83.2180, slot_type="ev"))
            # P6: EV
            db.session.add(Slot(slot_number=6, status="empty", location="P6", price_per_hour=8.0,
                        latitude=17.6863, longitude=83.2186, slot_type="ev"))
            db.session.commit()
            # Create default admin user
            hashed_password = generate_password_hash("admin123", method="pbkdf2:sha256")
            admin = User(email="admin@gmail.com", password=hashed_password, role="admin")
            db.session.add(admin)
            db.session.commit()
            print("Database initialized successfully!")
    except Exception as e:
        print(f"⚠️ Database initialization error: {e}")
        print("⚠️ PostgreSQL may not be running. Start PostgreSQL to enable database features.")
        print("⚠️ The app will continue running, but database features will be unavailable.")

# ---------------- SCHEDULER HELPERS ----------------

def _expire_bookings_job():
    """Called periodically by the background scheduler.

    The job explicitly pushes an application context because APScheduler runs
    outside of request handlers. Without the context SQLAlchemy queries will
    raise "Working outside of application context" errors.

    * Detect active bookings whose end_time has passed (today).
    * Mark them as completed only after successfully notifying the ESP32 exit gate.
    * Avoid double‑triggering by only operating on status == 'active'.

    SQLAlchemy equivalent of the raw query below is used:
        SELECT * FROM booking
        WHERE status = 'active'
          AND end_time <= NOW()
          AND DATE(start_time) = CURRENT_DATE;
    """
    with app.app_context():
        now = datetime.now()
        try:
            # find bookings that should have expired
            expired = Booking.query.filter(
                Booking.status == 'active',
                Booking.end_time <= now
            ).all()

            if not expired:
                return

            for b in expired:
                exit_url = app.config['ESP32_EXIT_URL']
                try:
                    print(f"🕒 Booking {b.id} expired at {b.end_time}, notifying ESP32 {exit_url}")
                    resp = requests.post(exit_url, timeout=5, headers={
                        'X-API-Key': app.config['ESP_API_KEY']
                    })
                    print(f"   -> HTTP {resp.status_code}")
                    if 200 <= resp.status_code < 300:
                        # only update status on success so failures can retry
                        b.status = 'completed'
                        db.session.add(b)
                    else:
                        print(f"   ✖ non‑success response, will retry later")
                except Exception as e:
                    print(f"   ⚠️ error sending exit signal: {e}")
                    # keep status active so it will be retried

            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"❌ scheduler job failed: {e}")


# initialize and start scheduler after app context is ready
scheduler = BackgroundScheduler()
scheduler.add_job(_expire_bookings_job, 'interval', seconds=app.config['BOOKING_EXPIRY_INTERVAL'], id='expire-bookings')
scheduler.start()
# ensure the scheduler is shut down when the process exits
atexit.register(lambda: scheduler.shutdown())


# ================= ESP32 UPDATE ENDPOINT =================
@app.route("/update_slots", methods=["POST"])
def update_slots():
    """
    Endpoint for an ESP32 to send parking slot occupancy status.
    Expected JSON format: {"slot1": "occupied", "slot2": "empty", ...}
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        print(f"📥 Received ESP32 data: {data}")

        updated_slots = []
        # Update slot statuses in database
        for slot_key, new_status in data.items():
            if slot_key.startswith('slot'):
                try:
                    slot_num = int(slot_key[4:])  # 'slot1' -> 1
                    slot = Slot.query.filter_by(slot_number=slot_num).first()
                    if slot:
                        old_status = slot.status
                        slot.status = new_status
                        db.session.add(slot)
                        print(f"✅ Slot {slot_num}: {old_status} → {slot.status}")
                        updated_slots.append(slot_num)
                    else:
                        print(f"⚠️ Slot number {slot_num} from key '{slot_key}' not found in DB.")
                except (ValueError, IndexError):
                    print(f"⚠️ Could not parse slot number from key: {slot_key}")

        db.session.commit()
        print(f"💾 Database committed successfully for slots: {updated_slots}")
        return jsonify({"status": "success", "message": f"Slot statuses updated for slots: {updated_slots}"}), 200

    except Exception as e:
        db.session.rollback()
        print(f"❌ Error updating slots: {e}")
        return jsonify({"error": str(e)}), 500


# ---------------- IMAGE UPLOAD & PROCESSING ----------------
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


def _allowed_file(filename):
    ext = os.path.splitext(filename)[1].lower()
    return ext in ['.jpg', '.jpeg', '.png']


@app.route('/api/upload_plate', methods=['POST'])
def upload_plate():
    """
    Secure endpoint for ESP32-CAM to POST an image (multipart/form-data).
    Headers: X-API-Key: <key>
    Form fields: file (image), slot_id (optional)
    """
    # Basic API key authentication from header
    api_key = request.headers.get('X-API-Key')
    print(f"DEBUG: Received API Key: '{api_key}' | Expected: '{app.config['ESP_API_KEY']}'")

    if not api_key or api_key != app.config['ESP_API_KEY']:
        return jsonify({'error': 'Unauthorized. Invalid or missing X-API-Key header.'}), 401

    slot_id = request.form.get('slot_id', type=int)

    # Accept either multipart/form-data 'file' or raw image bytes (Content-Type: image/jpeg)
    f = None
    saved_path = None
    if 'file' in request.files:
        f = request.files['file']
        if f.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        if not _allowed_file(f.filename):
            return jsonify({'error': 'Unsupported file type'}), 400
        filename = secure_filename(f.filename)
        token = secrets.token_hex(8)
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        saved_name = f"{timestamp}_{token}_{filename}"
        saved_path = os.path.join(app.config['UPLOAD_FOLDER'], saved_name)
        f.save(saved_path)
    else:
        # Try raw body (ESP32 sketch may POST raw JPEG bytes)
        content_type = request.headers.get('Content-Type', '')
        if request.data and content_type.startswith('image/'):
            ext = '.jpg' if 'jpeg' in content_type or 'jpg' in content_type else '.png'
            token = secrets.token_hex(8)
            timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
            saved_name = f"{timestamp}_{token}_capture{ext}"
            saved_path = os.path.join(app.config['UPLOAD_FOLDER'], saved_name)
            with open(saved_path, 'wb') as fh:
                fh.write(request.data)
        else:
            return jsonify({'error': 'No file part'}), 400

    # Defer heavy processing to separate function/module
    try:
        from plate_processor import process_image
    except Exception as e:
        process_image = None
        print(f"Plate processor import failed: {e}")

    processed_name = None
    plate_text = None
    confidence = None
    notes = None

    try:
        if process_image:
            processed_img_path, ocr_text, conf, extra = process_image(saved_path, output_dir=app.config['PROCESSED_FOLDER'])
            processed_name = os.path.basename(processed_img_path) if processed_img_path else None
            plate_text = ocr_text
            confidence = conf
            notes = extra
        else:
            notes = 'processor not available'

    except Exception as e:
        notes = f'processing_error: {e}'
        print('Error during image processing:', e)

    # Store record in DB
    rec = PlateImage(
        slot_id=slot_id,
        original_path=os.path.relpath(saved_path),
        processed_path=os.path.relpath(os.path.join(app.config['PROCESSED_FOLDER'], processed_name)) if processed_name else None,
        plate_text=plate_text,
        confidence=confidence,
        notes=notes
    )
    db.session.add(rec)
    db.session.commit()

    return jsonify({'message': 'uploaded', 'id': rec.id, 'plate_text': plate_text, 'processed_path': rec.processed_path}), 201

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
