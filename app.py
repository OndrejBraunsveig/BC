import os
from datetime import datetime

from flask import Flask, render_template, url_for, redirect, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField
from wtforms.validators import InputRequired, Length, ValidationError
import bcrypt

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
#app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://database_29he_user:Z41t7ityWH3l20r2zH0OgKXOdFMAs3n2@dpg-cp7jkomd3nmc73bsujsg-a.frankfurt-postgres.render.com/database_29he'
app.config['SECRET_KEY'] = 'abcd'

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(160), nullable=False)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(30), nullable=False)
    model_data = db.Column(db.String(100))
    bmd_data = db.Column(db.String(100))
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)

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

class AddForm(FlaskForm):
    name = StringField('Project Name', validators=[InputRequired(), Length(min=3, max=30)],
                       render_kw=({"placeholder": "Project Name"}))
    submit = SubmitField('Create')

class EditForm(FlaskForm):
    edit_id = StringField(validators=[InputRequired()])
    new_name = StringField('New Project Name', validators=[InputRequired(), Length(min=3, max=30)],
                            render_kw=({"placeholder": "New Project Name"}))
    submit = SubmitField('Edit')

class DeleteForm(FlaskForm):
    delete_id = StringField(validators=[InputRequired()])
    submit = SubmitField('Delete')

@app.route('/', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            if bcrypt.checkpw(form.password.data.encode('utf8'), user.password.encode('utf8')):
                login_user(user)
                session['user_id'] = user.id
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

@app.route('/dashboard/<username>', methods=['GET', 'POST'])
@login_required
def dashboard(username):
    id = session.get('user_id', None)

    add_form = AddForm()
    if add_form.validate_on_submit():
        new_project = Project(user_id=id, name=add_form.name.data)
        db.session.add(new_project)
        db.session.commit()

    edit_form = EditForm()
    if edit_form.validate_on_submit():
        project_id = int(edit_form.edit_id.data)
        project = Project.query.filter_by(id=project_id).first()
        project.name = edit_form.new_name.data
        db.session.commit()

    delete_form = DeleteForm()
    if delete_form.validate_on_submit():
        project_id = int(delete_form.delete_id.data)
        Project.query.filter_by(id=project_id).delete()
        db.session.commit()

    projects = Project.query.filter_by(user_id=id)
    project_list = [p.__dict__ for p in projects]
    return render_template('dashboard.html', username=username, projects=project_list, add_form=add_form,
                           edit_form=edit_form, delete_form=delete_form)

@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/editor', methods=['GET', 'POST'])
@login_required
def editor():
    
    return render_template('editor.html')

if __name__ == '__main__':
    app.run(debug=True)