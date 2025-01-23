from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import MySQLdb
import bcrypt
from config import Config
from flask_bcrypt import Bcrypt
from flask import jsonify
from datetime import datetime

app = Flask(__name__)
app.config.from_object(Config)
#bcrypt = Bcrypt(app)

# Set up Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'student_login'  # Default login view

# Database connection
def connect_db():
    return MySQLdb.connect(
        host=app.config['DB_HOST'],
        user=app.config['DB_USER'],
        passwd=app.config['DB_PASSWORD'],
        db=app.config['DB_NAME']
    )

class User(UserMixin):
    def __init__(self, srn=None, faculty_id=None, admin_id=None):
        self.srn = srn
        self.faculty_id = faculty_id
        self.admin_id = admin_id

    def get_id(self):
        if self.admin_id:
            return self.admin_id
        elif self.faculty_id:
            return self.faculty_id
        elif self.srn:
            return self.srn
        return None

@login_manager.user_loader
def load_user(user_id):
    db = connect_db()
    cursor = db.cursor()
    
    # Check if the user is a student
    cursor.execute("SELECT * FROM Student WHERE SRN = %s", (user_id,))
    student = cursor.fetchone()
    if student:
        return User(srn=student[0])  # Assuming SRN is the first column

    # Check if the user is a faculty member
    cursor.execute("SELECT * FROM Faculty WHERE FacultyID = %s", (user_id,))
    faculty = cursor.fetchone()
    if faculty:
        return User(faculty_id=faculty[0])  # Assuming FacultyID is the first column

    # Check if the user is an admin
    cursor.execute("SELECT * FROM Admin WHERE AdminID = %s", (user_id,))
    admin = cursor.fetchone()
    if admin:
        return User(admin_id=admin[0])  # Assuming AdminID is the first column

    return None

@app.route('/')
def index():
    return render_template('index.html')

