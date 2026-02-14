
import os
import time
import threading
import schedule
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from nadi_client import NadiClient

app = Flask(__name__)
CORS(app)

# --- Configuration ---
NODE_BACKEND_URL = os.environ.get('NODE_BACKEND_URL', 'https://c-production-a9ce.up.railway.app')
API_SECRET = os.environ.get('API_SECRET', 'Zeusndndjddnejdjdjdejekk29393838msmskxcm9239484jdndjdnddjj99292938338zeuslojdnejxxmejj82283849')

# --- In-Memory Scheduler State ---
# Structure: { job_id: { 'novel_id': ..., 'target_nadi_id': ..., 'chapters_queue': [num1, num2], 'interval': ..., 'last_run': ..., 'status': 'active', 'cookies': ... } }
active_jobs = {}

# --- Helper: Fetch Chapter From Node Backend ---
def fetch_chapter_from_backend(novel_id, chapter_num):
    """
    Fetches chapter data directly from the Node.js backend.
    """
    try:
        # Assuming the Node backend has a public route for fetching chapters or we use the scraper check route
        # Since we need CONTENT, we should use the standard reader API route.
        # GET /api/novels/:novelId/chapters/:chapterId
        url = f"{NODE_BACKEND_URL}/api/novels/{novel_id}/chapters/{chapter_num}"
        
        # We might need a user token, but let's try with the API_SECRET header 
        # (Assuming you added support or it's a public/semi-public route)
        # Note: If the route requires 'Authorization: Bearer token', this script might need a valid token.
        # For now, we simulate a request. 
        headers = {
            'Content-Type': 'application/json',
            # 'Authorization': f'Bearer {token}' # If needed
        }
        
        # NOTE: If your backend strictly requires a User Token for reading content, 
        # you should implement a login mechanism here or pass a token from the App.
        # However, following the "Scraper" pattern which uses API_SECRET for privileged access:
        headers['x-api-secret'] = API_SECRET 
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Failed to fetch from backend: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error fetching from backend: {e}")
        return None

# --- Worker Function ---
def run_publisher_job(job_id):
    job = active_jobs.get(job_id)
    if not job or job['status'] != 'active':
        return

    now = time.time()
    if now - job['last_run'] < (job['interval'] * 60): # interval in minutes
        return

    # Check if we have chapters to process
    if not job['chapters_queue']:
        job['status'] = 'completed'
        job['logs'].append("🏁 انتهت جميع الفصول المطلوبة")
        return

    try:
        # Get next chapter number
        current_ch_num = job['chapters_queue'][0]
        
        # 1. Fetch from Node Backend (HTTP)
        chapter_data = fetch_chapter_from_backend(job['novel_id'], current_ch_num)
        
        if not chapter_data or not chapter_data.get('content'):
            job['logs'].append(f"❌ الفصل {current_ch_num}: لم يتم العثور على المحتوى في السيرفر")
            # Move to next to avoid stuck loop? Or pause?
            # Let's pause to let user fix it
            job['status'] = 'paused' 
            return

        content = chapter_data.get('content', '')
        title = chapter_data.get('title', f'الفصل {current_ch_num}')

        # 2. Publish to Nadi
        client = NadiClient(job['cookies'])
        
        print(f"🚀 Publishing Ch {current_ch_num} to Nadi...")
        result = client.publish_chapter(job['target_nadi_id'], current_ch_num, title, content)

        if result['success']:
            job['logs'].append(f"✅ تم نشر الفصل {current_ch_num} بنجاح")
            # Remove from queue
            job['chapters_queue'].pop(0) 
            job['last_run'] = now
            job['published_count'] += 1
            
            if not job['chapters_queue']:
                job['status'] = 'completed'
                job['logs'].append("🏁 انتهت المهمة")
        else:
            job['logs'].append(f"❌ فشل نشر الفصل {current_ch_num}: {result['error']}")
            # Pause on failure to prevent spamming
            job['status'] = 'paused'

    except Exception as e:
        print(f"Job Error: {e}")
        job['logs'].append(f"❌ خطأ غير متوقع: {str(e)}")
        job['status'] = 'error'

# --- Background Thread ---
def scheduler_loop():
    while True:
        try:
            # Create a copy of keys to avoid runtime error if dict changes
            for job_id in list(active_jobs.keys()):
                run_publisher_job(job_id)
            time.sleep(10) # Check every 10 seconds
        except Exception as e:
            print(f"Scheduler Loop Error: {e}")
            time.sleep(10)

threading.Thread(target=scheduler_loop, daemon=True).start()

# --- API Endpoints ---

@app.route('/', methods=['GET'])
def health():
    return "Nadi Publisher Service Running", 200

@app.route('/nadi/jobs', methods=['GET'])
def get_jobs():
    # Convert dict to list for frontend
    jobs_list = []
    for jid, job in active_jobs.items():
        total = len(job['chapters_queue']) + job['published_count']
        current = job['published_count']
        
        jobs_list.append({
            'id': jid,
            'novelTitle': job['novel_title'],
            'status': job['status'],
            'progress': f"{current} / {total}",
            'lastLog': job['logs'][-1] if job['logs'] else "بدء...",
            'nextRun': job['last_run'] + (job['interval'] * 60) if job['status'] == 'active' else None
        })
    return jsonify(jobs_list)

@app.route('/nadi/start', methods=['POST'])
def start_job():
    data = request.json
    job_id = str(int(time.time()))
    
    # Generate queue of chapters based on input
    chapters_queue = []
    
    # If explicit list is provided (from manual selection)
    if 'chapters' in data and isinstance(data['chapters'], list):
        chapters_queue = sorted([int(x) for x in data['chapters']])
    # Or range
    elif 'startCh' in data and 'endCh' in data:
        start = int(data['startCh'])
        end = int(data['endCh'])
        chapters_queue = list(range(start, end + 1))
    
    if not chapters_queue:
        return jsonify({"success": False, "message": "No chapters selected"}), 400

    active_jobs[job_id] = {
        'id': job_id,
        'novel_id': data['novelId'],
        'novel_title': data['novelTitle'],
        'target_nadi_id': data['nadiId'], # ID on Nadi Website
        'chapters_queue': chapters_queue,
        'interval': int(data.get('interval', 15)), # Minutes
        'cookies': data.get('cookies'), # Can be None, client uses default
        'status': 'active',
        'last_run': 0, # Force immediate run
        'published_count': 0,
        'logs': [f"تم بدء المهمة: {len(chapters_queue)} فصل"]
    }
    return jsonify({"success": True, "jobId": job_id})

@app.route('/nadi/stop', methods=['POST'])
def stop_job():
    data = request.json
    job_id = data['jobId']
    if job_id in active_jobs:
        active_jobs[job_id]['status'] = 'paused'
        active_jobs[job_id]['logs'].append("⏸️ تم الإيقاف يدوياً")
    return jsonify({"success": True})

@app.route('/nadi/delete', methods=['POST'])
def delete_job():
    data = request.json
    job_id = data['jobId']
    if job_id in active_jobs:
        del active_jobs[job_id]
    return jsonify({"success": True})

@app.route('/nadi/search', methods=['POST'])
def search_nadi():
    data = request.json
    query = data.get('query')
    cookies = data.get('cookies')
    
    if not query:
        return jsonify([])
        
    client = NadiClient(cookies)
    results = client.search_novel(query)
    return jsonify(results)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
