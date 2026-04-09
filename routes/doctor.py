# doctor.py
from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Appointment, Prescription
from forms import PrescriptionForm
from datetime import date, timedelta, datetime
from functools import wraps

doctor_bp = Blueprint('doctor', __name__)


def doctor_only(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role != 'doctor':
            flash('Access denied.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def _week_bounds():
    """Return (monday, friday) of the current ISO week."""
    today  = date.today()
    monday = today - timedelta(days=today.weekday())       # weekday() 0=Mon
    friday = monday + timedelta(days=4)
    return monday, friday


@doctor_bp.route('/doctor/dashboard')
@login_required
@doctor_only
def dashboard():
    today          = date.today()
    monday, friday = _week_bounds()

    # All appointments for this doctor Mon–Fri of the current week
    appointments = (Appointment.query
                    .filter_by(doctor_id=current_user.id)
                    .filter(Appointment.date >= monday)
                    .filter(Appointment.date <= friday)
                    .order_by(Appointment.date, Appointment.time)
                    .all())

    week_days = [monday + timedelta(days=i) for i in range(5)]  # Mon–Fri dates

    return render_template('doctor_dashboard.html',
                           appointments=appointments,
                           today=today,
                           monday=monday,
                           friday=friday,
                           week_days=week_days)


@doctor_bp.route('/doctor/appointment/<int:appointment_id>/accept')
@login_required
@doctor_only
def accept_appointment(appointment_id):
    appointment        = Appointment.query.get_or_404(appointment_id)
    appointment.status = 'accepted'
    db.session.commit()
    flash(f'Appointment for {appointment.patient.name} accepted.', 'success')
    return redirect(url_for('doctor.dashboard'))


@doctor_bp.route('/doctor/appointment/<int:appointment_id>/reject')
@login_required
@doctor_only
def reject_appointment(appointment_id):
    appointment        = Appointment.query.get_or_404(appointment_id)
    appointment.status = 'rejected'
    db.session.commit()
    flash(f'Appointment for {appointment.patient.name} rejected.', 'warning')
    return redirect(url_for('doctor.dashboard'))

@doctor_bp.route('/doctor/prescribe/<int:appointment_id>', methods=['GET', 'POST'])
@login_required
@doctor_only
def prescribe(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    form        = PrescriptionForm()

    if form.validate_on_submit():
        if appointment.prescription:
            appointment.prescription.symptoms = form.symptoms.data
            appointment.prescription.notes    = form.notes.data
        else:
            prescription = Prescription(
                appointment_id = appointment.id,
                symptoms       = form.symptoms.data,
                notes          = form.notes.data
            )
            db.session.add(prescription)

        # Mark appointment as completed once prescription is saved
        appointment.status = 'completed'
        db.session.commit()
        flash('Prescription saved. Appointment marked as Completed.', 'success')
        return redirect(url_for('doctor.dashboard'))

    if appointment.prescription:
        form.symptoms.data = appointment.prescription.symptoms
        form.notes.data    = appointment.prescription.notes

    return render_template('prescribe.html',
                           form=form,
                           appointment=appointment)


@doctor_bp.route('/doctor/appointment/<int:appointment_id>/noshow')
@login_required
@doctor_only
def noshow_appointment(appointment_id):
    appointment        = Appointment.query.get_or_404(appointment_id)
    appointment.status = 'missed'
    db.session.commit()
    flash(f'Appointment for {appointment.patient.name} marked as No-Show.', 'warning')
    return redirect(url_for('doctor.dashboard'))