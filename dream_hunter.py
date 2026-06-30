import requests
import json
import os
import re
import random
import time
import hashlib
from datetime import datetime
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

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

GHOST_ACCOUNTS = [
    '22222222-2222-2222-2222-222222222222',
    '33333333-3333-3333-3333-333333333333',
    '44444444-4444-4444-4444-444444444444',
    '55555555-5555-5555-5555-555555555555',
]

def search_dreams():
    """SerpAPI ile rüya ara"""
    queries = [
        'I had a dream last night that',
        'last night I dreamed about',
        'weird dream I had',
        'nightmare I had last night',
        'dream journal entry',
        'strange dream last night',
        'recurring dream about',
        'lucid dream experience',
        'I woke up from a dream where',
        'in my dream I was'
    ]
    
    all_results = []
    seen_links = set()
    
    for query in queries:
        try:
            url = f'https://serpapi.com/search.json?q={requests.utils.quote(query)}&api_key={SERPAPI_KEY}&num=10'
            response = requests.get(url, timeout=60)
            data = response.json()
            
            if 'organic_results' in data:
                for result in data['organic_results']:
                    link = result.get('link', '')
                    if link and link not in seen_links:
                        seen_links.add(link)
                        all_results.append(result)
                print(f"✅ {len([r for r in data.get('organic_results', []) if r.get('link') not in seen_links])} yeni: {query[:40]}...")
            
            time.sleep(1)
        except Exception as e:
            print(f"❌ Hata ({query}): {e}")
    
    print(f"🔗 Toplam {len(all_results)} benzersiz sonuç")
    return all_results

