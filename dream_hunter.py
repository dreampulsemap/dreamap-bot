import requests
import json
from datetime import datetime
from supabase import create_client

# ============================================
# 🔑 API ANAHTARLARI (BURAYA YAPIŞTIR)
# ============================================
SERPAPI_KEY = 'BURAYA_SERPAPI_KEY'
GROQ_KEY = 'BURAYA_GROQ_KEY'
SUPABASE_URL = 'BURAYA_SUPABASE_URL'
SUPABASE_KEY = 'BURAYA_SUPABASE_ANON_KEY'

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
        url = f'https://serpapi.com/search.json?q={requests.utils.quote(query)}&api_key={SERPAPI_KEY}&num=10'
        response = requests.get(url)
        data = response.json()
        
        if 'organic_results' in data:
            all_results.extend(data['organic_results'])
    
    return all_results

def analyze_with_groq(results):
    """Groq ile rüyaları analiz et"""
    results_text = '\n'.join([
        f"[{i+1}] {r.get('title', '')}\n{r.get('snippet', '')}\n{r.get('link', '')}"
        for i, r in enumerate(results)
    ])
    
    prompt = f"""Sen uzman bir rüya analizcisisin. Aşağıdaki sonuçlardan GERÇEK rüyaları ayıkla ve analiz et.

SONUÇLAR:
{results_text}

JSON FORMATI:
[
  {{
    "ruya_metni": "Temizlenmiş rüya metni",
    "dream_date": "YYYY-MM-DD",
    "dil": "en/tr/ru/ar/es/hi/zh/de",
    "arketipler": ["Shadow", "Snake"],
    "duygu": "Fear/Anxiety/Awe/Joy",
    "ozet": "1 cümlelik analiz",
    "gorsel_prompt": "İngilizce AI görsel promptu",
    "kaynak_url": "Link",
    "konum": "Tahmini konum"
  }}
]

Sadece JSON array döndür. Rüya yoksa [] döndür."""
    
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
        }
    )
    
    data = response.json()
    result = json.loads(data['choices'][0]['message']['content'])
    return result if isinstance(result, list) else result.get('dreams', [])

def save_to_supabase(dreams):
    """Rüyaları Supabase'e kaydet"""
    for dream in dreams:
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

def main():
    print(f"[{datetime.now()}] Rüya avı başlatılıyor...")
    
    # 1. Web'i tara
    results = search_dreams()
    print(f"✅ {len(results)} sonuç bulundu")
    
    # 2. Groq ile analiz et
    dreams = analyze_with_groq(results)
    print(f"✅ {len(dreams)} rüya analiz edildi")
    
    # 3. Supabase'e kaydet
    save_to_supabase(dreams)
    print(f"✅ {len(dreams)} rüya Supabase'e kaydedildi")
    
    print(f"[{datetime.now()}] Rüya avı tamamlandı!")

if __name__ == '__main__':
    main()
