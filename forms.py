# forms.py
from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField, SubmitField,
                     IntegerField, SelectField, DateField, TextAreaField,
                     TelField)
from wtforms.validators import DataRequired, Length, NumberRange


class LoginForm(FlaskForm):
    username = StringField('Username',
                           validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('Password',
                             validators=[DataRequired()])
    submit   = SubmitField('Login')


class PatientForm(FlaskForm):
    name    = StringField('Patient Name',
                          validators=[DataRequired(), Length(min=2, max=120)])
    age     = IntegerField('Age',
                           validators=[DataRequired(), NumberRange(min=0, max=120)])
    gender  = SelectField('Gender',
                          choices=[('Male', 'Male'),
                                   ('Female', 'Female'),
                                   ('Other', 'Other')],
                          validators=[DataRequired()])
    contact = StringField('Contact Number',
                          validators=[DataRequired(), Length(min=10, max=15)])
    submit  = SubmitField('Admit Patient')


class AppointmentForm(FlaskForm):
    doctor_id = SelectField('Assign Doctor',
                            coerce=int,
                            validators=[DataRequired()])
    date      = DateField('Appointment Date',
                          validators=[DataRequired()])
    # Changed from TimeField to SelectField — populated via AJAX
    time      = SelectField('Time Slot',
                            validators=[DataRequired()])
    submit    = SubmitField('Book Appointment')


class PrescriptionForm(FlaskForm):
    symptoms = TextAreaField('Patient Symptoms / Problem',
                             validators=[DataRequired(), Length(min=5)])
    notes    = TextAreaField('Prescription / Notes',
                             validators=[DataRequired(), Length(min=5)])
    submit   = SubmitField('Save Prescription')

class RescheduleForm(FlaskForm):
    doctor_id = SelectField('Assign Doctor', coerce=int, validators=[DataRequired()])
    date      = DateField('New Date', validators=[DataRequired()])
    # Populated via AJAX — choices are set in the route before validation
    time      = SelectField('Available Time Slot', validators=[DataRequired()])
    submit    = SubmitField('Reschedule Appointment')

class PatientSelfBookingForm(FlaskForm):
    name         = StringField('Full Name',
                               validators=[DataRequired(), Length(min=2, max=120)])
    age          = IntegerField('Age',
                                validators=[DataRequired(), NumberRange(min=0, max=120)])
    gender       = SelectField('Gender',
                               choices=[('Male','Male'),('Female','Female'),('Other','Other')],
                               validators=[DataRequired()])
    country_code = SelectField('Country Code',
                               choices=[
                                   ('+91',  '🇮🇳 +91 (India)'),
                                   ('+1',   '🇺🇸 +1 (USA/Canada)'),
                                   ('+44',  '🇬🇧 +44 (UK)'),
                                   ('+61',  '🇦🇺 +61 (Australia)'),
                                   ('+971', '🇦🇪 +971 (UAE)'),
                                   ('+65',  '🇸🇬 +65 (Singapore)'),
                                   ('+60',  '🇲🇾 +60 (Malaysia)'),
                                   ('+1',   '🇨🇦 +1 (Canada)'),
                                   ('+49',  '🇩🇪 +49 (Germany)'),
                                   ('+33',  '🇫🇷 +33 (France)'),
                               ],
                               default='+91')
    contact      = StringField('Phone Number',
                               validators=[DataRequired(), Length(min=7, max=15)])
    email        = StringField('Email Address',
                               validators=[DataRequired(), Length(max=120)])
    address      = TextAreaField('Residential Address',
                                 validators=[DataRequired(), Length(min=5)])
    problem      = TextAreaField('Problem / Reason for Visit',
                                 validators=[DataRequired(), Length(min=5)])
    doctor_id    = SelectField('Preferred Doctor',
                               coerce=int, validators=[DataRequired()])
    date         = DateField('Preferred Date',
                             validators=[DataRequired()])
    time         = SelectField('Time Slot',
                               validators=[DataRequired()])
    submit       = SubmitField('Book My Appointment')