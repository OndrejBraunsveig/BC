import os

from flask import Flask, render_template, url_for, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError
import bcrypt

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SECRET_KEY'] = 'abcd'

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(160), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=3, max=20)],
                           render_kw=({"placeholder": "Username"}))
    password = PasswordField('Password', validators=[InputRequired(), Length(min=3, max=20)],
                             render_kw=({"placeholder": "Password"}))
    submit = SubmitField('Login')

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=3, max=20)],
                           render_kw=({"placeholder": "Username"}))
    password = PasswordField('Password', validators=[InputRequired(), Length(min=3, max=20)],
                             render_kw=({"placeholder": "Password"}))
    control_password = PasswordField('Control Password', validators=[InputRequired(), Length(min=3, max=20)],
                                     render_kw=({"placeholder": "Control password"}))
    submit = SubmitField('Register')

    def validate_username(self, username):
        existing_user_username = User.query.filter_by(username=username.data).first()

        if existing_user_username:
            raise ValidationError("That username already exists!")



@app.route('/', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            if bcrypt.checkpw(form.password.data.encode('utf8'), user.password.encode('utf8')):
                login_user(user)
                return redirect(url_for('dashboard', username=user.username))
        flash('Wrong username or password!')
        return redirect(url_for('login'))
    
    return render_template('index.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        if form.password.data == form.control_password.data:
            hashed_password = bcrypt.hashpw(form.password.data.encode("utf8"), bcrypt.gensalt()).decode('utf8')
            new_user = User(username=form.username.data, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash('Account created!')
            return redirect(url_for('login'))
        
        flash('Passwords dont match!')
        return redirect(url_for('register'))

    return render_template('register.html', form=form)

@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard/<username>', methods=['GET', 'POST'])
@login_required
def dashboard(username):
    return render_template('dashboard.html', username=username)

@app.route('/editor', methods=['GET', 'POST'])
@login_required
def editor():
    
    return render_template('editor.html')

if __name__ == '__main__':
    app.run(debug=True)