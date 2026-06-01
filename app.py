"""
app.py — Main Flask application for YSP Learns Learning Management System.

Routes:
  - Public: Landing, Catalog, Module Detail, Login, Signup
  - Student: Dashboard, Module Content, Assignment Submission, Enrollment
  - Admin: Dashboard, Module CRUD, Announcements, Submissions View
"""

import os
import uuid
import sqlite3
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, send_from_directory, abort, session, jsonify
)
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# ─── Configuration ───────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Manually load local .env file if present
env_path = os.path.join(BASE_DIR, '.env')
if os.path.exists(env_path):
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            if '=' in line and not line.strip().startswith('#'):
                key, val = line.strip().split('=', 1)
                os.environ[key.strip()] = val.strip()

# Detect if running in Vercel serverless environment
IS_VERCEL = os.environ.get('VERCEL') == '1' or 'VERCEL' in os.environ

if IS_VERCEL:
    DB_PATH = '/tmp/database.db'
    UPLOAD_DIR = '/tmp/uploads'
    
    try:
        # Copy seed database to writeable /tmp folder if not present
        original_db = os.path.join(BASE_DIR, 'database.db')
        if not os.path.exists(DB_PATH) and os.path.exists(original_db):
            import shutil
            # Use copyfile instead of copy2 to prevent copying OS metadata, which fails on Vercel
            shutil.copyfile(original_db, DB_PATH)
            try:
                os.chmod(DB_PATH, 0o666)
            except Exception:
                pass
    except Exception as e:
        print(f"Failed to initialize Vercel database path: {e}")
else:
    DB_PATH = os.path.join(BASE_DIR, 'database.db')
    UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')
ALLOWED_EXTENSIONS = {
    'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx',
    'txt', 'zip', 'rar', 'png', 'jpg', 'jpeg', 'gif', 'mp4', 'py', 'java', 'c', 'cpp'
}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static')
)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'ysp-learns-lms-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
app.config['GEMINI_API_KEY'] = os.environ.get('GEMINI_API_KEY', '')

os.makedirs(UPLOAD_DIR, exist_ok=True)

# ─── Flask-Login Setup ───────────────────────────────────────────────────────

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'


class User(UserMixin):
    """User model for Flask-Login session management."""

    def __init__(self, id, full_name, email, password_hash, role, created_at):
        self.id = id
        self.full_name = full_name
        self.email = email
        self.password_hash = password_hash
        self.role = role
        self.created_at = created_at

    def is_admin(self):
        return self.role == 'admin'


@login_manager.user_loader
def load_user(user_id):
    """Load user from database by ID for session management."""
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if user:
        return User(user['id'], user['full_name'], user['email'],
                    user['password_hash'], user['role'], user['created_at'])
    return None


# ─── Database Helpers ────────────────────────────────────────────────────────

def get_db():
    """Create a database connection. Bypasses WAL mode on Vercel."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    if not IS_VERCEL:
        conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def allowed_file(filename):
    """Check if a file extension is in the allowed list."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_upload(file):
    """Save an uploaded file with a unique name. Returns (stored_name, original_name)."""
    if file and file.filename and allowed_file(file.filename):
        original = secure_filename(file.filename)
        ext = original.rsplit('.', 1)[1].lower()
        stored = f"{uuid.uuid4().hex}.{ext}"
        file.save(os.path.join(UPLOAD_DIR, stored))
        return stored, original
    return None, None


# ─── Calendar Secure Tokens ──────────────────────────────────────────────────

def get_calendar_token(user_id):
    """Generate a secure HMAC token for user's iCalendar subscription feed."""
    import hmac
    import hashlib
    secret = app.config['SECRET_KEY'].encode('utf-8')
    message = f"cal_{user_id}".encode('utf-8')
    return hmac.new(secret, message, hashlib.sha256).hexdigest()[:16]


def verify_calendar_token(user_id, token):
    """Verify that the user's feed subscription token is valid."""
    import hmac
    return hmac.compare_digest(get_calendar_token(user_id), token)


# ─── Role Decorators ─────────────────────────────────────────────────────────

def admin_required(f):
    """Decorator: requires the current user to be an admin."""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin():
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('learn_landing'))
        return f(*args, **kwargs)
    return decorated


def student_required(f):
    """Decorator: requires the current user to be a student."""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if current_user.role != 'student':
            flash('Access denied. Student access only.', 'error')
            return redirect(url_for('learn_landing'))
        return f(*args, **kwargs)
    return decorated


# ─── Template Context ────────────────────────────────────────────────────────

@app.context_processor
def inject_now():
    """Make current datetime and calendar helper available in all templates."""
    return {
        'now': datetime.now(),
        'get_calendar_token': get_calendar_token
    }


# ─── Database Migration (add new tables to existing DB safely) ───────────────