# Student Login
@app.route('/login/student', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        db = connect_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM Student WHERE Email = %s", (email,))
        student = cursor.fetchone()

        if student:
            # The password is stored in the 12th column, adjust accordingly
            stored_password = student[11].encode('utf-8')  # Convert stored hash to bytes
            if bcrypt.checkpw(password.encode('utf-8'), stored_password):  # Compare hash
                user = User(srn=student[0])  # Assuming SRN is the first column
                login_user(user)
                return redirect(url_for('student_dashboard', srn=student[0]))
            else:
                flash('Invalid credentials, please try again.', 'danger')
        else:
            flash('Invalid credentials, please try again.', 'danger')

    return render_template('login.html')


# Student Registration
@app.route('/register/student', methods=['GET', 'POST'])
def student_register():
    if request.method == 'POST':
        srn = request.form['srn']
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        gender = request.form['gender']
        section = request.form['section']
        semester = request.form['semester']
        password = request.form['password']
        gpa = request.form['gpa']
        deptid = request.form['DeptID']
        teamid = request.form['TeamID']
        facultyid = request.form['FacultyID']

        db = connect_db()
        cursor = db.cursor()

        # Check if Team ID exists
        cursor.execute("SELECT COUNT(*) FROM Team WHERE TeamID = %s", (teamid,))
        team_exists = cursor.fetchone()[0]

        # Check if Faculty ID exists
        cursor.execute("SELECT COUNT(*) FROM Faculty WHERE FacultyID = %s", (facultyid,))
        faculty_exists = cursor.fetchone()[0]

        # Flash messages if the IDs are invalid
        if not team_exists:
            flash('Invalid Team ID. Please enter a valid Team ID.', 'danger')
        if not faculty_exists:
            flash('Invalid Faculty ID. Please enter a valid Faculty ID.', 'danger')

        # If there are errors, flash them and re-render the form
        if not team_exists or not faculty_exists:
            return render_template('register.html')

        # Hash the password using bcrypt (generate a salt and hash the password)
        salt = bcrypt.gensalt()  # Generate a salt
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)

        # Insert data if validation passes
        cursor.execute("""INSERT INTO Student (SRN, Name, Email, Phone, Gender, Section, Semester, GPA, deptid, teamid, facultyid, Password) 
                          VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                       (srn, name, email, phone, gender, section, semester, gpa, deptid, teamid, facultyid, hashed_password.decode('utf-8')))

        db.commit()
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('student_login'))

    return render_template('register.html')

# Faculty Login
@app.route('/login/faculty', methods=['GET', 'POST'])
def faculty_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        db = connect_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM Faculty WHERE Email = %s", (email,))
        faculty = cursor.fetchone()
        
        if faculty and bcrypt.checkpw(password.encode('utf-8'), faculty[4].encode('utf-8')):  # Assuming password is the fifth column
            user = User(faculty_id=faculty[0])  # Assuming FacultyID is the first column
            login_user(user)
            return redirect(url_for('faculty_dashboard', faculty_id=faculty[0]))
        else:
            flash('Invalid credentials, please try again.', 'danger')
    
    return render_template('faculty_login.html')

# Faculty Registration
@app.route('/register/faculty', methods=['GET', 'POST'])
def faculty_register():
    if request.method == 'POST':
        name = request.form['name']
        designation = request.form['designation']
        panel_id = request.form['panel_id']
        email = request.form['email']
        password = request.form['password']
        
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        db = connect_db()
        cursor = db.cursor()

        # Check if the entered Panel ID exists in the panel table
        cursor.execute("SELECT PanelID FROM panel WHERE PanelID = %s", (panel_id,))
        panel_exists = cursor.fetchone()

        if not panel_exists:
            # If the Panel ID does not exist, show an error message
            flash("The entered Panel ID does not exist. Please enter a valid Panel ID.", "error")
            return render_template('faculty_register.html')

        # Insert the faculty record if Panel ID exists
        cursor.execute(
            "INSERT INTO Faculty (FacultyName, Designation, Email, Password, PanelID) VALUES (%s, %s, %s, %s, %s)",
            (name, designation, email, hashed_password.decode('utf-8'), panel_id)
        )
        db.commit()
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('faculty_login'))
    
    return render_template('faculty_register.html')

# Admin Login
@app.route('/login/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        db = connect_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM Admin WHERE Email = %s", (email,))
        admin = cursor.fetchone()
        
        if admin and bcrypt.checkpw(password.encode('utf-8'), admin[3].encode('utf-8')):  # Assuming password is the fourth column
            user = User(admin_id=admin[0])  # Assuming AdminID is the first column
            login_user(user)  # Create the user session
            return redirect(url_for('admin_dashboard'))  # Redirect to admin dashboard
        else:
            flash('Invalid credentials, please try again.', 'danger')
    
    return render_template('admin_login.html')

# Admin Dashboard
@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    return render_template('admin_dashboard.html')

# Student Dashboard
@app.route('/student_dashboard/<srn>')
@login_required
def student_dashboard(srn):
    db = connect_db()
    cursor = db.cursor()

    # Query for team information
    cursor.execute("SELECT Team.ProjectName FROM Team "
                   "JOIN Student ON Team.TeamID = Student.TeamID WHERE Student.SRN = %s", (srn,))
    team_project_name = cursor.fetchone()

    # Query for all teammates in the same team
    cursor.execute("SELECT Student.Name FROM Student "
                   "WHERE TeamID = (SELECT TeamID FROM Student WHERE SRN = %s)", (srn,))
    teammates = cursor.fetchall()

    # Query for exam results
    cursor.execute("SELECT Exam.ExamID, Exam.ExamName, CapstoneMarks.TotalMarks FROM Exam "
                   "JOIN CapstoneMarks ON Exam.ExamID = CapstoneMarks.ExamID WHERE CapstoneMarks.SRN = %s", (srn,))
    exam_results = cursor.fetchall()

    # Query for upcoming exams
    current_date = datetime.now().date()
    cursor.execute("SELECT Exam.ExamID, Exam.ExamName, Exam.exam_date, Exam.exam_time FROM Exam "
                   "JOIN Student ON Exam.TeamID = Student.TeamID "
                   "WHERE Student.SRN = %s AND Exam.exam_date >= %s", (srn, current_date))
    upcoming_exams = cursor.fetchall()

    # Query for semester grades from StudentGrades
    cursor.execute("SELECT Semester, Total_marks_in_sem, Grade FROM StudentGrades WHERE SRN = %s", (srn,))
    semester_grades = cursor.fetchall()

    return render_template('student_dashboard.html', team_project_name=team_project_name,
                           teammates=teammates, exam_results=exam_results,
                           upcoming_exams=upcoming_exams, semester_grades=semester_grades)



# Faculty Dashboard
@app.route('/faculty_dashboard/<faculty_id>')
@login_required
def faculty_dashboard(faculty_id):
    db = connect_db()
    cursor = db.cursor()

    # Query for teams and students under the faculty's supervision
    cursor.execute("SELECT Team.TeamID, Team.ProjectName, Team.Domain, Student.Name FROM Team "
                   "JOIN Student ON Team.TeamID = Student.TeamID WHERE Student.FacultyID = %s", (faculty_id,))
    team_students = cursor.fetchall()

    # Query for upcoming exams for teams supervised by this faculty
    current_date = datetime.now().date()
    cursor.execute("""
        SELECT DISTINCT Exam.ExamID, Exam.ExamName, Exam.exam_date, Exam.exam_time 
        FROM Exam 
        JOIN Team ON Exam.TeamID = Team.TeamID 
        JOIN Student ON Student.TeamID = Team.TeamID 
        WHERE Student.FacultyID = %s AND Exam.exam_date >= %s
        """, (faculty_id, current_date))
    upcoming_exams = cursor.fetchall()

    return render_template('faculty_dashboard.html', team_students=team_students, upcoming_exams=upcoming_exams)


@app.route('/manage_teams', methods=['GET', 'POST'])
def manage_teams():
    if not is_admin():
        flash('You must be an admin to access this page.', 'error')
        return redirect(url_for('admin_login'))  # Redirect to admin login if needed

    db = connect_db()
    cursor = db.cursor()

    if request.method == 'POST':
        team_id = request.form.get('team_id')  # Get the team ID from the form
        project_name = request.form['project_name']
        domain = request.form['domain']
        dept_id = request.form['dept_id']
        faculty_id = request.form['faculty_id'] or None

        if team_id:  # If team_id is present, we are updating
            cursor.execute("UPDATE Team SET ProjectName = %s, Domain = %s, DeptID = %s WHERE TeamID = %s",
                           (project_name, domain, dept_id, team_id))
            # Update faculty supervisor if provided
            if faculty_id:
                cursor.execute("UPDATE Student SET FacultyID = %s WHERE TeamID = %s", (faculty_id, team_id))
            flash('Team updated successfully!', 'success')
        else:  # Otherwise, we are adding a new team
            cursor.execute("INSERT INTO Team (ProjectName, Domain, DeptID) VALUES (%s, %s, %s)",
                           (project_name, domain, dept_id))
            # Get the newly inserted team's ID
            new_team_id = cursor.lastrowid
            # Update faculty supervisor if provided
            if faculty_id:
                cursor.execute("UPDATE Student SET FacultyID = %s WHERE TeamID = %s", (faculty_id, new_team_id))
            flash('Team added successfully!', 'success')

        db.commit()

    # Retrieve the current teams with department and supervising faculty details
    cursor.execute("""
    SELECT Team.TeamID, Team.ProjectName, Team.Domain, Team.DeptID, Faculty.FacultyName
    FROM Team
    LEFT JOIN (
        SELECT DISTINCT TeamID, FacultyID FROM Student
    ) AS student_faculty ON Team.TeamID = student_faculty.TeamID
    LEFT JOIN Faculty ON student_faculty.FacultyID = Faculty.FacultyID
    """)
    teams = cursor.fetchall()

    # Retrieve departments for the dropdown
    cursor.execute("SELECT * FROM Department")
    departments = cursor.fetchall()

    # Retrieve faculties for the dropdown
    cursor.execute("SELECT FacultyID, FacultyName FROM Faculty")
    faculties = cursor.fetchall()

    return render_template('manage_teams.html', teams=teams, departments=departments, faculties=faculties)

# Route to delete a team
@app.route('/delete_team/<int:team_id>', methods=['POST'])
def delete_team(team_id):
    if not is_admin():
        flash('You must be an admin to perform this action.', 'error')
        return redirect(url_for('manage_teams'))

    db = connect_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM Team WHERE TeamID = %s", (team_id,))
    db.commit()
    flash('Team deleted successfully!', 'success')
    return redirect(url_for('manage_teams'))

# Update team route
@app.route('/update_team/<int:team_id>', methods=['POST'])
def update_team(team_id):
    if not is_admin():
        flash('You must be an admin to perform this action.', 'error')
        return redirect(url_for('manage_teams'))

    conn = connect_db()
    cursor = conn.cursor()

    project_name = request.form['project_name']
    domain = request.form['domain']
    dept_id = request.form['dept_id']
    faculty_id = request.form['faculty_id'] or None

    cursor.execute("""
    UPDATE Team SET ProjectName = %s, Domain = %s, DeptID = %s WHERE TeamID = %s
    """, (project_name, domain, dept_id, team_id))

    # Update faculty supervisor if provided
    if faculty_id:
        cursor.execute("UPDATE Student SET FacultyID = %s WHERE TeamID = %s", (faculty_id, team_id))

    conn.commit()
    conn.close()
    flash('Team updated successfully!')
    return redirect(url_for('manage_teams'))

# Function to check if the panel already exists in the database
def panel_exists(panel_name):
    db = connect_db()
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM Panel WHERE PanelName = %s", (panel_name,))
    count = cursor.fetchone()[0]
    db.close()
    return count > 0

# Route for managing panels
@app.route('/manage_panels', methods=['GET', 'POST'])
@login_required
def manage_panels():
    if not is_admin():
        flash('You must be an admin to access this page.', 'error')
        return redirect(url_for('admin_login'))  # Redirect to admin login if not admin

    db = connect_db()
    cursor = db.cursor()

    if request.method == 'POST':
        panel_id = request.form.get('panel_id')  # Get the panel ID from the form
        panel_name = request.form['panel_name']
        dept_id = request.form['dept_id']
        
        if panel_exists(panel_name):  # Check if the panel already exists
            flash('Panel with this name already exists!', 'error')
        else:
            if panel_id:  # If panel_id is present, we are updating
                cursor.execute("UPDATE Panel SET PanelName = %s, DeptID = %s WHERE PanelID = %s",
                               (panel_name, dept_id, panel_id))
                flash('Panel updated successfully!', 'success')
            else:  # Otherwise, we are adding a new panel
                cursor.execute("INSERT INTO Panel (PanelName, DeptID) VALUES (%s, %s)",
                               (panel_name, dept_id))
                flash('Panel added successfully!', 'success')

            db.commit()

        # Redirect to the same page to prevent resubmission (PRG Pattern)
        return redirect(url_for('manage_panels'))

    # Retrieve the current panels and departments for the dropdown
    cursor.execute("SELECT * FROM Panel")
    panels = cursor.fetchall()

    cursor.execute("SELECT * FROM Department")
    departments = cursor.fetchall()

    # Retrieve faculties for each panel
    cursor.execute("""
        SELECT p.PanelID, f.FacultyID, f.FacultyName, f.Designation
        FROM Panel p
        LEFT JOIN Faculty f ON p.PanelID = f.PanelID
        ORDER BY p.PanelID
    """)
    panel_faculty = cursor.fetchall()

    # Organize faculties by panel ID
    panel_faculty_dict = {}
    for panel_id, faculty_id, faculty_name, designation in panel_faculty:
        if panel_id not in panel_faculty_dict:
            panel_faculty_dict[panel_id] = []
        if faculty_id:
            panel_faculty_dict[panel_id].append({
                'FacultyID': faculty_id,
                'FacultyName': faculty_name,
                'Designation': designation
            })

    # Check faculties for a specific panel ID if provided
    check_panel_id = request.args.get('check_panel_id')
    faculties = []
    
    if check_panel_id:
        cursor.execute("SELECT FacultyID, FacultyName, Designation FROM Faculty WHERE PanelID = %s", (check_panel_id,))
        faculties = cursor.fetchall()

    db.close()  # Close the database connection

    return render_template('manage_panels.html', panels=panels, departments=departments,
                           panel_faculty_dict=panel_faculty_dict, faculties=faculties,
                           check_panel_id=check_panel_id)

@app.route('/delete_panel/<int:panel_id>', methods=['POST'])
@login_required
def delete_panel(panel_id):
    if not is_admin():
        flash('You must be an admin to delete a panel.', 'error')
        return redirect(url_for('admin_login'))

    db = connect_db()
    cursor = db.cursor()
    try:
        cursor.execute("DELETE FROM Panel WHERE PanelID = %s", (panel_id,))
        db.commit()
        flash('Panel deleted successfully!', 'success')
    except:
        db.rollback()
        flash('Error deleting panel.', 'error')
    finally:
        db.close()
    
    return redirect(url_for('manage_panels'))

@app.route('/update_faculty', methods=['POST'])
@login_required
def update_faculty():
    if not is_admin():
        flash('You must be an admin to update faculty details.', 'error')
        return redirect(url_for('admin_login'))

    faculty_id = request.form.get('faculty_id')
    faculty_name = request.form.get('faculty_name')
    designation = request.form.get('designation')
    panel_id = request.form.get('panel_id')
    # Debugging
    print(f"Received form data: {faculty_id}, {faculty_name}, {designation}, {panel_id}")
    db = connect_db()
    cursor = db.cursor()
    
    try:
        cursor.execute("""
            UPDATE Faculty 
            SET FacultyName = %s, Designation = %s, PanelID = %s 
            WHERE FacultyID = %s
        """, (faculty_name, designation, panel_id, faculty_id))
        db.commit()
        flash('Faculty updated successfully!', 'success')
    except:
        db.rollback()
        flash('Error updating faculty.', 'error')
    finally:
        db.close()
    
    return redirect(url_for('manage_panels'))



@app.route('/schedule_exams', methods=['GET', 'POST'])
@login_required  # Ensures only logged-in users can access
def schedule_exams():
    db = connect_db()
    cursor = db.cursor()

    if request.method == 'POST':
        # Get form data
        exam_name = request.form['exam_name']
        max_marks = request.form['max_marks_allotted']
        exam_date = request.form['exam_date']
        exam_time = request.form['exam_time']
        team_id = request.form['team_id']

        # Check if TeamID exists in the Team table
        cursor.execute("SELECT DeptID FROM Team WHERE TeamID = %s", (team_id,))
        result = cursor.fetchone()

        if not result:
            flash('Error: Team ID does not exist. Please enter a valid Team ID.', 'danger')
            db.close()
            return render_template('schedule_exam.html', exams=[])

        dept_id = result[0]

        # Check for exam scheduling conflict within the same department
        cursor.execute("""
            SELECT 1 
            FROM Exam e
            JOIN Team t ON e.TeamID = t.TeamID
            WHERE t.DeptID = %s AND e.exam_date = %s AND e.exam_time = %s
        """, (dept_id, exam_date, exam_time))
        
        conflict = cursor.fetchone()

        if conflict:
            flash('Error: Exam is already scheduled at this time for the department.', 'danger')
            db.close()
            return redirect(url_for('schedule_exams'))

        # Insert new exam into the database
        cursor.execute(
            "INSERT INTO Exam (ExamName, MaxMarksAllotted, exam_date, exam_time, TeamID) VALUES (%s, %s, %s, %s, %s)",
            (exam_name, max_marks, exam_date, exam_time, team_id)
        )
        db.commit()
        flash('Exam scheduled successfully!', 'success')
        return redirect(url_for('schedule_exams'))

    # Fetch all scheduled exams, sorted by ExamID in descending order
    cursor.execute("SELECT ExamID, ExamName, MaxMarksAllotted, exam_date, exam_time, TeamID FROM Exam ORDER BY ExamID DESC")
    exams = cursor.fetchall()
    db.close()

    return render_template('schedule_exam.html', exams=exams)


# Route for entering marks
@app.route('/marks_entry', methods=['GET', 'POST'])
def marks_entry():
    conn = connect_db()
    cursor = conn.cursor()
    
    # Fetch available Exam IDs and Faculty IDs
    cursor.execute("SELECT ExamID FROM exam")  # Changed from Exams to exam
    exam_ids = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT FacultyID FROM faculty")
    faculty_ids = [row[0] for row in cursor.fetchall()]
    
    if request.method == 'POST':
        srn = request.form['srn']
        exam_id = request.form['exam_id']
        faculty_id = request.form['faculty_id']
        marks_obtained = request.form['marks_obtained']
        
        try:
            cursor.execute("""
                INSERT INTO undergoes (SRN, ExamID, FacultyID, MarksObtained)
                VALUES (%s, %s, %s, %s)
            """, (srn, exam_id, faculty_id, marks_obtained))
            conn.commit()
            flash("Marks submitted successfully!", "success")
        except MySQLdb.IntegrityError as e:
            if 'foreign key constraint fails' in str(e):
                flash("Error: Invalid SRN, Exam ID, or Faculty ID. Please check and try again.", "danger")
            else:
                flash("An unexpected error occurred. Please try again later.", "danger")
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('marks_entry'))  # Redirect after POST to avoid form resubmission

    cursor.close()
    conn.close()
    
    return render_template('marks_entry.html', exam_ids=exam_ids, faculty_ids=faculty_ids)



# Route to handle search
@app.route('/search_marks', methods=['POST'])
def search_marks():
    srn = request.form['search_srn']
    exam_id = request.form['search_exam_id']

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT FacultyID, MarksObtained
        FROM Undergoes
        WHERE SRN = %s AND ExamID = %s
    """, (srn, exam_id))
    results = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('marks_entry.html', results=results, search_srn=srn, search_exam_id=exam_id)


