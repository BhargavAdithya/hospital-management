from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from models import db, Patient, Appointment, User
from forms import PatientSelfBookingForm
from datetime import date, datetime, time as dtime, timedelta

patient_bp = Blueprint('patient', __name__)


def _booking_window():
    today    = date.today()
    max_date = today + timedelta(days=7)
    return today, max_date


def _all_slots():
    slots = []
    for hour in range(9, 18):
        for minute in [0, 30]:
            slots.append(dtime(hour, minute))
    return slots


def _available_slots_public(doctor_id, date_obj):
    """Same slot logic as receptionist — used for public patient booking."""
    today, max_date = _booking_window()

    if date_obj.weekday() >= 5:
        return []
    if date_obj < today or date_obj > max_date:
        return []

    now = datetime.now()

    rejected_times = {
        a.time for a in Appointment.query.filter_by(
            doctor_id=doctor_id, date=date_obj, status='rejected'
        ).all()
    }
    booked_times = {
        a.time for a in Appointment.query.filter_by(
            doctor_id=doctor_id, date=date_obj
        ).filter(Appointment.status.in_(['pending', 'accepted'])).all()
    }
    blocked = rejected_times | booked_times

    choices = []
    for t in _all_slots():
        if t in blocked:
            continue
        if date_obj == today:
            slot_dt = datetime.combine(date_obj, t)
            if slot_dt <= now + timedelta(hours=1):
                continue
        choices.append((t.strftime('%H:%M'), t.strftime('%I:%M %p')))
    return choices


@patient_bp.route('/patient/slots')
def patient_slots():
    """Public AJAX endpoint for patient self-booking slot loading."""
    doctor_id = request.args.get('doctor_id', type=int)
    date_str  = request.args.get('date', '')

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

    choices = _available_slots_public(doctor_id, date_obj)
    return jsonify({'slots': [{'value': v, 'label': l} for v, l in choices]})


@patient_bp.route('/patient/book', methods=['GET', 'POST'])
def book():
    form    = PatientSelfBookingForm()
    doctors = User.query.filter_by(role='doctor').all()
    form.doctor_id.choices = [(d.id, f'Dr. {d.username}') for d in doctors]

    # Default time choices — real list comes from AJAX
    form.time.choices = [('', 'Select doctor & date first')]

    if request.method == 'POST':
        submitted_doctor = request.form.get('doctor_id', type=int)
        submitted_date_s = request.form.get('date', '')
        try:
            submitted_date = datetime.strptime(submitted_date_s, '%Y-%m-%d').date()
            slot_choices   = _available_slots_public(submitted_doctor, submitted_date)
        except ValueError:
            slot_choices = []
        form.time.choices = slot_choices or [('', 'No slots available')]

    if form.validate_on_submit():
        # Full contact = country code + number
        full_contact = form.country_code.data + form.contact.data
        chosen_time  = datetime.strptime(form.time.data, '%H:%M').time()

        # Check if patient already exists by name + contact
        existing = Patient.query.filter_by(
            name=form.name.data, contact=full_contact
        ).first()

        if existing:
            patient = existing
        else:
            patient = Patient(
                name    = form.name.data,
                age     = form.age.data,
                gender  = form.gender.data,
                contact = full_contact,
                email   = form.email.data,
                address = form.address.data
            )
            db.session.add(patient)
            db.session.flush()

        # Double-booking check
        conflict = Appointment.query.filter_by(
            doctor_id = form.doctor_id.data,
            date      = form.date.data,
            time      = chosen_time
        ).filter(Appointment.status.in_(['pending', 'accepted'])).first()

        if conflict:
            flash('That time slot is already taken. Please choose a different slot.', 'danger')
        else:
            appointment = Appointment(
                patient_id  = patient.id,
                doctor_id   = form.doctor_id.data,
                date        = form.date.data,
                time        = chosen_time,
                status      = 'pending',
                self_booked = True,
                # Store problem in prescription symptoms later via doctor
                # For now store as a note on the appointment via a workaround:
            )
            db.session.add(appointment)
            db.session.flush()

            # Store the patient-described problem as an early prescription stub
            from models import Prescription
            stub = Prescription(
                appointment_id = appointment.id,
                symptoms       = form.problem.data,
                notes          = 'Prescription not yet written.'
            )
            db.session.add(stub)
            db.session.commit()

            flash('Your appointment has been booked successfully! '
                  'Please arrive on time.', 'success')
            return redirect(url_for('patient.confirmation',
                                    appointment_id=appointment.id))

    today, max_date = _booking_window()
    return render_template('patient_booking.html',
                           form=form,
                           min_date=today.isoformat(),
                           max_date=max_date.isoformat())


@patient_bp.route('/patient/confirmation/<int:appointment_id>')
def confirmation(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    return render_template('patient_confirmation.html', appointment=appointment)