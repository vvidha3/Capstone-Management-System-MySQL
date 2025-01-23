create database capstone_management;
use capstone_management;

CREATE TABLE Department (
    DeptID INT AUTO_INCREMENT PRIMARY KEY,
    DeptName VARCHAR(50) NOT NULL
);

CREATE TABLE Team (
    TeamID INT AUTO_INCREMENT PRIMARY KEY,
    ProjectName VARCHAR(100),
    Domain VARCHAR(50),
    DeptID INT,
    FOREIGN KEY (DeptID) REFERENCES Department(DeptID)
);

CREATE TABLE Panel (
    PanelID INT AUTO_INCREMENT PRIMARY KEY,
    PanelName VARCHAR(50),
    DeptID INT,
    FOREIGN KEY (DeptID) REFERENCES Department(DeptID)
);

CREATE TABLE Faculty (
    FacultyID INT AUTO_INCREMENT PRIMARY KEY,
    FacultyName VARCHAR(100),
    Designation VARCHAR(50),
    PanelID INT,
    FOREIGN KEY (PanelID) REFERENCES Panel(PanelID)
);

ALTER TABLE faculty ADD Password VARCHAR(60);
ALTER TABLE faculty ADD email VARCHAR(30);

CREATE TABLE Student (
    SRN VARCHAR(10) PRIMARY KEY,
    Name VARCHAR(50),
    Email VARCHAR(50),
    Phone VARCHAR(15),
    Gender ENUM('M', 'F'),
    Section VARCHAR(10),
    Semester INT,
    GPA DECIMAL(4, 2),
    DeptID INT,
    TeamID INT,
    FacultyID INT,
    FOREIGN KEY (DeptID) REFERENCES Department(DeptID),
    FOREIGN KEY (TeamID) REFERENCES Team(TeamID),
    FOREIGN KEY (FacultyID) REFERENCES Faculty(FacultyID)
);

ALTER TABLE Student ADD Password VARCHAR(60);

CREATE TABLE Exam (
    ExamID INT AUTO_INCREMENT PRIMARY KEY,
    ExamName VARCHAR(50),
    MaxMarksAllotted INT
);

ALTER TABLE Exam ADD COLUMN exam_date DATE;
ALTER TABLE Exam ADD COLUMN exam_time TIME;
ALTER TABLE Exam ADD COLUMN TeamID INT;
ALTER TABLE Exam
ADD CONSTRAINT fk_team
FOREIGN KEY (TeamID) REFERENCES Team(TeamID)
ON DELETE CASCADE
ON UPDATE CASCADE;


CREATE TABLE CapstoneMarks (
    SRN VARCHAR(10),
    ExamID INT,
    TotalMarks INT,
    PRIMARY KEY (SRN, ExamID),
    FOREIGN KEY (SRN) REFERENCES Student(SRN) ON DELETE CASCADE,
    FOREIGN KEY (ExamID) REFERENCES Exam(ExamID) ON DELETE CASCADE
);

CREATE TABLE Undergoes (
    SRN VARCHAR(10),
    ExamID INT,
    FacultyID INT,
    MarksObtained INT,
    Date_of_Exam DATE,
    PRIMARY KEY (SRN, ExamID, FacultyID),
    FOREIGN KEY (SRN) REFERENCES Student(SRN) ON DELETE CASCADE,
    FOREIGN KEY (ExamID) REFERENCES Exam(ExamID),
    FOREIGN KEY (FacultyID) REFERENCES Faculty(FacultyID)
);

ALTER TABLE Undergoes DROP COLUMN Date_of_Exam;

CREATE TABLE EvaluatedBy (
    SRN VARCHAR(10),
    FacultyID INT,
    PRIMARY KEY (SRN, FacultyID),
    FOREIGN KEY (SRN) REFERENCES Student(SRN) ON DELETE CASCADE,
    FOREIGN KEY (FacultyID) REFERENCES Faculty(FacultyID)
);

CREATE TABLE StudentGrades (
    SRN VARCHAR(10),
    Semester INT,
    Total_marks_in_sem INT,
    Grade ENUM('S', 'A', 'B', 'C', 'D', 'E', 'F'),
    PRIMARY KEY (SRN, Semester),
    FOREIGN KEY (SRN) REFERENCES Student(SRN)
);

CREATE TABLE admin (
    AdminID int NOT NULL AUTO_INCREMENT,
    AdminName varchar(100),
    Email varchar(100) UNIQUE,
    Password varchar(255),
    PRIMARY KEY (AdminID)
);

DELIMITER //
CREATE TRIGGER calculate_total_marks
AFTER INSERT ON Undergoes
FOR EACH ROW
BEGIN
   DECLARE avg_marks INT;
   SELECT AVG(MarksObtained) INTO avg_marks
   FROM Undergoes
   WHERE SRN = NEW.SRN AND ExamID = NEW.ExamID;
   
   INSERT INTO CapstoneMarks (SRN, ExamID, TotalMarks)
   VALUES (NEW.SRN, NEW.ExamID, avg_marks)
   ON DUPLICATE KEY UPDATE TotalMarks = avg_marks;
END //
DELIMITER ;


DELIMITER //

CREATE PROCEDURE calculate_and_store_grades()
BEGIN
    -- Insert or update records in StudentGrades based on calculated total marks
    INSERT INTO StudentGrades (SRN, Semester, Total_marks_in_sem, Grade)
    SELECT
        s.SRN,
        s.Semester,
        SUM(c.TotalMarks) AS Total_marks_in_sem,
        CASE
            WHEN SUM(c.TotalMarks) >= 90 THEN 'S'
            WHEN SUM(c.TotalMarks) >= 80 THEN 'A'
            WHEN SUM(c.TotalMarks) >= 70 THEN 'B'
            WHEN SUM(c.TotalMarks) >= 60 THEN 'C'
            WHEN SUM(c.TotalMarks) >= 50 THEN 'D'
            WHEN SUM(c.TotalMarks) >= 40 THEN 'E'
            ELSE 'F'
        END AS Grade
    FROM
        Student s
    JOIN
        CapstoneMarks c ON s.SRN = c.SRN
    JOIN
        Exam e ON c.ExamID = e.ExamID
    WHERE
        LEFT(e.ExamName, 1) = CAST(s.Semester AS CHAR)  -- Match exams starting with the semester number
    GROUP BY
        s.SRN, s.Semester
    ON DUPLICATE KEY UPDATE
        Total_marks_in_sem = VALUES(Total_marks_in_sem),
        Grade = VALUES(Grade);
END //

DELIMITER ;

DELIMITER //
CREATE TRIGGER check_undergoes_count
AFTER INSERT ON undergoes
FOR EACH ROW
BEGIN
    DECLARE entry_count INT;

    -- Count total entries for the inserted SRN in the undergoes table
    SELECT COUNT(*) INTO entry_count
    FROM undergoes
    WHERE SRN = NEW.SRN;

    -- Check if the count is a multiple of 9
    IF entry_count % 9 = 0 THEN
        -- Call the grade calculation function
        CALL calculate_and_store_grades();
    END IF;
END //
DELIMITER ;
