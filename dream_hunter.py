import requests
import json
import os
import re
import random
import time
from datetime import datetime
from supabase import create_client

# ============================================
# 🔑 API ANAHTARLARI
# ============================================
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

print(f"🔑 GROQ_KEY başı: {GROQ_KEY[:10]}...")
print(f"🔑 GROQ_KEY sonu: ...{GROQ_KEY[-10:]}")
print(f"🔑 GROQ_KEY uzunluk: {len(GROQ_KEY)}")

# Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Hayalet hesaplar
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
# 🔍 JSON AYIKLAMA
# ============================================
def extract_json_from_text(text):
    """AI yanıtından saf JSON'u ayıkla"""
    if not text:
        return None
    
    # 1. Direkt parse
    try:
        return json.loads(text)
    except:
        pass
    
    # 2. ```json blokları
    match = re.search(r'```(?:json)?\s*(\[[\s\S]*?\])\s*```', text)
    if match:
        try:
            return json.loads(match.group(1))
        except:
            pass
    
    # 3. [ ile başlayıp ] ile biten
    start = text.find('[')
    end = text.rfind(']')
    if start != -1 and end != -1 and start < end:
        json_str = text[start:end+1]
        try:
            return json.loads(json_str)
        except:
            pass
    
    # 4. Tek obje { }
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
# 🔎 SERPAPI ARAMA
# ============================================
def search_dreams():
    """SerpAPI ile rüya ara"""
    queries = [
        'I had a dream last night',
        'weird dream I had today',
        'nightmare I had last night',
        'dream journal today',
        'I dreamed about last night',
        'had a dream about today',
        'strange dream last night',
        'lucid dream experience today',
        'I woke up from a dream',
        'recurring dream last night'
    ]
    
    all_results = []
    seen_links = set()
    
    for query in queries:
        try:
            url = f'https://serpapi.com/search.json?q={requests.utils.quote(query)}&api_key={SERPAPI_KEY}&num=10'
            response = requests.get(url, timeout=30)
            data = response.json()
            
            if 'organic_results' in data:
                new_count = 0
                for result in data['organic_results']:
                    link = result.get('link', '')
                    if link and link not in seen_links:
                        seen_links.add(link)
                        all_results.append(result)
                        new_count += 1
                print(f"✅ {new_count} yeni sonuç ({len(data['organic_results'])} toplam): {query}")
            else:
                print(f"⚠️ Sonuç yok: {query}")
        except Exception as e:
            print(f"❌ Hata ({query}): {e}")
    
    print(f"🔗 Toplam {len(all_results)} benzersiz sonuç")
    return all_results

# ============================================
# 🧠 GROQ ANALİZ (PARÇALI)
# ============================================
def analyze_chunk(chunk, chunk_num, total_chunks):
    """Bir parça sonucu analiz et"""
    print(f"\n📦 Parça {chunk_num}/{total_chunks} işleniyor ({len(chunk)} sonuç)...")
    
    results_text = '\n'.join([
        f"[{j+1}] {r.get('title', '')}\n{r.get('snippet', '')}\n{r.get('link', '')}"
        for j, r in enumerate(chunk)
    ])
    
    prompt = f"""Sen uzman bir Jungian psikolog ve rüya analizcisisin. Aşağıdaki sonuçlardan GERÇEK rüyaları ayıkla ve DERİNLEMESINE Jungian analizi yap.

ÖNEMLİ: Sadece saf JSON array döndür. Başına veya sonuna HİÇBİR açıklama yazma.

SONUÇLAR:
{results_text}

HER RÜYA İÇİN ŞU ALANLARI DOLDUR:

1. ruya_metni: Temizlenmiş rüya metni (en az 2 kelime)
2. dream_date: Rüyanın görüldüğü tarih (YYYY-MM-DD)
3. dil: Dil kodu (en/tr/ru/ar/es/hi/zh/de)
4. arketipler: Jungian arketipler array'i
5. duygu: Ana duygu (Fear/Anxiety/Awe/Joy/Confusion/Peace/Sadness/Anger/Disgust/Surprise)
6. motiv: Rüyanın altında yatan psikolojik motivasyon (1 cümle)
7. jungian_surec: Jungian süreç etiketleri array'i
8. ozet: 2-3 cümlelik DERİN Jungian analiz
9. gorsel_prompt: İngilizce AI görsel promptu (surreal, Jungian archetype, cinematic, 8k)
10. kaynak_url: Orijinal link
11. konum: Tahmini konum (yoksa "Unknown")

JSON FORMATI:
[
  {{
    "ruya_metni": "...",
    "dream_date": "YYYY-MM-DD",
    "dil": "en",
    "arketipler": ["Shadow", "Snake"],
    "duygu": "Fear",
    "motiv": "Bilinçdışındaki bastırılmış korkuların yüzeye çıkması",
    "jungian_surec": ["Shadow Integration", "Transformation"],
    "ozet": "Bu rüya, Shadow arketipinin Snake sembolü üzerinden yüzeye çıkışını temsil eder...",
    "gorsel_prompt": "surreal dark forest giant snake...",
    "kaynak_url": "...",
    "konum": "Unknown"
  }}
]

Sadece JSON array döndür. Rüya yoksa [] döndür."""
    
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
        
        if response.status_code != 200:
            print(f"❌ Groq API hatası: {response.status_code}")
            return []
        
        data = response.json()
        content = data['choices'][0]['message']['content']
        
        print(f"📝 Parça {chunk_num} yanıtı (ilk 200 karakter): {content[:200]}")
        
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

def analyze_with_groq(results):
    """Groq ile rüyaları analiz et - PARÇALI ANALİZ"""
    if not results:
        return []
    
    all_dreams = []
    chunk_size = 10
    total_chunks = (len(results) + chunk_size - 1) // chunk_size
    
    for i in range(0, len(results), chunk_size):
        chunk = results[i:i+chunk_size]
        chunk_num = (i // chunk_size) + 1
        
        dreams = analyze_chunk(chunk, chunk_num, total_chunks)
        all_dreams.extend(dreams)
        
        # Rate limit için bekle
        if i + chunk_size < len(results):
            print("⏳ 2 saniye bekleniyor...")
            time.sleep(2)
    
    print(f"\n🎯 Toplam {len(all_dreams)} rüya bulundu")
    return all_dreams

# ============================================
# 💾 SUPABASE'E KAYDET
# ============================================
def save_to_supabase(dreams):
    """Rüyaları Supabase'e kaydet"""
    saved = 0
    for dream in dreams:
        try:
            # Zorunlu alanları kontrol et
            if not dream.get('ruya_metni') or not dream.get('ozet'):
                print(f"⚠️ Eksik alan, atlandı")
                continue
            
            ghost_user_id = random.choice(GHOST_ACCOUNTS)
            
            # Görsel promptu temizle
            gorsel_prompt = dream.get('gorsel_prompt', 'surreal dream')
            if 'kelime' in gorsel_prompt.lower() or 'word' in gorsel_prompt.lower():
                gorsel_prompt = 'surreal dreamlike scene, Jungian archetype, cinematic lighting, 8k'
            
            image_url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(gorsel_prompt)}?width=768&height=768&nologo=true"
            
            supabase.table('dreams').insert({
                'user_id': ghost_user_id,
                'content': dream['ruya_metni'],
                'dream_date': dream.get('dream_date', datetime.now().strftime('%Y-%m-%d')),
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
            print(f"✅ Kaydedildi: {dream['ozet'][:50]}...")
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
