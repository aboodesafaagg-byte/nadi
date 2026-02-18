
import requests
import json
import re

# 🔥 القيم المستخرجة من الصور (جلسة حقيقية)
REAL_SESSION_ID = "p2u5rg3a873jfq4s9wqr0hgpise6s545"
REAL_CSRF_TOKEN = "r5N1EuEWndcd8KDEppfqeXqix12BfTPGby1QhySMCH22lg7B08pl6lqBHRg8xNsui"
REAL_AUTH_TOKEN = "Token 302bd3c2f811704f0fddce79a14f56250f9cc652" 

class NadiClient:
    def __init__(self, cookies_str=None):
        self.base_url = "https://api.rewayat.club/api"
        
        # بناء الكوكيز الافتراضية القوية
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
                # النتائج قد تكون في 'results' أو مباشرة في المصفوفة
                results = data.get('results', data) if isinstance(data, dict) else data
                
                formatted = []
                for item in results:
                    formatted.append({
                        "id": item.get('id'), # رقمي (Integer) - هام جداً للنشر
                        "slug": item.get('slug'), 
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
        """
        تنسيق النص ليكون مطابقاً تماماً لما يفعله سكربت JS
        - دمج الأسطر المتتالية في فقرة واحدة.
        - فصل الفقرات عند وجود سطر فارغ.
        - دعم فواصل <center>.
        """
        if not text: return ""
        
        lines = text.split('\n')
        paragraphs = []
        current_paragraph = []

        for line in lines:
            trimmed = line.strip()
            
            # سطر فارغ -> نهاية الفقرة الحالية
            if not trimmed:
                if current_paragraph:
                    paragraphs.append(" ".join(current_paragraph))
                    current_paragraph = []
                continue
            
            # فواصل (____ أو ****) -> نهاية الفقرة + إضافة الفاصل
            if re.match(r'^_{3,}$', trimmed) or re.match(r'^\*{3,}$', trimmed):
                if current_paragraph:
                    paragraphs.append(" ".join(current_paragraph))
                    current_paragraph = []
                paragraphs.append(f"<center>{trimmed}</center>")
                continue
            
            # نص عادي -> أضفه للفقرة الحالية
            current_paragraph.append(trimmed)
        
        # إضافة الفقرة الأخيرة إن وجدت
        if current_paragraph:
            paragraphs.append(" ".join(current_paragraph))
            
        # تحويل القائمة إلى HTML
        html_parts = []
        for p in paragraphs:
            if p.startswith("<center>"):
                html_parts.append(p)
            else:
                html_parts.append(f'<p dir="auto">{p}</p>')
                
        return "".join(html_parts)

    def publish_chapter(self, novel_id_numeric, chapter_num, title, content):
        """نشر فصل جديد - يستخدم ID الرقمي"""
        url = f"{self.base_url}/chapters/"
        
        html_content = self.format_content(content)
        
        payload = {
            "novel": int(novel_id_numeric), # يجب أن يكون رقم الرواية (ID)
            "number": float(chapter_num),
            "title": title,
            "content": html_content,
            "status": 1, # 1 = منشور
            "published_at": None 
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
        
        # نوع الرواية: 1 = مترجمة، 2 = مؤلفة
        novel_type = 1 if is_translated else 2
        
        # التأكد من أن التصنيفات مصفوفة أرقام
        genre_ids = [int(g) for g in genres] if isinstance(genres, list) else []

        payload = {
            "arabic": title_ar,
            "english": title_en,
            "about": description,
            "poster_url": cover_url,
            "genre": genre_ids, # [2, 5]
            "type": novel_type,
            "complete": False # افتراضياً غير مكتملة
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
