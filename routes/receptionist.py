from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Patient, Appointment, User
from forms import PatientForm, AppointmentForm, RescheduleForm
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
            # --- Duplicate patient check by name + contact ---
            existing_patient = Patient.query.filter_by(
                name    = patient_form.name.data,
                contact = patient_form.contact.data
            ).first()

            if existing_patient:
                # Reuse existing patient, do not create a new record
                patient = existing_patient
                flash(f'Returning patient {patient.name} found. '
                      f'New appointment booked with previous history preserved.', 'info')
            else:
                # Brand new patient — create record
                patient = Patient(
                    name    = patient_form.name.data,
                    age     = patient_form.age.data,
                    gender  = patient_form.gender.data,
                    contact = patient_form.contact.data
                )
                db.session.add(patient)
                db.session.flush()

            # Save the appointment linked to this patient (new or existing)
            appointment = Appointment(
                patient_id = patient.id,
                doctor_id  = appointment_form.doctor_id.data,
                date       = appointment_form.date.data,
                time       = appointment_form.time.data,
                status     = 'pending'
            )
            db.session.add(appointment)
            db.session.commit()

            flash(f'Appointment booked for {patient.name}.', 'success')
            return redirect(url_for('receptionist.dashboard'))

    # Check if a returning patient exists based on name + contact typed so far
    existing_patient = None
    previous_prescriptions = []

    name_typed    = patient_form.name.data
    contact_typed = patient_form.contact.data

    if name_typed and contact_typed:
        existing_patient = Patient.query.filter_by(
            name=name_typed, contact=contact_typed
        ).first()
        if existing_patient:
            for appt in existing_patient.appointments:
                if appt.prescription:
                    previous_prescriptions.append({
                        'date'   : appt.date,
                        'doctor' : appt.doctor.username,
                        'notes'  : appt.prescription.notes
                    })

    return render_template('add_patient.html',
                           patient_form=patient_form,
                           appointment_form=appointment_form,
                           existing_patient=existing_patient,
                           previous_prescriptions=previous_prescriptions)

@receptionist_bp.route('/receptionist/reschedule/<int:appointment_id>',
                       methods=['GET', 'POST'])
@login_required
@receptionist_only
def reschedule(appointment_id):
    from datetime import time as dtime, datetime as dt
    from flask import request

    appointment = Appointment.query.get_or_404(appointment_id)
    form        = RescheduleForm()

    doctors = User.query.filter_by(role='doctor').all()
    form.doctor_id.choices = [(d.id, d.username) for d in doctors]

    # Read doctor + date from query params (set by JS on change)
    selected_doctor_id = request.args.get('doctor_id', appointment.doctor_id, type=int)
    selected_date_str  = request.args.get('date', '')

    # Build full list of 30-minute slots 09:00 → 17:30
    all_slots = []
    for hour in range(9, 18):
        for minute in [0, 30]:
            t = dtime(hour, minute)
            all_slots.append(t.strftime('%H:%M'))

    # Find slots rejected for this doctor on selected date
    blocked_slots = []
    if selected_date_str:
        try:
            selected_date_obj = dt.strptime(selected_date_str, '%Y-%m-%d').date()
            rejected = Appointment.query.filter_by(
                doctor_id = selected_doctor_id,
                date      = selected_date_obj,
                status    = 'rejected'
            ).all()
            blocked_slots = [a.time.strftime('%H:%M') for a in rejected]
        except ValueError:
            pass

    # Only show available (non-blocked) time slots
    available_slots = [(t, dt.strptime(t, '%H:%M').strftime('%I:%M %p'))
                       for t in all_slots if t not in blocked_slots]
    form.time.choices = available_slots if available_slots else [('', 'No slots available')]

    if form.validate_on_submit():
        new_date      = form.date.data
        new_time_str  = form.time.data
        new_doctor_id = form.doctor_id.data

        # Confirm chosen slot is not blocked for this doctor on new date
        rejected_check = Appointment.query.filter_by(
            doctor_id = new_doctor_id,
            date      = new_date,
            status    = 'rejected'
        ).all()
        rejected_times = [a.time.strftime('%H:%M') for a in rejected_check]

        if new_time_str in rejected_times:
            flash('That time slot was previously rejected by the doctor. '
                  'Please choose another slot.', 'danger')
        else:
            appointment.doctor_id = new_doctor_id
            appointment.date      = new_date
            appointment.time      = dt.strptime(new_time_str, '%H:%M').time()
            appointment.status    = 'pending'
            db.session.commit()
            flash('Appointment rescheduled successfully.', 'success')
            return redirect(url_for('receptionist.dashboard'))

    return render_template('reschedule.html',
                           form=form,
                           appointment=appointment,
                           blocked_slots=blocked_slots,
                           selected_doctor_id=selected_doctor_id,
                           selected_date_str=selected_date_str)