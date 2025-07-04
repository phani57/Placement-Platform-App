# Placement Communication Platform

A web application for managing campus placement activities, allowing students to apply for jobs, and faculty/alumni to post and manage job opportunities.

## Features

- User registration and login (Student, Faculty, Alumni roles)
- Students can view jobs, apply with resume upload, and track their applications
- Faculty/Alumni can post jobs, view applicants, and download job posts as PDF
- Student profile page
- Secure file upload for resumes (PDF only)
- Responsive, modern UI with Bootstrap

## Project Structure

```
app.py
static/
    images/
    resumes/
templates/
    base.html
    dashboard_faculty_alumni.html
    dashboard_student.html
    index.html
    job_pdf_template.html
    login.html
    my_applications.html
    post_job.html
    register.html
    student_profile.html
    view_applicants.html
```

## Setup Instructions

1. **Clone the repository**

2. **Install dependencies**
   ```sh
   pip install flask flask-mysqldb flask-bcrypt flask-login xhtml2pdf
   ```

3. **MySQL Database Setup**
   - Create a database named `placement_db`.
   - Create the following tables:

   ```sql
   CREATE TABLE users (
       id INT AUTO_INCREMENT PRIMARY KEY,
       name VARCHAR(100),
       email VARCHAR(100) UNIQUE,
       password VARCHAR(255),
       role ENUM('student', 'faculty', 'alumni')
   );

   CREATE TABLE student_details (
       id INT AUTO_INCREMENT PRIMARY KEY,
       user_id INT,
       department VARCHAR(100),
       roll_number VARCHAR(50),
       FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
   );

   CREATE TABLE job_posts (
       id INT AUTO_INCREMENT PRIMARY KEY,
       title VARCHAR(255),
       description TEXT,
       posted_by INT,
       target_audience VARCHAR(50),
       skills VARCHAR(255),
       duration VARCHAR(100),
       stipend VARCHAR(100),
       application_deadline DATE,
       contact_email VARCHAR(100),
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       FOREIGN KEY (posted_by) REFERENCES users(id) ON DELETE CASCADE
   );

   CREATE TABLE applications (
       id INT AUTO_INCREMENT PRIMARY KEY,
       student_id INT,
       job_id INT,
       resume_filename VARCHAR(255),
       applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
       FOREIGN KEY (job_id) REFERENCES job_posts(id) ON DELETE CASCADE
   );
   ```

   - Update the MySQL credentials in [`app.py`](app.py) as needed.

4. **Run the application**
   ```sh
   python app.py
   ```

5. **Access the app**
   - Open [http://localhost:5000](http://localhost:5000) in your browser.

## Notes

- Resumes are stored in `static/resumes/`.
- Only PDF files are allowed for resume uploads.
- Faculty/Alumni can only view applicants for jobs they posted.
- Students can only view and edit their own profile.

##
