const express = require('express');
const cors = require('cors');
const path = require('path');
const { PythonShell } = require('python-shell');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 10000;

// Enable CORS
app.use(cors());

// Parse JSON bodies
app.use(express.json());

// Serve static files
app.use(express.static('static'));
app.use(express.static('public'));

// Serve the Flask app's static files
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// API routes - proxy to Python Flask app
app.all('/api/*', (req, res) => {
  const options = {
    mode: 'text',
    pythonPath: 'python',
    pythonOptions: ['-u'],
    scriptPath: __dirname,
    args: [JSON.stringify(req.body)]
  };

  PythonShell.run('flask_api.py', options, function (err, results) {
    if (err) {
      console.error('Error running Flask API:', err);
      return res.status(500).json({ error: 'Internal Server Error' });
    }
    
    try {
      const response = JSON.parse(results[0]);
      res.status(200).json(response);
    } catch (e) {
      console.error('Error parsing Flask API response:', e);
      res.status(500).json({ error: 'Internal Server Error' });
    }
  });
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'healthy', message: 'ScanMark API is running!' });
});

// Admin routes
app.get('/admin/*', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'admin-app.html'));
});

// Start the server
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
