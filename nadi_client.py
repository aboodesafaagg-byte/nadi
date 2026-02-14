
import requests
import json
import re

# 🔥 القيم المستخرجة من الصور (جلسة حقيقية)
REAL_SESSION_ID = "p2u5rg3a873jfq4s9wqr0hgpise6s545"
REAL_CSRF_TOKEN = "r5N1EuEWndcd8KDEppfqeXqix12BfTPGby1QhySMCH22lg7B08pl6lqBHRg8xNsui"
# تم فك الترميز من Token%20302... إلى Token 302...
REAL_AUTH_TOKEN = "Token 302bd3c2f811704f0fddce79a14f56250f9cc652" 

class NadiClient:
    def __init__(self, cookies_str=None):
        self.base_url = "https://api.rewayat.club/api"
        
        # بناء سلسلة الكوكيز الصلبة إذا لم يتم تمرير كوكيز
        if not cookies_str:
            self.cookies_dict = {
                "sessionid": REAL_SESSION_ID,
                "csrftoken": REAL_CSRF_TOKEN,
                "auth.strategy": "google",
                "auth._token.google": REAL_AUTH_TOKEN.replace(" ", "%20") # Re-encode for cookie
            }
            # تحويلها لنص للهيدر إذا لزم الأمر، لكن Requests يفضل Dict
        else:
            # محاولة تحليل النص الوارد
            self.cookies_dict = {}
            for pair in cookies_str.split(';'):
                if '=' in pair:
                    k, v = pair.strip().split('=', 1)
                    self.cookies_dict[k] = v

        # استخراج التوكن والـ CSRF لاستخدامهم في الهيدر
        self.auth_token = self.cookies_dict.get("auth._token.google", REAL_AUTH_TOKEN).replace("%20", " ")
        self.csrf_token = self.cookies_dict.get("csrftoken", REAL_CSRF_TOKEN)

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json',
            'Origin': 'https://rewayat.club',
            'Referer': 'https://rewayat.club/',
            'X-CSRFToken': self.csrf_token,
            'Authorization': self.auth_token 
        }

    def search_novel(self, query):
        """بحث حقيقي في مكتبة نادي الروايات"""
        try:
            # بناءً على ملف المكتبة، البحث يتم عبر باراميتر search
            url = f"{self.base_url}/novels/"
            params = {
                "search": query,
                "limit": 10  # أو page_size
            }
            res = requests.get(url, params=params, headers=self.headers, cookies=self.cookies_dict)
            
            if res.status_code == 200:
                data = res.json()
                # النتائج عادة تكون في root array أو داخل مفتاح results (Django REST default)
                results = data.get('results', data) if isinstance(data, dict) else data
                
                # تنسيق البيانات للتطبيق
                formatted = []
                for item in results:
                    formatted.append({
                        "id": item.get('slug') or item.get('id'), # Slug هو المعرف في النادي غالباً
                        "title": item.get('arabic') or item.get('english') or item.get('title'),
                        "cover": item.get('poster_url') or item.get('cover'),
                        "author": "نادي الروايات"
                    })
                return formatted
            else:
                print(f"Search Failed: {res.status_code} {res.text}")
                return []
        except Exception as e:
            print(f"Search Exception: {e}")
            return []

    def format_content(self, text):
        """تنسيق النص ليناسب محرر النادي (HTML)"""
        lines = text.split('\n')
        formatted = []
        for line in lines:
            line = line.strip()
            if not line: continue
            if re.match(r'^_{3,}$', line):
                formatted.append(f'<center>{line}</center>')
            else:
                formatted.append(f'<p dir="auto">{line}</p>')
        return "".join(formatted)

    def publish_chapter(self, novel_slug_or_id, chapter_num, title, content):
        """نشر فصل جديد"""
        url = f"{self.base_url}/chapters/"
        
        html_content = self.format_content(content)
        
        # بناءً على Vue component، البيانات المطلوبة هي:
        # novel (slug/id), number, title, content, status, published_at
        payload = {
            "novel": novel_slug_or_id, 
            "number": float(chapter_num),
            "title": title,
            "content": html_content,
            "status": 1, # 1 usually means Published in Django choices, or "published" string
            "published_at": None # Now
        }

        try:
            res = requests.post(url, json=payload, headers=self.headers, cookies=self.cookies_dict)
            
            if res.status_code in [200, 201]:
                return {"success": True, "data": res.json()}
            else:
                return {"success": False, "error": f"HTTP {res.status_code}: {res.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_novel(self, title_ar, title_en, description, cover_url, genres):
        """إنشاء رواية جديدة في النادي"""
        url = f"{self.base_url}/novels/"
        
        # بناءً على ملف "إنشاء رواية"، الحقول هي:
        # arabic, english, about, poster_url, genre (array of IDs), type (1=translated, 2=original)
        
        payload = {
            "arabic": title_ar,
            "english": title_en,
            "about": description,
            "poster_url": cover_url, # يفترض أنك رفعت الصورة مسبقاً أو ترسل رابط مباشر
            "genre": genres, # [1, 2, 5] IDs
            "original": False, # 1=Translated usually
            "complete": False
        }

        try:
            res = requests.post(url, json=payload, headers=self.headers, cookies=self.cookies_dict)
            if res.status_code in [200, 201]:
                data = res.json()
                return {"success": True, "id": data.get('slug') or data.get('id')}
            else:
                return {"success": False, "error": f"HTTP {res.status_code}: {res.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
