from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Appointment, Prescription
from forms import PrescriptionForm
from datetime import date
from functools import wraps

doctor_bp = Blueprint('doctor', __name__)


def doctor_only(f):
    """Decorator to block non-doctors from accessing a route."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role != 'doctor':
            flash('Access denied.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


@doctor_bp.route('/doctor/dashboard')
@login_required
@doctor_only
def dashboard():
    # Show only today's appointments for the logged-in doctor
    today = date.today()
    appointments = (Appointment.query
                    .filter_by(doctor_id=current_user.id)
                    .filter(Appointment.date == today)
                    .order_by(Appointment.time)
                    .all())
    return render_template('doctor_dashboard.html', appointments=appointments)


@doctor_bp.route('/doctor/appointment/<int:appointment_id>/accept')
@login_required
@doctor_only
def accept_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    appointment.status = 'accepted'
    db.session.commit()
    flash('Appointment accepted.', 'success')
    return redirect(url_for('doctor.dashboard'))


@doctor_bp.route('/doctor/appointment/<int:appointment_id>/reject')
@login_required
@doctor_only
def reject_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    appointment.status = 'rejected'
    db.session.commit()
    flash('Appointment rejected.', 'warning')
    return redirect(url_for('doctor.dashboard'))


@doctor_bp.route('/doctor/prescribe/<int:appointment_id>', methods=['GET', 'POST'])
@login_required
@doctor_only
def prescribe(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    form = PrescriptionForm()

    if form.validate_on_submit():
        # Update or create prescription
        if appointment.prescription:
            appointment.prescription.notes = form.notes.data
        else:
            prescription = Prescription(
                appointment_id = appointment.id,
                notes          = form.notes.data
            )
            db.session.add(prescription)

        db.session.commit()
        flash('Prescription saved successfully.', 'success')
        return redirect(url_for('doctor.dashboard'))

    # Pre-fill form if a prescription already exists
    if appointment.prescription:
        form.notes.data = appointment.prescription.notes

    return render_template('prescribe.html',
                           form=form,
                           appointment=appointment)