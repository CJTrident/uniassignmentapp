from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
from psycopg2.extras import RealDictCursor
import traceback
import uuid

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this to a random secret key

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
        firstName = request.form['firstName']
        lastName = request.form['lastName']
        username = request.form['username']
        password = request.form['password']

        # Validate password requirements
        if len(password) < 6 or not any(char in '!@#$%^&*(),.?":{}|<>' for char in password):
            flash('Password does not meet requirements!', 'error')
            return redirect(url_for('register'))

        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Check if username already exists
                    cur.execute('SELECT * FROM users WHERE username = %s', (username,))
                    if cur.fetchone() is not None:
                        flash('Username already exists!', 'error')
                        return redirect(url_for('register'))

                    # Hash the password
                    hashed_password = generate_password_hash(password)

                    # Insert new user
                    cur.execute(
                        'INSERT INTO users (firstname, lastname, username, password_hash) VALUES (%s, %s, %s, %s)',
                        (firstName, lastName, username, hashed_password)
                    )

                    conn.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))

        except Exception as e:
            print(f"Database Error: {e}")
            flash('Registration failed! Please try again.', 'error')
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Get user
                    cur.execute('SELECT * FROM users WHERE username = %s', (username,))
                    user = cur.fetchone()

                    if user and check_password_hash(user['password_hash'], password):
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
    return render_template('dashboard.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

if __name__ == '__main__':
    # Test database connection on startup
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Create users table if it doesn't exist
                cur.execute('''
                            CREATE TABLE IF NOT EXISTS users (
                                                                 id SERIAL PRIMARY KEY,
                                                                 firstname VARCHAR(100) NOT NULL,
                                lastname VARCHAR(100) NOT NULL,
                                username VARCHAR(100) UNIQUE NOT NULL,
                                password_hash VARCHAR(255) NOT NULL,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                                )
                            ''')
                conn.commit()
        print("Database connection and table setup successful!")
    except Exception as e:
        print(f"Database setup error: {e}")

    app.run(debug=True)  # Set debug=False for production