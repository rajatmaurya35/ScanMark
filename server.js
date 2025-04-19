const express = require('express');
const cors = require('cors');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 10000;

// Enable CORS
app.use(cors());

// Parse JSON bodies
app.use(express.json());

// Serve static files
app.use(express.static('public'));

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'healthy', message: 'ScanMark API is running!' });
});

// Root endpoint
app.get('/', (req, res) => {
  res.json({
    name: 'ScanMark API',
    status: 'online',
    message: 'Welcome to ScanMark API',
    endpoints: [
      { path: '/health', description: 'Health check endpoint' }
    ]
  });
});

// Start the server
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
