from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Patient, Appointment, User
from forms import PatientForm, AppointmentForm
from datetime import date

receptionist_bp = Blueprint('receptionist', __name__)


def receptionist_only(f):
    """Decorator to block non-receptionists from accessing a route."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role != 'receptionist':
            flash('Access denied.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


@receptionist_bp.route('/receptionist/dashboard')
@login_required
@receptionist_only
def dashboard():
    # Show all appointments along with patient and doctor info
    appointments = (Appointment.query
                    .order_by(Appointment.date.desc(), Appointment.time.desc())
                    .all())
    return render_template('receptionist_dashboard.html',
                           appointments=appointments)


@receptionist_bp.route('/receptionist/add_patient', methods=['GET', 'POST'])
@login_required
@receptionist_only
def add_patient():
    patient_form     = PatientForm()
    appointment_form = AppointmentForm()

    # Populate doctor dropdown with only users who are doctors
    doctors = User.query.filter_by(role='doctor').all()
    appointment_form.doctor_id.choices = [(d.id, d.username) for d in doctors]

    if patient_form.validate_on_submit() and appointment_form.validate_on_submit():
        # --- Double-booking validation ---
        conflict = Appointment.query.filter_by(
            doctor_id=appointment_form.doctor_id.data,
            date=appointment_form.date.data,
            time=appointment_form.time.data
        ).first()

        if conflict:
            flash('That doctor already has an appointment at this date and time. '
                  'Please choose a different slot.', 'danger')
        else:
            # Save the new patient
            patient = Patient(
                name    = patient_form.name.data,
                age     = patient_form.age.data,
                gender  = patient_form.gender.data,
                contact = patient_form.contact.data
            )
            db.session.add(patient)
            db.session.flush()  # get patient.id before committing

            # Save the appointment linked to this patient
            appointment = Appointment(
                patient_id = patient.id,
                doctor_id  = appointment_form.doctor_id.data,
                date       = appointment_form.date.data,
                time       = appointment_form.time.data,
                status     = 'pending'
            )
            db.session.add(appointment)
            db.session.commit()

            flash(f'Patient {patient.name} admitted and appointment booked.', 'success')
            return redirect(url_for('receptionist.dashboard'))

    return render_template('add_patient.html',
                           patient_form=patient_form,
                           appointment_form=appointment_form)