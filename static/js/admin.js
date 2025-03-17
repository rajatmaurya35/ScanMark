// Admin Dashboard JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize all tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    // Department Management
    const departmentForm = document.getElementById('departmentForm');
    if (departmentForm) {
        departmentForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(departmentForm);
            try {
                const response = await fetch('/admin/department/add', {
                    method: 'POST',
                    body: JSON.stringify(Object.fromEntries(formData)),
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                const result = await response.json();
                if (result.success) {
                    showAlert('success', 'Department added successfully!');
                    location.reload();
                } else {
                    showAlert('danger', result.message);
                }
            } catch (error) {
                showAlert('danger', 'Failed to add department');
            }
        });
    }

    // Course Management
    const courseForm = document.getElementById('courseForm');
    if (courseForm) {
        courseForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(courseForm);
            try {
                const response = await fetch('/admin/course/add', {
                    method: 'POST',
                    body: JSON.stringify(Object.fromEntries(formData)),
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                const result = await response.json();
                if (result.success) {
                    showAlert('success', 'Course added successfully!');
                    location.reload();
                } else {
                    showAlert('danger', result.message);
                }
            } catch (error) {
                showAlert('danger', 'Failed to add course');
            }
        });
    }

    // Student Management
    const studentForm = document.getElementById('studentForm');
    if (studentForm) {
        studentForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(studentForm);
            try {
                const response = await fetch('/admin/student/add', {
                    method: 'POST',
                    body: JSON.stringify(Object.fromEntries(formData)),
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                const result = await response.json();
                if (result.success) {
                    showAlert('success', 'Student added successfully!');
                    location.reload();
                } else {
                    showAlert('danger', result.message);
                }
            } catch (error) {
                showAlert('danger', 'Failed to add student');
            }
        });
    }

    // Teacher Management
    const teacherForm = document.getElementById('teacherForm');
    if (teacherForm) {
        teacherForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(teacherForm);
            try {
                const response = await fetch('/admin/teacher/add', {
                    method: 'POST',
                    body: JSON.stringify(Object.fromEntries(formData)),
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                const result = await response.json();
                if (result.success) {
                    showAlert('success', 'Teacher added successfully!');
                    location.reload();
                } else {
                    showAlert('danger', result.message);
                }
            } catch (error) {
                showAlert('danger', 'Failed to add teacher');
            }
        });
    }

    // Schedule Management
    const scheduleForm = document.getElementById('scheduleForm');
    if (scheduleForm) {
        scheduleForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(scheduleForm);
            try {
                const response = await fetch('/admin/schedule/add', {
                    method: 'POST',
                    body: JSON.stringify(Object.fromEntries(formData)),
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                const result = await response.json();
                if (result.success) {
                    showAlert('success', 'Schedule added successfully!');
                    location.reload();
                } else {
                    showAlert('danger', result.message);
                }
            } catch (error) {
                showAlert('danger', 'Failed to add schedule');
            }
        });
    }

    // Attendance Reports
    const generateReportBtn = document.getElementById('generateReport');
    if (generateReportBtn) {
        generateReportBtn.addEventListener('click', async () => {
            const courseId = document.getElementById('reportCourse').value;
            const startDate = document.getElementById('startDate').value;
            const endDate = document.getElementById('endDate').value;

            try {
                const response = await fetch(`/admin/report?courseId=${courseId}&startDate=${startDate}&endDate=${endDate}`);
                const result = await response.json();
                if (result.success) {
                    displayReport(result.data);
                } else {
                    showAlert('danger', 'Failed to generate report');
                }
            } catch (error) {
                showAlert('danger', 'Error generating report');
            }
        });
    }

    // Utility Functions
    function showAlert(type, message) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.querySelector('.container').insertBefore(alertDiv, document.querySelector('.container').firstChild);
        setTimeout(() => alertDiv.remove(), 5000);
    }

    function displayReport(data) {
        const reportContainer = document.getElementById('reportContainer');
        if (!reportContainer) return;

        let html = `
            <div class="card mt-4">
                <div class="card-header">
                    <h5 class="mb-0">Attendance Report</h5>
                </div>
                <div class="card-body">
                    <div class="table-responsive">
                        <table class="table table-hover">
                            <thead>
                                <tr>
                                    <th>Student Name</th>
                                    <th>Roll Number</th>
                                    <th>Present</th>
                                    <th>Absent</th>
                                    <th>Late</th>
                                    <th>Attendance %</th>
                                </tr>
                            </thead>
                            <tbody>
        `;

        data.forEach(student => {
            const attendancePercentage = ((student.present / (student.present + student.absent + student.late)) * 100).toFixed(2);
            html += `
                <tr>
                    <td>${student.name}</td>
                    <td>${student.rollNumber}</td>
                    <td>${student.present}</td>
                    <td>${student.absent}</td>
                    <td>${student.late}</td>
                    <td>
                        <div class="progress">
                            <div class="progress-bar ${getProgressBarClass(attendancePercentage)}" 
                                 role="progressbar" 
                                 style="width: ${attendancePercentage}%">
                                ${attendancePercentage}%
                            </div>
                        </div>
                    </td>
                </tr>
            `;
        });

        html += `
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;

        reportContainer.innerHTML = html;
    }

    function getProgressBarClass(percentage) {
        if (percentage >= 75) return 'bg-success';
        if (percentage >= 60) return 'bg-warning';
        return 'bg-danger';
    }

    // Initialize date pickers if present
    const dateInputs = document.querySelectorAll('input[type="date"]');
    dateInputs.forEach(input => {
        input.valueAsDate = new Date();
    });
});
