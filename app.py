import os
import sys
import io
import base64
from datetime import datetime, timezone
import pytz
import json
import rdata

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
import pandas as pd

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from rekonstrukce import reconstruction
from stl_to_mha import STL2Mask
from warp import warp
from morfer import morf
from dsp import dsp

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
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    base64_image = db.Column(db.String)
    active_template_id = db.Column(db.Integer, nullable=False, default=6)
    PUM = db.Column(db.Float, default=0)
    SPU = db.Column(db.Float, default=0)
    DCOX = db.Column(db.Float, default=0)
    IIMT = db.Column(db.Float, default=0)
    ISMM = db.Column(db.Float, default=0)
    SCOX = db.Column(db.Float, default=0)
    SS = db.Column(db.Float, default=0)
    SA = db.Column(db.Float, default=0)
    SIS = db.Column(db.Float, default=0)
    VEAC = db.Column(db.Float, default=0)
    sex = db.Column(db.String(1), default='?')
    probM = db.Column(db.Float, default=0.5)
    probF = db.Column(db.Float, default=0.5)
    

class Template(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), nullable=False)
    added_by = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

# Google Drive access
API_NAME = 'drive'
API_VERSION = 'v3'
SCOPES = ['https://www.googleapis.com/auth/drive']
TEMPLATE_FOLDER_ID = os.getenv('TEMPLATE_FOLDER_ID')
PROJECT_MODELS_FOLDER_ID = os.getenv('PROJECT_MODELS_FOLDER_ID')


creds_json = json.loads(os.getenv('DRIVE_CREDENTIALS'))
creds = service_account.Credentials.from_service_account_info(creds_json, scopes=SCOPES)

service = build(API_NAME, API_VERSION, credentials=creds)

def get_id_from_name(folder_id, filename):

    results = service.files().list(
        q=f"'{folder_id}' in parents and name='{filename}' and trashed=false",
        fields="files(id, name)"
    ).execute()

    files = results.get('files', [])
    if files:
        return files[0]['id']
    return ''

