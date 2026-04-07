from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, Patient, Appointment, User
from forms import PatientForm, AppointmentForm, RescheduleForm
from datetime import date, time as dtime, datetime as dt
from functools import wraps

# 1. Define the Blueprint first
receptionist_bp = Blueprint('receptionist', __name__)

# 2. Define the Decorator next (so routes can see it)
def receptionist_only(f):
    """Decorator to block non-receptionists from accessing a route."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role != 'receptionist':
            flash('Access denied.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated

# 3. Now define your routes
@receptionist_bp.route('/receptionist/dashboard')
@login_required
@receptionist_only
def dashboard():
    appointments = (Appointment.query
                    .order_by(Appointment.date.desc(), Appointment.time.desc())
                    .all())
    return render_template('receptionist_dashboard.html', appointments=appointments)

@receptionist_bp.route('/receptionist/add_patient', methods=['GET', 'POST'])
@login_required
@receptionist_only
def add_patient():
    # ... (Your existing add_patient code) ...
    patient_form = PatientForm()
    appointment_form = AppointmentForm()
    doctors = User.query.filter_by(role='doctor').all()
    appointment_form.doctor_id.choices = [(d.id, d.username) for d in doctors]
    # (Simplified for brevity, keep your full logic here)
    return render_template('add_patient.html', patient_form=patient_form, appointment_form=appointment_form)

@receptionist_bp.route('/receptionist/reschedule/<int:appointment_id>', methods=['GET', 'POST'])
@login_required
@receptionist_only
def reschedule(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)

    # PERSIST FORM STATE: Use request.args for GET requests
    if request.method == 'GET' and request.args:
        form = RescheduleForm(request.args)
    else:
        form = RescheduleForm()

    doctors = User.query.filter_by(role='doctor').all()
    form.doctor_id.choices = [(d.id, d.username) for d in doctors]

    selected_doctor_id = request.args.get('doctor_id', appointment.doctor_id, type=int)
    selected_date_str  = request.args.get('date', '')

    # --- Slot Logic ---
    all_slots = []
    for hour in range(9, 18):
        for minute in [0, 30]:
            t = dtime(hour, minute)
            all_slots.append(t.strftime('%H:%M'))

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

    available_slots = [(t, dt.strptime(t, '%H:%M').strftime('%I:%M %p'))
                       for t in all_slots if t not in blocked_slots]
    form.time.choices = available_slots if available_slots else [('', 'No slots available')]

    if form.validate_on_submit():
        # ... (Your existing submission logic) ...
        appointment.doctor_id = form.doctor_id.data
        appointment.date      = form.date.data
        appointment.time      = dt.strptime(form.time.data, '%H:%M').time()
        appointment.status    = 'pending'
        db.session.commit()
        flash('Appointment rescheduled successfully.', 'success')
        return redirect(url_for('receptionist.dashboard'))

    return render_template('reschedule.html',
                           form=form,
                           appointment=appointment,
                           blocked_slots=blocked_slots)