# Route for viewing all students
@app.route('/student_details')
@login_required
def student_details():
    if not is_admin():
        flash('Access denied: Admins only', 'danger')
        return redirect(url_for('admin_login'))
    
    db = connect_db()
    cursor = db.cursor()
    
    cursor.execute("SELECT * FROM Student")
    students = cursor.fetchall()
    db.close()
    
    return render_template('student_details.html', students=students)

# Route to search for a specific student by SRN
@app.route('/search_student', methods=['GET'])
@login_required
def search_student():
    if not is_admin():
        flash('Access denied: Admins only', 'danger')
        return redirect(url_for('admin_login'))

    srn = request.args.get('srn')
    
    db = connect_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM Student WHERE SRN = %s", (srn,))
    student = cursor.fetchone()
    db.close()
    
    students = [student] if student else []  # Return as a list for consistency with the template
    
    return render_template('student_details.html', students=students)

# Route to fetch a student's data for updating
@app.route('/get_student_data/<srn>', methods=['GET'])
@login_required
def get_student_data(srn):
    if not is_admin():
        return jsonify({'message': 'Access denied: Admins only'}), 403

    db = connect_db()
    cursor = db.cursor()
    cursor.execute("SELECT SRN, Name, Email, Phone, Gender, Section, Semester, GPA, DeptID, TeamID, FacultyID, Password FROM Student WHERE SRN = %s", (srn,))
    student = cursor.fetchone()
    db.close()

    if student:
        # Convert the result into a dictionary for easier access in the frontend
        student_data = {
            'srn': student[0],
            'name': student[1],
            'email': student[2],
            'phone': student[3],
            'gender': student[4],
            'section': student[5],
            'semester': student[6],
            'gpa': student[7],
            'deptID': student[8],
            'teamID': student[9],
            'facultyID': student[10],
            'password': student[11]
        }
        return jsonify(student_data)
    else:
        return jsonify({'message': 'Student not found'}), 404

