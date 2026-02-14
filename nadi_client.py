
import requests
import json
import time
import re

# 🔥 الكوكيز الافتراضية المستخرجة من الصور
DEFAULT_COOKIES = 'wordpress_sec_198f6e9e82ba200a53325105f201ddc5=mikey%7C1771590380%7CKJphcZkhBFCpXyLUDrDcGPi9XmNOC47IPCSEHAPyfXS%7C5e8e596c5389b65f91a30668be6f16c7134b98b3ae55a007ed360594dd035527; cf_clearance=qYXkJIaj1IiaBKgi561_IQ.9oWgJ3fx10itfVR20lXY-1765278736-1.2.1.1-soYoRwUhDSq_.2cCoaJ22MPadmCmaQ0cW3AkfA1L97BJIbxQQro5hvpmuJxhQaT57TxfEW10l9gQYsmy5QgrwLsiWHScUWVvqYzZufRRYs9LIDPAhyxiOnL2Byevi12fb8iAZWttVNlqYWeKjH06tTp8bNhPx4dsmudPpIh0qzijEZhRk8lK6nWip1SeDFO2Of35W2rBKDEtjidGFyIj1RU3B7Xt.4CVoQbE9pGFaS8gFTMOp.0qmMMiz1UmHoFc; wpmanga-body-contrast=light; wpmanga-reading-history=W3siaWQiOjEyODE3LCJjIjoiMzEzMDgiLCJwIjoxLCJpIjoiIiwidCI6MTc2ODEwMTY3MH1d; sbjs_migrations=1418474375998%3D1; sbjs_current_add=fd%3D2026-02-06%2012%3A25%3A57%7C%7C%7Cep%3Dhttps%3A%2F%2Fmarkazriwayat.com%2F%7C%7C%7Crf%3Dhttps%3A%2F%2Fwww.bing.com%2F; sbjs_first_add=fd%3D2026-02-06%2012%3A25%3A57%7C%7C%7Cep%3Dhttps%3A%2F%2Fmarkazriwayat.com%2F%7C%7C%7Crf%3Dhttps%3A%2F%2Fwww.bing.com%2F; sbjs_current=typ%3Dreferral%7C%7C%7Csrc%3Dbing.com%7C%7C%7Cmdm%3Dreferral%7C%7C%7Ccmp%3D%28none%29%7C%7C%7Ccnt%3D%2F%7C%7C%7Ctrm%3D%28none%29%7C%7C%7Cid%3D%28none%29%7C%7C%7Cplt%3D%28none%29%7C%7C%7Cfmt%3D%28none%29%7C%7C%7Ctct%3D%28none%29; sbjs_first=typ%3Dreferral%7C%7C%7Csrc%3Dbing.com%7C%7C%7Cmdm%3Dreferral%7C%7C%7Ccmp%3D%28none%29%7C%7C%7Ccnt%3D%2F%7C%7C%7Ctrm%3D%28none%29%7C%7C%7Cid%3D%28none%29%7C%7C%7Cplt%3D%28none%29%7C%7C%7Cfmt%3D%28none%29%7C%7C%7Ctct%3D%28none%29; sbjs_udata=vst%3D1%7C%7C%7Cuip%3D%28none%29%7C%7C%7Cuag%3DMozilla%2F5.0%20%28Windows%20NT%206.2%3B%20Win64%3B%20x64%29%20AppleWebKit%2F537.36%20%28KHTML%2C%20like%20Gecko%29%20Chrome%2F109.0.0.0%20Safari%2F537.36%20Edg%2F109.0.1518.140; wordpress_test_cookie=WP%20Cookie%20check; _lscache_vary=8d8d3777c370b0211addc5b0a9411cd9; wordpress_logged_in_198f6e9e82ba200a53325105f201ddc5=mikey%7C1771590380%7CKJphcZkhBFCpXyLUDrDcGPi9XmNOC47IPCSEHAPyfXS%7Cb7d906dce3f0b160d5c2f585bfec331fe7d0cc3e4640a74945cc619df837e5c9; sbjs_session=pgs%3D2%7C%7C%7Ccpg%3Dhttps%3A%2F%2Fmarkazriwayat.com%2F%3Fnsl_bypass_cache%3D74d71305203b9ce18787813c87e33f8c'

class NadiClient:
    def __init__(self, cookies_str=None):
        self.base_url = "https://api.rewayat.club" 
        # استخدم الكوكيز الممررة، وإذا كانت فارغة استخدم الافتراضية
        self.cookies = cookies_str if cookies_str and len(cookies_str) > 20 else DEFAULT_COOKIES
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json',
            'Origin': 'https://rewayat.club',
            'Referer': 'https://rewayat.club/',
            'Cookie': self.cookies
        }

    def search_novel(self, query):
        """Simulate the autocomplete search to find novel ID"""
        try:
            # Try public API first or the search endpoint derived from HTML logic
            url = f"{self.base_url}/novels"
            res = requests.get(url, params={'search': query, 'limit': 5}, headers=self.headers)
            if res.status_code == 200:
                data = res.json()
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
