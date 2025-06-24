from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
from psycopg2.extras import RealDictCursor
import traceback
import uuid
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-this')

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgres://neondb_owner:npg_Lw8ei2tjzQKd@ep-late-king-ablwak3c-pooler.eu-west-2.aws.neon.tech/neondb?sslmode=require"
)

def get_db_connection():
    try:
        conn = psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        raise

def generate_error_id():
    return str(uuid.uuid4())[:8]

@app.errorhandler(404)
def not_found_error(error):
    error_id = generate_error_id()
    error_message = "The page you're looking for doesn't exist or has been moved."
    print(f"404 Error (ID: {error_id}): {request.url}")
    return render_template('404.html', error_message=error_message, error_id=error_id), 404

@app.errorhandler(500)
def internal_error(error):
    error_id = generate_error_id()
    error_message = "Something went wrong on our end. Our team has been notified."
    print(f"500 Error (ID: {error_id}): {str(error)}")
    print(traceback.format_exc())
    return render_template('404.html', error_message=error_message, error_id=error_id), 500

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    print("Using DB_URL:", DB_URL)
    if request.method == 'POST':
        firstName = request.form.get('firstName', '').strip()
        lastName = request.form.get('lastName', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not all([firstName, lastName, email, password]):
            flash('Please fill out all fields!', 'error')
            return redirect(url_for('register'))

        if len(password) < 6 or not any(char in '!@#$%^&*(),.?":{}|<>' for char in password):
            flash('Password does not meet requirements!', 'error')
            return redirect(url_for('register'))

        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('SELECT 1 FROM users WHERE email = %s', (email,))
                    if cur.fetchone():
                        flash('An account with that email already exists!', 'error')
                        return redirect(url_for('register'))

                    hashed_password = generate_password_hash(password)
                    cur.execute(
                        'INSERT INTO users (firstname, lastname, email, password_hash) VALUES (%s, %s, %s, %s)',
                        (firstName, lastName, email, hashed_password)
                    )
                    conn.commit()

            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))

        except Exception as e:
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'users'")
                        columns = cur.fetchall()
                        print("Current users table columns are:", [row['column_name'] for row in columns])
            except Exception as sub_e:
                print("Failed to fetch users table columns:", sub_e)
            print(f"Registration error: {e}")
            flash('Registration failed! Please try again.', 'error')
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Please enter both email and password', 'error')
            return redirect(url_for('login'))

        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('SELECT * FROM users WHERE email = %s', (email,))
                    user = cur.fetchone()

                    if user and check_password_hash(user['password_hash'], password):
                        session.clear()
                        session['email'] = email
                        session['user_id'] = user['id']
                        session['permission_level'] = user.get('permission_level', 'User')
                        flash('Login successful!', 'success')
                        return redirect(url_for('dashboard'))
                    else:
                        flash('Invalid email or password', 'error')

        except Exception as e:
            print(f"Login error: {e}")
            flash('Login failed! Please try again.', 'error')

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'email' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('login'))

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT firstname, lastname FROM users WHERE email = %s', (session['email'],))
                user_info = cur.fetchone()
                if user_info:
                    return render_template(
                        'dashboard.html',
                        email=session['email'],
                        firstname=user_info.get('firstname', ''),
                        lastname=user_info.get('lastname', '')
                    )
    except Exception as e:
        print(f"Dashboard error: {e}")
        flash('Error loading dashboard', 'error')
        return redirect(url_for('login'))

    return render_template('dashboard.html', email=session['email'])

@app.route('/admin')
def admin():
    if 'email' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('login'))

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT permission_level FROM users WHERE email = %s', (session['email'],))
                user = cur.fetchone()

                if not user or user.get('permission_level') != 'Admin':
                    flash('Unauthorized access', 'error')
                    return redirect(url_for('dashboard'))

                cur.execute('SELECT id, firstname, lastname, email, permission_level, submissions FROM users')
                users = cur.fetchall()

                cur.execute('SELECT id, name FROM resources')
                resources = cur.fetchall()

                cur.execute('SELECT id, name, status FROM equipment')
                equipment_list = cur.fetchall()

        return render_template(
            'admin.html',
            users=users,
            resources=resources,
            equipment_list=equipment_list
        )

    except Exception as e:
        print(f"Admin dashboard load error: {e}")
        flash("Failed to load admin dashboard.", "error")
        return render_template('admin.html', users=[], resources=[], equipment_list=[])

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'email' not in session or session.get('permission_level') != 'Admin':
        flash('Unauthorized', 'error')
        return redirect(url_for('dashboard'))
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('DELETE FROM users WHERE id = %s', (user_id,))
                conn.commit()
        flash('User deleted.', 'success')
    except Exception as e:
        print(f"Delete user error: {e}")
        flash('Failed to delete user.', 'error')
    return redirect(url_for('admin'))