# Route to update a student's details via AJAX
@app.route('/update_student_ajax', methods=['POST'])
@login_required
def update_student_ajax():
    if not is_admin():
        return jsonify({'message': 'Access denied: Admins only'}), 403

    data = request.get_json()
    srn = data.get('srn')
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')
    gender = data.get('gender')
    section = data.get('section')
    semester = data.get('semester')
    gpa = data.get('gpa')
    deptid = data.get('deptID')
    teamid = data.get('teamID')
    facultyid = data.get('facultyID')
    password = data.get('password')

    db = connect_db()
    cursor = db.cursor()

    salt = bcrypt.gensalt()  # Generate a salt
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)

    cursor.execute("""UPDATE Student SET Name=%s, Email=%s, Phone=%s, Gender=%s, 
                      Section=%s, Semester=%s, GPA=%s, DeptID=%s, TeamID=%s, FacultyID=%s, Password=%s 
                      WHERE SRN=%s""",
                   (name, email, phone, gender, section, semester, gpa, deptid, teamid, facultyid, hashed_password.decode('utf-8'), srn))
    
    db.commit()
    db.close()
    
    return jsonify({'message': 'Student updated successfully!'})

@app.route('/delete_student_ajax', methods=['POST'])
@login_required
def delete_student_ajax():
    if not is_admin():
        return jsonify({'message': 'Access denied: Admins only'}), 403

    data = request.get_json()
    srn = data.get('srn')

    try:
        db = connect_db()
        cursor = db.cursor()
        cursor.execute("DELETE FROM Student WHERE SRN = %s", (srn,))
        db.commit()
        cursor.close()
        db.close()
        return jsonify({'message': 'Student deleted successfully!'})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'message': 'Failed to delete student'}), 500

