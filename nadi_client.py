
import requests
import json
import time
import re

class NadiClient:
    def __init__(self, cookies_str):
        self.base_url = "https://api.rewayat.club" # Based on the HTML provided
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json',
            'Origin': 'https://rewayat.club',
            'Referer': 'https://rewayat.club/',
            'Cookie': cookies_str
        }

    def search_novel(self, query):
        """Simulate the autocomplete search to find novel ID"""
        # Based on Nuxt/Vuetify pattern in the HTML
        url = f"{self.base_url}/novels/search?q={query}" 
        # Fallback if API structure is different, we try standard REST
        try:
            # Try public API first
            res = requests.get(f"{self.base_url}/novels", params={'search': query, 'limit': 5}, headers=self.headers)
            if res.status_code == 200:
                data = res.json()
                # Adapt based on actual response structure
                results = data.get('results', data.get('data', data))
                return results
        except Exception as e:
            print(f"Search Error: {e}")
        return []

    def format_content(self, text):
        """Format text to HTML as per Nadi requirements"""
        lines = text.split('\n')
        formatted = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if re.match(r'^_{3,}$', line): # Separator
                formatted.append(f'<center>{line}</center>')
            else:
                formatted.append(f'<p dir="auto">{line}</p>')
        return "".join(formatted)

    def publish_chapter(self, novel_id_nadi, chapter_num, title, content):
        """Send POST request to create chapter"""
        url = f"{self.base_url}/chapters"
        
        html_content = self.format_content(content)
        
        payload = {
            "novel": novel_id_nadi, # The ID in Nadi Database
            "number": float(chapter_num),
            "title": title,
            "content": html_content,
            "status": "published", # or 'draft'
            "published_at": None # Means 'Now'
        }

        try:
            res = requests.post(url, json=payload, headers=self.headers)
            if res.status_code in [200, 201]:
                return {"success": True, "data": res.json()}
            else:
                return {"success": False, "error": f"HTTP {res.status_code}: {res.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
