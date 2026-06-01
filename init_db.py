"""
init_db.py — Database initialization and seeding for YSP Learns LMS.

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
            institution TEXT DEFAULT 'YSP Learns',
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

    # Route Enrollments — tracks which YSP route a student is on and their phase progress
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS route_enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            route_name TEXT NOT NULL CHECK(route_name IN ('Research', 'Policy', 'Business', 'Diplomacy', 'Environment', 'Community')),
            current_phase TEXT NOT NULL DEFAULT 'Foundations' CHECK(current_phase IN ('Foundations', 'Deep Dive', 'Capstone')),
            current_week INTEGER NOT NULL DEFAULT 1,
            start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(student_id, route_name)
        )
    ''')

    # Capstone Milestones — tracks capstone project progress per student
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS capstone_milestones (
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
        )
    ''')

    # Mentor Sessions — logs mentor meetings per student
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mentor_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            session_date TIMESTAMP NOT NULL,
            duration_minutes INTEGER DEFAULT 60,
            notes TEXT,
            mentor_name TEXT,
            next_session_date TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # Certificates — tracks certificate status per student per module
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS certificates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            module_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'issued')),
            issued_at TIMESTAMP,
            certificate_code TEXT,
            FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (module_id) REFERENCES modules(id) ON DELETE CASCADE,
            UNIQUE(student_id, module_id)
        )
    ''')

    # Resources — admin-managed secondary sources (articles, papers, templates)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS resources (
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
        )
    ''')

    # Indexes for new tables
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_route_enrollments_student ON route_enrollments(student_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_capstone_student ON capstone_milestones(student_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_mentor_sessions_student ON mentor_sessions(student_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_certificates_student ON certificates(student_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_resources_category ON resources(category)')

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
    admin_hash = generate_password_hash('ysplearn123', method='pbkdf2:sha256')
    cursor.execute(
        "INSERT INTO users (full_name, email, password_hash, role) VALUES (?, ?, ?, ?)",
        ('Admin Instructor', 'ysplearn123@edu', admin_hash, 'admin')
    )
    admin_id = cursor.lastrowid
    print(f"[OK] Admin created: ysplearn123@edu / ysplearn123")

    # ── Default Student Account (for testing) ──
    student_hash = generate_password_hash('student123', method='pbkdf2:sha256')
    cursor.execute(
        "INSERT INTO users (full_name, email, password_hash, role) VALUES (?, ?, ?, ?)",
        ('Alex Student', 'student@ysplearns.com', student_hash, 'student')
    )
    student_id = cursor.lastrowid
    print(f"[OK] Student created: student@ysplearns.com / student123")

    # ── Sample Modules (mirroring PoliTeMall categories) ──
    modules = [
        ('Introduction to Business Management', 
         'This module provides foundational knowledge in business principles, covering topics such as organizational structure, management functions, marketing fundamentals, and financial literacy. Students will develop critical thinking skills applicable to real-world business scenarios.',
         'Foundation Modules', 'Business & Management', 'YSP Learns', 'Self-paced'),

        ('Principles of Accounting',
         'An introductory module covering the basics of financial accounting, including the accounting cycle, preparation of financial statements, and analysis of business transactions. Ideal for students beginning their journey in finance.',
         'Foundation Modules', 'Business & Management', 'YSP Learns', 'Instructor-led'),

        ('Digital Media Production',
         'Learn the fundamentals of creating compelling digital media content. This module covers video production, audio editing, graphic design basics, and storytelling techniques for modern digital platforms.',
         'Foundation Modules', 'Design, Media & Humanities', 'YSP Learns', 'Blended'),

        ('Art History & Visual Culture',
         'Explore the evolution of art across civilizations and eras. This module engages learners with an appreciation and understanding of artworks through various themes that form relevant connections to their lived experiences.',
         'Foundation Modules', 'Design, Media & Humanities', 'YSP Learns', 'Self-paced'),

        ('Basic IT Security',
         'Gain foundational understanding of IT security concepts including key concepts, systems and endpoint security, access controls, and network security. Essential knowledge for anyone working with digital systems.',
         'Foundation Modules', 'Information & Digital Technologies', 'YSP Learns', 'Self-paced'),

        ('Web Development Fundamentals',
         'A hands-on module teaching HTML, CSS, and JavaScript from scratch. Students will build responsive websites and understand modern web development practices and deployment workflows.',
         'Foundation Modules', 'Information & Digital Technologies', 'YSP Learns', 'Instructor-led'),

        ('Cell and Molecular Biology',
         'An introductory module to help students understand the important biological processes within a cell and biological molecules, particularly DNA, RNA and protein molecules.',
         'Foundation Modules', 'Applied & Health Sciences', 'YSP Learns', 'Self-paced'),

        ('Engineering Mathematics',
         'This module covers essential mathematical concepts used in engineering fields, including calculus, linear algebra, differential equations, and statistical analysis with practical engineering applications.',
         'Foundation Modules', 'Built Environment, Engineering & Maritime', 'YSP Learns', 'Instructor-led'),

        ('Advanced Python Programming',
         'Dive deep into Python with advanced topics including object-oriented programming, decorators, generators, async programming, data structures, and building production-ready applications.',
         'Discipline-Specific Modules', 'Information & Digital Technologies', 'YSP Learns', 'Blended'),

        ('Data Analytics with Python',
         'Learn to analyze and visualize data using Python libraries such as Pandas, NumPy, and Matplotlib. Apply statistical methods to derive meaningful insights from real-world datasets.',
         'Discipline-Specific Modules', 'Information & Digital Technologies', 'YSP Learns', 'Self-paced'),

        ('Digital Marketing Strategy',
         'Master the art of digital marketing including SEO, social media marketing, content strategy, email campaigns, and analytics. Build comprehensive digital marketing plans for real businesses.',
         'Discipline-Specific Modules', 'Business & Management', 'YSP Learns', 'Self-paced'),

        ('Cyber Wellness & Digital Citizenship',
         'This module covers topics on cyber safety, digital wellness, responsible online behavior, and maintenance of positive well-being for internet users in academic and professional settings.',
         'General Modules', 'General Education', 'YSP Learns', 'Self-paced'),

        ('Career Planning & Professional Development',
         'Equip yourself with essential career planning skills including resume writing, interview preparation, networking strategies, personal branding, and workplace communication.',
         'General Modules', 'General Education', 'YSP Learns', 'Self-paced'),
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
        ('Welcome to YSP Learns Portal',
         'We are excited to launch the YSP Learns Learning Management System! Explore our wide range of modules across Foundation, Discipline-Specific, and General programme areas. Start your learning journey by browsing the module catalog and enrolling in courses that interest you.',
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

    # ── Sample Route Enrollment (test student enrolled in Research route) ──
    cursor.execute(
        "INSERT INTO route_enrollments (student_id, route_name, current_phase, current_week, start_date) VALUES (?, ?, ?, ?, ?)",
        (student_id, 'Research', 'Deep Dive', 6, (now - timedelta(weeks=6)).strftime('%Y-%m-%d %H:%M:%S'))
    )
    route_enrollment_id = cursor.lastrowid
    print("[OK] Test student enrolled in Research route (Deep Dive, Week 6).")

    # ── Sample Capstone Milestone ──
    cursor.execute(
        "INSERT INTO capstone_milestones (student_id, route_enrollment_id, draft_submitted_at, project_title, notes) VALUES (?, ?, ?, ?, ?)",
        (student_id, route_enrollment_id,
         (now - timedelta(days=3)).strftime('%Y-%m-%d %H:%M:%S'),
         'Impact of Urban Green Spaces on Youth Mental Health',
         'First draft submitted for review. Awaiting mentor feedback.')
    )
    print("[OK] Capstone milestone created for test student.")

    # ── Sample Mentor Sessions ──
    mentor_sessions = [
        ((now - timedelta(weeks=4)).strftime('%Y-%m-%d %H:%M:%S'), 45,
         'Discussed research question framing and literature review scope. Mentor suggested focusing on Southeast Asian urban contexts.',
         'Dr. Sarah Chen', (now - timedelta(weeks=2)).strftime('%Y-%m-%d %H:%M:%S')),
        ((now - timedelta(weeks=2)).strftime('%Y-%m-%d %H:%M:%S'), 60,
         'Reviewed draft methodology section. Discussed qualitative vs mixed-methods approach. Action item: revise interview protocol.',
         'Dr. Sarah Chen', (now + timedelta(weeks=1)).strftime('%Y-%m-%d %H:%M:%S')),
    ]
    for sd, dur, notes, mentor, nxt in mentor_sessions:
        cursor.execute(
            "INSERT INTO mentor_sessions (student_id, session_date, duration_minutes, notes, mentor_name, next_session_date) VALUES (?, ?, ?, ?, ?, ?)",
            (student_id, sd, dur, notes, mentor, nxt)
        )
    print(f"[OK] {len(mentor_sessions)} mentor sessions created.")

    # ── Sample Certificates (one issued, one pending) ──
    cursor.execute(
        "INSERT INTO certificates (student_id, module_id, status, issued_at, certificate_code) VALUES (?, ?, ?, ?, ?)",
        (student_id, 1, 'issued', (now - timedelta(days=5)).strftime('%Y-%m-%d %H:%M:%S'), 'YSP-2026-RES-0001')
    )
    cursor.execute(
        "INSERT INTO certificates (student_id, module_id, status) VALUES (?, ?, ?)",
        (student_id, 5, 'pending')
    )
    print("[OK] 2 sample certificates created (1 issued, 1 pending).")

    # ── Sample Resources ──
    resources = [
        ('How to Write a Policy Brief',
         'A step-by-step guide to writing effective policy briefs that influence decision-makers. Covers structure, evidence use, and persuasion techniques.',
         'Template', 'https://www.idrc.ca/en/how-write-policy-brief'),
        ('Climate Action: Youth Perspectives (UN Report 2025)',
         'United Nations report documenting how young people around the world are contributing to climate policy through local and global advocacy.',
         'Research Paper', 'https://www.un.org/en/climatechange/youth-in-action'),
        ('Introduction to Research Ethics',
         'Essential reading on ethical considerations in social research, including informed consent, privacy, and data management best practices.',
         'Article', 'https://www.who.int/ethics/research/en/'),
        ('YSP Capstone Project Template',
         'Official template for structuring your capstone project document. Includes sections for abstract, methodology, findings, and policy recommendations.',
         'Template', None),
        ('Sustainability in ASEAN: Policy Challenges & Opportunities',
         'News article covering the latest developments in sustainability policy across Southeast Asian nations, with focus on youth engagement.',
         'News', 'https://asean.org/sustainability-youth-engagement'),
        ('Data Visualization for Policy Research (Video)',
         'A 45-minute workshop recording covering how to create compelling data visualizations for policy documents using free tools.',
         'Video', 'https://www.youtube.com/watch?v=example_ysp'),
    ]
    for r_title, r_desc, r_cat, r_url in resources:
        cursor.execute(
            "INSERT INTO resources (title, description, category, url, admin_id) VALUES (?, ?, ?, ?, ?)",
            (r_title, r_desc, r_cat, r_url, admin_id)
        )
    print(f"[OK] {len(resources)} sample resources created.")

    conn.commit()
    print("\n[DONE] Database seeded successfully!")
    print("=" * 50)
    print("  Admin login:   ysplearn123@edu / ysplearn123")
    print("  Student login:  student@ysplearns.com / student123")
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
