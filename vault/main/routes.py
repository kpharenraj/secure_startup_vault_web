import os
import uuid
import io
from flask import render_template, url_for, flash, redirect, request, current_app, send_file, make_response
from flask_login import current_user, login_required
from flask_wtf.csrf import generate_csrf
from flask_mail import Message
from vault import db
# CHANGE: Import the blueprint from the local __init__.py file
from vault.extensions import main_bp 
from vault.main.forms import UploadFileForm, ContactForm
from vault.models import File, Company, memberships
from vault.auth.utils import send_email_sync
from sqlalchemy import select

def _get_user_companies():
    if not current_user.is_authenticated:
        return []
    owned_companies = Company.query.filter_by(owner_id=current_user.id).all()
    member_companies_query = db.session.execute(
        select(Company).join(memberships, Company.id == memberships.c.company_id).where(memberships.c.user_id == current_user.id)
    ).all()
    member_companies = [row[0] for row in member_companies_query]
    # dedupe by id
    companies_map = {c.id: c for c in owned_companies}
    for c in member_companies:
        companies_map[c.id] = c
    return list(companies_map.values())
from vault.crypto_utils import decrypt_file_data
from vault.crypto_utils import encrypt_file_data, decrypt_file_data

# REMOVE the line: main_bp = Blueprint("main", __name__) 
# (It is now created in __init__.py)

@main_bp.route("/")
def index():
    return render_template('main/index.html')

@main_bp.route("/dashboard")
@login_required
def dashboard():
    # ... rest of your code remains the same ...
    # Fetch user's personal files (where company_id is NULL)
    user_files = File.query.filter_by(user_id=current_user.id, company_id=None).all()
    
    # Calculate file sizes (based on DB data length)
    for file in user_files:
        if file.data:
            file.size = len(file.data)
        else:
            file.size = 0
    
    # Fetch companies for the sidebar list (owned or member)
    from sqlalchemy import select
    owned_companies = Company.query.filter_by(owner_id=current_user.id).all()
    member_companies_query = db.session.execute(
        select(Company).join(memberships, Company.id == memberships.c.company_id).where(memberships.c.user_id == current_user.id)
    ).all()
    member_companies = [row[0] for row in member_companies_query]
    user_companies = list(set(owned_companies + member_companies))
    form = UploadFileForm()
    return render_template('main/dashboard.html', 
                           files=user_files, 
                           companies=user_companies, 
                           form=form,
                           company=None,
                           csrf_token=generate_csrf())

@main_bp.route("/upload", methods=['POST'])
@login_required
def upload_file():
    form = UploadFileForm()
    if form.validate_on_submit():
        file_storage = form.file.data
        original_filename = file_storage.filename
        # Validate extension (defensive)
        _, ext = os.path.splitext(original_filename)
        ext = ext.lower().lstrip('.')
        allowed = {'pdf', 'txt', 'docx', 'png', 'jpg', 'jpeg'}
        if ext not in allowed:
            flash('File type not allowed. Allowed: PDF, TXT, DOCX, PNG, JPG', 'danger')
            return redirect(url_for('main.dashboard'))

        # 1. Read file and Encrypt
        file_content = file_storage.read()
        encrypted_data, aes_key, iv = encrypt_file_data(file_content, current_user.rsa_public_key)
        
        # 2. Save encrypted blob to DB (instead of disk)
        unique_name = str(uuid.uuid4())
        # file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_name)
        
        # with open(file_path, 'wb') as f:
        #     f.write(encrypted_data)
        
        # 3. Save metadata to DB
        new_file = File(
            filename=original_filename,
            encrypted_name=unique_name,
            data=encrypted_data, # Store file content in DB
            encrypted_aes_key=aes_key,
            iv=iv,
            user_id=current_user.id
        )
        db.session.add(new_file)
        db.session.commit()
        
        flash(f'File "{original_filename}" has been encrypted and secured!', 'success')
    return redirect(url_for('main.dashboard'))

@main_bp.route("/download/<int:file_id>")
@login_required
def download_file(file_id):
    try:
        file_record = File.query.get_or_404(file_id)
        
        # Check ownership
        if file_record.user_id != current_user.id:
            flash("Unauthorized access!", "danger")
            return redirect(url_for('main.dashboard'))
        
        # Read encrypted data from DB
        encrypted_data = file_record.data
        
        if not encrypted_data:
            flash("File not found in database (Legacy file or error).", "danger")
            return redirect(url_for('main.dashboard'))
        
        # Decrypt using User's Private Key
        decrypted_data = decrypt_file_data(
            encrypted_data, 
            file_record.encrypted_aes_key, 
            file_record.iv, 
            current_user.rsa_private_key
        )
        
        # Send back to user with fresh BytesIO object
        file_stream = io.BytesIO(decrypted_data)
        
        return send_file(
            file_stream,
            download_name=file_record.filename,
            as_attachment=True,
            mimetype='application/octet-stream'
        )
    except Exception as e:
        flash(f"Error downloading file: {str(e)}", "danger")
        return redirect(url_for('main.dashboard'))

