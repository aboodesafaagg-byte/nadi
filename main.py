
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

active_jobs = {}

# --- Helper: Fetch Chapter From Node Backend ---
def fetch_chapter_from_backend(novel_id, chapter_num):
    try:
        url = f"{NODE_BACKEND_URL}/api/novels/{novel_id}/chapters/{chapter_num}"
        headers = {
            'Content-Type': 'application/json',
            'x-api-secret': API_SECRET 
        }
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            return response.json()
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
    if now - job['last_run'] < (job['interval'] * 60): 
        return

    if not job['chapters_queue']:
        job['status'] = 'completed'
        job['logs'].append("🏁 انتهت جميع الفصول المطلوبة")
        return

    try:
        current_ch_num = job['chapters_queue'][0]
        
        # 1. Fetch content locally
        chapter_data = fetch_chapter_from_backend(job['novel_id'], current_ch_num)
        
        if not chapter_data or not chapter_data.get('content'):
            job['logs'].append(f"❌ الفصل {current_ch_num}: لم يتم العثور على المحتوى")
            job['status'] = 'paused' 
            return

        content = chapter_data.get('content', '')
        title = chapter_data.get('title', f'الفصل {current_ch_num}')

        # 2. Publish to Nadi
        # Use provided cookies OR default hardcoded ones in client
        client = NadiClient(job.get('cookies'))
        
        print(f"🚀 Publishing Ch {current_ch_num} to Nadi...")
        result = client.publish_chapter(job['target_nadi_id'], current_ch_num, title, content)

        if result['success']:
            job['logs'].append(f"✅ تم نشر الفصل {current_ch_num}")
            job['chapters_queue'].pop(0) 
            job['last_run'] = now
            job['published_count'] += 1
            
            if not job['chapters_queue']:
                job['status'] = 'completed'
                job['logs'].append("🏁 انتهت المهمة")
        else:
            job['logs'].append(f"❌ فشل الفصل {current_ch_num}: {result['error']}")
            job['status'] = 'paused'

    except Exception as e:
        print(f"Job Error: {e}")
        job['logs'].append(f"❌ خطأ: {str(e)}")
        job['status'] = 'error'

# --- Background Thread ---
def scheduler_loop():
    while True:
        try:
            for job_id in list(active_jobs.keys()):
                run_publisher_job(job_id)
            time.sleep(10)
        except Exception as e:
            print(f"Scheduler Error: {e}")
            time.sleep(10)

threading.Thread(target=scheduler_loop, daemon=True).start()

# --- API Endpoints ---

@app.route('/', methods=['GET'])
def health():
    return "Nadi Publisher Service V2 Running", 200

@app.route('/nadi/jobs', methods=['GET'])
def get_jobs():
    jobs_list = []
    for jid, job in active_jobs.items():
        total = len(job['chapters_queue']) + job['published_count']
        current = job['published_count']
        jobs_list.append({
            'id': jid,
            'novelTitle': job['novel_title'],
            'status': job['status'],
            'progress': f"{current} / {total}",
            'lastLog': job['logs'][-1] if job['logs'] else "...",
            'nextRun': job['last_run'] + (job['interval'] * 60) if job['status'] == 'active' else None
        })
    return jsonify(jobs_list)

@app.route('/nadi/start', methods=['POST'])
def start_job():
    data = request.json
    job_id = str(int(time.time()))
    
    chapters_queue = []
    if 'chapters' in data and isinstance(data['chapters'], list):
        chapters_queue = sorted([int(x) for x in data['chapters']])
    
    if not chapters_queue:
        return jsonify({"success": False, "message": "No chapters"}), 400

    active_jobs[job_id] = {
        'id': job_id,
        'novel_id': data['novelId'],
        'novel_title': data['novelTitle'],
        'target_nadi_id': data['nadiId'],
        'chapters_queue': chapters_queue,
        'interval': int(data.get('interval', 15)),
        'cookies': data.get('cookies'), 
        'status': 'active',
        'last_run': 0,
        'published_count': 0,
        'logs': [f"بدء المهمة: {len(chapters_queue)} فصل"]
    }
    return jsonify({"success": True, "jobId": job_id})

@app.route('/nadi/stop', methods=['POST'])
def stop_job():
    data = request.json
    job_id = data['jobId']
    if job_id in active_jobs:
        active_jobs[job_id]['status'] = 'paused'
        active_jobs[job_id]['logs'].append("⏸️ إيقاف يدوي")
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

@app.route('/nadi/create-novel', methods=['POST'])
def create_novel():
    data = request.json
    client = NadiClient(data.get('cookies'))
    
    result = client.create_novel(
        title_ar=data['titleAr'],
        title_en=data['titleEn'],
        description=data['description'],
        cover_url=data['cover'],
        genres=data['genres'] # List of IDs e.g. [1, 5]
    )
    return jsonify(result)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
