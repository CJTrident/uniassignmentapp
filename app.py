from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
from psycopg2.extras import RealDictCursor
import traceback
import uuid

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

def get_db_connection():
    return psycopg2.connect(
        "postgresql://neondb_owner:npg_Lw8ei2tjzQKd@ep-tight-wave-abc3bc1l-pooler.eu-west-2.aws.neon.tech/neondb?sslmode=require",
        cursor_factory=RealDictCursor
    )

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
    if request.method == 'POST':
        print(f"Form data received: {request.form}")

        firstName = request.form.get('firstName')
        lastName = request.form.get('lastName')
        username = request.form.get('username')
        password = request.form.get('password')

        if not all([firstName, lastName, username, password]):
            flash('Please fill out all fields!', 'error')
            return redirect(url_for('register'))

        if len(password) < 6 or not any(char in '!@#$%^&*(),.?":{}|<>' for char in password):
            flash('Password does not meet requirements!', 'error')
            return redirect(url_for('register'))

        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('SELECT * FROM users WHERE username = %s', (username,))
                    if cur.fetchone() is not None:
                        flash('Username already exists!', 'error')
                        return redirect(url_for('register'))

                    hashed_password = generate_password_hash(password)

                    cur.execute(
                        'INSERT INTO users (firstname, lastname, username, password_hash) VALUES (%s, %s, %s, %s)',
                        (firstName, lastName, username, hashed_password)
                    )

                    conn.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))

        except Exception as e:
            error_msg = str(e)
            print(f"Database Error: {error_msg}")
            flash(f'Registration failed! {error_msg}', 'error')
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('SELECT * FROM users WHERE username = %s', (username,))
                    user = cur.fetchone()

                    if user and check_password_hash(user['password_hash'], password):
                        session['username'] = username
                        flash('Login successful!', 'success')
                        return redirect(url_for('dashboard'))
                    else:
                        flash('Invalid username or password', 'error')

        except Exception as e:
            print(f"Database Error: {e}")
            flash('Login failed! Please try again.', 'error')

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    username = session.get('username')
    if not username:
        flash('Please log in first.', 'error')
        return redirect(url_for('login'))
    return render_template('dashboard.html', username=username)

# ------------ ADMIN ROUTE ------------
@app.route('/admin')
def admin():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Fetch users
                permission_fallback = False
                users = []
                try:
                    cur.execute("SELECT id, firstname, lastname, username, permission_level, submissions FROM users")
                    users = cur.fetchall()
                except Exception:
                    cur.execute("SELECT id, firstname, lastname, username FROM users")
                    users = cur.fetchall()
                    permission_fallback = True

                # Fetch resources
                cur.execute("SELECT id, name FROM resources")
                resources = cur.fetchall()

                # Fetch equipment
                cur.execute("SELECT id, name, status FROM equipment")
                equipment_list = cur.fetchall()

        return render_template(
            'admin.html',
            users=users,
            resources=resources,
            equipment_list=equipment_list,
            permission_fallback=permission_fallback
        )
    except Exception as e:
        print(f"Admin Data Load Error: {e}")
        flash("Failed to load admin dashboard.", "error")
        return render_template(
            'admin.html',
            users=[],
            resources=[],
            equipment_list=[],
            permission_fallback=True
        )
# --------------------------------------

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('Logged out.', 'success')
    return redirect(url_for('login'))

# -------- RESOURCE MANAGEMENT ---------

@app.route('/add_resource', methods=['POST'])
def add_resource():
    name = request.form.get('name')
    if not name:
        flash('Resource name is required.', 'error')
        return redirect(url_for('admin'))
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('INSERT INTO resources (name) VALUES (%s)', (name,))
                conn.commit()
        flash("Resource added successfully!", "success")
    except Exception as e:
        print(f"Failed to add resource: {e}")
        flash("Failed to add resource.", "error")
    return redirect(url_for('admin'))

@app.route('/delete_resource/<int:resource_id>', methods=['POST'])
def delete_resource(resource_id):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('DELETE FROM resources WHERE id=%s', (resource_id,))
                conn.commit()
        flash("Resource deleted!", "success")
    except Exception as e:
        print(f"Failed to delete resource: {e}")
        flash("Failed to delete resource.", "error")
    return redirect(url_for('admin'))

# -------- EQUIPMENT MANAGEMENT --------

@app.route('/add_equipment', methods=['POST'])
def add_equipment():
    name = request.form.get('name')
    status = request.form.get('status')
    if not name or not status:
        flash('Both name and status are required for equipment.', 'error')
        return redirect(url_for('admin'))
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('INSERT INTO equipment (name, status) VALUES (%s, %s)', (name, status))
                conn.commit()
        flash("Equipment added successfully!", "success")
    except Exception as e:
        print(f"Failed to add equipment: {e}")
        flash("Failed to add equipment.", "error")
    return redirect(url_for('admin'))

@app.route('/delete_equipment/<int:equipment_id>', methods=['POST'])
def delete_equipment(equipment_id):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('DELETE FROM equipment WHERE id=%s', (equipment_id,))
                conn.commit()
        flash("Equipment deleted!", "success")
    except Exception as e:
        print(f"Failed to delete equipment: {e}")
        flash("Failed to delete equipment.", "error")
    return redirect(url_for('admin'))

# -------------- USERS -----------------

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('DELETE FROM users WHERE id=%s', (user_id,))
                conn.commit()
        flash("User deleted!", "success")
    except Exception as e:
        print(f"Failed to delete user: {e}")
        flash("Failed to delete user.", "error")
    return redirect(url_for('admin'))

# ----------- MIGRATION COLUMN FIX -------------
def ensure_columns_exist():
    """Ensures all needed columns exist in the table to avoid migration crashes."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Add columns if missing
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='users'")
            columns = set(row['column_name'] for row in cur.fetchall())
            alter_list = []
            if 'permission_level' not in columns:
                alter_list.append("ADD COLUMN permission_level VARCHAR(20) DEFAULT 'User'")
            if 'submissions' not in columns:
                alter_list.append("ADD COLUMN submissions INTEGER DEFAULT 0")
            if alter_list:
                cur.execute(f"ALTER TABLE users {', '.join(alter_list)}")
            conn.commit()

if __name__ == '__main__':
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # USERS table
                cur.execute('''
                            CREATE TABLE IF NOT EXISTS users (
                                                                 id SERIAL PRIMARY KEY,
                                                                 firstname VARCHAR(100) NOT NULL,
                                lastname VARCHAR(100) NOT NULL,
                                username VARCHAR(100) UNIQUE NOT NULL,
                                password_hash VARCHAR(255) NOT NULL,
                                permission_level VARCHAR(20) DEFAULT 'User',
                                submissions INTEGER DEFAULT 0,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                                )
                            ''')
                # RESOURCES
                cur.execute('''
                            CREATE TABLE IF NOT EXISTS resources (
                                                                     id SERIAL PRIMARY KEY,
                                                                     name VARCHAR(100) NOT NULL
                                )
                            ''')
                # EQUIPMENT
                cur.execute('''
                            CREATE TABLE IF NOT EXISTS equipment (
                                                                     id SERIAL PRIMARY KEY,
                                                                     name VARCHAR(100) NOT NULL,
                                status VARCHAR(50) NOT NULL
                                )
                            ''')

                conn.commit()

        # Migrate table columns if necessary (safe-guard for old DBs)
        ensure_columns_exist()
        print("Database connection and table setup successful!")
    except Exception as e:
        print(f"Database setup error: {e}")

    app.run(debug=True)