def migrate_db():
    """Create new tables if they don't exist. Safe to call on existing DB."""
    conn = get_db()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS route_enrollments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        route_name TEXT NOT NULL CHECK(route_name IN ('Research', 'Policy', 'Business', 'Diplomacy', 'Environment', 'Community')),
        current_phase TEXT NOT NULL DEFAULT 'Foundations' CHECK(current_phase IN ('Foundations', 'Deep Dive', 'Capstone')),
        current_week INTEGER NOT NULL DEFAULT 1,
        start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
        UNIQUE(student_id, route_name)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS capstone_milestones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        route_enrollment_id INTEGER NOT NULL,
        draft_submitted_at TIMESTAMP,
        feedback_received_at TIMESTAMP,
        revised_draft_at TIMESTAMP,
        published_at TIMESTAMP,
        project_title TEXT,
        notes TEXT,
        FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (route_enrollment_id) REFERENCES route_enrollments(id) ON DELETE CASCADE,
        UNIQUE(student_id, route_enrollment_id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS mentor_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        session_date TIMESTAMP NOT NULL,
        duration_minutes INTEGER DEFAULT 60,
        notes TEXT,
        mentor_name TEXT,
        next_session_date TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS certificates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        module_id INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'issued')),
        issued_at TIMESTAMP,
        certificate_code TEXT,
        FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (module_id) REFERENCES modules(id) ON DELETE CASCADE,
        UNIQUE(student_id, module_id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS resources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        category TEXT NOT NULL DEFAULT 'Article' CHECK(category IN ('Article', 'Research Paper', 'Template', 'News', 'Video', 'Other')),
        url TEXT,
        file_filename TEXT,
        file_original_name TEXT,
        admin_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE SET NULL
    )''')

    # Indexes
    c.execute('CREATE INDEX IF NOT EXISTS idx_route_enrollments_student ON route_enrollments(student_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_capstone_student ON capstone_milestones(student_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_mentor_sessions_student ON mentor_sessions(student_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_certificates_student ON certificates(student_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_resources_category ON resources(category)')

    conn.commit()
    conn.close()

# Run migration at import time
migrate_db()


# ─── Public Routes ───────────────────────────────────────────────────────────

@app.route('/')
def index():
    """Main homepage of YSP Website."""
    return render_template('index.html')


@app.route('/learn')
def learn_landing():
    """Landing page with featured modules and stats for YSP Learns."""
    conn = get_db()
    modules = conn.execute(
        "SELECT * FROM modules ORDER BY created_at DESC LIMIT 6"
    ).fetchall()
    announcements = conn.execute(
        "SELECT a.*, u.full_name as author FROM announcements a "
        "LEFT JOIN users u ON a.admin_id = u.id "
        "ORDER BY a.created_at DESC LIMIT 3"
    ).fetchall()
    total_modules = conn.execute("SELECT COUNT(*) FROM modules").fetchone()[0]
    total_students = conn.execute("SELECT COUNT(*) FROM users WHERE role='student'").fetchone()[0]
    total_enrollments = conn.execute("SELECT COUNT(*) FROM enrollments").fetchone()[0]
    conn.close()
    return render_template('landing.html',
                           modules=modules,
                           announcements=announcements,
                           total_modules=total_modules,
                           total_students=total_students,
                           total_enrollments=total_enrollments)


@app.route('/catalog')
def catalog():
    """Public module catalog with search and category filters."""
    conn = get_db()
    programme = request.args.get('programme', '')
    cluster = request.args.get('cluster', '')
    search = request.args.get('search', '')

    query = "SELECT * FROM modules WHERE 1=1"
    params = []

    if programme:
        query += " AND programme_area = ?"
        params.append(programme)
    if cluster:
        query += " AND cluster = ?"
        params.append(cluster)
    if search:
        query += " AND (title LIKE ? OR description LIKE ?)"
        params.extend([f'%{search}%', f'%{search}%'])

    query += " ORDER BY created_at DESC"
    modules = conn.execute(query, params).fetchall()

    # Get distinct categories for filter dropdowns
    programmes = conn.execute(
        "SELECT DISTINCT programme_area FROM modules ORDER BY programme_area"
    ).fetchall()
    clusters = conn.execute(
        "SELECT DISTINCT cluster FROM modules ORDER BY cluster"
    ).fetchall()

    conn.close()
    return render_template('catalog.html',
                           modules=modules,
                           programmes=programmes,
                           clusters=clusters,
                           current_programme=programme,
                           current_cluster=cluster,
                           current_search=search)


@app.route('/module/<int:module_id>')
def module_detail(module_id):
    """Public module detail page with enrollment option."""
    conn = get_db()
    module = conn.execute(
        "SELECT m.*, u.full_name as instructor FROM modules m "
        "LEFT JOIN users u ON m.admin_id = u.id WHERE m.id = ?",
        (module_id,)
    ).fetchone()
    if not module:
        conn.close()
        abort(404)

    enrolled = False
    enrollment = None
    submission = None
    if current_user.is_authenticated and current_user.role == 'student':
        enrollment = conn.execute(
            "SELECT * FROM enrollments WHERE student_id = ? AND module_id = ?",
            (current_user.id, module_id)
        ).fetchone()
        enrolled = enrollment is not None
        submission = conn.execute(
            "SELECT * FROM submissions WHERE student_id = ? AND module_id = ? "
            "ORDER BY submitted_at DESC LIMIT 1",
            (current_user.id, module_id)
        ).fetchone()

    total_enrolled = conn.execute(
        "SELECT COUNT(*) FROM enrollments WHERE module_id = ?", (module_id,)
    ).fetchone()[0]

    conn.close()
    return render_template('module_detail.html',
                           module=module,
                           enrolled=enrolled,
                           enrollment=enrollment,
                           submission=submission,
                           total_enrolled=total_enrolled)


# ─── Auth Routes ─────────────────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login with email and password."""
    if current_user.is_authenticated:
        return redirect(url_for('student_dashboard') if current_user.role == 'student'
                        else url_for('admin_dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember') == 'on'

        if not email or not password:
            flash('Please enter both email and password.', 'error')
            return render_template('login.html')

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            user_obj = User(user['id'], user['full_name'], user['email'],
                           user['password_hash'], user['role'], user['created_at'])
            login_user(user_obj, remember=remember)
            flash(f'Welcome back, {user["full_name"]}!', 'success')

            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('student_dashboard') if user['role'] == 'student'
                            else url_for('admin_dashboard'))
        else:
            flash('Invalid email or password. Please try again.', 'error')

    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Student registration."""
    if current_user.is_authenticated:
        return redirect(url_for('learn_landing'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        # Validation
        errors = []
        if not full_name or len(full_name) < 2:
            errors.append('Full name must be at least 2 characters.')
        if not email or '@' not in email:
            errors.append('Please enter a valid email address.')
        if len(password) < 6:
            errors.append('Password must be at least 6 characters.')
        if password != confirm:
            errors.append('Passwords do not match.')

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('signup.html', full_name=full_name, email=email)

        conn = get_db()
        existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            conn.close()
            flash('An account with this email already exists.', 'error')
            return render_template('signup.html', full_name=full_name, email=email)

        password_hash = generate_password_hash(password, method='pbkdf2:sha256')
        conn.execute(
            "INSERT INTO users (full_name, email, password_hash, role) VALUES (?, ?, ?, 'student')",
            (full_name, email, password_hash)
        )
        conn.commit()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        user_obj = User(user['id'], user['full_name'], user['email'],
                       user['password_hash'], user['role'], user['created_at'])
        login_user(user_obj)
        flash('Account created successfully! Welcome to YSP Learns.', 'success')
        return redirect(url_for('student_dashboard'))

    return render_template('signup.html')


@app.route('/logout')
@login_required
def logout():
    """Log out the current user."""
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('learn_landing'))


# ─── Student Routes ──────────────────────────────────────────────────────────

@app.route('/enroll/<int:module_id>', methods=['POST'])
@student_required
def enroll(module_id):
    """Enroll current student in a module."""
    conn = get_db()
    module = conn.execute("SELECT * FROM modules WHERE id = ?", (module_id,)).fetchone()
    if not module:
        conn.close()
        abort(404)

    existing = conn.execute(
        "SELECT * FROM enrollments WHERE student_id = ? AND module_id = ?",
        (current_user.id, module_id)
    ).fetchone()

    if existing:
        flash('You are already enrolled in this module.', 'info')
    else:
        conn.execute(
            "INSERT INTO enrollments (student_id, module_id) VALUES (?, ?)",
            (current_user.id, module_id)
        )
        conn.commit()
        flash(f'Successfully enrolled in "{module["title"]}"!', 'success')

    conn.close()
    return redirect(url_for('module_detail', module_id=module_id))


@app.route('/student/dashboard')
@student_required
def student_dashboard():
    """Student dashboard: enrolled modules, announcements, stats, progress overview."""
    conn = get_db()
    enrollments = conn.execute(
        "SELECT e.*, m.title, m.programme_area, m.cluster, m.delivery_mode, m.description "
        "FROM enrollments e "
        "JOIN modules m ON e.module_id = m.id "
        "WHERE e.student_id = ? ORDER BY e.enrolled_at DESC",
        (current_user.id,)
    ).fetchall()

    announcements = conn.execute(
        "SELECT a.*, u.full_name as author FROM announcements a "
        "LEFT JOIN users u ON a.admin_id = u.id "
        "ORDER BY a.created_at DESC LIMIT 5"
    ).fetchall()

    submissions_count = conn.execute(
        "SELECT COUNT(*) FROM submissions WHERE student_id = ?",
        (current_user.id,)
    ).fetchone()[0]

    # New: Route enrollment summary
    route_enrollment = conn.execute(
        "SELECT * FROM route_enrollments WHERE student_id = ?",
        (current_user.id,)
    ).fetchone()

    # New: Certificate counts
    certs_issued = conn.execute(
        "SELECT COUNT(*) FROM certificates WHERE student_id = ? AND status = 'issued'",
        (current_user.id,)
    ).fetchone()[0]
    certs_pending = conn.execute(
        "SELECT COUNT(*) FROM certificates WHERE student_id = ? AND status = 'pending'",
        (current_user.id,)
    ).fetchone()[0]

    # New: Upcoming mentor session
    next_mentor = conn.execute(
        "SELECT * FROM mentor_sessions WHERE student_id = ? AND next_session_date IS NOT NULL "
        "ORDER BY next_session_date DESC LIMIT 1",
        (current_user.id,)
    ).fetchone()

    # New: Mentor sessions count
    mentor_count = conn.execute(
        "SELECT COUNT(*) FROM mentor_sessions WHERE student_id = ?",
        (current_user.id,)
    ).fetchone()[0]

    conn.close()
    return render_template('student/dashboard.html',
                           enrollments=enrollments,
                           announcements=announcements,
                           submissions_count=submissions_count,
                           route_enrollment=route_enrollment,
                           certs_issued=certs_issued,
                           certs_pending=certs_pending,
                           next_mentor=next_mentor,
                           mentor_count=mentor_count)


@app.route('/student/module/<int:module_id>', methods=['GET', 'POST'])
@student_required
def student_module(module_id):
    """Enrolled module view: content, materials, assignment submission."""
    conn = get_db()

    # Verify enrollment
    enrollment = conn.execute(
        "SELECT * FROM enrollments WHERE student_id = ? AND module_id = ?",
        (current_user.id, module_id)
    ).fetchone()
    if not enrollment:
        conn.close()
        flash('You must enroll in this module first.', 'error')
        return redirect(url_for('module_detail', module_id=module_id))

    module = conn.execute(
        "SELECT m.*, u.full_name as instructor FROM modules m "
        "LEFT JOIN users u ON m.admin_id = u.id WHERE m.id = ?",
        (module_id,)
    ).fetchone()
    if not module:
        conn.close()
        abort(404)

    # Handle assignment submission
    if request.method == 'POST':
        text_response = request.form.get('text_response', '').strip()
        file = request.files.get('submission_file')

        if not text_response and (not file or not file.filename):
            flash('Please provide a text response or upload a file.', 'error')
        else:
            file_filename, file_original = save_upload(file) if file and file.filename else (None, None)

            conn.execute(
                "INSERT INTO submissions (student_id, module_id, text_response, file_filename, file_original_name) "
                "VALUES (?, ?, ?, ?, ?)",
                (current_user.id, module_id, text_response or None, file_filename, file_original)
            )
            # Update enrollment progress
            conn.execute(
                "UPDATE enrollments SET progress = 'completed' WHERE student_id = ? AND module_id = ?",
                (current_user.id, module_id)
            )
            conn.commit()
            flash('Assignment submitted successfully!', 'success')
            return redirect(url_for('student_module', module_id=module_id))

    # Get previous submissions
    submissions = conn.execute(
        "SELECT * FROM submissions WHERE student_id = ? AND module_id = ? "
        "ORDER BY submitted_at DESC",
        (current_user.id, module_id)
    ).fetchall()

    conn.close()
    return render_template('student/module.html',
                           module=module,
                           enrollment=enrollment,
                           submissions=submissions)


@app.route('/student/calendar')
@student_required
def student_calendar():
    """Render student calendar page."""
    from datetime import timedelta
    conn = get_db()
    
    # Query all student's enrollments and their latest submissions
    rows = conn.execute(
        "SELECT e.*, m.title, m.description, m.programme_area, m.delivery_mode, m.cluster, MAX(s.submitted_at) as submitted_at "
        "FROM enrollments e "
        "JOIN modules m ON e.module_id = m.id "
        "LEFT JOIN submissions s ON e.student_id = s.student_id AND e.module_id = s.module_id "
        "WHERE e.student_id = ? "
        "GROUP BY e.id "
        "ORDER BY e.enrolled_at DESC",
        (current_user.id,)
    ).fetchall()
    
    # Also fetch standard announcements to show platform events in the calendar!
    announcements = conn.execute(
        "SELECT * FROM announcements ORDER BY created_at DESC LIMIT 10"
    ).fetchall()
    
    events = []
    
    # Process enrollment events
    for row in rows:
        title = row['title']
        enrolled_dt = datetime.strptime(row['enrolled_at'][:19], "%Y-%m-%d %H:%M:%S")
        
        # 1. Started event
        events.append({
            'id': f"start_{row['module_id']}",
            'title': f"🌱 Started: {title}",
            'date': enrolled_dt.strftime('%Y-%m-%d'),
            'type': 'start',
            'desc': f"You enrolled in the module '{title}'."
        })
        
        # 2. Target deadline (30 days from enrollment)
        target_dt = enrolled_dt + timedelta(days=30)
        events.append({
            'id': f"target_{row['module_id']}",
            'title': f"⏰ Target: {title}",
            'date': target_dt.strftime('%Y-%m-%d'),
            'type': 'target',
            'desc': f"Target date to complete '{title}' (30 days limit)."
        })
        
        # 3. Completed event (if completed)
        if row['progress'] == 'completed' and row['submitted_at']:
            sub_dt = datetime.strptime(row['submitted_at'][:19], "%Y-%m-%d %H:%M:%S")
            events.append({
                'id': f"completed_{row['module_id']}",
                'title': f"✅ Completed: {title}",
                'date': sub_dt.strftime('%Y-%m-%d'),
                'type': 'completed',
                'desc': f"You submitted the assignment and completed '{title}'!"
            })
            
    # Process announcements as platform events
    for ann in announcements:
        ann_dt = datetime.strptime(ann['created_at'][:19], "%Y-%m-%d %H:%M:%S")
        events.append({
            'id': f"ann_{ann['id']}",
            'title': f"📢 Note: {ann['title']}",
            'date': ann_dt.strftime('%Y-%m-%d'),
            'type': 'announcement',
            'desc': ann['content'][:150] + ('...' if len(ann['content']) > 150 else '')
        })

    # Get sidebar list of enrollments (needed for sidebar rendering in dashboard layout)
    enrollments_sidebar = conn.execute(
        "SELECT e.*, m.title FROM enrollments e JOIN modules m ON e.module_id = m.id "
        "WHERE e.student_id = ? ORDER BY e.enrolled_at DESC",
        (current_user.id,)
    ).fetchall()
    
    conn.close()
    
    return render_template(
        'student/calendar.html',
        events=events,
        enrollments=enrollments_sidebar
    )


@app.route('/learn/calendar/feed/<int:user_id>/<token>.ics')
def calendar_feed(user_id, token):
    """Serve dynamically generated iCalendar (RFC 5545) subscription feed for a user."""
    from flask import Response
    from datetime import timedelta
    
    # Verify the token
    if not verify_calendar_token(user_id, token):
        abort(403)
        
    conn = get_db()
    
    # Verify user exists
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        conn.close()
        abort(404)
        
    # Query student's enrollments and submissions
    rows = conn.execute(
        "SELECT e.*, m.title, m.description, m.programme_area, MAX(s.submitted_at) as submitted_at "
        "FROM enrollments e "
        "JOIN modules m ON e.module_id = m.id "
        "LEFT JOIN submissions s ON e.student_id = s.student_id AND e.module_id = s.module_id "
        "WHERE e.student_id = ? "
        "GROUP BY e.id",
        (user_id,)
    ).fetchall()
    
    conn.close()
    
    # Construct iCalendar content
    ical_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//YSP Learns//Calendar Feed//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:YSP Learns - {user['full_name']}",
        "X-WR-TIMEZONE:UTC"
    ]
    
    now_str = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    
    for row in rows:
        title = row['title']
        clean_title = title.replace(",", "\\,").replace(";", "\\;")
        enrolled_dt = datetime.strptime(row['enrolled_at'][:19], "%Y-%m-%d %H:%M:%S")
        
        # 1. Started event
        start_date_str = enrolled_dt.strftime('%Y%m%d')
        ical_lines.extend([
            "BEGIN:VEVENT",
            f"UID:ysp_start_{user_id}_{row['module_id']}",
            f"DTSTAMP:{now_str}",
            f"DTSTART;VALUE=DATE:{start_date_str}",
            f"SUMMARY:Started: {clean_title}",
            f"DESCRIPTION:You enrolled in the module '{clean_title}' in {row['programme_area']}.",
            "STATUS:CONFIRMED",
            "END:VEVENT"
        ])
        
        # 2. Target deadline
        target_dt = enrolled_dt + timedelta(days=30)
        target_date_str = target_dt.strftime('%Y%m%d')
        ical_lines.extend([
            "BEGIN:VEVENT",
            f"UID:ysp_target_{user_id}_{row['module_id']}",
            f"DTSTAMP:{now_str}",
            f"DTSTART;VALUE=DATE:{target_date_str}",
            f"SUMMARY:Target: {clean_title}",
            f"DESCRIPTION:Target completion date for the module '{clean_title}'. Please submit your assignment.",
            "STATUS:CONFIRMED",
            "END:VEVENT"
        ])
        
        # 3. Completed event (if completed)
        if row['progress'] == 'completed' and row['submitted_at']:
            sub_dt = datetime.strptime(row['submitted_at'][:19], "%Y-%m-%d %H:%M:%S")
            sub_date_str = sub_dt.strftime('%Y%m%d')
            ical_lines.extend([
                "BEGIN:VEVENT",
                f"UID:ysp_comp_{user_id}_{row['module_id']}",
                f"DTSTAMP:{now_str}",
                f"DTSTART;VALUE=DATE:{sub_date_str}",
                f"SUMMARY:Completed: {clean_title}",
                f"DESCRIPTION:You completed and submitted the assignment for '{clean_title}'. Great job!",
                "STATUS:CONFIRMED",
                "END:VEVENT"
            ])
            
    ical_lines.append("END:VCALENDAR")
    ical_content = "\r\n".join(ical_lines) + "\r\n"
    
    return Response(
        ical_content,
        mimetype='text/calendar',
        headers={
            'Content-Disposition': f'attachment; filename=ysp_learns_calendar_{user_id}.ics',
            'Cache-Control': 'no-cache, no-store, must-revalidate'
        }
    )


# ─── Student Resources Route ────────────────────────────────────────────────

@app.route('/student/resources')
@student_required
def student_resources():
    """Browse curated resources: articles, papers, templates, news, videos."""
    conn = get_db()
    category = request.args.get('category', '')
    search = request.args.get('search', '')

    query = "SELECT r.*, u.full_name as author FROM resources r LEFT JOIN users u ON r.admin_id = u.id WHERE 1=1"
    params = []

    if category:
        query += " AND r.category = ?"
        params.append(category)
    if search:
        query += " AND (r.title LIKE ? OR r.description LIKE ?)"
        params.extend([f'%{search}%', f'%{search}%'])

    query += " ORDER BY r.created_at DESC"
    resources = conn.execute(query, params).fetchall()

    categories = conn.execute(
        "SELECT DISTINCT category FROM resources ORDER BY category"
    ).fetchall()

    # Sidebar enrollments
    enrollments = conn.execute(
        "SELECT e.*, m.title FROM enrollments e JOIN modules m ON e.module_id = m.id "
        "WHERE e.student_id = ? ORDER BY e.enrolled_at DESC",
        (current_user.id,)
    ).fetchall()

    conn.close()
    return render_template('student/resources.html',
                           resources=resources,
                           categories=categories,
                           current_category=category,
                           current_search=search,
                           enrollments=enrollments)


# ─── Student Progress Route (Route, Capstone, Mentoring, Certificates) ──────

@app.route('/student/progress')
@student_required
def student_progress():
    """Student progress hub: route enrollment, capstone tracker, mentor log, certificates."""
    conn = get_db()

    # Route enrollment
    route_enrollment = conn.execute(
        "SELECT * FROM route_enrollments WHERE student_id = ?",
        (current_user.id,)
    ).fetchone()

    # Capstone milestone
    capstone = None
    if route_enrollment:
        capstone = conn.execute(
            "SELECT * FROM capstone_milestones WHERE student_id = ? AND route_enrollment_id = ?",
            (current_user.id, route_enrollment['id'])
        ).fetchone()

    # Mentor sessions
    mentor_sessions = conn.execute(
        "SELECT * FROM mentor_sessions WHERE student_id = ? ORDER BY session_date DESC",
        (current_user.id,)
    ).fetchall()

    # Certificates
    certificates = conn.execute(
        "SELECT c.*, m.title as module_title, m.programme_area "
        "FROM certificates c JOIN modules m ON c.module_id = m.id "
        "WHERE c.student_id = ? ORDER BY c.issued_at DESC NULLS LAST",
        (current_user.id,)
    ).fetchall()

    # Sidebar enrollments
    enrollments = conn.execute(
        "SELECT e.*, m.title FROM enrollments e JOIN modules m ON e.module_id = m.id "
        "WHERE e.student_id = ? ORDER BY e.enrolled_at DESC",
        (current_user.id,)
    ).fetchall()

    conn.close()
    return render_template('student/progress.html',
                           route_enrollment=route_enrollment,
                           capstone=capstone,
                           mentor_sessions=mentor_sessions,
                           certificates=certificates,
                           enrollments=enrollments)


# ─── Student Mentor Session Log (CRUD) ──────────────────────────────────────

@app.route('/student/mentor-session/add', methods=['POST'])
@student_required
def add_mentor_session():
    """Log a new mentor session."""
    session_date = request.form.get('session_date', '').strip()
    duration = request.form.get('duration_minutes', '60').strip()
    notes = request.form.get('notes', '').strip()
    mentor_name = request.form.get('mentor_name', '').strip()
    next_session = request.form.get('next_session_date', '').strip()

    if not session_date or not mentor_name:
        flash('Session date and mentor name are required.', 'error')
        return redirect(url_for('student_progress'))

    conn = get_db()
    conn.execute(
        "INSERT INTO mentor_sessions (student_id, session_date, duration_minutes, notes, mentor_name, next_session_date) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (current_user.id, session_date, int(duration) if duration else 60,
         notes or None, mentor_name, next_session or None)
    )
    conn.commit()
    conn.close()
    flash('Mentor session logged successfully!', 'success')
    return redirect(url_for('student_progress'))


# ─── Admin Resources CRUD ───────────────────────────────────────────────────

@app.route('/admin/resources', methods=['GET', 'POST'])
@admin_required
def admin_resources():
    """Manage resources: create and list."""
    conn = get_db()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', 'Article')
        url_link = request.form.get('url', '').strip()
        file = request.files.get('resource_file')

        if not title:
            flash('Title is required.', 'error')
        else:
            file_filename, file_original = save_upload(file) if file and file.filename else (None, None)
            conn.execute(
                "INSERT INTO resources (title, description, category, url, file_filename, file_original_name, admin_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (title, description, category, url_link or None, file_filename, file_original, current_user.id)
            )
            conn.commit()
            flash(f'Resource "{title}" added successfully!', 'success')
            return redirect(url_for('admin_resources'))

    resources = conn.execute(
        "SELECT r.*, u.full_name as author FROM resources r "
        "LEFT JOIN users u ON r.admin_id = u.id "
        "ORDER BY r.created_at DESC"
    ).fetchall()
    conn.close()
    return render_template('admin/resources.html', resources=resources)


@app.route('/admin/delete-resource/<int:res_id>', methods=['POST'])
@admin_required
def delete_resource(res_id):
    """Delete a resource."""
    conn = get_db()
    resource = conn.execute("SELECT * FROM resources WHERE id = ?", (res_id,)).fetchone()
    if resource and resource['file_filename']:
        fpath = os.path.join(UPLOAD_DIR, resource['file_filename'])
        if os.path.exists(fpath):
            os.remove(fpath)
    conn.execute("DELETE FROM resources WHERE id = ?", (res_id,))
    conn.commit()
    conn.close()
    flash('Resource deleted.', 'success')
    return redirect(url_for('admin_resources'))


# ─── Admin Certificates Management ──────────────────────────────────────────

@app.route('/admin/issue-certificate', methods=['POST'])
@admin_required
def issue_certificate():
    """Issue a certificate to a student for a completed module."""
    student_id = request.form.get('student_id', type=int)
    module_id = request.form.get('module_id', type=int)

    if not student_id or not module_id:
        flash('Student ID and Module ID are required.', 'error')
        return redirect(url_for('admin_submissions'))

    conn = get_db()
    # Generate certificate code
    cert_code = f"YSP-{datetime.now().year}-{uuid.uuid4().hex[:6].upper()}"

    existing = conn.execute(
        "SELECT * FROM certificates WHERE student_id = ? AND module_id = ?",
        (student_id, module_id)
    ).fetchone()

    if existing:
        conn.execute(
            "UPDATE certificates SET status = 'issued', issued_at = ?, certificate_code = ? "
            "WHERE student_id = ? AND module_id = ?",
            (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), cert_code, student_id, module_id)
        )
    else:
        conn.execute(
            "INSERT INTO certificates (student_id, module_id, status, issued_at, certificate_code) "
            "VALUES (?, ?, 'issued', ?, ?)",
            (student_id, module_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), cert_code)
        )

    conn.commit()
    conn.close()
    flash(f'Certificate {cert_code} issued successfully!', 'success')
    return redirect(url_for('admin_submissions'))


# ─── Admin Routes ────────────────────────────────────────────────────────────

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """Admin dashboard with overview stats."""
    conn = get_db()
    stats = {
        'students': conn.execute("SELECT COUNT(*) FROM users WHERE role='student'").fetchone()[0],
        'modules': conn.execute("SELECT COUNT(*) FROM modules").fetchone()[0],
        'submissions': conn.execute("SELECT COUNT(*) FROM submissions").fetchone()[0],
        'enrollments': conn.execute("SELECT COUNT(*) FROM enrollments").fetchone()[0],
        'announcements': conn.execute("SELECT COUNT(*) FROM announcements").fetchone()[0],
    }
    recent_submissions = conn.execute(
        "SELECT s.*, u.full_name as student_name, m.title as module_title "
        "FROM submissions s "
        "JOIN users u ON s.student_id = u.id "
        "JOIN modules m ON s.module_id = m.id "
        "ORDER BY s.submitted_at DESC LIMIT 5"
    ).fetchall()
    recent_enrollments = conn.execute(
        "SELECT e.*, u.full_name as student_name, m.title as module_title "
        "FROM enrollments e "
        "JOIN users u ON e.student_id = u.id "
        "JOIN modules m ON e.module_id = m.id "
        "ORDER BY e.enrolled_at DESC LIMIT 5"
    ).fetchall()
    conn.close()
    return render_template('admin/dashboard.html',
                           stats=stats,
                           recent_submissions=recent_submissions,
                           recent_enrollments=recent_enrollments)


@app.route('/admin/modules')
@admin_required
def admin_modules():
    """List all modules for admin management."""
    conn = get_db()
    modules = conn.execute(
        "SELECT m.*, u.full_name as instructor, "
        "(SELECT COUNT(*) FROM enrollments WHERE module_id = m.id) as enrolled_count "
        "FROM modules m LEFT JOIN users u ON m.admin_id = u.id "
        "ORDER BY m.created_at DESC"
    ).fetchall()
    conn.close()
    return render_template('admin/modules.html', modules=modules)


@app.route('/admin/create-module', methods=['GET', 'POST'])
@admin_required
def create_module():
    """Create a new learning module."""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        programme_area = request.form.get('programme_area', '').strip()
        cluster = request.form.get('cluster', '').strip()
        delivery_mode = request.form.get('delivery_mode', 'Self-paced')
        file = request.files.get('material')

        if not title or not programme_area or not cluster:
            flash('Title, Programme Area, and Cluster are required.', 'error')
            return render_template('admin/create_module.html')

        file_filename, file_original = save_upload(file) if file and file.filename else (None, None)

        conn = get_db()
        conn.execute(
            "INSERT INTO modules (title, description, programme_area, cluster, delivery_mode, "
            "material_filename, material_original_name, admin_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (title, description, programme_area, cluster, delivery_mode,
             file_filename, file_original, current_user.id)
        )
        conn.commit()
        conn.close()
        flash(f'Module "{title}" created successfully!', 'success')
        return redirect(url_for('admin_modules'))

    return render_template('admin/create_module.html')


@app.route('/admin/edit-module/<int:module_id>', methods=['GET', 'POST'])
@admin_required
def edit_module(module_id):
    """Edit an existing module."""
    conn = get_db()
    module = conn.execute("SELECT * FROM modules WHERE id = ?", (module_id,)).fetchone()
    if not module:
        conn.close()
        abort(404)

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        programme_area = request.form.get('programme_area', '').strip()
        cluster = request.form.get('cluster', '').strip()
        delivery_mode = request.form.get('delivery_mode', 'Self-paced')
        file = request.files.get('material')

        if not title or not programme_area or not cluster:
            flash('Title, Programme Area, and Cluster are required.', 'error')
            return render_template('admin/create_module.html', module=module, editing=True)

        file_filename = module['material_filename']
        file_original = module['material_original_name']
        if file and file.filename:
            # Delete old file if exists
            if module['material_filename']:
                old_path = os.path.join(UPLOAD_DIR, module['material_filename'])
                if os.path.exists(old_path):
                    os.remove(old_path)
            file_filename, file_original = save_upload(file)

        conn.execute(
            "UPDATE modules SET title=?, description=?, programme_area=?, cluster=?, "
            "delivery_mode=?, material_filename=?, material_original_name=? WHERE id=?",
            (title, description, programme_area, cluster, delivery_mode,
             file_filename, file_original, module_id)
        )
        conn.commit()
        conn.close()
        flash(f'Module "{title}" updated successfully!', 'success')
        return redirect(url_for('admin_modules'))

    conn.close()
    return render_template('admin/create_module.html', module=module, editing=True)


@app.route('/admin/delete-module/<int:module_id>', methods=['POST'])
@admin_required
def delete_module(module_id):
    """Delete a module and its associated enrollments/submissions."""
    conn = get_db()
    module = conn.execute("SELECT * FROM modules WHERE id = ?", (module_id,)).fetchone()
    if module:
        # Delete material file
        if module['material_filename']:
            fpath = os.path.join(UPLOAD_DIR, module['material_filename'])
            if os.path.exists(fpath):
                os.remove(fpath)
        conn.execute("DELETE FROM modules WHERE id = ?", (module_id,))
        conn.commit()
        flash('Module deleted successfully.', 'success')
    conn.close()
    return redirect(url_for('admin_modules'))


@app.route('/admin/announcements', methods=['GET', 'POST'])
@admin_required
def admin_announcements():
    """Create and manage announcements."""
    conn = get_db()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()

        if not title or not content:
            flash('Both title and content are required.', 'error')
        else:
            conn.execute(
                "INSERT INTO announcements (title, content, admin_id) VALUES (?, ?, ?)",
                (title, content, current_user.id)
            )
            conn.commit()
            flash('Announcement posted successfully!', 'success')
            return redirect(url_for('admin_announcements'))

    announcements = conn.execute(
        "SELECT a.*, u.full_name as author FROM announcements a "
        "LEFT JOIN users u ON a.admin_id = u.id "
        "ORDER BY a.created_at DESC"
    ).fetchall()
    conn.close()
    return render_template('admin/announcements.html', announcements=announcements)


@app.route('/admin/delete-announcement/<int:ann_id>', methods=['POST'])
@admin_required
def delete_announcement(ann_id):
    """Delete an announcement."""
    conn = get_db()
    conn.execute("DELETE FROM announcements WHERE id = ?", (ann_id,))
    conn.commit()
    conn.close()
    flash('Announcement deleted.', 'success')
    return redirect(url_for('admin_announcements'))


@app.route('/admin/submissions')
@admin_required
def admin_submissions():
    """View all student submissions."""
    conn = get_db()
    submissions = conn.execute(
        "SELECT s.*, u.full_name as student_name, u.email as student_email, "
        "m.title as module_title, m.programme_area "
        "FROM submissions s "
        "JOIN users u ON s.student_id = u.id "
        "JOIN modules m ON s.module_id = m.id "
        "ORDER BY s.submitted_at DESC"
    ).fetchall()
    conn.close()
    return render_template('admin/submissions.html', submissions=submissions)


# ─── Chatbot API ─────────────────────────────────────────────────────────────

@app.route('/api/chat', methods=['POST'])
def api_chat():
    """Chat endpoint communicating with Gemini API."""
    import json
    import urllib.request
    import urllib.error

    data = request.get_json() or {}
    messages = data.get('messages', [])

    if not messages:
        return jsonify({'status': 'error', 'message': 'No messages provided'}), 400

    # Map message roles to Gemini's expected roles ('user', 'model')
    gemini_contents = []
    for msg in messages:
        role = msg.get('role', 'user')
        content = msg.get('content', '')
        gemini_role = 'model' if role in ('assistant', 'model') else 'user'
        gemini_contents.append({
            'role': gemini_role,
            'parts': [{'text': content}]
        })

    # Gemini requires the conversation to start with a 'user' turn.
    # Discard any initial 'model' turns (like the welcome message).
    while gemini_contents and gemini_contents[0]['role'] == 'model':
        gemini_contents.pop(0)

    # Helper for generating Demo Mode fallback responses
    def get_demo_response(messages_list):
        last_msg = messages_list[-1].get('content', '') if messages_list else ''
        last_msg_lower = last_msg.lower()

        if any(w in last_msg_lower for w in ['program', 'route', 'research', 'policy', 'business', 'diplomacy', 'environment', 'community']):
            return "We offer 6 specialized Programme Routes: **Research, Policy, Business, Diplomacy, Environment, and Community**. Each route is designed to help fellows develop publishable capstones or real-world policy briefs. 🌿 Which track interests you most?"
        elif any(w in last_msg_lower for w in ['learn', 'module', 'portal', 'course', 'lms']):
            return "YSP Learns is our dynamic learning platform where you can sign up for self-paced modules in policy, research, climate, and more! Click on the **YSP Learns** menu link at the top to check out the module catalog! 📚"
        elif any(w in last_msg_lower for w in ['join', 'apply', 'volunteer', 'hiring', 'intake']):
            return "You can apply for our next intake by clicking the **Apply for the next intake** button on the homepage, or contact us directly. We'd love to have you onboard! 🌱"
        elif any(w in last_msg_lower for w in ['who are you', 'your name', 'mascot', 'verdi']):
            return "I'm **Verdi**, the official mascot and AI assistant for Youth for Sustainable Policy! 🌍💚 I represent curiosity, empathy, and evidence-based action."
        else:
            return (
                f"Hi! I'm Verdi, your friendly YSP mascot. 🌿\n\n"
                f"I'm here to help answer questions about Youth for Sustainable Policy (YSP) and YSP Learns modules. "
                f"Feel free to ask me about our programmes, how to apply, or how YSP Learns works!"
            )

    # Map message roles to Gemini's expected roles ('user', 'model')
    gemini_contents = []
    for msg in messages:
        role = msg.get('role', 'user')
        content = msg.get('content', '')
        gemini_role = 'model' if role in ('assistant', 'model') else 'user'
        gemini_contents.append({
            'role': gemini_role,
            'parts': [{'text': content}]
        })

    # Gemini requires the conversation to start with a 'user' turn.
    # Discard any initial 'model' turns (like the welcome message).
    while gemini_contents and gemini_contents[0]['role'] == 'model':
        gemini_contents.pop(0)

    api_key = os.environ.get('GEMINI_API_KEY') or app.config.get('GEMINI_API_KEY')
    if not api_key:
        return jsonify({
            'status': 'success',
            'message': get_demo_response(messages),
            'demo': True
        })

    # Prepare request payload for Gemini 2.5 Flash
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": gemini_contents,
        "systemInstruction": {
            "parts": [
                {
                    "text": (
                        "You are Verdi, the official AI mascot and assistant for Youth for Sustainable Policy (YSP). "
                        "Your tone is warm, curious, encouraging, intellectually rigorous, and helpful. "
                        "You represent youth leadership in sustainability and policy. "
                        "When answering questions about YSP, explain that YSP is a global youth-led initiative that empowers "
                        "the next generation to engage with global challenges through research, storytelling, and policy dialogue. "
                        "Recommend our 'YSP Learns' portal for dynamic learning modules. "
                        "Keep your responses concise, engaging, and friendly. Use green emojis like 🌿, 🌱, 🍀, 🌲 where appropriate."
                    )
                }
            ]
        },
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 800
        }
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            candidates = res_data.get('candidates', [])
            if candidates:
                content_parts = candidates[0].get('content', {}).get('parts', [])
                if content_parts:
                    reply_text = content_parts[0].get('text', '')
                    return jsonify({
                        'status': 'success',
                        'message': reply_text
                    })
            print("Gemini API returned empty response. Falling back to Demo Mode.")
            return jsonify({
                'status': 'success',
                'message': get_demo_response(messages),
                'demo': True
            })
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode('utf-8', errors='ignore')
        print(f"Gemini API HTTPError {e.code}: {error_msg}. Falling back to Demo Mode.")
        return jsonify({
            'status': 'success',
            'message': get_demo_response(messages) + "\n\n*(Note: I'm currently running in Demo Mode fallback due to temporary Gemini rate limiting or quota limits.)*",
            'demo': True
        })
    except Exception as e:
        print(f"Gemini API Exception: {e}. Falling back to Demo Mode.")
        return jsonify({
            'status': 'success',
            'message': get_demo_response(messages) + "\n\n*(Note: I'm currently running in Demo Mode fallback due to a temporary connection issue.)*",
            'demo': True
        })


# ─── File Serving ────────────────────────────────────────────────────────────

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files (publicly accessible)."""
    return send_from_directory(UPLOAD_DIR, filename)


@app.route('/assets/<path:filename>')
def serve_assets(filename):
    """Serve main website assets (images, team pictures, etc.)."""
    return send_from_directory(os.path.join(BASE_DIR, 'assets'), filename)


# ─── Generic Page Serving ───────────────────────────────────────────────────

@app.route('/<page>')
@app.route('/<page>.html')
def serve_html_page(page):
    """Serve main website static pages from templates folder."""
    if '..' in page or page.startswith('/') or page.startswith('.'):
        abort(404)
    template_name = f"{page}.html"
    if os.path.exists(os.path.join(app.template_folder, template_name)):
        return render_template(template_name)
    abort(404)


# ─── Error Handlers ──────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return render_template('base.html', error_code=404, error_message='Page not found'), 404

@app.errorhandler(413)
def too_large(e):
    flash('File too large. Maximum upload size is 16 MB.', 'error')
    return redirect(request.referrer or url_for('learn_landing'))

@app.errorhandler(500)
def server_error(e):
    return render_template('base.html', error_code=500, error_message='Internal server error'), 500


# ─── Run ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    # Auto-initialize DB if it doesn't exist
    if not os.path.exists(DB_PATH):
        print("[!] Database not found. Running init_db.py...")
        import subprocess
        subprocess.run(['python', os.path.join(BASE_DIR, 'init_db.py')], cwd=BASE_DIR)

    app.run(host='0.0.0.0', port=5000, debug=True)
