import requests
import json
import os
import re
import random
import time
from datetime import datetime, date
from supabase import create_client

# ============================================
# 🔑 API ANAHTARLARI
# ============================================
SERPAPI_KEY = os.environ.get('SERPAPI_KEY')
GROQ_KEY = os.environ.get('GROQ_KEY')
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

if not all([SERPAPI_KEY, GROQ_KEY, SUPABASE_URL, SUPABASE_KEY]):
    print("❌ Eksik API anahtarı!")
    exit(1)

print(f"🔑 GROQ_KEY uzunluk: {len(GROQ_KEY)}")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

GHOST_ACCOUNTS = [
    '22222222-2222-2222-2222-222222222222',
    '33333333-3333-3333-3333-333333333333',
    '44444444-4444-4444-4444-444444444444',
    '55555555-5555-5555-5555-555555555555',
    '66666666-6666-6666-6666-666666666666',
    '77777777-7777-7777-7777-777777777777',
    '88888888-8888-8888-8888-888888888888',
    '99999999-9999-9999-9999-999999999999',
]

# ============================================
# 🛠️ YARDIMCI FONKSİYONLAR
# ============================================
def parse_valid_date(date_str):
    """Tarihi doğrula, geçersizse bugünün tarihini döndür"""
    if not date_str or date_str.lower() in ['unknown', 'null', 'none', '']:
        return datetime.now().strftime('%Y-%m-%d')
    
    # YYYY-MM-DD formatını dene
    patterns = [
        r'(\d{4}-\d{2}-\d{2})',
        r'(\d{4}/\d{2}/\d{2})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, str(date_str))
        if match:
            date_val = match.group(1).replace('/', '-')
            try:
                # Geçerli tarih mi kontrol et
                datetime.strptime(date_val, '%Y-%m-%d')
                return date_val
            except:
                continue
    
    # Hiçbiri çalışmazsa bugünün tarihi
    return datetime.now().strftime('%Y-%m-%d')

def extract_json_from_text(text):
    """AI yanıtından saf JSON'u ayıkla"""
    if not text:
        return None
    
    try:
        return json.loads(text)
    except:
        pass
    
    match = re.search(r'```(?:json)?\s*(\[[\s\S]*?\])\s*```', text)
    if match:
        try:
            return json.loads(match.group(1))
        except:
            pass
    
    start = text.find('[')
    end = text.rfind(']')
    if start != -1 and end != -1 and start < end:
        json_str = text[start:end+1]
        try:
            return json.loads(json_str)
        except:
            pass
    
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and start < end:
        json_str = text[start:end+1]
        try:
            obj = json.loads(json_str)
            return [obj]
        except:
            pass
    
    return None

# ============================================
# 🔎 SERPAPI ARAMA (TIMEOUT ARTIRILDI)
# ============================================
def search_dreams():
    """SerpAPI ile rüya ara"""
    queries = [
        'I had a dream last night',
        'weird dream I had today',
        'nightmare I had last night',
        'I dreamed about last night',
        'strange dream last night'
    ]
    
    all_results = []
    seen_links = set()
    
    for query in queries:
        try:
            url = f'https://serpapi.com/search.json?q={requests.utils.quote(query)}&api_key={SERPAPI_KEY}&num=10'
            response = requests.get(url, timeout=60)  # 60 saniye timeout
            data = response.json()
            
            if 'organic_results' in data:
                new_count = 0
                for result in data['organic_results']:
                    link = result.get('link', '')
                    if link and link not in seen_links:
                        seen_links.add(link)
                        all_results.append(result)
                        new_count += 1
                print(f"✅ {new_count} yeni sonuç: {query}")
            else:
                print(f"⚠️ Sonuç yok: {query}")
            
            # Her sorgu arası 1 saniye bekle
            time.sleep(1)
            
        except Exception as e:
            print(f"❌ Hata ({query}): {e}")
    
    print(f"🔗 Toplam {len(all_results)} benzersiz sonuç")
    return all_results

# ============================================
# 🧠 GROQ ANALİZ (RATE LİMİT DÜZENLENDİ)
# ============================================
def analyze_chunk(chunk, chunk_num, total_chunks):
    """Bir parça sonucu analiz et"""
    print(f"\n📦 Parça {chunk_num}/{total_chunks} işleniyor ({len(chunk)} sonuç)...")
    
    results_text = '\n'.join([
        f"[{j+1}] {r.get('title', '')}\n{r.get('snippet', '')}\n{r.get('link', '')}"
        for j, r in enumerate(chunk)
    ])
    
    prompt = f"""Sen uzman bir Jungian psikolog ve rüya analizcisisin. Aşağıdaki sonuçlardan GERÇEK rüyaları ayıkla.

ÖNEMLİ: 
- Sadece saf JSON array döndür
- dream_date MUTLAKA YYYY-MM-DD formatında olmalı (örn: 2026-06-30)
- Tarih bilinmiyorsa bugünün tarihini kullan: {datetime.now().strftime('%Y-%m-%d')}
- "Unknown" yazma!

SONUÇLAR:
{results_text}

JSON FORMATI:
[
  {{
    "ruya_metni": "Temizlenmiş rüya metni",
    "dream_date": "YYYY-MM-DD",
    "dil": "en/tr/ru/ar/es/hi/zh/de",
    "arketipler": ["Shadow", "Snake"],
    "duygu": "Fear/Anxiety/Awe/Joy/Confusion/Peace/Sadness/Anger/Surprise",
    "motiv": "1 cümlelik psikolojik motivasyon",
    "jungian_surec": ["Shadow Integration", "Transformation"],
    "ozet": "2-3 cümlelik Jungian analiz",
    "gorsel_prompt": "surreal Jungian cinematic 8k",
    "kaynak_url": "link",
    "konum": "City, Country"
  }}
]

Sadece JSON array döndür."""
    
    # Rate limit için tekrar deneme
    max_retries = 3
    for attempt in range(max_retries):
        try:
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
                    'max_tokens': 4000
                },
                timeout=60
            )
            
            if response.status_code == 429:
                wait_time = 30 * (attempt + 1)  # 30, 60, 90 saniye
                print(f"⏳ Rate limit, {wait_time} saniye bekleniyor (deneme {attempt+1}/{max_retries})...")
                time.sleep(wait_time)
                continue
            
            if response.status_code != 200:
                print(f"❌ Groq API hatası: {response.status_code}")
                return []
            
            data = response.json()
            content = data['choices'][0]['message']['content']
            
            result = extract_json_from_text(content)
            if result is None:
                print(f"⚠️ Parça {chunk_num}: JSON ayıklanamadı")
                return []
            
            dreams = result if isinstance(result, list) else result.get('dreams', [])
            print(f"✅ Parça {chunk_num}: {len(dreams)} rüya bulundu")
            return dreams
            
        except Exception as e:
            print(f"❌ Parça {chunk_num} hatası: {e}")
            return []
    
    return []

