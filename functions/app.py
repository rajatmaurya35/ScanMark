from flask import Flask, request, jsonify
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import app as flask_app

def handler(event, context):
    # Get HTTP method, headers, and body from event
    method = event.get('httpMethod', 'GET')
    headers = event.get('headers', {})
    body = event.get('body', '')
    path = event.get('path', '/')
    query_params = event.get('queryStringParameters', {})

    # Convert API Gateway format to WSGI format
    environ = {
        'REQUEST_METHOD': method,
        'SCRIPT_NAME': '',
        'PATH_INFO': path,
        'QUERY_STRING': '&'.join([f"{k}={v}" for k, v in query_params.items()]) if query_params else '',
        'SERVER_NAME': headers.get('Host', 'localhost'),
        'SERVER_PORT': headers.get('X-Forwarded-Port', '80'),
        'SERVER_PROTOCOL': 'HTTP/1.1',
        'wsgi.version': (1, 0),
        'wsgi.url_scheme': headers.get('X-Forwarded-Proto', 'http'),
        'wsgi.input': body,
        'wsgi.errors': sys.stderr,
        'wsgi.multithread': False,
        'wsgi.multiprocess': False,
        'wsgi.run_once': False,
    }

    # Add headers
    for key, value in headers.items():
        key = key.upper().replace('-', '_')
        if key not in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
            key = f'HTTP_{key}'
        environ[key] = value

    # Run Flask app
    response = {}
    def start_response(status, headers):
        status_code = int(status.split()[0])
        response['statusCode'] = status_code
        response['headers'] = dict(headers)

    body = b''.join(flask_app(environ, start_response))
    response['body'] = body.decode('utf-8')

    return response
