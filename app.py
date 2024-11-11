import os
import base64
from datetime import datetime

from flask import Flask, render_template, url_for, redirect, flash, session, jsonify, request, Response
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FileField
from wtforms.validators import InputRequired, Length, ValidationError
import bcrypt

app = Flask(__name__)
#app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://bonee_database_dwzv_user:3A5RKafkCvbGJuVYbcUx9F0kB7aYOoOR@dpg-cri20a0gph6c73et7g20-a.frankfurt-postgres.render.com/bonee_database_dwzv'
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
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)
    model_data = db.Column(db.String)
    base64_image = db.Column(db.String)

class Template(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    model_data = db.Column(db.String)

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

def is_allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() == 'stl'

@app.route('/', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            if bcrypt.checkpw(form.password.data.encode('utf8'), user.password.encode('utf8')):
                login_user(user)
                session['user_id'] = user.id
                session['username'] = user.username
                return redirect(url_for('dashboard'))
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

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
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

    if request.method == 'POST':
        return redirect(url_for('dashboard'))

    return render_template('dashboard.html', projects=project_list, add_form=add_form,
                           edit_form=edit_form, delete_form=delete_form)

@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/editor/<int:project_id>', methods=['GET', 'POST'])
@login_required
def editor(project_id):
    
    if request.method == 'POST':
        pass

    return render_template('editor.html', project_id=project_id)

@app.route('/template/<id>', methods=['GET'])
def template(id):
    data = Template.query.filter_by(id=id).first()
    if data:
        return jsonify(data.model_data)
    return {}

@app.route('/addTemplate', methods=['GET', 'POST'])
def add_template():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and is_allowed_file(file.filename):
            byte_array = file.read()
            bytes_base64 = (base64.b64encode(byte_array)).decode()
            new_template = Template(name=request.form['template-name'], model_data=bytes_base64)
            db.session.add(new_template)
            db.session.commit()
            flash('Template added succesfully!')
    return render_template('template-load.html')

@app.route('/saveProjectImage/<int:project_id>', methods=['POST'])
def save_model_image(project_id):

    data = request.get_json()
    base64_image = data.get('base64_image')

    if base64_image:
        project = Project.query.filter_by(id=project_id).first()
        project.base64_image = base64_image
        db.session.commit()

        return jsonify({"message": "Image saved successfully"}), 200

    return jsonify({"message": "Image save failed"}), 500

@app.route('/loadProjectImage/<int:project_id>', methods=['GET'])
def load_model_image(project_id):
    
    project = Project.query.filter_by(id=project_id).first()
    base64_image = project.base64_image

    if base64_image:
        return jsonify({"base64_image": base64_image}), 200
    
    return {}

@app.route('/saveModel/<int:project_id>', methods=['POST'])
def saveModel(project_id):

    model_file = request.files['file']
    model_blob = model_file.read()

    if model_blob:
        project = Project.query.filter_by(id=project_id).first()
        project.model_data = model_blob
        db.session.commit()

        return jsonify({"message": "Model saved successfully"}), 200

    return jsonify({"message": "Model save error"}), 500

@app.route('/loadModel/<int:project_id>', methods=['GET', 'POST'])
def loadModel(project_id):

    project = Project.query.filter_by(id=project_id).first()
    model_blob = project.model_data
    if model_blob:
        model_base64 = base64.b64encode(model_blob).decode('utf-8')
        return jsonify({"model_base64": model_base64})
    return {}

if __name__ == '__main__':
    app.run(debug=True)