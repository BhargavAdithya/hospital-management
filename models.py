from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role          = db.Column(db.String(20), nullable=False)  # 'doctor' or 'receptionist'

    # If the user is a doctor, they have appointments assigned to them
    appointments  = db.relationship('Appointment', backref='doctor', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'


class Patient(db.Model):
    __tablename__ = 'patients'

    id           = db.Column(db.Integer, primary_key=True)
    name         = db.Column(db.String(120), nullable=False)
    age          = db.Column(db.Integer, nullable=False)
    gender       = db.Column(db.String(10), nullable=False)
    contact      = db.Column(db.String(15), nullable=False)
    email        = db.Column(db.String(120), nullable=True)
    address      = db.Column(db.Text, nullable=True)
    admitted_at  = db.Column(db.DateTime, default=datetime.utcnow)

    # One patient can have multiple appointments
    appointments = db.relationship('Appointment', backref='patient', lazy=True)

    def __repr__(self):
        return f'<Patient {self.name}>'


class Appointment(db.Model):
    __tablename__ = 'appointments'

    id         = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id  = db.Column(db.Integer, db.ForeignKey('users.id'),    nullable=False)
    date       = db.Column(db.Date,    nullable=False)
    time       = db.Column(db.Time,    nullable=False)

    # pending / accepted / rejected
    status     = db.Column(db.String(20), default='pending', nullable=False)

    rescheduled  = db.Column(db.Boolean, default=False, nullable=False)
    self_booked  = db.Column(db.Boolean, default=False, nullable=False)
    # One appointment has at most one prescription
    prescription = db.relationship('Prescription', backref='appointment',
                                   uselist=False, lazy=True)

    def __repr__(self):
        return f'<Appointment patient={self.patient_id} doctor={self.doctor_id}>'


class Prescription(db.Model):
    __tablename__ = 'prescriptions'

    id             = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=False)
    symptoms       = db.Column(db.Text, nullable=False, default='')
    notes          = db.Column(db.Text, nullable=False)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Prescription appointment={self.appointment_id}>'