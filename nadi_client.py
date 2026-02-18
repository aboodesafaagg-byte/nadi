
import requests
import json
import re

# 🔥 القيم المستخرجة من الصور (جلسة حقيقية)
REAL_SESSION_ID = "p2u5rg3a873jfq4s9wqr0hgpise6s545"
REAL_CSRF_TOKEN = "r5N1EuEWndcd8KDEppfqeXqix12BfTPGby1QhySMCH22lg7B08pl6lqBHRg8xNsui"
REAL_AUTH_TOKEN = "Token 302bd3c2f811704f0fddce79a14f56250f9cc652" 

class NadiClient:
    def __init__(self, cookies_str=None):
        # 🔥 الرابط الصحيح للـ API
        self.base_url = "https://api.rewayat.club/api"
        
        # بناء سلسلة الكوكيز الصلبة
        if not cookies_str:
            self.cookies_dict = {
                "sessionid": REAL_SESSION_ID,
                "csrftoken": REAL_CSRF_TOKEN,
                "auth.strategy": "google",
                "auth._token.google": REAL_AUTH_TOKEN.replace(" ", "%20")
            }
        else:
            self.cookies_dict = {}
            for pair in cookies_str.split(';'):
                if '=' in pair:
                    k, v = pair.strip().split('=', 1)
                    self.cookies_dict[k] = v

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
        """بحث حقيقي - استخراج الـ ID الرقمي ضروري للنشر"""
        try:
            url = f"{self.base_url}/novels/"
            params = { "search": query, "limit": 10 }
            res = requests.get(url, params=params, headers=self.headers, cookies=self.cookies_dict)
            
            if res.status_code == 200:
                data = res.json()
                results = data.get('results', data) if isinstance(data, dict) else data
                
                formatted = []
                for item in results:
                    # 🔥 نأخذ الـ id الرقمي وليس الـ slug، لأن إنشاء الفصل يطلب ID
                    formatted.append({
                        "id": item.get('id'), # رقمي (Integer) - مهم جداً
                        "slug": item.get('slug'), # نصي
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
        """تنسيق النص كفقرات HTML للحفاظ على التنسيق كما في السكربت JS"""
        if not text: return ""
        lines = text.split('\n')
        formatted = []
        for line in lines:
            line = line.strip()
            if not line: continue
            
            # فواصل النادي (ثلاث شرطات أو أكثر)
            if re.match(r'^_{3,}$', line) or re.match(r'^\*{3,}$', line):
                formatted.append(f'<center>{line}</center>')
            else:
                # التفاف النص في وسم p مع dir="auto"
                formatted.append(f'<p dir="auto">{line}</p>')
        return "".join(formatted)

    def publish_chapter(self, novel_id_numeric, chapter_num, title, content):
        """نشر فصل جديد - يستخدم ID الرقمي"""
        # 🔥 الرابط يجب أن ينتهي بـ slash /
        url = f"{self.base_url}/chapters/"
        
        html_content = self.format_content(content)
        
        payload = {
            "novel": int(novel_id_numeric), # يجب أن يكون رقم الرواية (ID) وليس الاسم أو الـ Slug
            "number": float(chapter_num),
            "title": title,
            "content": html_content,
            "status": 1, # 1 = منشور (Published)
            "published_at": None # يعني "الآن"
        }

        try:
            res = requests.post(url, json=payload, headers=self.headers, cookies=self.cookies_dict)
            
            if res.status_code in [200, 201]:
                return {"success": True, "data": res.json()}
            else:
                return {"success": False, "error": f"HTTP {res.status_code}: {res.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_novel(self, title_ar, title_en, description, cover_url, genres, is_translated=True):
        """إنشاء رواية جديدة في النادي"""
        url = f"{self.base_url}/novels/"
        
        # نوع الرواية: 1 = مترجمة، 2 = مؤلفة (بناء على ملف JS)
        novel_type = 1 if is_translated else 2
        
        # التأكد من أن التصنيفات مصفوفة أرقام
        genre_ids = [int(g) for g in genres] if isinstance(genres, list) else []

        payload = {
            "arabic": title_ar,
            "english": title_en,
            "about": description,
            "poster_url": cover_url,
            "genre": genre_ids, # مصفوفة أرقام [2, 5]
            "type": novel_type,
            "complete": False
        }

        try:
            res = requests.post(url, json=payload, headers=self.headers, cookies=self.cookies_dict)
            if res.status_code in [200, 201]:
                data = res.json()
                return {
                    "success": True, 
                    "id": data.get('id'), # الرقم
                    "slug": data.get('slug'), 
                    "title": data.get('arabic')
                }
            else:
                return {"success": False, "error": f"HTTP {res.status_code}: {res.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