# Route to display all faculty details (Admin only)
@app.route('/faculty_details', methods=['GET'])
@login_required
def faculty_details():
    if not is_admin():
        flash('Access denied: Admins only', 'danger')
        return redirect(url_for('admin_login'))
    
    faculty_id = request.args.get('faculty_id')  # Get faculty_id from query parameters
    db = connect_db()
    cursor = db.cursor()

    if faculty_id:  # If a Faculty ID is provided, search for that specific faculty
        cursor.execute("SELECT * FROM Faculty WHERE FacultyID = %s", (faculty_id,))
        faculties = cursor.fetchall()
    else:  # Otherwise, retrieve all faculty records
        cursor.execute("SELECT * FROM Faculty")
        faculties = cursor.fetchall()
    
    db.close()
    
    return render_template('faculty_details.html', faculties=faculties)

# Route to fetch a single faculty's data for the update modal
@app.route('/get_faculty_data/<int:faculty_id>', methods=['GET'])
@login_required
def get_faculty_data(faculty_id):
    if not is_admin():
        return jsonify({'message': 'Access denied: Admins only'}), 403

    db = connect_db()
    cursor = db.cursor()
    cursor.execute("SELECT FacultyID, FacultyName, Designation, PanelID, email, Password FROM Faculty WHERE FacultyID = %s", (faculty_id,))
    faculty = cursor.fetchone()
    db.close()

    if faculty:
        faculty_data = {
            'faculty_id': faculty[0],
            'name': faculty[1],
            'designation': faculty[2],
            'panel_id': faculty[3],
            'email':faculty[4],
            'password':faculty[5]
        }
        return jsonify(faculty_data)
    else:
        return jsonify({'message': 'Faculty not found'}), 404

