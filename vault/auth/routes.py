from flask import render_template, url_for, flash, redirect, request, session
from flask_login import login_user, current_user, logout_user, login_required
from vault import db
from vault.models import User
from vault.auth import auth_bp
from vault.auth.forms import RegistrationForm, LoginForm
from vault.crypto_utils import generate_user_keys
from werkzeug.security import generate_password_hash, check_password_hash
from vault.auth.utils import send_otp_email
import random
import string
from datetime import datetime, timedelta
import re

@auth_bp.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        
        try:
            user = User.query.filter_by(email=email).first()
            if user and check_password_hash(user.password, password):
                # Generate OTP
                otp = ''.join(random.choices(string.digits, k=6))
                user.otp_code = otp
                user.otp_expiry = datetime.now() + timedelta(minutes=10)
                
                db.session.commit()
                
                # Send Email
                send_otp_email(user)
                flash('OTP sent to your email. Please verify.', 'info')
                
                # ALWAYS PRINT OTP FOR DEBUGGING (Development only)
                print(f"\n{'='*30}")
                print(f"DEBUG OTP: {otp}")
                print(f"{'='*30}\n") 

                # Store user ID in session for the next step
                session['pre_2fa_user_id'] = user.id
                return redirect(url_for('auth.verify_otp'))
            else:
                flash('Login Unsuccessful. Please check email and password', 'danger')

        except Exception as e:
            db.session.rollback()
            print(f"LOGIN ERROR: {e}") # This will show in Vercel logs
            flash(f'An error occurred: {str(e)}', 'danger')
            
    return render_template('auth/login.html', form=form)

@auth_bp.route("/verify-otp", methods=['GET', 'POST'])
def verify_otp():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
        
    user_id = session.get('pre_2fa_user_id')
    print(f"\n[DEBUG] verify_otp accessed. Session user_id: {user_id}")
    
    if not user_id:
        print("[DEBUG] No user_id in session. Redirecting to login.")
        flash("Session expired or invalid. Please login to verify OTP.", "warning")
        return redirect(url_for('auth.login'))
        
    user = User.query.get(user_id)
    if not user:
        print(f"[DEBUG] User {user_id} not found in DB. Redirecting to login.")
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        otp = request.form.get('otp')
        
        if user.otp_code == otp and user.otp_expiry > datetime.now():
            # Clear OTP fields
            user.otp_code = None
            user.otp_expiry = None
            db.session.commit()
            
            # Login User
            login_user(user, remember=True)
            session.pop('pre_2fa_user_id', None)
            return redirect(url_for('main.dashboard'))
        else:
            flash('Invalid or expired OTP', 'danger')

    return render_template('auth/verify_otp.html')

@auth_bp.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        try:
            # Validation
            email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_regex, email):
                flash('Invalid email address format.', 'danger')
                return render_template('auth/login.html', form=RegistrationForm())

            if len(password) < 8:
                flash('Password must be at least 8 characters long.', 'danger')
                return render_template('auth/login.html', form=RegistrationForm())
                
            if not re.search(r'[a-zA-Z]', password) or not re.search(r'[0-9]', password):
                 flash('Password must contain both letters and numbers.', 'danger')
                 return render_template('auth/login.html', form=RegistrationForm())

            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                 flash('Email already exists.', 'danger')
                 return render_template('auth/login.html', form=RegistrationForm())

            from vault.crypto_utils import generate_user_keys
            priv_key, pub_key = generate_user_keys()
            
            hashed_password = generate_password_hash(password)
            new_user = User(
                email=email, 
                password=hashed_password,
                rsa_private_key=priv_key,
                rsa_public_key=pub_key
            )
            db.session.add(new_user)
            db.session.commit()
            
            # --- START OTP FLOW IMMEDIATELY ---
            # Generate OTP
            otp = ''.join(random.choices(string.digits, k=6))
            new_user.otp_code = otp
            new_user.otp_expiry = datetime.now() + timedelta(minutes=10)
            db.session.commit()
            
            # Send Email
            from vault.auth.utils import send_otp_email
            send_otp_email(new_user)
            
            # Debug OTP
            print(f"\n{'='*30}")
            print(f"DEBUG OTP (Register): {otp}")
            print(f"DEBUG New User ID: {new_user.id}")
            print(f"{'='*30}\n")
            
            # Store user ID in session for verify_otp
            session['pre_2fa_user_id'] = new_user.id
            session.modified = True # Force session save
            flash('Account created! OTP sent to your email.', 'info')
            return redirect(url_for('auth.verify_otp'))
            # ----------------------------------

        except Exception as e:
            db.session.rollback()
            print(f"REGISTER ERROR: {e}")
            flash(f'An error occurred during registration: {str(e)}', 'danger')
            return render_template('auth/login.html', form=RegistrationForm())
        
    return render_template('auth/login.html', form=RegistrationForm())

@auth_bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('auth.login'))