from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
# import sqlite3  # or you can use SQLAlchemy later

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Required for flash messages

# Database setup (commented out for now)
"""
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            login_name TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Optional: Create an admin user for testing
    # admin_password = generate_password_hash('admin_password')
    # try:
    #     c.execute('''
    #         INSERT INTO users (login_name, password_hash, first_name, last_name, email)
    #         VALUES (?, ?, ?, ?, ?)
    #     ''', ('admin', admin_password, 'Admin', 'User', 'admin@example.com'))
    # except sqlite3.IntegrityError:
    #     print('Admin user already exists')
    
    conn.commit()
    conn.close()

def register_user(login_name, password, first_name, last_name, email):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        c.execute('''
            INSERT INTO users (login_name, password_hash, first_name, last_name, email)
            VALUES (?, ?, ?, ?, ?)
        ''', (login_name, hashed_password, first_name, last_name, email))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()
"""

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_name = request.form['login_name']
        password = request.form['password']
        
        # Database authentication (to be implemented)
        """
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        user = c.execute('SELECT * FROM users WHERE login_name = ?', (login_name,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user[2], password):
            flash(f'Welcome back, {user[3]}!', 'success')
            return redirect(url_for('dashboard'))
        """
        
        # Temporary placeholder response
        if login_name == "admin" and password == "password":
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid login name or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        login_name = request.form['login_name']
        password = request.form['password']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        
        # Registration logic (to be implemented)
        """
        if register_user(login_name, password, first_name, last_name, email):
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Login name or email already exists', 'error')
        """
        
        flash('Registration functionality coming soon!', 'info')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

if __name__ == '__main__':
    # init_db()  # Uncomment when ready to set up the database
    app.run(debug=True)