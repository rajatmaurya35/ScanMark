// Dashboard JavaScript

// Handle QR Code Generation
document.getElementById('qrForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const formData = {
        subject: document.getElementById('subject').value,
        faculty: document.getElementById('faculty').value,
        branch: document.getElementById('branch').value,
        semester: document.getElementById('semester').value
    };

    try {
        const response = await fetch('/admin/generate-qr', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });

        const data = await response.json();

        if (data.success) {
            document.getElementById('qrForm').style.display = 'none';
            document.getElementById('qrResult').style.display = 'block';
            document.getElementById('qrImage').src = `data:image/png;base64,${data.qr_code}`;
            document.getElementById('qrLink').href = data.form_url;
        } else {
            Swal.fire('Error', data.message || 'Failed to generate QR code', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        Swal.fire('Error', 'Failed to generate QR code', 'error');
    }
});

// View QR Code
function viewQR(token) {
    fetch(`/admin/qr/${token}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                Swal.fire({
                    title: 'QR Code',
                    html: `
                        <img src="data:image/png;base64,${data.qr_code}" class="img-fluid">
                        <div class="mt-3">
                            <a href="${data.form_url}" target="_blank" class="btn btn-success">Open Form</a>
                            <button onclick="shareQRCode('${data.form_url}')" class="btn btn-info">Share</button>
                            <button onclick="downloadQR('${data.qr_code}')" class="btn btn-primary">Download</button>
                        </div>
                    `,
                    showConfirmButton: false
                });
            } else {
                Swal.fire('Error', data.message || 'Failed to load QR code', 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            Swal.fire('Error', 'Failed to load QR code', 'error');
        });
}

// Share QR Code
function shareQR(token) {
    fetch(`/admin/qr/${token}`)
        .then(response => response.json())
        .then(data => {
            if (data.success && data.form_url) {
                if (navigator.share) {
                    navigator.share({
                        title: 'ScanMark Attendance QR',
                        text: 'Scan this QR code to mark your attendance',
                        url: data.form_url
                    });
                } else {
                    navigator.clipboard.writeText(data.form_url)
                        .then(() => Swal.fire('Success', 'Link copied to clipboard!', 'success'));
                }
            }
        })
        .catch(error => {
            console.error('Error:', error);
            Swal.fire('Error', 'Failed to share QR code', 'error');
        });
}

// View Session History
function viewHistory(token) {
    fetch(`/admin/session/${token}/history`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const historyContent = document.getElementById('historyContent');
                historyContent.innerHTML = `
                    <div class="table-responsive">
                        <table class="table">
                            <thead>
                                <tr>
                                    <th>Student ID</th>
                                    <th>Time</th>
                                    <th>Location</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${data.history.map(entry => `
                                    <tr>
                                        <td>${entry.student_id}</td>
                                        <td>${new Date(entry.created_at).toLocaleString()}</td>
                                        <td>
                                            <a href="https://www.openstreetmap.org/?mlat=${entry.latitude}&mlon=${entry.longitude}" 
                                               target="_blank" class="btn btn-sm btn-info">
                                                View Location
                                            </a>
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                `;
                new bootstrap.Modal(document.getElementById('historyModal')).show();
            } else {
                Swal.fire('Error', data.message || 'Failed to load history', 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            Swal.fire('Error', 'Failed to load history', 'error');
        });
}

// Delete Session
function deleteSession(token) {
    Swal.fire({
        title: 'Delete Session',
        text: 'Are you sure you want to delete this session?',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#d33',
        cancelButtonColor: '#3085d6',
        confirmButtonText: 'Yes, delete it!'
    }).then((result) => {
        if (result.isConfirmed) {
            fetch(`/admin/session/${token}`, {
                method: 'DELETE'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    Swal.fire('Deleted!', 'Session has been deleted.', 'success')
                        .then(() => window.location.reload());
                } else {
                    Swal.fire('Error', data.message || 'Failed to delete session', 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                Swal.fire('Error', 'Failed to delete session', 'error');
            });
        }
    });
}

// Download QR Code
function downloadQR(base64Data) {
    const link = document.createElement('a');
    link.href = `data:image/png;base64,${base64Data}`;
    link.download = 'scanmark-qr.png';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Share QR Code
function shareQRCode(url) {
    if (navigator.share) {
        navigator.share({
            title: 'ScanMark Attendance QR',
            text: 'Scan this QR code to mark your attendance',
            url: url
        });
    } else {
        navigator.clipboard.writeText(url)
            .then(() => Swal.fire('Success', 'Link copied to clipboard!', 'success'));
    }
}

// Handle Cancel Button
document.querySelector('#qrModal .btn-secondary').addEventListener('click', function() {
    document.getElementById('qrForm').reset();
    document.getElementById('qrForm').style.display = 'block';
    document.getElementById('qrResult').style.display = 'none';
});
