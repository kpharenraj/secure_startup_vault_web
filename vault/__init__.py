import os
from flask import Flask
# Added 'csrf' to the import list
from .extensions import db, login_manager, main_bp, csrf, mail 

def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # --- CLOUD DEPLOYMENT HARDWIRING ---
    # Use Vercel Environment Variables if they exist, otherwise use local defaults
    app.config['SECRET_KEY'] = 'fixed-secret-key-for-vercel-2026-secure-vault'
    
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        # Fix: Vercel/Neon often provide 'postgres://', but SQLAlchemy needs 'postgresql://'
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    else:
        # Fallback to your local instance folder database
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../instance/vault.db'
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    # -----------------------------------

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    
    # Initialize Migrate
    from .extensions import migrate
    migrate.init_app(app, db)

    # --- EMAIL CONFIGURATION ---
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.googlemail.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    # ---------------------------
    
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    with app.app_context():
        # Register Blueprints
        from .auth import auth_bp
        from .companies import companies_bp
        from .api import api_bp
        from .main import routes 

        app.register_blueprint(auth_bp)
        app.register_blueprint(main_bp) 
        app.register_blueprint(companies_bp)
        app.register_blueprint(api_bp)

        # Build tables automatically (ONLY if they don't exist)
        from . import models
        try:
            db.create_all()
        except Exception as e:
            print(f"Table creation skipped or failed: {e}")

    # --- AUTOMATIC SCHEMA MIGRATION (For Vercel/Production) ---
    with app.app_context():
        from sqlalchemy import text
        try:
            # Check/Add 'data' column to 'file' table
            with db.engine.connect() as conn:
                # 1. Update File table
                try:
                    conn.execute(text("ALTER TABLE file ADD COLUMN data BYTEA"))
                    conn.commit()
                    print("Added 'data' column to 'file' table.")
                except Exception as e:
                    # Column likely exists or table doesn't exist yet (handled by db.create_all)
                    # For SQLite (local), syntax is different (ADD COLUMN data BLOB)
                    # But assuming Vercel is Postgres. Handling SQLite fallback just in case.
                    if "sqlite" in str(app.config['SQLALCHEMY_DATABASE_URI']):
                         try:
                             conn.execute(text("ALTER TABLE file ADD COLUMN data BLOB"))
                             conn.commit()
                         except:
                             pass
                    pass

                # 2. Update Company table
                try:
                    conn.execute(text("ALTER TABLE company ADD COLUMN logo_data BYTEA"))
                    conn.commit()
                    print("Added 'logo_data' column to 'company' table.")
                except Exception as e:
                     if "sqlite" in str(app.config['SQLALCHEMY_DATABASE_URI']):
                         try:
                             conn.execute(text("ALTER TABLE company ADD COLUMN logo_data BLOB"))
                             conn.commit()
                         except:
                             pass
                     pass

        except Exception as e:
            print(f"Schema migration error (ignored if tables/columns exist): {e}")

    # --- FIX FOR READ-ONLY FILE SYSTEM ---
    # We now store files in DB, so UPLOAD_FOLDER is less critical but kept for temp ops if needed
    if os.environ.get('VERCEL'):
        app.config['UPLOAD_FOLDER'] = '/tmp'
    else:
        app.config['UPLOAD_FOLDER'] = os.path.abspath(os.path.join(app.root_path, '..', 'uploads'))
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])

    # --- SECURITY HEADERS ---
    # Add common headers to mitigate scripting attacks and clickjacking
    @app.after_request
    def set_security_headers(response):
        response.headers['Content-Security-Policy'] = "default-src 'self'; img-src 'self' https://upload.wikimedia.org; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline';"
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'no-referrer'
        return response

    return app




    