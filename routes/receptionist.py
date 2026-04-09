# receptionist.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import db, Patient, Appointment, User
from forms import PatientForm, AppointmentForm, RescheduleForm
from datetime import date, datetime, time as dtime, timedelta

receptionist_bp = Blueprint('receptionist', __name__)

# ── Helpers ───────────────────────────────────────────────────────────────────

def receptionist_only(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role != 'receptionist':
            flash('Access denied.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def _booking_window():
    """
    Returns (min_date, max_date) for the booking calendar.
    min_date = today
    max_date = today + 7 calendar days (skipping to next weekday if needed)
    We actually just pass today and today+7 as raw bounds;
    weekend filtering is handled separately.
    """
    today    = date.today()
    max_date = today + timedelta(days=7)
    return today, max_date


def _all_slots():
    """All 30-min slots 09:00 – 17:30."""
    slots = []
    for hour in range(9, 18):
        for minute in [0, 30]:
            slots.append(dtime(hour, minute))
    return slots


def _available_slots(doctor_id, date_obj, rejected_appt_id=None):
    """
    Return list of (value, label) tuples for bookable slots.

    Rules applied in order:
      1. Weekend  → empty list.
      2. Date outside booking window (past or > 7 days ahead) → empty list.
      3. Past slots (+ 1-hour buffer for today) → excluded.
      4. Slots that THIS doctor has already REJECTED on this date → excluded.
         - If rejected_appt_id is given, that appointment's own rejected slot
           is ALWAYS excluded (it was the one the doctor said no to).
         - All other rejected appointments by this doctor on this date are
           also excluded (doctor already said no to that time generally).
      5. Slots already booked (non-rejected) by this doctor → excluded
         (double-booking prevention).

    The rejected_appt_id parameter identifies which appointment is being
    rescheduled; its slot must stay hidden when same doctor + same date are
    selected, and reappear only if a different doctor or different date is used.
    """
    today    = date.today()
    min_date, max_date = _booking_window()

    # 1. Weekend
    if date_obj.weekday() >= 5:
        return []

    # 2. Out of booking window
    if date_obj < min_date or date_obj > max_date:
        return []

    now = datetime.now()

    # 4a. All rejected slots by this doctor on this date
    rejected_times = {
        a.time
        for a in Appointment.query.filter_by(
            doctor_id=doctor_id,
            date=date_obj,
            status='rejected'
        ).all()
    }

    # 4b. If we're rescheduling a specific appointment, ensure its original
    #     rejected slot is hidden when same doctor + same date combo is chosen.
    #     (Already included above if it matches doctor+date, but being explicit.)
    if rejected_appt_id:
        orig = Appointment.query.get(rejected_appt_id)
        if orig and orig.doctor_id == doctor_id and orig.date == date_obj:
            rejected_times.add(orig.time)

    # 5. Already-booked (pending/accepted) slots — prevent double booking
    booked_times = {
        a.time
        for a in Appointment.query.filter_by(
            doctor_id=doctor_id,
            date=date_obj,
        ).filter(Appointment.status.in_(['pending', 'accepted'])).all()
    }
    # Exclude the appointment being rescheduled from booked set
    # (its old slot will be freed once saved)
    if rejected_appt_id:
        orig = Appointment.query.get(rejected_appt_id)
        if orig:
            booked_times.discard(orig.time)

    blocked = rejected_times | booked_times

    choices = []
    for t in _all_slots():
        if t in blocked:
            continue
        # 3. Past-slot buffer
        if date_obj == today:
            slot_dt = datetime.combine(date_obj, t)
            if slot_dt <= now + timedelta(hours=1):
                continue
        choices.append((t.strftime('%H:%M'), t.strftime('%I:%M %p')))

    return choices


# ── AJAX slot endpoint ────────────────────────────────────────────────────────

@receptionist_bp.route('/receptionist/slots')
@login_required
@receptionist_only
def get_slots():
    """
    GET /receptionist/slots
        ?doctor_id=<int>
        &date=<YYYY-MM-DD>
        [&reschedule_appt=<int>]   ← ID of appointment being rescheduled

    Returns JSON: { slots: [{value, label}, ...], weekend?: bool, out_of_range?: bool }
    """
    doctor_id       = request.args.get('doctor_id', type=int)
    date_str        = request.args.get('date', '')
    reschedule_appt = request.args.get('reschedule_appt', type=int)  # may be None

    if not doctor_id or not date_str:
        return jsonify({'slots': [], 'error': 'Missing parameters'})

    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'slots': [], 'error': 'Invalid date'})

    if date_obj.weekday() >= 5:
        return jsonify({'slots': [], 'weekend': True})

    today, max_date = _booking_window()
    if date_obj < today or date_obj > max_date:
        return jsonify({'slots': [], 'out_of_range': True})

    choices = _available_slots(doctor_id, date_obj, rejected_appt_id=reschedule_appt)
    return jsonify({
        'slots': [{'value': v, 'label': l} for v, l in choices]
    })


# ── Receptionist dashboard ────────────────────────────────────────────────────

@receptionist_bp.route('/receptionist/dashboard')
@login_required
@receptionist_only
def dashboard():
    appointments = (Appointment.query
                    .order_by(Appointment.date.desc(), Appointment.time.desc())
                    .all())
    return render_template('receptionist_dashboard.html', appointments=appointments)


# ── Add patient ───────────────────────────────────────────────────────────────

