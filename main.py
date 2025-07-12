import os
from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'

# Enable CORS for all origins
CORS(app, supports_credentials=True, origins=['*'])

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'version': '2.0.0'})

@app.route('/')
def home():
    return jsonify({'message': 'PT Management System API', 'status': 'running'})

@app.route('/api/v1/info')
def api_info():
    return jsonify({'api': 'PT Management System', 'version': '2.0.0'})

@app.route('/api/v1/auth/login', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        return '', 200
    
    # Simple test login - accepts any credentials
    data = request.get_json() if request.is_json else {}
    username = data.get('username', '')
    
    if username:
        return jsonify({
            'message': 'Login successful',
            'user': {
                'id': 1,
                'username': username,
                'role': 'admin'
            },
            'token': 'test-token-123'
        })
    else:
        return jsonify({'error': 'Username required'}), 400

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

