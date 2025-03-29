from flask import Flask, request, jsonify
from redis import Redis

from rq import Queue
from rq.registry import FailedJobRegistry, StartedJobRegistry, FinishedJobRegistry

import json
import os
import psutil
from datetime import datetime

from worker import embed_snippet, decode_redis_data

app = Flask(__name__)
data_folder = './data'

redis_conn = Redis(host='localhost', port=6379, decode_responses=False)
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
    job = queue.enqueue(embed_snippet, data, timestamp)
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
    try:
        # Check Redis connection
        redis_status = redis_conn.ping()

        # Get queue stats
        job_count = len(queue.jobs)  # Jobs in queue
        started_registry = StartedJobRegistry(queue.name, connection=redis_conn)
        active_jobs = len(started_registry.get_job_ids())

        failed_registry = FailedJobRegistry(queue.name, connection=redis_conn)
        failed_jobs = len(failed_registry.get_job_ids())

        finished_registry = FinishedJobRegistry(queue.name, connection=redis_conn)
        completed_jobs = len(finished_registry.get_job_ids())

        # Get system resource usage
        memory_usage = psutil.virtual_memory().percent
        cpu_usage = psutil.cpu_percent(interval=1)

        return jsonify({
            "status": "ok" if redis_status else "unhealthy",
            "queue": {
                "pending_jobs": job_count,
                "active_jobs": active_jobs,
                "failed_jobs": failed_jobs,
                "completed_jobs": completed_jobs
            },
            "system": {
                "cpu_usage": f"{cpu_usage}%",
                "memory_usage": f"{memory_usage}%"
            }
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/job_status/<job_id>', methods=['GET'])
def job_status(job_id):
    try:
        raw_job = redis_conn.hgetall(f"rq:job:{job_id}")
        job = decode_redis_data(raw_job)

        desc = job["description"]

        return jsonify({
            "job_id": job_id,
            "started_at": job["started_at"],
            "ended_at": job["ended_at"]
        }), 200
    except Exception as e:
        print(f"Error fetching job status: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/failed_jobs', methods=['GET'])
def failed_jobs():
    failed_registry = FailedJobRegistry(queue.name, connection=redis_conn)
    failed_job_ids = failed_registry.get_job_ids()

    return jsonify({
        "failed_jobs": failed_job_ids,
        "count": len(failed_job_ids)
    }), 200

@app.before_request
def log_request():
    with open("api_requests.log", "a") as log_file:
        log_file.write(f"{datetime.now()} - {request.method} {request.path}\n")
        
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
