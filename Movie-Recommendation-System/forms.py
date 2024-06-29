from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, PasswordField, SubmitField, TextAreaField, validators, Form, RadioField
from wtforms.validators import InputRequired


class RatingForm(FlaskForm):
    note = RadioField('Rating', choices=[('10', '10'),('9', '9'),('8', '8'),('7', '7'),('6', '6'),('5', '5'), ('4', '4'), ('3', '3'), ('2', '2'), ('1', '1')])
    submit = SubmitField('Submit')

class RegisterForm(FlaskForm):
    mail = StringField('Email',[validators.Length(min=6, max=50)] )
    username = StringField('Username', [validators.Length(min=4, max=25)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('verify_password', message='Passwords do not match')
    ])
    verify_password = PasswordField('Confirm Password')
   
    dateOfBirth = IntegerField('Year of birth', [validators.NumberRange(min=1900, max=2023, message="Please enter a valid year")])
    favActors = StringField('Favourite Actor')
    favDirectors = StringField('Favourite Director')
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    username = StringField('Username')
    password = PasswordField('Password')
    submit = SubmitField('Login')

class SearchForm(FlaskForm):
    movie = StringField('Movie')
    search = SubmitField('Search')

class CommentForm(FlaskForm):
    comment = StringField('Comment')
    add = SubmitField('Post')

