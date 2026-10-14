import sqlite3
import os
from config import Config

def get_db():
    conn = sqlite3.connect(Config.DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn

def init_db():
    conn = sqlite3.connect(Config.DATABASE)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")

    conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin','lab_manager','lab_tech','sample_collector','viewer')),
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS sample_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            storage_req TEXT,
            shelf_life_hrs INTEGER DEFAULT 24,
            instructions TEXT,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS test_catalog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            unit TEXT,
            ref_min REAL,
            ref_max REAL,
            reference_text TEXT,
            turnaround_hrs INTEGER DEFAULT 24,
            price REAL DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            contact_person TEXT,
            phone TEXT,
            email TEXT,
            address TEXT,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS samples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sample_code TEXT UNIQUE NOT NULL,
            client_id INTEGER REFERENCES clients(id),
            sample_type_id INTEGER NOT NULL REFERENCES sample_types(id),
            patient_name TEXT NOT NULL,
            patient_dob TEXT,
            patient_gender TEXT CHECK(patient_gender IN ('M','F','Other','')),
            priority TEXT NOT NULL DEFAULT 'routine' CHECK(priority IN ('routine','urgent')),
            status TEXT NOT NULL DEFAULT 'registered' CHECK(status IN ('registered','triaged','analysis','review','approved','reported','cancelled')),
            registered_by INTEGER REFERENCES users(id),
            triaged_by INTEGER REFERENCES users(id),
            analyzed_by INTEGER REFERENCES users(id),
            reviewed_by INTEGER REFERENCES users(id),
            approved_by INTEGER REFERENCES users(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            triaged_at TIMESTAMP,
            analyzed_at TIMESTAMP,
            reviewed_at TIMESTAMP,
            approved_at TIMESTAMP,
            reported_at TIMESTAMP,
            completed_at TIMESTAMP,
            estimated_turnaround INTEGER,
            notes TEXT,
            cancelled_reason TEXT
        );

        CREATE TABLE IF NOT EXISTS sample_tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sample_id INTEGER NOT NULL REFERENCES samples(id) ON DELETE CASCADE,
            test_catalog_id INTEGER NOT NULL REFERENCES test_catalog(id),
            status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','in_progress','completed','cancelled')),
            result TEXT,
            unit TEXT,
            reference_range TEXT,
            flagged INTEGER DEFAULT 0,
            notes TEXT,
            performed_by INTEGER REFERENCES users(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS sample_status_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sample_id INTEGER NOT NULL REFERENCES samples(id) ON DELETE CASCADE,
            from_status TEXT,
            to_status TEXT NOT NULL,
            user_id INTEGER REFERENCES users(id),
            username TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS sample_attachments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sample_id INTEGER NOT NULL REFERENCES samples(id) ON DELETE CASCADE,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            uploaded_by INTEGER REFERENCES users(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS system_config (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            action TEXT NOT NULL,
            resource_type TEXT,
            resource_id INTEGER,
            details TEXT,
            ip_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS test_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS test_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            group_id INTEGER REFERENCES test_groups(id),
            description TEXT,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS laboratory_tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category_id INTEGER REFERENCES test_categories(id),
            specimen_id INTEGER,
            turnaround_hrs INTEGER DEFAULT 24,
            price REAL DEFAULT 0,
            description TEXT,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS test_parameters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_id INTEGER NOT NULL REFERENCES laboratory_tests(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            unit TEXT,
            ref_min REAL,
            ref_max REAL,
            reference_text TEXT,
            decimal_places INTEGER DEFAULT 1,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS specimens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            storage_req TEXT,
            shelf_life_hrs INTEGER DEFAULT 24,
            instructions TEXT,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS machine_tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_name TEXT NOT NULL,
            test_id INTEGER REFERENCES laboratory_tests(id),
            machine_code TEXT,
            manufacturer TEXT,
            model TEXT,
            calibration_date TEXT,
            next_calibration TEXT,
            status TEXT DEFAULT 'active' CHECK(status IN ('active','maintenance','inactive')),
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            contact_person TEXT,
            phone TEXT,
            email TEXT,
            address TEXT,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            sku TEXT,
            unit TEXT DEFAULT 'pcs',
            price REAL DEFAULT 0,
            cost REAL DEFAULT 0,
            quantity INTEGER DEFAULT 0,
            min_quantity INTEGER DEFAULT 0,
            supplier_id INTEGER REFERENCES suppliers(id),
            active INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_code TEXT UNIQUE NOT NULL,
            client_id INTEGER REFERENCES clients(id),
            sale_date TEXT DEFAULT (date('now')),
            subtotal REAL DEFAULT 0,
            tax REAL DEFAULT 0,
            total REAL DEFAULT 0,
            status TEXT DEFAULT 'pending' CHECK(status IN ('pending','completed','cancelled')),
            notes TEXT,
            created_by INTEGER REFERENCES users(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS sale_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL REFERENCES sales(id) ON DELETE CASCADE,
            item_id INTEGER NOT NULL REFERENCES items(id),
            quantity INTEGER NOT NULL DEFAULT 1,
            unit_price REAL NOT NULL,
            total REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_code TEXT UNIQUE NOT NULL,
            client_id INTEGER REFERENCES clients(id),
            invoice_date TEXT DEFAULT (date('now')),
            due_date TEXT,
            subtotal REAL DEFAULT 0,
            tax REAL DEFAULT 0,
            total REAL DEFAULT 0,
            status TEXT DEFAULT 'pending' CHECK(status IN ('pending','paid','overdue','cancelled')),
            notes TEXT,
            created_by INTEGER REFERENCES users(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
            description TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            unit_price REAL NOT NULL,
            total REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS deliveries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            delivery_code TEXT UNIQUE NOT NULL,
            client_id INTEGER REFERENCES clients(id),
            delivery_date TEXT DEFAULT (date('now')),
            status TEXT DEFAULT 'pending' CHECK(status IN ('pending','dispatched','delivered','cancelled')),
            tracking_number TEXT,
            notes TEXT,
            created_by INTEGER REFERENCES users(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS delivery_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            delivery_id INTEGER NOT NULL REFERENCES deliveries(id) ON DELETE CASCADE,
            item_id INTEGER NOT NULL REFERENCES items(id),
            quantity INTEGER NOT NULL DEFAULT 1,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS quotations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quote_code TEXT UNIQUE NOT NULL,
            client_id INTEGER REFERENCES clients(id),
            quote_date TEXT DEFAULT (date('now')),
            valid_until TEXT,
            subtotal REAL DEFAULT 0,
            tax REAL DEFAULT 0,
            total REAL DEFAULT 0,
            status TEXT DEFAULT 'draft' CHECK(status IN ('draft','sent','accepted','rejected','expired')),
            notes TEXT,
            created_by INTEGER REFERENCES users(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS quotation_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quotation_id INTEGER NOT NULL REFERENCES quotations(id) ON DELETE CASCADE,
            description TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            unit_price REAL NOT NULL,
            total REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')

    _run_migrations(conn)

    _seed_default_data(conn)

    conn.close()


def _run_migrations(conn):
    migrations = [
        ("ALTER TABLE samples ADD COLUMN cancelled_reason TEXT",),
    ]
    for migration in migrations:
        try:
            conn.execute(migration[0])
        except sqlite3.OperationalError:
            pass
    conn.commit()


def _seed_default_data(conn):
    cursor = conn.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        from werkzeug.security import generate_password_hash
        conn.execute(
            "INSERT INTO users (username, password_hash, role, first_name, last_name) VALUES (?, ?, ?, ?, ?)",
            ("admin", generate_password_hash("admin123"), "admin", "System", "Admin")
        )

    cursor = conn.execute("SELECT COUNT(*) FROM sample_types")
    if cursor.fetchone()[0] == 0:
        defaults = [
            ("Blood", "Refrigerate 2-8C", 48, "Handle with care. Invert gently 8-10 times."),
            ("Urine", "Refrigerate 2-8C", 24, "Midstream clean catch preferred."),
            ("Stool", "Room temperature", 48, "Collect in sterile container."),
            ("CSF", "Refrigerate 2-8C", 4, "Handle gently. Do not shake."),
            ("Tissue", "Frozen -20C", 720, "Place in formalin if not freezing."),
            ("Swab", "Room temperature", 24, "Collect before antibiotic administration."),
            ("Sputum", "Refrigerate 2-8C", 24, "Deep cough specimen required."),
            ("Serum", "Frozen -20C", 720, "Allow blood to clot before centrifuging."),
        ]
        conn.executemany(
            "INSERT INTO sample_types (name, storage_req, shelf_life_hrs, instructions) VALUES (?, ?, ?, ?)",
            defaults
        )

    cursor = conn.execute("SELECT COUNT(*) FROM test_catalog")
    if cursor.fetchone()[0] == 0:
        tests = [
            ("Complete Blood Count (CBC)", "Hematology", "x10^3/uL", None, None, "WBC: 4.5-11.0, RBC: 4.5-5.5, Hgb: 12-16, Hct: 36-46", 4, 15.00),
            ("Hemoglobin", "Hematology", "g/dL", 12, 16, "12-16 g/dL", 2, 8.00),
            ("Blood Glucose", "Chemistry", "mg/dL", 70, 100, "70-100 mg/dL (fasting)", 1, 5.00),
            ("Lipid Panel", "Chemistry", "mg/dL", None, None, "Total Chol: <200, LDL: <100, HDL: >40, Trig: <150", 4, 20.00),
            ("Liver Function Test (LFT)", "Chemistry", "U/L", None, None, "ALT: 7-56, AST: 10-40, ALP: 44-147", 4, 18.00),
            ("Kidney Function (BUN/Creatinine)", "Chemistry", "mg/dL", None, None, "BUN: 7-20, Creatinine: 0.7-1.3", 3, 12.00),
            ("Urinalysis", "Urinalysis", "", None, None, "Color: yellow, Clarity: clear, pH: 4.5-8.0, SpG: 1.005-1.030", 2, 10.00),
            ("Urine Microscopy", "Urinalysis", "/hpf", None, None, "WBC: 0-5, RBC: 0-2, Casts: 0", 3, 12.00),
            ("PT/INR", "Coagulation", "sec", 11, 14, "INR: 0.8-1.2", 2, 15.00),
            ("aPTT", "Coagulation", "sec", 25, 35, "25-35 seconds", 2, 15.00),
            ("Erythrocyte Sedimentation Rate (ESR)", "Hematology", "mm/hr", 0, 20, "0-20 mm/hr", 3, 10.00),
            ("Thyroid Stimulating Hormone (TSH)", "Immunology", "mIU/L", 0.4, 4.0, "0.4-4.0 mIU/L", 6, 25.00),
            ("Hemoglobin A1c (HbA1c)", "Chemistry", "%", 4.0, 5.7, "Normal: <5.7%, Pre-diabetes: 5.7-6.4%, Diabetes: >6.5%", 4, 22.00),
            ("C-Reactive Protein (CRP)", "Immunology", "mg/L", 0, 3.0, "0-3.0 mg/L", 4, 18.00),
            ("Procalcitonin", "Immunology", "ng/mL", 0, 0.05, "<0.05 ng/mL (normal)", 6, 35.00),
        ]
        conn.executemany(
            "INSERT INTO test_catalog (name, category, unit, ref_min, ref_max, reference_text, turnaround_hrs, price) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            tests
        )

    cursor = conn.execute("SELECT COUNT(*) FROM system_config")
    if cursor.fetchone()[0] == 0:
        configs = [
            ("lab_name", "Seal MW Lab System"),
            ("lab_address", ""),
            ("lab_phone", ""),
            ("lab_email", ""),
        ]
        conn.executemany(
            "INSERT OR IGNORE INTO system_config (key, value) VALUES (?, ?)",
            configs
        )

    cursor = conn.execute("SELECT COUNT(*) FROM test_groups")
    if cursor.fetchone()[0] == 0:
        groups = [
            ("Clinical Chemistry", "Chemistry tests"),
            ("Hematology", "Blood cell tests"),
            ("Immunology", "Immune system tests"),
            ("Microbiology", "Infection tests"),
            ("Urinalysis", "Urine tests"),
            ("Coagulation", "Blood clotting tests"),
        ]
        conn.executemany(
            "INSERT INTO test_groups (name, description) VALUES (?, ?)",
            groups
        )

    cursor = conn.execute("SELECT COUNT(*) FROM test_categories")
    if cursor.fetchone()[0] == 0:
        categories = [
            ("Blood Chemistry", 1, "Tests on blood serum/plasma"),
            ("Liver Function", 1, "Liver health tests"),
            ("Kidney Function", 1, "Kidney health tests"),
            ("Lipid Profile", 1, "Cholesterol and fats"),
            ("Blood Count", 2, "Cell counts in blood"),
            ("Hemoglobin Studies", 2, "Hemoglobin tests"),
            ("Thyroid Function", 3, "Thyroid hormone tests"),
            ("Inflammatory Markers", 3, "Inflammation tests"),
            ("Routine Urinalysis", 5, "Standard urine tests"),
            ("Urine Microscopy", 5, "Urine cell examination"),
            ("Coagulation Profile", 6, "Blood clotting tests"),
        ]
        conn.executemany(
            "INSERT INTO test_categories (name, group_id, description) VALUES (?, ?, ?)",
            categories
        )

    cursor = conn.execute("SELECT COUNT(*) FROM specimens")
    if cursor.fetchone()[0] == 0:
        specimens = [
            ("Whole Blood (EDTA)", "Refrigerate 2-8C", 48, "Purple top tube. Mix gently."),
            ("Serum", "Frozen -20C", 720, "Red top tube. Allow to clot."),
            ("Plasma", "Frozen -20C", 720, "Gray/green top tube."),
            ("Urine (Random)", "Refrigerate 2-8C", 24, "Midstream clean catch."),
            ("Urine (24hr)", "Refrigerate 2-8C", 48, "Collect all urine for 24 hours."),
            ("CSF", "Refrigerate 2-8C", 4, "Handle gently. Do not shake."),
            ("Stool", "Room temperature", 48, "Sterile container."),
            ("Sputum", "Refrigerate 2-8C", 24, "Deep cough specimen."),
            ("Swab", "Room temperature", 24, "Collect before antibiotics."),
            ("Tissue", "Formalin", 720, "10% neutral buffered formalin."),
            ("Synovial Fluid", "Refrigerate 2-8C", 24, "Sterile tube."),
            ("Body Fluid", "Refrigerate 2-8C", 24, "Sterile container."),
        ]
        conn.executemany(
            "INSERT INTO specimens (name, storage_req, shelf_life_hrs, instructions) VALUES (?, ?, ?, ?)",
            specimens
        )

    cursor = conn.execute("SELECT COUNT(*) FROM laboratory_tests")
    if cursor.fetchone()[0] == 0:
        lab_tests = [
            ("Complete Blood Count", 5, 1, 4, 15.00, "Full blood count with differential"),
            ("Blood Glucose", 1, 1, 1, 5.00, "Fasting blood glucose"),
            ("Lipid Panel", 4, 2, 4, 20.00, "Total cholesterol, LDL, HDL, triglycerides"),
            ("Liver Function Test", 2, 2, 4, 18.00, "ALT, AST, ALP, bilirubin"),
            ("Kidney Function", 3, 2, 3, 12.00, "BUN, creatinine, electrolytes"),
            ("Thyroid TSH", 7, 2, 6, 25.00, "Thyroid stimulating hormone"),
            ("HbA1c", 6, 1, 4, 22.00, "Glycated hemoglobin"),
            ("Urinalysis", 9, 4, 2, 10.00, "Standard urinalysis"),
            ("PT/INR", 11, 1, 2, 15.00, "Prothrombin time"),
            ("CRP", 8, 2, 4, 18.00, "C-reactive protein"),
        ]
        conn.executemany(
            "INSERT INTO laboratory_tests (name, category_id, specimen_id, turnaround_hrs, price, description) VALUES (?, ?, ?, ?, ?, ?)",
            lab_tests
        )

    conn.commit()
