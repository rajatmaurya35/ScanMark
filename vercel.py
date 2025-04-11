from app import app
from urllib.parse import urlencode

def handler(request, context):
    # Convert Vercel request to WSGI environ
    environ = {
        'REQUEST_METHOD': request['method'],
        'SCRIPT_NAME': '',
        'PATH_INFO': request['path'],
        'QUERY_STRING': urlencode(request.get('query', {})),
        'SERVER_PROTOCOL': 'HTTP/1.1',
        'wsgi.version': (1, 0),
        'wsgi.url_scheme': 'https',
        'wsgi.input': request.get('body', ''),
        'wsgi.errors': '',
        'wsgi.multithread': False,
        'wsgi.multiprocess': False,
        'wsgi.run_once': False,
        'HTTP_HOST': request.get('headers', {}).get('host', ''),
        'SERVER_NAME': request.get('headers', {}).get('host', '').split(':')[0],
        'SERVER_PORT': '443',
        'CONTENT_TYPE': request.get('headers', {}).get('content-type', ''),
        'CONTENT_LENGTH': request.get('headers', {}).get('content-length', ''),
    }

    # Add HTTP headers
    for key, value in request.get('headers', {}).items():
        key = key.upper().replace('-', '_')
        if key not in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
            environ[f'HTTP_{key}'] = value

    # Response data
    response_data = {'statusCode': 200, 'headers': {}, 'body': ''}

    def start_response(status, headers):
        status_code = int(status.split()[0])
        response_data['statusCode'] = status_code
        response_data['headers'].update(dict(headers))

    # Get response from Flask app
    response_body = b''.join(app(environ, start_response))
    response_data['body'] = response_body.decode('utf-8')

    return response_data
