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

# for CSRF error handling
from flask_wtf.csrf import CSRFError


@auth_bp.errorhandler(CSRFError)
def handle_csrf(error):
    # log the CSRF error for debugging
    print(f"CSRFError on {request.method} {request.path}: {error.description}")
    print(f"  Referer header: {request.headers.get('Referer', 'MISSING')}")
    print(f"  Origin header: {request.headers.get('Origin', 'MISSING')}")
    flash('Form submission failed. Please try again.', 'danger')
    return redirect(url_for('auth.login'))

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
            
    # render the template, ensuring register_mode is False
    return render_template('auth/login.html', form=form, register_mode=False)

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
    
    form = RegistrationForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        
        try:
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
            send_otp_email(new_user)
            
            # Debug OTP
            print(f"\n{'='*30}")
            print(f"DEBUG OTP (Register): {otp}")
            print(f"DEBUG New User ID: {new_user.id}")
            print(f"{'='*30}\n") 

            # Store user ID in session for the next step
            session['pre_2fa_user_id'] = new_user.id
            flash('OTP sent to your email. Please verify to complete registration.', 'info')
            return redirect(url_for('auth.verify_otp'))
            
        except Exception as e:
            db.session.rollback()
            print(f"REGISTER ERROR: {e}")
            flash(f'An error occurred: {str(e)}', 'danger')
            
    # when displaying registration page, signal register_mode=True
    return render_template('auth/login.html', form=form, register_mode=True)

@auth_bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('auth.login'))