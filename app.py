from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
import traceback
import uuid

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Required for flash messages


def generate_error_id():
    """Generate a unique error ID for tracking"""
    return str(uuid.uuid4())[:8]


@app.errorhandler(404)
def not_found_error(error):
    error_id = generate_error_id()
    error_message = "The page you're looking for doesn't exist or has been moved."

    print(f"404 Error (ID: {error_id}): {request.url}")

    return render_template(
        '404.html',
        error_message=error_message,
        error_id=error_id
    ), 404


@app.errorhandler(500)
def internal_error(error):
    error_id = generate_error_id()
    error_message = "Something went wrong on our end. Our team has been notified."

    print(f"500 Error (ID: {error_id}): {str(error)}")
    print(traceback.format_exc())

    return render_template(
        '404.html',
        error_message=error_message,
        error_id=error_id
    ), 500


# Your existing routes
@app.route('/')
def home():
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_name = request.form['login_name']
        password = request.form['password']

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

        flash('Registration functionality coming soon!', 'info')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


# Optional test route for 500 errors (remove in production)
@app.route('/test-500')
def test_500():
    raise Exception("Test 500 error")


if __name__ == '__main__':
    app.run(debug=False)  # Set debug=False for production