// Global variables
let stream;
let faceCapture = null;
let fingerprintData = null;

// Face capture functionality
async function initializeCamera() {
    try {
        stream = await navigator.mediaDevices.getUserMedia({ video: true });
        document.getElementById('video').srcObject = stream;
    } catch (err) {
        console.error('Error accessing camera:', err);
        alert('Unable to access camera. Please check permissions.');
    }
}

document.getElementById('captureBtn').addEventListener('click', () => {
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const context = canvas.getContext('2d');
    
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    context.drawImage(video, 0, 0);
    
    faceCapture = canvas.toDataURL('image/jpeg');
    alert('Face captured successfully!');
});

// Fingerprint simulation
document.getElementById('scanFingerprint').addEventListener('click', () => {
    // Simulate fingerprint scanning
    fingerprintData = {
        timestamp: Date.now(),
        data: Array.from({ length: 32 }, () => Math.floor(Math.random() * 256))
    };
    alert('Fingerprint scanned successfully!');
});

// Registration form submission
document.getElementById('registrationForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    if (!faceCapture || !fingerprintData) {
        alert('Please capture both face and fingerprint data');
        return;
    }
    
    const formData = {
        name: document.getElementById('name').value,
        face_image: faceCapture,
        fingerprint: fingerprintData
    };
    
    try {
        const response = await fetch('/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        alert(result.message);
        
        if (result.success) {
            document.getElementById('registrationForm').reset();
            faceCapture = null;
            fingerprintData = null;
        }
    } catch (err) {
        console.error('Error during registration:', err);
        alert('Registration failed. Please try again.');
    }
});

// QR Code scanning
let html5QrcodeScanner;

document.getElementById('startScanning').addEventListener('click', () => {
    if (!html5QrcodeScanner) {
        html5QrcodeScanner = new Html5Qrcode("qrReader");
    }
    
    const qrConfig = { fps: 10, qrbox: { width: 250, height: 250 } };
    
    html5QrcodeScanner.start(
        { facingMode: "environment" },
        qrConfig,
        async (decodedText) => {
            // Get current location
            try {
                const position = await getCurrentPosition();
                const attendanceData = {
                    student_id: decodedText,
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude,
                    verification_method: 'qr'
                };
                
                const response = await fetch('/mark-attendance', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(attendanceData)
                });
                
                const result = await response.json();
                document.getElementById('attendanceStatus').innerHTML = 
                    `<div class="alert alert-${result.success ? 'success' : 'danger'}">${result.message}</div>`;
                
                if (result.success) {
                    html5QrcodeScanner.stop();
                }
            } catch (err) {
                console.error('Error marking attendance:', err);
                alert('Failed to mark attendance. Please try again.');
            }
        },
        (error) => {
            console.warn(`QR Code scanning error: ${error}`);
        }
    );
});

// Get current position
function getCurrentPosition() {
    return new Promise((resolve, reject) => {
        if (!navigator.geolocation) {
            reject(new Error('Geolocation is not supported by your browser'));
        } else {
            navigator.geolocation.getCurrentPosition(resolve, reject, {
                enableHighAccuracy: true,
                timeout: 5000,
                maximumAge: 0
            });
        }
    });
}

// Initialize camera when page loads
window.addEventListener('load', initializeCamera);