@app.route('/delete_resource/<int:resource_id>', methods=['POST'])
def delete_resource(resource_id):
    if 'email' not in session or session.get('permission_level') != 'Admin':
        flash('Unauthorized', 'error')
        return redirect(url_for('dashboard'))
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('DELETE FROM resources WHERE id = %s', (resource_id,))
                conn.commit()
        flash('Resource deleted.', 'success')
    except Exception as e:
        print(f"Delete resource error: {e}")
        flash('Failed to delete resource.', 'error')
    return redirect(url_for('admin'))

@app.route('/delete_equipment/<int:equipment_id>', methods=['POST'])
def delete_equipment(equipment_id):
    if 'email' not in session or session.get('permission_level') != 'Admin':
        flash('Unauthorized', 'error')
        return redirect(url_for('dashboard'))
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('DELETE FROM equipment WHERE id = %s', (equipment_id,))
                conn.commit()
        flash('Equipment deleted.', 'success')
    except Exception as e:
        print(f"Delete equipment error: {e}")
        flash('Failed to delete equipment.', 'error')
    return redirect(url_for('admin'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

def initialize_tables():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                            CREATE TABLE IF NOT EXISTS users (
                                                                 id SERIAL PRIMARY KEY,
                                                                 firstname VARCHAR(100) NOT NULL,
                                lastname VARCHAR(100) NOT NULL,
                                email VARCHAR(255) UNIQUE NOT NULL,
                                password_hash VARCHAR(255) NOT NULL,
                                permission_level VARCHAR(20) DEFAULT 'User',
                                submissions INTEGER DEFAULT 0,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                                );
                            ''')
                cur.execute('''
                            CREATE TABLE IF NOT EXISTS resources (
                                                                     id SERIAL PRIMARY KEY,
                                                                     name VARCHAR(100) NOT NULL
                                );
                            ''')
                cur.execute('''
                            CREATE TABLE IF NOT EXISTS equipment (
                                                                     id SERIAL PRIMARY KEY,
                                                                     name VARCHAR(100) NOT NULL,
                                status VARCHAR(50) NOT NULL DEFAULT 'Available'
                                );
                            ''')
                cur.execute('''
                            CREATE TABLE IF NOT EXISTS activity_submissions (
                                                                                id SERIAL PRIMARY KEY,
                                                                                submitted_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
                                activity_date DATE NOT NULL,
                                activity_type VARCHAR(100) NOT NULL,
                                description TEXT,
                                shift VARCHAR(20) NOT NULL,
                                shift_start TIME NOT NULL,
                                shift_end TIME NOT NULL,
                                location VARCHAR(255),
                                manpower_count INTEGER,
                                incident_report BOOLEAN DEFAULT FALSE,
                                incident_details TEXT,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                                );
                            ''')
                cur.execute('''
                            CREATE TABLE IF NOT EXISTS activity_submission_resources (
                                                                                         activity_submission_id INTEGER REFERENCES activity_submissions(id) ON DELETE CASCADE,
                                resource_id INTEGER REFERENCES resources(id) ON DELETE CASCADE,
                                PRIMARY KEY (activity_submission_id, resource_id)
                                );
                            ''')
                cur.execute('''
                            CREATE TABLE IF NOT EXISTS activity_submission_equipment (
                                                                                         activity_submission_id INTEGER REFERENCES activity_submissions(id) ON DELETE CASCADE,
                                equipment_id INTEGER REFERENCES equipment(id) ON DELETE CASCADE,
                                PRIMARY KEY (activity_submission_id, equipment_id)
                                );
                            ''')
                conn.commit()
        print("Database tables initialized successfully!")
    except Exception as e:
        print(f"Database initialization error: {e}")

initialize_tables()

@app.route('/add_resource', methods=['POST'])
def add_resource():
    if 'email' not in session or session.get('permission_level') != 'Admin':
        flash('Unauthorized', 'error')
        return redirect(url_for('dashboard'))
    name = request.form.get('name', '').strip()
    if not name:
        flash('Resource name required!', 'error')
        return redirect(url_for('admin'))
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('INSERT INTO resources (name) VALUES (%s)', (name,))
                conn.commit()
        flash('Resource added!', 'success')
    except Exception as e:
        print(f"Add resource error: {e}")
        flash('Failed to add resource.', 'error')
    return redirect(url_for('admin'))

@app.route('/add_equipment', methods=['POST'])
def add_equipment():
    if 'email' not in session or session.get('permission_level') != 'Admin':
        flash('Unauthorized', 'error')
        return redirect(url_for('dashboard'))
    name = request.form.get('name', '').strip()
    status = request.form.get('status', '').strip() or 'Available'
    if not name:
        flash('Equipment name required!', 'error')
        return redirect(url_for('admin'))
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('INSERT INTO equipment (name, status) VALUES (%s, %s)', (name, status))
                conn.commit()
        flash('Equipment added!', 'success')
    except Exception as e:
        print(f"Add equipment error: {e}")
        flash('Failed to add equipment.', 'error')
    return redirect(url_for('admin'))

#############################################
# Activity Submission
#############################################

@app.route('/submit_activity', methods=['GET', 'POST'])
def submit_activity():
    if 'email' not in session:
        flash('Please log in to submit an activity.', 'error')
        return redirect(url_for('login'))

    # Fetch resources and equipment for the select fields
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT id, name FROM resources ORDER BY name;')
                resources = cur.fetchall()
                cur.execute('SELECT id, name FROM equipment ORDER BY name;')
                equipment_list = cur.fetchall()
    except Exception as e:
        print(f"Error fetching resources/equipment: {e}")
        flash('Failed to load activity submission form.', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        # Collect fields
        submitted_by = session.get('user_id')
        activity_date = request.form.get('activity_date')
        activity_type = request.form.get('activity_type', '').strip()
        description = request.form.get('description', '').strip()
        shift = request.form.get('shift', '').strip()
        shift_start = request.form.get('shift_start')
        shift_end = request.form.get('shift_end')
        manpower_count = request.form.get('manpower_count')
        location = request.form.get('location', '').strip()
        incident_report = request.form.get('incident_report')
        incident_details = request.form.get('incident_details', '').strip()

        # Convert checkbox
        incident_report_bool = True if incident_report else False
        manpower_count_int = int(manpower_count) if manpower_count else None

        # Multiple selects:
        resources_used_ids = request.form.getlist('resources_used')
        equipment_used_ids = request.form.getlist('equipment_used')

        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Insert into main activity_submissions table
                    cur.execute('''
                                INSERT INTO activity_submissions (
                                    submitted_by, activity_date, activity_type, description,
                                    shift, shift_start, shift_end, location, manpower_count,
                                    incident_report, incident_details
                                ) VALUES (
                                             %s, %s, %s, %s,
                                             %s, %s, %s, %s, %s,
                                             %s, %s
                                         ) RETURNING id
                                ''', (
                                    submitted_by, activity_date, activity_type, description,
                                    shift, shift_start, shift_end, location, manpower_count_int,
                                    incident_report_bool, incident_details if incident_report_bool else None
                                ))
                    activity_submission_id = cur.fetchone()['id']

                    # Resources relationship
                    for resource_id in resources_used_ids:
                        cur.execute(
                            'INSERT INTO activity_submission_resources (activity_submission_id, resource_id) VALUES (%s, %s)',
                            (activity_submission_id, int(resource_id))
                        )

                    # Equipment relationship
                    for equipment_id in equipment_used_ids:
                        cur.execute(
                            'INSERT INTO activity_submission_equipment (activity_submission_id, equipment_id) VALUES (%s, %s)',
                            (activity_submission_id, int(equipment_id))
                        )

                    # Optionally, increment user's submissions count:
                    cur.execute('UPDATE users SET submissions = submissions + 1 WHERE id = %s', (submitted_by, ))
                    conn.commit()

            flash('Activity submitted successfully!', 'success')
            return redirect(url_for('dashboard'))

        except Exception as e:
            print(f"Error submitting activity: {e}")
            flash('Failed to submit activity, please try again.', 'error')
            # Let the user try again with the same lists!
            return render_template('submit_activity.html', resources=resources, equipment_list=equipment_list)

    # GET: render the form
    return render_template('submit_activity.html', resources=resources, equipment_list=equipment_list)

if __name__ == '__main__':
    app.run(debug=True)

app = app  # for Vercel