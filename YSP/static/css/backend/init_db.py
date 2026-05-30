"""
init_db.py — Database initialization and seeding for BibLabU LMS.

Creates all tables and seeds sample data including a default admin account,
sample modules across programme areas, and welcome announcements.

Usage:
    python init_db.py
"""

import sqlite3
import os
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')


def get_connection():
    """Create a new database connection with row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # Better concurrency for up to 50 users
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def create_tables(conn):
    """Create all required LMS tables."""
    cursor = conn.cursor()

    # Users table — stores both admins (instructors) and students
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'student' CHECK(role IN ('admin', 'student')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Modules — learning courses organized by programme area and cluster
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS modules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            programme_area TEXT NOT NULL,
            cluster TEXT NOT NULL,
            institution TEXT DEFAULT 'Biblabu Polytechnic',
            delivery_mode TEXT DEFAULT 'Self-paced' CHECK(delivery_mode IN ('Self-paced', 'Instructor-led', 'Blended')),
            material_filename TEXT,
            material_original_name TEXT,
            admin_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE SET NULL
        )
    ''')

    # Enrollments — tracks which students are enrolled in which modules
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            module_id INTEGER NOT NULL,
            enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            progress TEXT DEFAULT 'enrolled' CHECK(progress IN ('enrolled', 'in-progress', 'completed')),
            FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (module_id) REFERENCES modules(id) ON DELETE CASCADE,
            UNIQUE(student_id, module_id)
        )
    ''')

    # Announcements — platform-wide notices posted by admins
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            admin_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE SET NULL
        )
    ''')

    # Submissions — student assignment responses (text and/or file)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            module_id INTEGER NOT NULL,
            text_response TEXT,
            file_filename TEXT,
            file_original_name TEXT,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (module_id) REFERENCES modules(id) ON DELETE CASCADE
        )
    ''')

    # Create indexes for common queries
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_enrollments_student ON enrollments(student_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_enrollments_module ON enrollments(module_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_submissions_student ON submissions(student_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_submissions_module ON submissions(module_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_modules_programme ON modules(programme_area)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_modules_cluster ON modules(cluster)')

    conn.commit()
    print("[OK] Tables created successfully.")


def seed_data(conn):
    """Insert seed data: admin user, sample modules, and announcements."""
    cursor = conn.cursor()

    # Check if data already exists
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] > 0:
        print("[SKIP] Database already has data. Skipping seed.")
        return

    # ── Default Admin Account ──
    admin_hash = generate_password_hash('admin123', method='pbkdf2:sha256')
    cursor.execute(
        "INSERT INTO users (full_name, email, password_hash, role) VALUES (?, ?, ?, ?)",
        ('Admin Instructor', 'admin@biblabu.edu', admin_hash, 'admin')
    )
    admin_id = cursor.lastrowid
    print(f"[OK] Admin created: admin@biblabu.edu / admin123")

    # ── Default Student Account (for testing) ──
    student_hash = generate_password_hash('student123', method='pbkdf2:sha256')
    cursor.execute(
        "INSERT INTO users (full_name, email, password_hash, role) VALUES (?, ?, ?, ?)",
        ('Alex Student', 'student@biblabu.edu', student_hash, 'student')
    )
    student_id = cursor.lastrowid
    print(f"[OK] Student created: student@biblabu.edu / student123")

    # ── Sample Modules (mirroring PoliTeMall categories) ──
    modules = [
        ('Introduction to Business Management', 
         'This module provides foundational knowledge in business principles, covering topics such as organizational structure, management functions, marketing fundamentals, and financial literacy. Students will develop critical thinking skills applicable to real-world business scenarios.',
         'Foundation Modules', 'Business & Management', 'Biblabu Polytechnic', 'Self-paced'),

        ('Principles of Accounting',
         'An introductory module covering the basics of financial accounting, including the accounting cycle, preparation of financial statements, and analysis of business transactions. Ideal for students beginning their journey in finance.',
         'Foundation Modules', 'Business & Management', 'Biblabu Polytechnic', 'Instructor-led'),

        ('Digital Media Production',
         'Learn the fundamentals of creating compelling digital media content. This module covers video production, audio editing, graphic design basics, and storytelling techniques for modern digital platforms.',
         'Foundation Modules', 'Design, Media & Humanities', 'Biblabu Polytechnic', 'Blended'),

        ('Art History & Visual Culture',
         'Explore the evolution of art across civilizations and eras. This module engages learners with an appreciation and understanding of artworks through various themes that form relevant connections to their lived experiences.',
         'Foundation Modules', 'Design, Media & Humanities', 'Biblabu Polytechnic', 'Self-paced'),

        ('Basic IT Security',
         'Gain foundational understanding of IT security concepts including key concepts, systems and endpoint security, access controls, and network security. Essential knowledge for anyone working with digital systems.',
         'Foundation Modules', 'Information & Digital Technologies', 'Biblabu Polytechnic', 'Self-paced'),

        ('Web Development Fundamentals',
         'A hands-on module teaching HTML, CSS, and JavaScript from scratch. Students will build responsive websites and understand modern web development practices and deployment workflows.',
         'Foundation Modules', 'Information & Digital Technologies', 'Biblabu Polytechnic', 'Instructor-led'),

        ('Cell and Molecular Biology',
         'An introductory module to help students understand the important biological processes within a cell and biological molecules, particularly DNA, RNA and protein molecules.',
         'Foundation Modules', 'Applied & Health Sciences', 'Biblabu Polytechnic', 'Self-paced'),

        ('Engineering Mathematics',
         'This module covers essential mathematical concepts used in engineering fields, including calculus, linear algebra, differential equations, and statistical analysis with practical engineering applications.',
         'Foundation Modules', 'Built Environment, Engineering & Maritime', 'Biblabu Polytechnic', 'Instructor-led'),

        ('Advanced Python Programming',
         'Dive deep into Python with advanced topics including object-oriented programming, decorators, generators, async programming, data structures, and building production-ready applications.',
         'Discipline-Specific Modules', 'Information & Digital Technologies', 'Biblabu Polytechnic', 'Blended'),

        ('Data Analytics with Python',
         'Learn to analyze and visualize data using Python libraries such as Pandas, NumPy, and Matplotlib. Apply statistical methods to derive meaningful insights from real-world datasets.',
         'Discipline-Specific Modules', 'Information & Digital Technologies', 'Biblabu Polytechnic', 'Self-paced'),

        ('Digital Marketing Strategy',
         'Master the art of digital marketing including SEO, social media marketing, content strategy, email campaigns, and analytics. Build comprehensive digital marketing plans for real businesses.',
         'Discipline-Specific Modules', 'Business & Management', 'Biblabu Polytechnic', 'Self-paced'),

        ('Cyber Wellness & Digital Citizenship',
         'This module covers topics on cyber safety, digital wellness, responsible online behavior, and maintenance of positive well-being for internet users in academic and professional settings.',
         'General Modules', 'General Education', 'Biblabu Polytechnic', 'Self-paced'),

        ('Career Planning & Professional Development',
         'Equip yourself with essential career planning skills including resume writing, interview preparation, networking strategies, personal branding, and workplace communication.',
         'General Modules', 'General Education', 'Biblabu Polytechnic', 'Self-paced'),
    ]

    for mod in modules:
        cursor.execute(
            """INSERT INTO modules (title, description, programme_area, cluster, institution, delivery_mode, admin_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (*mod, admin_id)
        )
    print(f"[OK] {len(modules)} sample modules created.")

    # Enroll the test student in a few modules
    cursor.execute("INSERT INTO enrollments (student_id, module_id) VALUES (?, ?)", (student_id, 1))
    cursor.execute("INSERT INTO enrollments (student_id, module_id) VALUES (?, ?)", (student_id, 5))
    cursor.execute("INSERT INTO enrollments (student_id, module_id) VALUES (?, ?)", (student_id, 6))
    print("[OK] Test student enrolled in 3 modules.")

    # ── Sample Announcements ──
    now = datetime.now()
    announcements = [
        ('Welcome to BibLabU Learning Portal',
         'We are excited to launch the BibLabU Learning Management System! Explore our wide range of modules across Foundation, Discipline-Specific, and General programme areas. Start your learning journey by browsing the module catalog and enrolling in courses that interest you.',
         now - timedelta(days=2)),

        ('New Modules Available — Semester 2 2026',
         'New modules have been added to the catalog for Semester 2, including Advanced Python Programming, Data Analytics, and Digital Marketing Strategy. Check the catalog for full details and enroll today!',
         now - timedelta(hours=12)),

        ('System Maintenance Notice',
         'The platform will undergo scheduled maintenance this Saturday from 2:00 AM to 5:00 AM SGT. During this time, the portal may be temporarily unavailable. Please save your work beforehand.',
         now),
    ]

    for title, content, created in announcements:
        cursor.execute(
            "INSERT INTO announcements (title, content, admin_id, created_at) VALUES (?, ?, ?, ?)",
            (title, content, admin_id, created.strftime('%Y-%m-%d %H:%M:%S'))
        )
    print(f"[OK] {len(announcements)} announcements created.")

    conn.commit()
    print("\n[DONE] Database seeded successfully!")
    print("=" * 50)
    print("  Admin login:   admin@biblabu.edu / admin123")
    print("  Student login:  student@biblabu.edu / student123")
    print("=" * 50)


if __name__ == '__main__':
    # Delete old database if it exists for a clean start
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("[OK] Old database removed.")

    conn = get_connection()
    create_tables(conn)
    seed_data(conn)
    conn.close()
