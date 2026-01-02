import requests
import time  # استيراد الوقت للانتظار
from django.conf import settings

class GeminiClient:
    @staticmethod
    def call_gemini(system_prompt, user_prompt):
        api_key = getattr(settings, "OPENROUTER_API_KEY", None)
        if not api_key:
            raise Exception("API Key is missing in settings!")
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "X-Title": "Software Documentation Agent",
            # إضافة الـ Referer ضرورية جداً في بعض الأحيان للموديلات المجانية
            "HTTP-Referer": "http://localhost:8000" 
        }
        payload = {
            "model": "google/gemini-2.0-flash-exp:free",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
        }

        max_retries = 3  # عدد محاولات إعادة الطلب
        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                
                # إذا كان الخطأ هو "كثير من الطلبات" 429
                if response.status_code == 429:
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 5  # انتظر 5 ثواني ثم 10...
                        time.sleep(wait_time)
                        continue  # أعد المحاولة
                
                response.raise_for_status()
                return response.json()['choices'][0]['message']['content']

            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:  # إذا كانت هذه آخر محاولة
                    raise Exception(f"خطأ في الاتصال بـ Gemini بعد عدة محاولات: {str(e)}")
                time.sleep(2)  # انتظر قليلاً قبل المحاولة التالية في حال وجود خطأ شبكة