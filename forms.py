from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField, SubmitField,
                     IntegerField, SelectField, DateField, TimeField, TextAreaField)
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
    time      = TimeField('Appointment Time',
                          validators=[DataRequired()])
    submit    = SubmitField('Book Appointment')


class PrescriptionForm(FlaskForm):
    notes  = TextAreaField('Prescription / Notes',
                           validators=[DataRequired(), Length(min=5)])
    submit = SubmitField('Save Prescription')