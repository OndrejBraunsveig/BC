import os
import sys
import io
import base64
from datetime import datetime
import json

from dotenv import load_dotenv
from flask import Flask, render_template, url_for, redirect, flash, session, jsonify, request, Response
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user
from flask_wtf import FlaskForm
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2 import service_account
from wtforms import StringField, PasswordField, SubmitField, FileField
from wtforms.validators import InputRequired, Length, ValidationError
import bcrypt
from memory_profiler import profile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from rekonstrukce import reconstruction
from stl_to_mha import STL2Mask
from warp import warp
from morfer import morf

app = Flask(__name__)
app.config['FLASK_ENV'] = os.getenv('FLASK_ENV')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

# Database
db = SQLAlchemy(app)

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
    active_template_id = db.Column(db.Integer, nullable=False, default=6)
    M1 = db.Column(db.Float, default=0)
    M2 = db.Column(db.Float, default=0)
    M3 = db.Column(db.Float, default=0)
    M4 = db.Column(db.Float, default=0)
    M5 = db.Column(db.Float, default=0)
    M6 = db.Column(db.Float, default=0)
    M7 = db.Column(db.Float, default=0)
    M8 = db.Column(db.Float, default=0)
    M9 = db.Column(db.Float, default=0)
    M10 = db.Column(db.Float, default=0)
    

class Template(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)

# Google Drive access
API_NAME = 'drive'
API_VERSION = 'v3'
SCOPES = ['https://www.googleapis.com/auth/drive']
TEMPLATE_FOLDER_ID = os.getenv('TEMPLATE_FOLDER_ID')
PROJECT_MODELS_FOLDER_ID = os.getenv('PROJECT_MODELS_FOLDER_ID')


creds_json = json.loads(os.getenv('DRIVE_CREDENTIALS'))
creds = service_account.Credentials.from_service_account_info(creds_json, scopes=SCOPES)

service = build(API_NAME, API_VERSION, credentials=creds)

def getIdFromName(folder_id, filename):

    results = service.files().list(
        q=f"'{folder_id}' in parents and name='{filename}' and trashed=false",
        fields="files(id, name)"
    ).execute()

    files = results.get('files', [])
    if files:
        return files[0]['id']
    return ''

def uploadToCloud(folder_id, filename, file_bytes):

    # Check if file already exists
    file_id = getIdFromName(folder_id, filename)

    media = MediaIoBaseUpload(
        file_bytes,
        mimetype='application/octet-stream',
        resumable=True
    )

    # Create new file if the file with the same name doesn't exist
    if file_id == '':
        file_metadata = {
        'name': filename,
        'parents': [folder_id]
        }

        file = service.files().create(
            body=file_metadata,
            media_body=media
        ).execute()

        return file
    
    # Edit file if the file exists
    file = service.files().update(
        fileId=file_id,
        media_body=media
    ).execute()

    return file

@profile
def downloadFromCloud(file_id):

    request = service.files().get_media(fileId=file_id)

    file_stream = io.BytesIO()
    downloader = MediaIoBaseDownload(file_stream, request)

    done = False
    while not done:
        status, done = downloader.next_chunk()
        print(f'Download progress: {int(status.progress() * 100)}%')

    file_stream.seek(0)
    return file_stream.read()


# Managing logins
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):

    return db.session.get(User, int(user_id))

# WTForms
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

# Filtering STL files
def is_allowed_file(filename):

    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() == 'stl'

# Login/registration/logout routes
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

@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():

    logout_user()
    return redirect(url_for('login'))

# Dashboard route
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

    return render_template('dashboard.html',
                           projects=project_list,
                           add_form=add_form,
                           edit_form=edit_form,
                           delete_form=delete_form)

# Editor route
@app.route('/editor/<int:project_id>', methods=['GET', 'POST'])
@login_required
def editor(project_id):

    project = Project.query.filter_by(id=project_id).first()
    active_template_id = project.active_template_id
    
    all_templates = Template.query.all()

    M_distances = {
        'M1': project.M1,
        'M2': project.M2,
        'M3': project.M3,
        'M4': project.M4,
        'M5': project.M5,
        'M6': project.M6,
        'M7': project.M7,
        'M8': project.M8,
        'M9': project.M9,
        'M10': project.M10,               
    }

    return render_template('editor.html',
                           project_id=project_id,
                           active_template_id=active_template_id,
                           all_templates=all_templates,
                           M_distances=M_distances)

