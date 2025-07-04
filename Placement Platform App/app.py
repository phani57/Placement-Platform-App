from flask import Flask, render_template, redirect, url_for, request, flash, send_from_directory, make_response
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from werkzeug.utils import secure_filename
import MySQLdb.cursors
from xhtml2pdf import pisa
from io import BytesIO
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MySQL Config
app.config['MYSQL_HOST']       = 'localhost'
app.config['MYSQL_USER']       = 'root'
app.config['MYSQL_PASSWORD']   = 'Phanidhar@57'
app.config['MYSQL_DB']         = 'placement_db'
mysql = MySQL(app)

bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Upload configuration
UPLOAD_FOLDER = 'static/resumes'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, name, email, role):
        self.id    = id
        self.name  = name
        self.email = email
        self.role  = role

@login_manager.user_loader
def load_user(user_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
    u = cursor.fetchone()
    if u:
        return User(u['id'], u['name'], u['email'], u['role'])
    return None

# --- Public Routes ---

@app.route('/')
def index():
    return render_template('index.html')

# @app.route('/register', methods=['GET','POST'])
# def register():
#     if request.method == 'POST':
#         name     = request.form['name']
#         email    = request.form['email']
#         password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
#         role     = request.form['role']
#         cursor = mysql.connection.cursor()
#         cursor.execute(
#             "INSERT INTO users (name, email, password, role) VALUES (%s,%s,%s,%s)",
#             (name, email, password, role)
#         )
#         mysql.connection.commit()
#         flash('Registration successful! Please login.', 'success')
#         return redirect(url_for('login'))
#     return render_template('register.html')
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name     = request.form['name']
        email    = request.form['email']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        role     = request.form['role']

        cursor = mysql.connection.cursor()
        # Insert into users table
        cursor.execute(
            "INSERT INTO users (name, email, password, role) VALUES (%s,%s,%s,%s)",
            (name, email, password, role)
        )
        mysql.connection.commit()

        # Get the inserted user ID
        user_id = cursor.lastrowid

        # If the role is student, insert into student_details
        if role == 'student':
            department  = request.form['department']
            roll_number = request.form['roll_number']
            cursor.execute(
                "INSERT INTO student_details (user_id, department, roll_number) VALUES (%s, %s, %s)",
                (user_id, department, roll_number)
            )
            mysql.connection.commit()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email    = request.form['email']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        u = cursor.fetchone()
        if u and bcrypt.check_password_hash(u['password'], password):
            user_obj = User(u['id'], u['name'], u['email'], u['role'])
            login_user(user_obj)
            return redirect(url_for('dashboard'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

# --- Dashboard ---

@app.route('/dashboard')
@login_required
def dashboard():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if current_user.role == 'student':
        cursor.execute("SELECT * FROM job_posts ORDER BY created_at DESC")
        jobs = cursor.fetchall()
        cursor.execute("SELECT job_id FROM applications WHERE student_id = %s", (current_user.id,))
        applied_jobs = {row['job_id'] for row in cursor.fetchall()}
        return render_template('dashboard_student.html', jobs=jobs, applied_jobs=applied_jobs)
    else:
        cursor.execute("""
        SELECT j.*, COUNT(a.id) AS applicant_count
        FROM job_posts j
        LEFT JOIN applications a ON j.id = a.job_id
        WHERE j.posted_by = %s
        GROUP BY j.id
        ORDER BY j.created_at DESC
    """, (current_user.id,))
    jobs = cursor.fetchall()
    for job in jobs:
            cursor.execute("""
                SELECT u.name, u.email, a.resume_filename, a.applied_at
                FROM applications a
                JOIN users u ON a.student_id = u.id
                WHERE a.job_id = %s
            """, (job['id'],))
            job['applicants'] = cursor.fetchall()

    return render_template('dashboard_faculty_alumni.html', jobs=jobs)    

# --- Job Posting ---

@app.route('/post-job', methods=['GET','POST'])
@login_required
def post_job():
    if current_user.role == 'student':
        flash('Access denied! Students cannot post jobs.', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        title         = request.form['title']
        description   = request.form['description']
        target        = request.form['target']
        skills        = request.form['skills']
        duration      = request.form['duration']
        stipend       = request.form['stipend']
        deadline      = request.form['application_deadline']
        contact_email = request.form['contact_email']

        cursor = mysql.connection.cursor()
        cursor.execute("""
            INSERT INTO job_posts (
                title, description, posted_by, target_audience,
                skills, duration, stipend, application_deadline, contact_email
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            title, description, current_user.id, target,
            skills, duration, stipend, deadline, contact_email
        ))
        mysql.connection.commit()
        flash('Job posted successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('post_job.html')

# --- Apply to Job ---

@app.route('/apply-job/<int:job_id>', methods=['POST'])
@login_required
def apply_job(job_id):
    if current_user.role != 'student':
        flash('Only students can apply for jobs.', 'danger')
        return redirect(url_for('dashboard'))

    if 'resume' not in request.files:
        flash('No resume uploaded.', 'danger')
        return redirect(url_for('dashboard'))

    file = request.files['resume']
    if file.filename == '' or not allowed_file(file.filename):
        flash('Invalid file type. Please upload a PDF.', 'danger')
        return redirect(url_for('dashboard'))

    # Save file
    filename = secure_filename(f"{current_user.id}_{job_id}_{file.filename}")
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    # Record application
    cursor = mysql.connection.cursor()
    cursor.execute(
        "INSERT INTO applications (student_id, job_id, resume_filename) VALUES (%s,%s,%s)",
        (current_user.id, job_id, filename)
    )
    mysql.connection.commit()
    flash('Successfully applied for job.', 'success')
    return redirect(url_for('dashboard'))

# --- View My Applications ---

@app.route('/my-applications')
@login_required
def my_applications():
    if current_user.role != 'student':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT a.id AS app_id, a.resume_filename, a.applied_at, j.title
        FROM applications a
        JOIN job_posts j ON a.job_id = j.id
        WHERE a.student_id = %s
        ORDER BY a.applied_at DESC
    """, (current_user.id,))
    applications = cursor.fetchall()
    return render_template('my_applications.html', applications=applications)

# --- Download Resume ---

@app.route('/download_resume/<filename>')
@login_required
def download_resume(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

# --- Download Job as PDF ---

@app.route('/download-job/<int:job_id>')
@login_required
def download_job(job_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM job_posts WHERE id = %s", (job_id,))
    job = cursor.fetchone()
    if not job:
        flash('Job not found', 'danger')
        return redirect(url_for('dashboard'))

    rendered = render_template('job_pdf_template.html', job=job)
    pdf = BytesIO()
    pisa_status = pisa.CreatePDF(rendered, dest=pdf)
    if pisa_status.err:
        return 'PDF generation failed'
    pdf.seek(0)
    response = make_response(pdf.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=job_{job_id}.pdf'
    return response

# --- Logout ---

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/delete-job/<int:job_id>', methods=['POST'])
@login_required
def delete_job(job_id):
    cursor = mysql.connection.cursor()

    # Ensure only the job poster can delete
    cursor.execute("SELECT * FROM job_posts WHERE id = %s AND posted_by = %s", (job_id, current_user.id))
    job = cursor.fetchone()
    if not job:
        flash("Job not found or unauthorized", "danger")
        return redirect(url_for('dashboard'))

    # First delete applications linked to this job
    cursor.execute("DELETE FROM applications WHERE job_id = %s", (job_id,))

    # Then delete the job post
    cursor.execute("DELETE FROM job_posts WHERE id = %s", (job_id,))
    mysql.connection.commit()

    flash("Job post deleted successfully.", "success")
    return redirect(url_for('dashboard'))

# --- Student Profile Page ---
# @app.route('/profile')
# @login_required
# def profile():
#     if current_user.role != 'student':
#         flash('Access denied. Only students can view this page.', 'danger')
#         return redirect(url_for('dashboard'))

#     cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
#     cursor.execute("SELECT name, email, role FROM users WHERE id = %s", (current_user.id,))
#     student = cursor.fetchone()

#     if not student:
#         flash("Student profile not found.", "danger")
#         return redirect(url_for('dashboard'))

#     return render_template('student_profile.html', student=student)
@app.route('/profile')
@login_required
def profile():
    if current_user.role != 'student':
        flash('Access denied. Only students can view this page.', 'danger')
        return redirect(url_for('dashboard'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT u.name, u.email, u.role, s.department, s.roll_number
        FROM users u
        LEFT JOIN student_details s ON u.id = s.user_id
        WHERE u.id = %s
    """, (current_user.id,))
    student = cursor.fetchone()

    if not student:
        flash("Student profile not found.", "danger")
        return redirect(url_for('dashboard'))

    return render_template('student_profile.html', student=student)

@app.route('/job/<int:job_id>/applicants')
@login_required
def view_applicants(job_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # Ensure only the job poster can view applicants
    cursor.execute("SELECT * FROM job_posts WHERE id = %s AND posted_by = %s", (job_id, current_user.id))
    job = cursor.fetchone()
    if not job:
        flash("Job not found or unauthorized", "danger")
        return redirect(url_for('dashboard'))

    cursor.execute("""
        SELECT u.name, u.email, a.resume_filename, a.applied_at
        FROM applications a
        JOIN users u ON a.student_id = u.id
        WHERE a.job_id = %s
        ORDER BY a.applied_at DESC
    """, (job_id,))
    applications = cursor.fetchall()
    return render_template('view_applicants.html', job=job, applications=applications)

@app.route('/download_resume/<filename>')
@login_required
def download_resumes(filename):
    return send_from_directory('static/resumes', filename, as_attachment=True)


# --- Run Server ---

if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)
