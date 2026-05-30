"""
app.py — Main Flask application for BibLabU Learning Management System.

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
    flash, send_from_directory, abort, session
)
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# ─── Configuration ───────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'database.db')
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')
ALLOWED_EXTENSIONS = {
    'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx',
    'txt', 'zip', 'rar', 'png', 'jpg', 'jpeg', 'gif', 'mp4', 'py', 'java', 'c', 'cpp'
}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(BASE_DIR), 'templates'),
    static_folder=os.path.join(os.path.dirname(BASE_DIR), 'static')
)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'biblabu-lms-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

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
    """Create a database connection with WAL mode for concurrency."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
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


# ─── Role Decorators ─────────────────────────────────────────────────────────

def admin_required(f):
    """Decorator: requires the current user to be an admin."""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin():
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated


def student_required(f):
    """Decorator: requires the current user to be a student."""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if current_user.role != 'student':
            flash('Access denied. Student access only.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated


# ─── Template Context ────────────────────────────────────────────────────────

@app.context_processor
def inject_now():
    """Make current datetime available in all templates."""
    return {'now': datetime.now()}


# ─── Public Routes ───────────────────────────────────────────────────────────

@app.route('/')
def index():
    """Landing page with featured modules and stats."""
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
        return redirect(url_for('index'))

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
        flash('Account created successfully! Welcome to BibLabU.', 'success')
        return redirect(url_for('student_dashboard'))

    return render_template('signup.html')


@app.route('/logout')
@login_required
def logout():
    """Log out the current user."""
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))


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
    """Student dashboard: enrolled modules, announcements, stats."""
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

    conn.close()
    return render_template('student/dashboard.html',
                           enrollments=enrollments,
                           announcements=announcements,
                           submissions_count=submissions_count)


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


# ─── File Serving ────────────────────────────────────────────────────────────

@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    """Serve uploaded files (authenticated users only)."""
    return send_from_directory(UPLOAD_DIR, filename)


# ─── Error Handlers ──────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return render_template('base.html', error_code=404, error_message='Page not found'), 404

@app.errorhandler(413)
def too_large(e):
    flash('File too large. Maximum upload size is 16 MB.', 'error')
    return redirect(request.referrer or url_for('index'))

@app.errorhandler(500)
def server_error(e):
    return render_template('base.html', error_code=500, error_message='Internal server error'), 500


# ─── Run ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    # Auto-initialize DB if it doesn't exist
    if not os.path.exists(DB_PATH):
        print("[!] Database not found. Run 'python init_db.py' first.")
        print("    Attempting auto-initialization...")
        import subprocess
        subprocess.run(['python', os.path.join(BASE_DIR, 'init_db.py')], cwd=BASE_DIR)

    app.run(host='127.0.0.1', port=5000, debug=True)
