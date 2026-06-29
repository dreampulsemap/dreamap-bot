import requests
import json
import os
from datetime import datetime
from supabase import create_client

# API anahtarları
SERPAPI_KEY = os.environ.get('SERPAPI_KEY')
GROQ_KEY = os.environ.get('GROQ_KEY')
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

# Kontrol
if not all([SERPAPI_KEY, GROQ_KEY, SUPABASE_URL, SUPABASE_KEY]):
    print("❌ Eksik API anahtarı!")
    print(f"SERPAPI_KEY: {'✅' if SERPAPI_KEY else '❌'}")
    print(f"GROQ_KEY: {'✅' if GROQ_KEY else '❌'}")
    print(f"SUPABASE_URL: {'✅' if SUPABASE_URL else '❌'}")
    print(f"SUPABASE_KEY: {'✅' if SUPABASE_KEY else '❌'}")
    exit(1)

# Groq key'in başını ve sonunu göster (debug için)
print(f"🔑 GROQ_KEY başı: {GROQ_KEY[:10]}...")
print(f"🔑 GROQ_KEY sonu: ...{GROQ_KEY[-10:]}")
print(f"🔑 GROQ_KEY uzunluk: {len(GROQ_KEY)}")

# Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def search_dreams():
    """SerpAPI ile rüya ara"""
    queries = [
        'I had a weird dream last night',
        'strange dream I had',
        'nightmare I had recently',
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
def extract_json_from_text(text):
    """AI yanıtından saf JSON'u ayıkla"""
    import re
    
    # Önce direkt parse etmeyi dene
    try:
        return json.loads(text)
    except:
        pass
    
    # [ ile başlayıp ] ile biten kısmı bul
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except:
            pass
    
    # { ile başlayıp } ile biten kısmı bul
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except:
            pass
    
    return None

def analyze_with_groq(results):
    """Groq ile rüyaları analiz et - JSON AYIKLAMA EKLENDİ"""
    if not results:
        return []
    
    results_text = '\n'.join([
        f"[{i+1}] {r.get('title', '')}\n{r.get('snippet', '')}\n{r.get('link', '')}"
        for i, r in enumerate(results[:10])
    ])
    
    prompt = f"""Sen uzman bir rüya analizcisisin. Aşağıdaki sonuçlardan GERÇEK rüyaları ayıkla ve analiz et.

SONUÇLAR:
{results_text}

ÖNEMLİ: SADECE saf JSON array döndür. Başına veya sonuna HİÇBİR açıklama yazma. Sadece [ ile başla ve ] ile bitir.

JSON FORMATI:
[
  {{
    "ruya_metni": "Temizlenmiş rüya metni",
    "dream_date": "2025-01-16",
    "dil": "en",
    "arketipler": ["Shadow", "Snake"],
    "duygu": "Fear",
    "ozet": "1 cümlelik analiz",
    "gorsel_prompt": "surreal dark forest snake cinematic",
    "kaynak_url": "link",
    "konum": "Unknown"
  }}
]

Rüya yoksa sadece [] döndür."""
    
    try:
        print(f"📡 Groq API'ye istek gönderiliyor...")
        
        response = requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers={
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + GROQ_KEY
            },
            json={
                'model': 'llama-3.1-8b-instant',
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0.3,
                'max_tokens': 2000
            },
            timeout=60
        )
        
        print(f"📥 Groq API yanıt kodu: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ Groq API hatası: {response.status_code}")
            print(f"❌ Detay: {response.text[:500]}")
            return []
        
        data = response.json()
        content = data['choices'][0]['message']['content']
        
        print(f"📝 Groq içeriği (ilk 200 karakter): {content[:200]}")
        
        # YENİ: JSON'u ayıkla
        result = extract_json_from_text(content)
        
        if result is None:
            print(f"❌ JSON ayıklanamadı!")
            print(f"❌ Tam içerik: {content}")
            return []
        
        dreams = result if isinstance(result, list) else result.get('dreams', [])
        
        print(f"✅ Groq {len(dreams)} rüya döndürdü")
        return dreams
        
    except Exception as e:
        print(f"❌ Groq hatası: {e}")
        import traceback
        traceback.print_exc()
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
