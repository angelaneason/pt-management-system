@app.route('/api/v1/auth/login', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        return '', 200
    
    data = request.get_json() if request.is_json else {}
    username = data.get('username', '')
    
    return jsonify({
        'user': {
            'id': 1,
            'username': username,
            'role': 'admin'
        },
        'token': 'test-token-123'
    })