# Template routes
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
            # Pridat jeste overeni na jmeno
            try:
                template_name = request.form['template-name']
                new_template = Template(name=template_name)
                db.session.add(new_template)
                db.session.commit()
                
                filename = f'T{new_template.id}'
                template_bytes = io.BytesIO(file.read())
                uploadToCloud(TEMPLATE_FOLDER_ID, filename, template_bytes)

                flash('Template added succesfully!')
            except:
                flash('Template addition failed!')

    return render_template('template-load.html')

@app.route('/project/<project_id>/template/<template_id>', methods=['GET'])
def template(project_id, template_id):

    try:
        filename = f'T{template_id}'
        file_id = getIdFromName(TEMPLATE_FOLDER_ID, filename)
        file_bytes = downloadFromCloud(file_id)

        project = Project.query.filter_by(id=project_id).first()
        project.active_template_id = template_id
        db.session.commit()

        template_base64 = base64.b64encode(file_bytes).decode('utf-8')
        return jsonify({"template_base64": template_base64})
    except:
        return {}

# Project image routes
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

# Project model routes
@app.route('/saveModel/<int:project_id>', methods=['POST'])
def saveModel(project_id):

    try:
        filename = f'PM{project_id}'
        model_file = request.files['file']
        model_bytes = io.BytesIO(model_file.read())
        uploadToCloud(PROJECT_MODELS_FOLDER_ID, filename, model_bytes)

        # Reset M distances
        project = Project.query.filter_by(id=project_id)
        project.M1 = 0
        project.M2 = 0
        project.M3 = 0
        project.M4 = 0
        project.M5 = 0
        project.M6 = 0
        project.M7 = 0
        project.M8 = 0
        project.M9 = 0
        project.M10 = 0

        return jsonify({"message": "Model saved successfully"}), 200
    except:
        return jsonify({"message": "Model save error"}), 500

@app.route('/loadModel/<int:project_id>', methods=['GET', 'POST'])
@profile
def loadModel(project_id):

    try:
        filename = f'PM{project_id}'
        file_id = getIdFromName(PROJECT_MODELS_FOLDER_ID, filename)
        file_bytes = downloadFromCloud(file_id)

        return jsonify({"model_base64": base64.b64encode(file_bytes).decode('utf-8')})
    except:
        return {}

# Calculation route
@app.route('/calculate/<int:project_id>', methods=['GET'])
def calculate(project_id):

    project = Project.query.filter_by(id=project_id).first()

    template_id = project.active_template_id
    template_filename = f'T{template_id}'
    file_id = getIdFromName(TEMPLATE_FOLDER_ID, template_filename)
    template_bytes = downloadFromCloud(file_id)

    project_model_filename = f'PM{project_id}'
    file_id = getIdFromName(PROJECT_MODELS_FOLDER_ID, project_model_filename)
    model_bytes = downloadFromCloud(file_id)

    #try:
        # Template to STL
    with open(f'{template_filename}.stl', 'wb') as f:
        f.write(template_bytes)
        del template_bytes

    # Model to STL
    with open(f'{project_model_filename}.stl', 'wb') as f:
        f.write(model_bytes)
        del model_bytes

    # Poisson a decimation to model STL
    reconstruction(project_model_filename)

    # Template to MHA
    STL2Mask(template_filename)

    # Model to MHA
    STL2Mask(f'R_{project_model_filename}')

    # Calculate M3 distance from model MHA
    #M3_calc(project_model_filename)

    warp(project_model_filename, template_filename)
    results = morf(project_model_filename, template_filename)

    project.M1 = results['M1']
    project.M2 = results['M2']
    project.M3 = results['M3']
    project.M4 = results['M4']
    project.M5 = results['M5']
    project.M6 = results['M6']
    project.M7 = results['M7']
    project.M8 = results['M8']
    project.M9 = results['M9']
    project.M10 = results['M10']

    db.session.commit()


    return jsonify({"message": "Vsechno v klidu", "M_distances": results}), 200
    #except:
        #return jsonify({"message": "Bohuzel"}), 500

if __name__ == '__main__':
    app.run(debug=True)