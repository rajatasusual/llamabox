from flask import Flask, request, jsonify
import os
import json
from datetime import datetime

app = Flask(__name__)
data_folder = './data'

if not os.path.exists(data_folder):
    os.makedirs(data_folder)

@app.route('/snippet', methods=['POST'])
def snippet():
    data = request.json
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    filename = os.path.join(data_folder, f'snippet_{timestamp}.json')
    with open(filename, 'w') as f:
        json.dump(data, f)
    print("Received snippet data:", data)
    return jsonify({"message": "Snippet data received"}), 200

@app.route('/page', methods=['POST'])
def page():
    data = request.json
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    filename = os.path.join(data_folder, f'page_{timestamp}.json')
    with open(filename, 'w') as f:
        json.dump(data, f)
    print("Received page data:", data)
    return jsonify({"message": "Page data received"}), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
