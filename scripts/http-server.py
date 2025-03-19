from flask import Flask, request, jsonify
from redis import Redis
from rq import Queue
import json
import os
from datetime import datetime
from worker import process_snippet  # Import the function for processing

app = Flask(__name__)
data_folder = './data'

redis_conn = Redis(host='localhost', port=6379, decode_responses=True)
queue = Queue('snippet_queue', connection=redis_conn)  # Create Redis-backed queue

if not os.path.exists(data_folder):
    os.makedirs(data_folder)

@app.route('/snippet', methods=['POST'])
def snippet():
    data = request.json
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    
    # Save the raw data for logging/debugging
    filename = os.path.join(data_folder, f'snippet_{timestamp}.json')
    with open(filename, 'w') as f:
        json.dump(data, f)
    
    # Enqueue the task for processing
    job = queue.enqueue(process_snippet, data, timestamp)
    print(f"Queued job {job.id} for processing.")

    return jsonify({"message": "Snippet data received", "job_id": job.id}), 202

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
    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
