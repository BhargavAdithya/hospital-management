from flask import Flask
from config import Config
from models import db, User, Patient, Appointment, Prescription
from flask_login import LoginManager

login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialise extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'       # redirect here if not logged in
    login_manager.login_message = 'Please log in to continue.'

    # Register blueprints
    from routes.auth         import auth_bp
    from routes.receptionist import receptionist_bp
    from routes.doctor       import doctor_bp
    from routes.patient      import patient_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(receptionist_bp)
    app.register_blueprint(doctor_bp)
    app.register_blueprint(patient_bp)

    # Create tables and seed default users on first run
    with app.app_context():
        db.create_all()
        seed_users()

    return app


@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))


def seed_users():
    """Create default doctor and receptionist accounts if they don't exist."""
    from models import User
    if not User.query.filter_by(username='receptionist1').first():
        r = User(username='receptionist1', role='receptionist')
        r.set_password('rec123')
        db.session.add(r)

    if not User.query.filter_by(username='doctor1').first():
        d = User(username='doctor1', role='doctor')
        d.set_password('doc123')
        db.session.add(d)

    db.session.commit()


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)