@main_bp.route('/file/delete/<int:file_id>', methods=['POST'])
@login_required
def delete_file(file_id):
    file_to_delete = File.query.get_or_404(file_id)
    if file_to_delete.user_id != current_user.id:
        flash("Unauthorized action.", "danger")
        return redirect(url_for('main.dashboard'))
    
    db.session.delete(file_to_delete)
    db.session.commit()
    flash("File removed from vault.", "success")
    return redirect(url_for('main.dashboard'))

@main_bp.route("/view/<int:file_id>")
@login_required
def view_file(file_id):
    file_record = File.query.get_or_404(file_id)
    
    # Check ownership
    if file_record.user_id != current_user.id:
        flash("Unauthorized access!", "danger")
        return redirect(url_for('main.dashboard'))
    
    # 1. Read encrypted data from DB
    encrypted_data = file_record.data
    
    if not encrypted_data:
         flash("File content not found.", "danger")
         return redirect(url_for('main.dashboard'))
    
    # 2. Decrypt using User's Private Key
    decrypted_data = decrypt_file_data(
        encrypted_data, 
        file_record.encrypted_aes_key, 
        file_record.iv, 
        current_user.rsa_private_key
    )
    
    # 3. Send back to user for viewing
    return send_file(
        io.BytesIO(decrypted_data),
        mimetype='application/pdf',  # Or detect type based on extension
        as_attachment=False
    )


@main_bp.route('/about')
def about():
    return render_template('main/about.html', companies=_get_user_companies())


@main_bp.route('/privacy')
def privacy():
    return render_template('main/privacy.html', companies=_get_user_companies())


@main_bp.route('/terms')
def terms():
    return render_template('main/terms.html', companies=_get_user_companies())


@main_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        sender_name = form.name.data.strip()
        sender_email = form.email.data.strip()
        subject = form.subject.data
        message_body = form.message.data.strip()
        admin_email = 'koyalkarpulkalharenraj@gmail.com'

        mail_user = current_app.config.get('MAIL_USERNAME')
        mail_password = current_app.config.get('MAIL_PASSWORD')
        if not mail_user or not mail_password:
            flash(
                'Email service is not configured right now. Please contact me directly at koyalkarpulkalharenraj@gmail.com.',
                'warning'
            )
            return redirect(url_for('main.contact'))

        msg = Message(
            subject=f'Contact Form - {subject}',
            sender=mail_user,
            recipients=[admin_email]
        )
        msg.body = (
            f'Contact form message from {sender_name} <{sender_email}>\n\n'
            f'Subject: {subject}\n\n'
            f'{message_body}\n\n'
            'Please reply to the sender email address above.'
        )

        try:
            send_email_sync(current_app._get_current_object(), msg)
            flash('Your message was sent successfully. I will contact you soon.', 'success')
        except Exception as e:
            current_app.logger.error(f'Contact email error: {e}')
            flash('Unable to send your message right now. Please try again later.', 'danger')
        return redirect(url_for('main.contact'))

    return render_template('main/contact.html', companies=_get_user_companies(), form=form)

@main_bp.route('/sitemap.xml')
def sitemap():
    """Generate sitemap.xml dynamically."""
    pages = []
    
    # All static pages that don't require login
    # Use _external=True to get the full URL (https://...)
    pages.append(url_for('auth.login', _external=True))
    pages.append(url_for('auth.register', _external=True))
    pages.append(url_for('main.about', _external=True))
    pages.append(url_for('main.privacy', _external=True))
    pages.append(url_for('main.terms', _external=True))
    pages.append(url_for('main.contact', _external=True))
    
    sitemap_xml = render_template('main/sitemap_template.xml', pages=pages)
    response = make_response(sitemap_xml)
    response.headers["Content-Type"] = "application/xml"
    return response

@main_bp.route('/robots.txt')
def robots():
    """Generate robots.txt dynamically."""
    lines = [
        "User-agent: *",
        "Disallow: /dashboard",
        "Disallow: /vault/",
        "Disallow: /companies/",
        f"Sitemap: {url_for('main.sitemap', _external=True)}"
    ]
    response = make_response("\n".join(lines))
    response.headers["Content-Type"] = "text/plain"
    return response

@main_bp.route('/favicon.ico')
def favicon():
    return current_app.send_static_file('img/shield-icon.svg')