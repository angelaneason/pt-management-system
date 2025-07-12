import os
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'

# Simple CORS - allows all origins
CORS(app, supports_credentials=True, origins=['*'])

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'version': '2.0.0'})

@app.route('/')
def home():
    return jsonify({'message': 'PT Management System API', 'status': 'running'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
