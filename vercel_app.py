from flask import Flask, request, jsonify
from app import app as flask_app

def handler(request):
    """Handle Vercel serverless function requests."""
    path = request.get('path', '/')
    method = request.get('method', 'GET')
    body = request.get('body', '')
    headers = request.get('headers', {})
    
    # Create test client
    client = flask_app.test_client()
    
    # Make request to Flask app
    if method == 'GET':
        response = client.get(path, headers=headers)
    elif method == 'POST':
        response = client.post(path, data=body, headers=headers)
    else:
        return {
            'statusCode': 405,
            'body': 'Method not allowed'
        }
    
    # Return response
    return {
        'statusCode': response.status_code,
        'headers': dict(response.headers),
        'body': response.get_data(as_text=True)
    }
