from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from functools import wraps

app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///banking.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Models
class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    bank_account_number = db.Column(db.String(20), unique=True, nullable=False)
    account_type = db.Column(db.String(20), nullable=False)
    balance = db.Column(db.Float, default=0.0)
    date_opened = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(10), default='active')

# Create tables
with app.app_context():
    db.create_all()
    # Create default admin if none exists
    if not Admin.query.filter_by(username='admin').first():
        default_admin = Admin(
            username='admin',
            email='admin@example.com',
            password=generate_password_hash('admin123')
        )
        db.session.add(default_admin)
        db.session.commit()

# Decorators for access control
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_role' not in session or session['user_role'] != 'admin':
            flash('You do not have permission to access this page', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Check if admin
        admin = Admin.query.filter_by(username=username).first()
        if admin and check_password_hash(admin.password, password):
            session['user_id'] = admin.id
            session['username'] = admin.username
            session['user_role'] = 'admin'
            flash('Welcome, Admin!', 'success')
            return redirect(url_for('admin_dashboard'))
        
        # If not admin, check if it's a customer (using email as username)
        customer = Customer.query.filter_by(email=username).first()
        if customer and customer.status == 'active' and check_password_hash(customer.password, password):
            session['user_id'] = customer.id
            session['username'] = customer.full_name
            session['user_role'] = 'customer'
            flash('Welcome, Customer!', 'success')
            return redirect(url_for('customer_dashboard'))
        
        flash('Invalid credentials or inactive account', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    if session.get('user_role') == 'admin':
        return redirect(url_for('admin_dashboard'))
    else:
        return redirect(url_for('customer_dashboard'))

# Admin routes
@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    admin_count = Admin.query.count()
    customer_count = Customer.query.count()
    active_customers = Customer.query.filter_by(status='active').count()
    return render_template('admin/dashboard.html', 
                          admin_count=admin_count, 
                          customer_count=customer_count,
                          active_customers=active_customers)

@app.route('/admin/admins')
@login_required
@admin_required
def admin_list():
    admins = Admin.query.all()
    return render_template('admin/admin_list.html', admins=admins)

@app.route('/admin/admins/add', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_add():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validation
        if not username or not email or not password:
            flash('All fields are required', 'danger')
            return redirect(url_for('admin_add'))
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('admin_add'))
        
        if Admin.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('admin_add'))
        
        if Admin.query.filter_by(email=email).first():
            flash('Email already exists', 'danger')
            return redirect(url_for('admin_add'))
        
        # Create new admin
        new_admin = Admin(
            username=username,
            email=email,
            password=generate_password_hash(password)
        )
        db.session.add(new_admin)
        db.session.commit()
        
        flash('Admin created successfully', 'success')
        return redirect(url_for('admin_list'))
    
    return render_template('admin/admin_form.html')

@app.route('/admin/admins/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit(id):
    admin = Admin.query.get_or_404(id)
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Validation
        if not username or not email:
            flash('Username and email are required', 'danger')
            return redirect(url_for('admin_edit', id=id))
        
        existing_admin = Admin.query.filter_by(username=username).first()
        if existing_admin and existing_admin.id != id:
            flash('Username already exists', 'danger')
            return redirect(url_for('admin_edit', id=id))
        
        existing_admin = Admin.query.filter_by(email=email).first()
        if existing_admin and existing_admin.id != id:
            flash('Email already exists', 'danger')
            return redirect(url_for('admin_edit', id=id))
        
        # Update admin
        admin.username = username
        admin.email = email
        if password:
            admin.password = generate_password_hash(password)
        
        db.session.commit()
        flash('Admin updated successfully', 'success')
        return redirect(url_for('admin_list'))
    
    return render_template('admin/admin_form.html', admin=admin)

@app.route('/admin/admins/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def admin_delete(id):
    admin = Admin.query.get_or_404(id)
    
    # Prevent deleting yourself
    if admin.id == session['user_id']:
        flash('You cannot delete your own account', 'danger')
        return redirect(url_for('admin_list'))
    
    db.session.delete(admin)
    db.session.commit()
    flash('Admin deleted successfully', 'success')
    return redirect(url_for('admin_list'))

# Customer routes (for admin)
@app.route('/admin/customers')
@login_required
@admin_required
def customer_list():
    customers = Customer.query.all()
    return render_template('admin/customer_list.html', customers=customers)

@app.route('/admin/customers/add', methods=['GET', 'POST'])
@login_required
@admin_required
def customer_add():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        account_type = request.form.get('account_type')
        balance = float(request.form.get('balance', 0))
        status = request.form.get('status')
        
        # Generate a unique account number (simplified for demo)
        import random
        bank_account_number = f"ACC{random.randint(10000, 99999)}"
        
        # Validation
        if not full_name or not email or not account_type or not password:
            flash('Name, email, password and account type are required', 'danger')
            return redirect(url_for('customer_add'))
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('customer_add'))
        
        if Customer.query.filter_by(email=email).first():
            flash('Email already exists', 'danger')
            return redirect(url_for('customer_add'))
        
        # Create new customer
        new_customer = Customer(
            full_name=full_name,
            email=email,
            password=generate_password_hash(password),
            bank_account_number=bank_account_number,
            account_type=account_type,
            balance=balance,
            status=status or 'active'
        )
        db.session.add(new_customer)
        db.session.commit()
        
        flash('Customer created successfully', 'success')
        return redirect(url_for('customer_list'))
    
    return render_template('admin/customer_form.html')

@app.route('/admin/customers/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def customer_edit(id):
    customer = Customer.query.get_or_404(id)
    
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        account_type = request.form.get('account_type')
        balance = float(request.form.get('balance', 0))
        status = request.form.get('status')
        
        # Validation
        if not full_name or not email or not account_type:
            flash('Name, email and account type are required', 'danger')
            return redirect(url_for('customer_edit', id=id))
        
        if password and password != confirm_password:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('customer_edit', id=id))
        
        existing_customer = Customer.query.filter_by(email=email).first()
        if existing_customer and existing_customer.id != id:
            flash('Email already exists', 'danger')
            return redirect(url_for('customer_edit', id=id))
        
        # Update customer
        customer.full_name = full_name
        customer.email = email
        customer.account_type = account_type
        customer.balance = balance
        customer.status = status
        
        if password:
            customer.password = generate_password_hash(password)
        
        db.session.commit()
        flash('Customer updated successfully', 'success')
        return redirect(url_for('customer_list'))
    
    return render_template('admin/customer_form.html', customer=customer)

@app.route('/admin/customers/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def customer_delete(id):
    customer = Customer.query.get_or_404(id)
    db.session.delete(customer)
    db.session.commit()
    flash('Customer deleted successfully', 'success')
    return redirect(url_for('customer_list'))

# Customer dashboard
@app.route('/customer/dashboard')
@login_required
def customer_dashboard():
    if session.get('user_role') != 'customer':
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    
    customer = Customer.query.get(session['user_id'])
    return render_template('customer/dashboard.html', customer=customer)

# Handler for Vercel serverless deployment
def handler(event, context):
    return app

if __name__ == '__main__':
    app.run(debug=False)
