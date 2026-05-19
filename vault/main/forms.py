from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, Length

ALLOWED_EXTENSIONS = {'pdf', 'txt', 'docx', 'png', 'jpg', 'jpeg'}


class UploadFileForm(FlaskForm):
    file = FileField('Select File', validators=[FileRequired(), FileAllowed(ALLOWED_EXTENSIONS, 'Only PDF, TXT, DOCX, PNG, JPG files allowed')])
    submit = SubmitField('Secure to Vault')


class ContactForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(max=120)])
    email = StringField('Email Address', validators=[DataRequired(), Email(), Length(max=150)])
    subject = SelectField('Subject', choices=[
        ('Technical Inquiry', 'Technical Inquiry'),
        ('Security Feedback', 'Security Feedback'),
        ('Collaboration', 'Collaboration'),
        ('Other', 'Other')
    ], validators=[DataRequired()])
    message = TextAreaField('Message', validators=[DataRequired(), Length(min=10, max=2000)])
    submit = SubmitField('Send Message')