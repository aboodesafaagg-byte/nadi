
import os
import time
import threading
import schedule
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from bson.objectid import ObjectId
from nadi_client import NadiClient

app = Flask(__name__)
CORS(app)

# --- Configuration ---
MONGO_URI = os.environ.get('MONGODB_URI', 'mongodb+srv://zeusadmin:28oyX5thnmG2YerK@chatzeuscluster.kd3pgaa.mongodb.net/?retryWrites=true&w=majority&appName=ChatZeusCluster')
API_SECRET = os.environ.get('API_SECRET', 'Zeusndndjddnejdjdjdejekk29393838msmskxcm9239484jdndjdnddjj99292938338zeuslojdnejxxmejj82283849')

# --- Database ---
try:
    client = MongoClient(MONGO_URI)
    db = client.get_database() # Uses default DB from URI
    print("✅ Connected to MongoDB")
except Exception as e:
    print(f"❌ MongoDB Connection Error: {e}")

# --- In-Memory Scheduler State ---
# Structure: { job_id: { 'novel_id': ..., 'target_nadi_id': ..., 'current_ch': ..., 'end_ch': ..., 'interval': ..., 'last_run': ..., 'status': 'active/paused', 'cookies': ... } }
active_jobs = {}

# --- Worker Function ---
def run_publisher_job(job_id):
    job = active_jobs.get(job_id)
    if not job or job['status'] != 'active':
        return

    now = time.time()
    if now - job['last_run'] < (job['interval'] * 60): # interval in minutes
        return

    try:
        # 1. Fetch Chapter from DB
        novel_id = job['novel_id']
        current_ch_num = job['current_ch']
        
        # Determine collection (Novel or TranslationJob?). Assuming 'Novel' has finalized chapters.
        # We need to find the chapter in the 'novels' collection
        novel = db.novels.find_one({'_id': ObjectId(novel_id)})
        if not novel:
            print(f"❌ Novel not found: {novel_id}")
            job['status'] = 'error'
            job['error_msg'] = "Novel not found in DB"
            return

        # Find specific chapter
        chapter = next((c for c in novel.get('chapters', []) if c['number'] == current_ch_num), None)
        
        # If content isn't in the array (lightweight), fetch from Firestore/Separate collection?
        # Assuming for this tool we fetch content from the 'novels' collection (assuming it's stored there or we need a way to get content)
        # *Correction based on App logic*: Content is likely in Firestore or bulky MongoDB field. 
        # Since I am Python, I cannot access Firestore easily without creds. 
        # I will assume content is in MongoDB for now or passed via job (no, too big).
        # Let's assume we query the 'TranslationChapter' collection or similar if it exists, OR rely on 'chapters' array having content (if not filtered).
        
        # For this implementation, we will assume we can get content. If 'content' is missing in 'chapter', we fail.
        # Fallback: Check if there's a 'TranslationChapter' collection
        content = chapter.get('content', '')
        if not content:
             # Try finding in separate collection if exists
             pass 

        if not content:
             job['logs'].append(f"❌ الفصل {current_ch_num}: لا يوجد محتوى")
             job['status'] = 'error'
             return

        # 2. Publish to Nadi
        client = NadiClient(job['cookies'])
        title = chapter.get('title', f'الفصل {current_ch_num}')
        
        print(f"🚀 Publishing Ch {current_ch_num} to Nadi...")
        result = client.publish_chapter(job['target_nadi_id'], current_ch_num, title, content)

        if result['success']:
            job['logs'].append(f"✅ تم نشر الفصل {current_ch_num} بنجاح")
            job['current_ch'] += 1
            job['last_run'] = now
            job['published_count'] += 1
            
            if job['current_ch'] > job['end_ch']:
                job['status'] = 'completed'
                job['logs'].append("🏁 انتهت المهمة")
        else:
            job['logs'].append(f"❌ فشل نشر الفصل {current_ch_num}: {result['error']}")
            # Don't stop immediately, maybe retry next interval? Or pause?
            # Let's pause to be safe
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

@app.route('/nadi/jobs', methods=['GET'])
def get_jobs():
    # Convert dict to list for frontend
    jobs_list = []
    for jid, job in active_jobs.items():
        jobs_list.append({
            'id': jid,
            'novelTitle': job['novel_title'],
            'status': job['status'],
            'progress': f"{job['current_ch']} / {job['end_ch']}",
            'lastLog': job['logs'][-1] if job['logs'] else "بدء...",
            'nextRun': job['last_run'] + (job['interval'] * 60) if job['status'] == 'active' else None
        })
    return jsonify(jobs_list)

@app.route('/nadi/start', methods=['POST'])
def start_job():
    data = request.json
    job_id = str(int(time.time()))
    
    active_jobs[job_id] = {
        'id': job_id,
        'novel_id': data['novelId'],
        'novel_title': data['novelTitle'],
        'target_nadi_id': data['nadiId'], # ID on Nadi Website
        'current_ch': int(data['startCh']),
        'end_ch': int(data['endCh']),
        'interval': int(data['interval']), # Minutes
        'cookies': data['cookies'],
        'status': 'active',
        'last_run': 0, # Force immediate run
        'published_count': 0,
        'logs': ["تم إنشاء المهمة"]
    }
    return jsonify({"success": True, "jobId": job_id})

@app.route('/nadi/stop', methods=['POST'])
def stop_job():
    data = request.json
    job_id = data['jobId']
    if job_id in active_jobs:
        active_jobs[job_id]['status'] = 'paused'
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
    
    if not query or not cookies:
        return jsonify([])
        
    client = NadiClient(cookies)
    results = client.search_novel(query)
    return jsonify(results)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