def analyze_with_groq(results):
    """Groq ile rüyaları analiz et - PARÇALI"""
    if not results:
        return []
    
    all_dreams = []
    chunk_size = 15  # Daha az parça
    total_chunks = (len(results) + chunk_size - 1) // chunk_size
    
    for i in range(0, len(results), chunk_size):
        chunk = results[i:i+chunk_size]
        chunk_num = (i // chunk_size) + 1
        
        dreams = analyze_chunk(chunk, chunk_num, total_chunks)
        all_dreams.extend(dreams)
        
        # Parçalar arası 30 saniye bekle (rate limit için)
        if i + chunk_size < len(results):
            print("⏳ 30 saniye bekleniyor (rate limit)...")
            time.sleep(30)
    
    print(f"\n🎯 Toplam {len(all_dreams)} rüya bulundu")
    return all_dreams

# ============================================
# 💾 SUPABASE'E KAYDET (TARİH DOĞRULAMA)
# ============================================
def save_to_supabase(dreams):
    """Rüyaları Supabase'e kaydet"""
    saved = 0
    for dream in dreams:
        try:
            if not dream.get('ruya_metni') or not dream.get('ozet'):
                print(f"⚠️ Eksik alan, atlandı")
                continue
            
            ghost_user_id = random.choice(GHOST_ACCOUNTS)
            
            # TARİH DOĞRULAMA - KRİTİK!
            dream_date = parse_valid_date(dream.get('dream_date'))
            
            # Görsel promptu temizle
            gorsel_prompt = dream.get('gorsel_prompt', 'surreal dream')
            if not gorsel_prompt or len(gorsel_prompt) < 10:
                gorsel_prompt = 'surreal dreamlike scene, Jungian archetype, cinematic lighting, 8k'
            if 'kelime' in gorsel_prompt.lower() or 'word' in gorsel_prompt.lower():
                gorsel_prompt = 'surreal dreamlike scene, Jungian archetype, cinematic lighting, 8k'
            
            image_url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(gorsel_prompt)}?width=768&height=768&nologo=true"
            
            supabase.table('dreams').insert({
                'user_id': ghost_user_id,
                'content': dream['ruya_metni'],
                'dream_date': dream_date,  # Artık geçerli tarih
                'original_language': dream.get('dil', 'en'),
                'ai_archetypes': dream.get('arketipler', []),
                'ai_sentiment': dream.get('duygu', 'Unknown'),
                'ai_summary': dream['ozet'],
                'ai_image_prompt': gorsel_prompt,
                'ai_image_url': image_url,
                'is_bot_generated': True,
                'location_name': dream.get('konum', 'Unknown')
            }).execute()
            saved += 1
            print(f"✅ Kaydedildi ({dream_date}): {dream['ozet'][:50]}...")
        except Exception as e:
            print(f"❌ Kaydetme hatası: {e}")
    
    return saved

# ============================================
# 🚀 ANA FONKSİYON
# ============================================
def main():
    print(f"\n{'='*60}")
    print(f"[{datetime.now()}] 🌌 DREAMAP RÜYA AVI BAŞLATILIYOR")
    print(f"{'='*60}\n")
    
    print("🔍 SerpAPI ile web taranıyor...")
    results = search_dreams()
    print(f"✅ Toplam {len(results)} sonuç bulundu\n")
    
    if not results:
        print("⚠️ Hiç sonuç bulunamadı.")
        return
    
    print("🧠 Groq ile rüyalar analiz ediliyor...")
    dreams = analyze_with_groq(results)
    print(f"✅ {len(dreams)} rüya analiz edildi\n")
    
    if not dreams:
        print("⚠️ Hiç rüya bulunamadı.")
        return
    
    print("💾 Rüyalar Supabase'e kaydediliyor...")
    saved = save_to_supabase(dreams)
    print(f"✅ {saved} rüya başarıyla kaydedildi\n")
    
    print(f"{'='*60}")
    print(f"[{datetime.now()}] 🎉 RÜYA AVI TAMAMLANDI!")
    print(f"{'='*60}\n")

if __name__ == '__main__':
    main()
