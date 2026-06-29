import requests
import json
import os
from datetime import datetime
from supabase import create_client

# ============================================
# 🔑 API ANAHTARLARI (Environment variables'dan okur)
# ============================================
SERPAPI_KEY = os.environ.get('SERPAPI_KEY')
GROQ_KEY = os.environ.get('GROQ_KEY')
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

# Kontrol
if not all([SERPAPI_KEY, GROQ_KEY, SUPABASE_URL, SUPABASE_KEY]):
    print("❌ Eksik API anahtarı! Secrets'ları kontrol et.")
    exit(1)

# Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def search_dreams():
    """SerpAPI ile rüya ara"""
    queries = [
        'site:reddit.com/r/dreams "I had a dream"',
        'site:tumblr.com "dream journal"',
        'site:medium.com "dream experience"',
    ]
    
    all_results = []
    for query in queries:
        try:
            url = f'https://serpapi.com/search.json?q={requests.utils.quote(query)}&api_key={SERPAPI_KEY}&num=10'
            response = requests.get(url, timeout=30)
            data = response.json()
            
            if 'organic_results' in data:
                all_results.extend(data['organic_results'])
                print(f"✅ {len(data['organic_results'])} sonuç: {query}")
        except Exception as e:
            print(f"⚠️ Hata ({query}): {e}")
    
    return all_results

def analyze_with_groq(results):
    """Groq ile rüyaları analiz et"""
    if not results:
        return []
    
    results_text = '\n'.join([
        f"[{i+1}] {r.get('title', '')}\n{r.get('snippet', '')}\n{r.get('link', '')}"
        for i, r in enumerate(results[:20])  # İlk 20 sonuç
    ])
    
    prompt = f"""Sen uzman bir rüya analizcisisin. Aşağıdaki sonuçlardan GERÇEK rüyaları ayıkla ve analiz et.

SONUÇLAR:
{results_text}

JSON FORMATI:
[
  {{
    "ruya_metni": "Temizlenmiş rüya metni (en az 50 kelime)",
    "dream_date": "YYYY-MM-DD (bugünün tarihi)",
    "dil": "en/tr/ru/ar/es/hi/zh/de",
    "arketipler": ["Shadow", "Snake", "Water"],
    "duygu": "Fear/Anxiety/Awe/Joy/Confusion/Peace",
    "ozet": "1-2 cümlelik Jungian analiz",
    "gorsel_prompt": "İngilizce AI görsel promptu (surreal, Jungian, cinematic, 8k)",
    "kaynak_url": "Orijinal link",
    "konum": "Tahmini konum veya Unknown"
  }}
]

KURALLAR:
1. Sadece GERÇEK rüyaları al (reklam, makale değil)
2. Her rüya en az 50 kelime içermeli
3. Sadece JSON array döndür
4. Rüya yoksa [] döndür"""
    
    try:
        response = requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {GROQ_KEY}'
            },
            json={
                'model': 'qwen-2.5-72b',
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0.3,
                'max_tokens': 4000,
                'response_format': {'type': 'json_object'}
            },
            timeout=60
        )
        
        data = response.json()
        result = json.loads(data['choices'][0]['message']['content'])
        return result if isinstance(result, list) else result.get('dreams', [])
    except Exception as e:
        print(f"❌ Groq hatası: {e}")
        return []

def save_to_supabase(dreams):
    """Rüyaları Supabase'e kaydet"""
    saved = 0
    for dream in dreams:
        try:
            image_url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(dream['gorsel_prompt'])}?width=768&height=768&nologo=true"
            
            supabase.table('dreams').insert({
                'content': dream['ruya_metni'],
                'dream_date': dream['dream_date'],
                'original_language': dream['dil'],
                'ai_archetypes': dream['arketipler'],
                'ai_sentiment': dream['duygu'],
                'ai_summary': dream['ozet'],
                'ai_image_prompt': dream['gorsel_prompt'],
                'ai_image_url': image_url,
                'is_bot_generated': True,
                'location_name': dream.get('konum', 'Unknown')
            }).execute()
            saved += 1
            print(f"✅ Kaydedildi: {dream['ozet'][:50]}...")
        except Exception as e:
            print(f"❌ Kaydetme hatası: {e}")
    
    return saved

def main():
    print(f"\n{'='*60}")
    print(f"[{datetime.now()}] 🌌 DREAMAP RÜYA AVI BAŞLATILIYOR")
    print(f"{'='*60}\n")
    
    # 1. Web'i tara
    print("🔍 SerpAPI ile web taranıyor...")
    results = search_dreams()
    print(f"✅ Toplam {len(results)} sonuç bulundu\n")
    
    if not results:
        print("⚠️ Hiç sonuç bulunamadı, çıkılıyor.")
        return
    
    # 2. Groq ile analiz et
    print("🧠 Groq ile rüyalar analiz ediliyor...")
    dreams = analyze_with_groq(results)
    print(f"✅ {len(dreams)} rüya analiz edildi\n")
    
    if not dreams:
        print("⚠️ Hiç rüya bulunamadı, çıkılıyor.")
        return
    
    # 3. Supabase'e kaydet
    print("💾 Rüyalar Supabase'e kaydediliyor...")
    saved = save_to_supabase(dreams)
    print(f"✅ {saved} rüya başarıyla kaydedildi\n")
    
    print(f"{'='*60}")
    print(f"[{datetime.now()}] 🎉 RÜYA AVI TAMAMLANDI!")
    print(f"{'='*60}\n")

if __name__ == '__main__':
    main()