def upload_to_cloud(folder_id, filename, file_bytes, mimetype):

    # Check if file already exists
    file_id = get_id_from_name(folder_id, filename)

    media = MediaIoBaseUpload(
        file_bytes,
        mimetype=mimetype,
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
def download_from_cloud(file_id):

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
login_manager.login_view = ""

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
def is_stl(filename):

    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() == 'stl'

# Filtering CSV files
def is_csv(filename):

    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() == 'csv'

def format_timestamp(timestamp):

    dt = datetime.strptime(str(timestamp), "%Y-%m-%d %H:%M:%S.%f%z")
    return dt.strftime("%d-%m-%Y %H:%M:%S")

def time_difference(change_time):
    print(datetime.now(timezone.utc))
    print(change_time.astimezone(pytz.utc))
    delta = datetime.now(timezone.utc) - change_time.astimezone(pytz.utc)
    total_seconds = int(delta.total_seconds())
    
    # Determine the time difference dynamically
    # Less than 1 minute
    if total_seconds < 60:
        return f"{total_seconds} seconds ago"
    
    # Less than 1 hour
    if total_seconds < 3600:
        minutes = total_seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    
    # Less than 1 day
    if total_seconds < 86400:  # Less than 24 hours
        hours = total_seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    
    # More than 1 day
    days = total_seconds // 86400
    return f"{days} day{'s' if days > 1 else ''} ago"

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

    # potencialne zmenit
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

    if request.method == 'POST':
        return redirect(url_for('dashboard'))

    projects = Project.query.filter_by(user_id=id).order_by(Project.updated_at.desc()).all()
    
    # Format timestamp
    for project in projects:
        project.updated_at = time_difference(project.updated_at)


    return render_template('dashboard.html',
                           projects=projects,
                           add_form=add_form,
                           edit_form=edit_form,
                           delete_form=delete_form)

@app.route('/templates', methods=['GET', 'POST'])
@login_required
def templates():

    edit_form = EditForm()
    if edit_form.validate_on_submit():
        try:
            template_id = int(edit_form.edit_id.data)
            template = Template.query.filter_by(id=template_id).first()
            template.name = edit_form.new_name.data
            db.session.commit()

            print('Template edited!')
        except:
            print('Template edit failed!')

        return redirect(request.url)

    delete_form = DeleteForm()
    if delete_form.validate_on_submit():
        try:
            template_id = int(delete_form.delete_id.data)

            filename = f'T{template_id}'
            file_id = get_id_from_name(TEMPLATE_FOLDER_ID, filename)
            service.files().delete(fileId=file_id).execute()

            filename = f'{filename}_points'
            file_id = get_id_from_name(TEMPLATE_FOLDER_ID, filename)
            service.files().delete(fileId=file_id).execute()

            Template.query.filter_by(id=template_id).delete()
            db.session.commit()

            print('Template deleted succesfully!')
        except:
            print('Template deletion failed!')
        
        return redirect(request.url)

    if request.method == 'POST':

        user_id = session.get('user_id', None)
        user = User.query.filter_by(id=user_id).first()
        username = user.username

        template_name = request.form['template-name']
        StlFile = request.files.get('STL')
        CsvFile = request.files.get('CSV')

        if template_name == '':
            print('Template must have a name')
            return redirect(request.url)
        
        if (StlFile and is_stl(StlFile.filename)) and (CsvFile and is_csv(CsvFile.filename)):
            # Pridat jeste overeni na jmeno
            try:
                new_template = Template(name=template_name, added_by=username)
                db.session.add(new_template)
                db.session.commit()
                
                filename = f'T{new_template.id}'
                template_bytes = io.BytesIO(StlFile.read())
                upload_to_cloud(TEMPLATE_FOLDER_ID, filename, template_bytes, 'application/octet-stream')

                filename = f'{filename}_points'
                points_text = io.BytesIO(CsvFile.read())
                upload_to_cloud(TEMPLATE_FOLDER_ID, filename, points_text, 'text/csv')

                print('Template added succesfully!')
            except:
                print('Template addition failed!')
        else:
            print('Files were not in STL and CSV format')

        return redirect(request.url)

    all_templates = Template.query.order_by(Template.name.asc()).all()

    # Format timestamp
    for template in all_templates:
        template.updated_at = time_difference(template.updated_at)

    return render_template('all-templates.html',
                           all_templates=all_templates,
                           edit_form=edit_form,
                           delete_form=delete_form)

# Editor route
@app.route('/editor/<int:project_id>', methods=['GET', 'POST'])
@login_required
def editor(project_id):

    project = Project.query.filter_by(id=project_id).first()
    active_template_id = project.active_template_id
    
    all_templates = Template.query.order_by(Template.name.asc()).all()

    M_distances = {
        'PUM': project.PUM,
        'SPU': project.SPU,
        'DCOX': project.DCOX,
        'IIMT': project.IIMT,
        'ISMM': project.ISMM,
        'SCOX': project.SCOX,
        'SS': project.SS,
        'SA': project.SA,
        'SIS': project.SIS,
        'VEAC': project.VEAC,
        'sex' : project.sex,
        'probF' : project.probF,
        'probM' : project.probM
    }

    return render_template('editor.html',
                           project_id=project_id,
                           active_template_id=active_template_id,
                           all_templates=all_templates,
                           M_distances=M_distances)

@app.route('/project/<project_id>/template/<template_id>', methods=['GET'])
def template(project_id, template_id):

    try:
        filename = f'T{template_id}'
        file_id = get_id_from_name(TEMPLATE_FOLDER_ID, filename)
        file_bytes = download_from_cloud(file_id)

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
        upload_to_cloud(PROJECT_MODELS_FOLDER_ID, filename, model_bytes, 'application/octet-stream')

        # Reset M distances
        project = Project.query.filter_by(id=project_id)
        project.PUM = 0
        project.SPU = 0
        project.DCOX = 0
        project.IIMT = 0
        project.ISMM = 0
        project.SCOX = 0
        project.SS = 0
        project.SA = 0
        project.SIS = 0
        project.VEAC = 0
        project.sex = '?'
        project.probF = 0.5
        project.probM = 0.5
        db.session.commit()

        return jsonify({"message": "Model saved successfully"}), 200
    except:
        return jsonify({"message": "Model save error"}), 500

@app.route('/loadModel/<int:project_id>', methods=['GET', 'POST'])
@profile
def loadModel(project_id):

    try:
        filename = f'PM{project_id}'
        file_id = get_id_from_name(PROJECT_MODELS_FOLDER_ID, filename)
        if file_id == '':
            return {}
        file_bytes = download_from_cloud(file_id)

        return jsonify({"model_base64": base64.b64encode(file_bytes).decode('utf-8')})
    except:
        return {}

# Calculation route
@app.route('/calculate/<int:project_id>', methods=['GET'])
def calculate(project_id):

    project = Project.query.filter_by(id=project_id).first()

    # Template bytes
    template_id = project.active_template_id
    template_filename = f'T{template_id}'
    file_id = get_id_from_name(TEMPLATE_FOLDER_ID, template_filename)
    template_bytes = download_from_cloud(file_id)

    # Template points bytes
    points_filename = f'{template_filename}_points'
    file_id = get_id_from_name(TEMPLATE_FOLDER_ID, points_filename)
    points_bytes = download_from_cloud(file_id)

    # Project model bytes
    project_model_filename = f'PM{project_id}'
    file_id = get_id_from_name(PROJECT_MODELS_FOLDER_ID, project_model_filename)
    model_bytes = download_from_cloud(file_id)

    #try:
    # Template to STL
    with open(f'{template_filename}.stl', 'wb') as f:
        f.write(template_bytes)
        del template_bytes

    # Points to CSV
    with open(f'{points_filename}.csv', 'wb') as f:
        f.write(points_bytes)
        del points_bytes

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

    project.PUM = results['M1']
    project.SPU = results['M2']
    project.DCOX = results['M3']
    project.IIMT = results['M4']
    project.ISMM = results['M5']
    project.SCOX = results['M6']
    project.SS = results['M7']
    project.SA = results['M8']
    project.SIS = results['M9']
    project.VEAC = results['M10']


    db.session.commit()

    # Sex estimation
    results_new = {
        'PUM': project.PUM,
        'SPU': project.SPU,
        'DCOX': project.DCOX,
        'IIMT': project.IIMT,
        'ISMM': project.ISMM,
        'SCOX': project.SCOX,
        'SS': project.SS,
        'SA': project.SA,
        'SIS': project.SIS,
        'VEAC': project.VEAC,
    }

    df_results = pd.DataFrame(results_new, index=[0])

    converted = rdata.read_rda("sysdata.rda")
    w = converted['W']
    mu = converted['mu']

    df_w = w.to_pandas()
    df_mu = mu.to_pandas()

    sex_est = dsp(df_results, df_w, df_mu)
    print(sex_est)

    project.sex = sex_est['Sex estimate']
    project.probF = sex_est['ProbF']
    project.probM = sex_est['ProbM']
    db.session.commit()

    results_new['sex'] = sex_est['Sex estimate']
    results_new['probF'] = sex_est['ProbF']
    results_new['probM'] = sex_est['ProbM']
    
    return jsonify({"message": "Vsechno v klidu", "M_distances": results_new}), 200
    #except:
        #return jsonify({"message": "Bohuzel"}), 500

if __name__ == '__main__':
    app.run(debug=True)