# AJAX route for updating faculty details
@app.route('/update_faculty_ajax', methods=['POST'])
@login_required
def update_faculty_ajax():
    if not is_admin():
        return jsonify({'message': 'Access denied: Admins only'}), 403

    data = request.get_json()
    faculty_id = data.get('faculty_id')
    name = data.get('name')
    designation = data.get('designation')
    panel_id = data.get('panel_id')
    email=data.get('email')
    password=data.get('password')

    try:
        db = connect_db()
        cursor = db.cursor()
        salt = bcrypt.gensalt()  # Generate a salt
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
        cursor.execute("""UPDATE Faculty SET FacultyName=%s, Designation=%s, PanelID=%s, email=%s, Password=%s WHERE FacultyID=%s""",
                       (name, designation, panel_id, email, hashed_password.decode('utf-8'), faculty_id))
        db.commit()
        db.close()

        # Send a JSON response with success message
        return jsonify({'message': 'Faculty updated successfully!', 'success': True})
    except Exception as e:
        print("Error updating faculty:", e)  # Log error for debugging
        return jsonify({'message': 'Failed to update faculty', 'success': False}), 500

# Route for deleting a faculty record using standard HTTP POST
@app.route('/delete_faculty/<int:faculty_id>', methods=['POST'])
@login_required
def delete_faculty(faculty_id):
    if not is_admin():
        flash('Access denied: Admins only', 'danger')
        return redirect(url_for('admin_login'))
    
    db = connect_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM Faculty WHERE FacultyID = %s", (faculty_id,))
    db.commit()
    db.close()
    
    flash('Faculty deleted successfully!', 'success')
    return redirect(url_for('faculty_details'))

# Route for deleting a faculty via AJAX
@app.route('/delete_faculty_ajax', methods=['POST'])
@login_required
def delete_faculty_ajax():
    if not is_admin():
        return jsonify({'message': 'Access denied: Admins only'}), 403

    data = request.get_json()
    faculty_id = data.get('faculty_id')

    try:
        db = connect_db()
        cursor = db.cursor()
        cursor.execute("DELETE FROM Faculty WHERE FacultyID = %s", (faculty_id,))
        db.commit()
        db.close()

        # Send a JSON response with success message
        return jsonify({'message': 'Faculty deleted successfully!'})
    except Exception as e:
        print("Error deleting faculty:", e)  # Log error for debugging
        return jsonify({'message': 'Failed to delete faculty'}), 500
    

# Logout
@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))

# Check if user is admin
def is_admin():
    return current_user.is_authenticated and current_user.admin_id is not None

if __name__ == '__main__':
    app.run(debug=True)