def extract_dream_content(text):
    """Gerçek rüya içeriğini ayıkla"""
    # "I had a dream" ile başlayan cümleleri bul
    patterns = [
        r'(?:I had a dream|I dreamed|In my dream|Last night I dreamt)[^\n]{50,500}',
        r'(?:I was|There was|I saw|I felt)[^\n]{30,400}(?:dream|nightmare|sleeping)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            content = match.group(0).strip()
            if len(content) > 50:
                return content
    
    return text[:300] if len(text) > 50 else text

def analyze_chunk(chunk, chunk_num, total_chunks):
    """Bir parça sonucu analiz et - GELİŞMİŞ"""
    print(f"\n📦 Parça {chunk_num}/{total_chunks} işleniyor ({len(chunk)} sonuç)...")
    
    results_text = '\n\n---\n\n'.join([
        f"SOURCE {j+1}:\nTitle: {r.get('title', '')}\nSnippet: {r.get('snippet', '')}\nURL: {r.get('link', '')}"
        for j, r in enumerate(chunk)
    ])
    
    # Rastgelelik için seed
    random_seed = random.randint(1000, 9999)
    
    prompt = f"""You are an EXPERT Jungian dream analyst and psychologist. Analyze the following web search results for ACTUAL dream narratives.

CRITICAL INSTRUCTIONS:
1. Extract ONLY complete dream narratives (minimum 50 words)
2. IGNORE generic posts like "I had a dream" without details
3. Extract the FULL dream story with all details, emotions, and imagery
4. Provide DEEP, SPECIFIC Jungian analysis - NOT generic interpretations
5. Each dream must have UNIQUE analysis - NO repetitive patterns
6. Generate CREATIVE, DETAILED visual prompts (specific objects, colors, atmosphere)

SEARCH RESULTS:
{results_text}

For EACH valid dream, extract:

1. ruya_metni: The COMPLETE dream narrative (extract full story, minimum 80 words)
2. dream_date: Date in YYYY-MM-DD format (use today: {datetime.now().strftime('%Y-%m-%d')} if unknown)
3. dil: Language code (en/tr/ru/ar/es/hi/zh/de)
4. arketipler: SPECIFIC Jungian archetypes from this list:
   - Shadow, Anima, Animus, Wise Old Man, Great Mother
   - Hero, Trickster, Self, Persona, Child
   - Plus symbols: Snake, Water, Forest, Door, Tower, Bridge, Mountain, Ocean
5. duygu: Primary emotion (Fear/Anxiety/Awe/Joy/Confusion/Peace/Sadness/Anger/Disgust/Surprise)
6. motiv: SPECIFIC psychological motivation (2-3 sentences, NOT generic)
7. jungian_surec: SPECIFIC Jungian processes (Shadow Integration/Individuation/Anima Projection/Collective Unconscious Activation/Persona Dissolution/Self Realization/Transformation/Rebirth/Initiation)
8. ozet: DEEP Jungian analysis (4-5 sentences, mention SPECIFIC symbols, their archetypal meaning, and psychological significance - BE UNIQUE)
9. gorsel_prompt: DETAILED visual description in English (specific objects, colors, lighting, atmosphere, composition - 60-80 words, be CREATIVE and UNIQUE)
10. kaynak_url: Original URL
11. konum: Location if mentioned (city, country)
12. lat: Latitude (number, e.g., 41.0082)
13. lng: Longitude (number, e.g., 28.9784)

LOCATION MAPPING (use these coordinates):
- Turkey/Istanbul: 41.0082, 28.9784
- Turkey/Ankara: 39.9334, 32.8597
- USA/New York: 40.7128, -74.0060
- USA/Los Angeles: 34.0522, -118.2437
- UK/London: 51.5074, -0.1278
- Germany/Berlin: 52.5200, 13.4050
- France/Paris: 48.8566, 2.3522
- Japan/Tokyo: 35.6762, 139.6503
- China/Beijing: 39.9042, 116.4074
- India/Mumbai: 19.0760, 72.8777
- Australia/Sydney: -33.8688, 151.2093
- Brazil/Sao Paulo: -23.5505, -46.6333
- If location unknown: 0, 0

VISUAL PROMPT GUIDELINES:
- Be SPECIFIC: "surreal dark forest with twisted ancient trees, glowing blue mushrooms, misty atmosphere, moonlight filtering through canopy, mysterious shadowy figure in distance, cinematic lighting, hyperrealistic, 8k"
- NOT generic: "surreal dreamlike scene"
- Include: specific objects, colors, lighting type, atmosphere, composition
- Make each prompt UNIQUE and DETAILED

JUNGIAN ANALYSIS GUIDELINES:
- Be SPECIFIC to the dream content
- Mention exact symbols and their archetypal meanings
- Explain psychological significance
- Connect to collective unconscious patterns
- Provide unique insights - NO repetitive "Shadow integration" for every dream
- Example GOOD: "The recurring water symbol represents the unconscious mind's depths. The drowning sensation indicates overwhelming emotions from the Persona archetype conflicting with authentic Self. This suggests a Transformation process where old identity structures dissolve."
- Example BAD: "This dream shows Shadow integration and transformation." (too generic)

Return ONLY a valid JSON array. If no valid dreams found, return [].

JSON FORMAT:
[
  {{
    "ruya_metni": "Complete dream narrative here...",
    "dream_date": "2026-06-30",
    "dil": "en",
    "arketipler": ["Shadow", "Water", "Forest"],
    "duygu": "Fear",
    "motiv": "Specific psychological motivation explaining why this dream occurred...",
    "jungian_surec": ["Shadow Integration", "Transformation"],
    "ozet": "Deep 4-5 sentence Jungian analysis with specific symbols and meanings...",
    "gorsel_prompt": "Detailed visual description with specific objects, colors, lighting...",
    "kaynak_url": "https://...",
    "konum": "Istanbul, Turkey",
    "lat": 41.0082,
    "lng": 28.9784
  }}
]

Remember:
- MINIMUM 80 words for ruya_metni
- DEEP, SPECIFIC analysis (not generic)
- UNIQUE visual prompts (not repetitive)
- Only include dreams with substantial content
- Random seed for variety: {random_seed}"""

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
                    'messages': [
                        {'role': 'system', 'content': 'You are an expert Jungian dream analyst. Provide deep, specific, unique analyses.'},
                        {'role': 'user', 'content': prompt}
                    ],
                    'temperature': 0.7 + (random_seed % 10) / 100,  # 0.7-0.8 arası
                    'max_tokens': 4000
                },
                timeout=90
            )
            
            if response.status_code == 429:
                wait_time = 30 * (attempt + 1)
                print(f"⏳ Rate limit, {wait_time}s bekleniyor...")
                time.sleep(wait_time)
                continue
            
            if response.status_code != 200:
                print(f"❌ Groq API hatası: {response.status_code}")
                return []
            
            data = response.json()
            content = data['choices'][0]['message']['content']
            
            # JSON ayıkla
            result = extract_json_from_text(content)
            
            if result is None:
                print(f"⚠️ Parça {chunk_num}: JSON ayıklanamadı")
                return []
            
            dreams = result if isinstance(result, list) else result.get('dreams', [])
            
            # Kalite kontrolü - kısa/boş rüyaları filtrele
            valid_dreams = [d for d in dreams if len(d.get('ruya_metni', '')) >= 50]
            
            print(f"✅ Parça {chunk_num}: {len(valid_dreams)} kaliteli rüya bulundu (toplam {len(dreams)})")
            return valid_dreams
            
        except Exception as e:
            print(f"❌ Parça {chunk_num} hatası: {e}")
            return []
    
    return []

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
    
    return None

