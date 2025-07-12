from flask import Flask, jsonify, request
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app, origins=['*'])

@app.route('/')
def home():
    return jsonify({'message': 'Working!', 'status': 'ok'})

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

@app.route('/api/v1/auth/login', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        return '', 200
    return jsonify({'message': 'Login works', 'token': 'test123'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
