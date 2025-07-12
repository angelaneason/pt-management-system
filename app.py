from flask import Flask, jsonify, request
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app, origins=['*'])

@app.route('/')
def home():
    return jsonify({'message': 'API Working'})

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

@app.route('/api/v1/auth/login', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        return '', 200
    
    return jsonify({
        'success': True,
        'user': {
            'id': 1,
            'username': 'admin',
            'email': 'admin@test.com',
            'role': 'admin',
            'companies': []
        },
        'token': 'fake-jwt-token-123',
        'message': 'Login successful'
    })

@app.route('/api/v1/companies', methods=['GET', 'OPTIONS'])
def get_companies():
    if request.method == 'OPTIONS':
        return '', 200
    return jsonify([])

@app.route('/api/v1/tenants/<slug>/patients', methods=['GET', 'OPTIONS'])
def get_patients(slug):
    if request.method == 'OPTIONS':
        return '', 200
    return jsonify([])

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)