@receptionist_bp.route('/receptionist/add_patient', methods=['GET', 'POST'])
@login_required
@receptionist_only
def add_patient():
    patient_form     = PatientForm()
    appointment_form = AppointmentForm()

    doctors = User.query.filter_by(role='doctor').all()
    appointment_form.doctor_id.choices = [(d.id, d.username) for d in doctors]

    # Default dummy choices; real list comes from AJAX or POST rebuild
    appointment_form.time.choices = [('', 'Select doctor & date first')]

    if request.method == 'POST':
        submitted_doctor = request.form.get('doctor_id', type=int)
        submitted_date_s = request.form.get('date', '')
        try:
            submitted_date = datetime.strptime(submitted_date_s, '%Y-%m-%d').date()
            slot_choices   = _available_slots(submitted_doctor, submitted_date)
        except ValueError:
            slot_choices = []
        appointment_form.time.choices = slot_choices or [('', 'No slots available')]

    if patient_form.validate_on_submit() and appointment_form.validate_on_submit():
        chosen_time = datetime.strptime(appointment_form.time.data, '%H:%M').time()

        existing_patient = Patient.query.filter_by(
            name    = patient_form.name.data,
            contact = patient_form.contact.data
        ).first()

        if existing_patient:
            patient = existing_patient
            flash(f'Returning patient {patient.name} found. '
                  f'New appointment booked with previous history preserved.', 'info')
        else:
            patient = Patient(
                name    = patient_form.name.data,
                age     = patient_form.age.data,
                gender  = patient_form.gender.data,
                contact = patient_form.contact.data
            )
            db.session.add(patient)
            db.session.flush()

        appointment = Appointment(
            patient_id = patient.id,
            doctor_id  = appointment_form.doctor_id.data,
            date       = appointment_form.date.data,
            time       = chosen_time,
            status     = 'pending'
        )
        db.session.add(appointment)
        db.session.commit()

        flash(f'Appointment booked for {patient.name}.', 'success')
        return redirect(url_for('receptionist.dashboard'))

    existing_patient       = None
    previous_prescriptions = []
    if patient_form.name.data and patient_form.contact.data:
        existing_patient = Patient.query.filter_by(
            name    = patient_form.name.data,
            contact = patient_form.contact.data
        ).first()
        if existing_patient:
            for appt in existing_patient.appointments:
                if appt.prescription:
                    previous_prescriptions.append({
                        'date'  : appt.date,
                        'doctor': appt.doctor.username,
                        'notes' : appt.prescription.notes
                    })

    today, max_date = _booking_window()
    return render_template('add_patient.html',
                           patient_form=patient_form,
                           appointment_form=appointment_form,
                           existing_patient=existing_patient,
                           previous_prescriptions=previous_prescriptions,
                           min_date=today.isoformat(),
                           max_date=max_date.isoformat())


# ── Reschedule ────────────────────────────────────────────────────────────────

@receptionist_bp.route('/receptionist/reschedule/<int:appointment_id>',
                       methods=['GET', 'POST'])
@login_required
@receptionist_only
def reschedule(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    form        = RescheduleForm()

    doctors = User.query.filter_by(role='doctor').all()
    form.doctor_id.choices = [(d.id, d.username) for d in doctors]

    if request.method == 'POST':
        submitted_doctor = request.form.get('doctor_id', type=int)
        submitted_date_s = request.form.get('date', '')
        try:
            submitted_date = datetime.strptime(submitted_date_s, '%Y-%m-%d').date()
            slot_choices   = _available_slots(
                submitted_doctor, submitted_date,
                rejected_appt_id=appointment_id
            )
        except ValueError:
            slot_choices = []
        form.time.choices = slot_choices or [('', 'No slots available')]

        if form.validate_on_submit():
            new_date        = form.date.data
            new_time_str    = form.time.data
            new_doctor_id   = form.doctor_id.data
            new_time        = datetime.strptime(new_time_str, '%H:%M').time()

            old_doctor = appointment.doctor.username
            old_date   = appointment.date
            old_time   = appointment.time.strftime('%I:%M %p')

            # Keep old appointment as rejected — do NOT overwrite it.
            # Create a fresh appointment so all rejected slots stay in DB.
            from models import Appointment as Appt
            # Mark the old rejected appointment as rescheduled
            # so the dashboard hides the reschedule button
            appointment.rescheduled = True

            new_appt = Appt(
                patient_id  = appointment.patient_id,
                doctor_id   = new_doctor_id,
                date        = new_date,
                time        = new_time,
                status      = 'pending',
                rescheduled = False
            )
            db.session.add(new_appt)
            db.session.commit()

            new_doctor_name = User.query.get(new_doctor_id).username
            flash(
                f'Appointment for {appointment.patient.name} rescheduled — '
                f'Dr. {old_doctor} | {old_date.strftime("%d %b %Y")} {old_time} → '
                f'Dr. {new_doctor_name} | {new_date.strftime("%d %b %Y")} '
                f'{datetime.strptime(new_time_str, "%H:%M").strftime("%I:%M %p")}. '
                f'Status reset to Pending.',
                'success'
            )
            return redirect(url_for('receptionist.dashboard'))

    else:
        form.doctor_id.data = appointment.doctor_id
        form.time.choices   = [('', 'Select a date to load slots')]

    today, max_date = _booking_window()
    return render_template('reschedule.html',
                           form=form,
                           appointment=appointment,
                           reschedule_appt_id=appointment_id,
                           min_date=today.isoformat(),
                           max_date=max_date.isoformat())

@receptionist_bp.route('/receptionist/receipt/<int:appointment_id>')
@login_required
@receptionist_only
def receipt(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    return render_template('prescription_receipt.html',
                           appointment=appointment)