def save_to_supabase(dreams):
    """Rüyaları Supabase'e kaydet"""
    saved = 0
    for dream in dreams:
        try:
            if not dream.get('ruya_metni') or not dream.get('ozet'):
                print(f"⚠️ Eksik alan, atlandı")
                continue
            
            # İçerik çok kısa ise atla
            if len(dream['ruya_metni']) < 50:
                print(f"⚠️ Çok kısa rüya ({len(dream['ruya_metni'])} kelime), atlandı")
                continue
            
            ghost_user_id = random.choice(GHOST_ACCOUNTS)
            
            # Tarih doğrulama
            dream_date = dream.get('dream_date', datetime.now().strftime('%Y-%m-%d'))
            try:
                datetime.strptime(dream_date, '%Y-%m-%d')
            except:
                dream_date = datetime.now().strftime('%Y-%m-%d')
            
            # Görsel promptu temizle
            gorsel_prompt = dream.get('gorsel_prompt', 'surreal dreamlike scene')
            if len(gorsel_prompt) < 20:
                gorsel_prompt = 'surreal dreamlike scene with vivid colors and symbolic imagery, cinematic lighting, 8k quality'
            
            # Görsel URL oluştur
            image_url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(gorsel_prompt)}?width=768&height=768&nologo=true&seed={random.randint(1, 9999)}"
            
            # Koordinatlar
            lat = dream.get('lat')
            lng = dream.get('lng')
            
            supabase.table('dreams').insert({
                'user_id': ghost_user_id,
                'content': dream['ruya_metni'],
                'dream_date': dream_date,
                'original_language': dream.get('dil', 'en'),
                'ai_archetypes': dream.get('arketipler', []),
                'ai_sentiment': dream.get('duygu', 'Unknown'),
                'ai_motiv': dream.get('motiv', ''),
                'ai_jungian_process': dream.get('jungian_surec', []),
                'ai_summary': dream['ozet'],
                'ai_image_prompt': gorsel_prompt,
                'ai_image_url': image_url,
                'is_bot_generated': True,
                'location_name': dream.get('konum', 'Unknown'),
                'latitude': float(lat) if lat else None,
                'longitude': float(lng) if lng else None
            }).execute()
            saved += 1
            print(f"✅ Kaydedildi ({dream_date}): {dream['ozet'][:60]}...")
        except Exception as e:
            print(f"❌ Kaydetme hatası: {e}")
    
    return saved

def analyze_with_groq(results):
    """Groq ile rüyaları analiz et - PARÇALI"""
    if not results:
        return []
    
    all_dreams = []
    chunk_size = 10  # Daha az, daha kaliteli
    total_chunks = (len(results) + chunk_size - 1) // chunk_size
    
    for i in range(0, len(results), chunk_size):
        chunk = results[i:i+chunk_size]
        chunk_num = (i // chunk_size) + 1
        
        dreams = analyze_chunk(chunk, chunk_num, total_chunks)
        all_dreams.extend(dreams)
        
        if i + chunk_size < len(results):
            print("⏳ 30 saniye bekleniyor (rate limit)...")
            time.sleep(30)
    
    print(f"\n🎯 Toplam {len(all_dreams)} kaliteli rüya bulundu")
    return all_dreams

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
    
    print("🧠 Groq ile derin Jungian analiz yapılıyor...")
    dreams = analyze_with_groq(results)
    print(f"✅ {len(dreams)} rüya analiz edildi\n")
    
    if not dreams:
        print("⚠️ Hiç kaliteli rüya bulunamadı.")
        return
    
    print("💾 Rüyalar Supabase'e kaydediliyor...")
    saved = save_to_supabase(dreams)
    print(f"✅ {saved} rüya başarıyla kaydedildi\n")
    
    print(f"{'='*60}")
    print(f"[{datetime.now()}] 🎉 RÜYA AVI TAMAMLANDI!")
    print(f"{'='*60}\n")

if __name__ == '__main__':
    main()
