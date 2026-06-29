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
    """SerpAPI ile SON 24 SAATTEKİ rüyaları ara"""
    from datetime import datetime, timedelta
    
    # Dünün tarihini hesapla (SerpAPI tbs parametresi için)
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%m/%d/%Y')
    today = datetime.now().strftime('%m/%d/%Y')
    
    # Son 24 saat filtre parametresi
    time_filter = f'cdr:1,cd_min:{yesterday},cd_max:{today}'
    
    queries = [
        '"I had a dream last night"',
        '"weird dream I had today"',
        '"nightmare I had last night"',
        '"dream journal" today',
        '"I dreamed about" last night',
        '"had a dream about" today',
        '"strange dream" last night',
        '"lucid dream" experience today',
        '"I woke up from a dream"',
        '"recurring dream" last night'
    ]
    
    all_results = []
    seen_links = set()  # Duplicate engelleme
    
    for query in queries:
        try:
            # SerpAPI'de tarih filtresi
            url = f'https://serpapi.com/search.json?q={requests.utils.quote(query)}&api_key={SERPAPI_KEY}&num=10&tbs={requests.utils.quote(time_filter)}'
            response = requests.get(url, timeout=30)
            data = response.json()
            
            if 'organic_results' in data:
                new_count = 0
                for result in data['organic_results']:
                    link = result.get('link', '')
                    if link not in seen_links:
                        seen_links.add(link)
                        all_results.append(result)
                        new_count += 1
                print(f"✅ {new_count} yeni sonuç ({len(data['organic_results'])} toplam): {query}")
            else:
                print(f"⚠️ Sonuç yok: {query}")
        except Exception as e:
            print(f"❌ Hata ({query}): {e}")
    
    print(f"🔗 Toplam {len(all_results)} benzersiz sonuç (duplikatlar çıkarıldı)")
    return all_results
    
def extract_json_from_text(text):
    """AI yanıtından saf JSON'u ayıkla - SON DÜZENLEME"""
    import re
    import json
    
    # 1. ```json ... ``` bloklarını bul
    match = re.search(r'```json\s*(\[.*?\])\s*```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except:
            pass
    
    # 2. [ ile başlayıp ] ile biten kısmı bul
    start = text.find('[')
    end = text.rfind(']')
    
    if start != -1 and end != -1 and start < end:
        json_str = text[start:end+1]
        try:
            return json.loads(json_str)
        except:
            # Eğer hala hata veriyorsa, ] karakterinden sonra gelenleri temizle
            # ve en son ]'e kadar olan kısmı al
            clean_str = json_str.split('},')[0] + '}]'  # Son elemanı kapat
            try:
                return json.loads(clean_str)
            except:
                pass
    
    print(f"❌ JSON ayıklanamadı, içerik: {text[:500]}")
    return None
def analyze_with_groq(results):
    """Groq ile rüyaları analiz et - JSON AYIKLAMA EKLENDİ"""
    if not results:
        return []
        
    results_text = '\n'.join([
        f"[{i+1}] {r.get('title', '')}\n{r.get('snippet', '')}\n{r.get('link', '')}"
        for i, r in enumerate(results[:10])
    ])
    
    prompt = f"""Sen uzman bir Jungian psikolog ve rüya analizcisisin. Aşağıdaki sonuçlardan GERÇEK rüyaları ayıkla ve DERİNLEMESINE Jungian analizi yap.

ÖNEMLİ: Sadece saf JSON array döndür. Başına veya sonuna HİÇBİR açıklama yazma.

SONUÇLAR:
{results_text}

HER RÜYA İÇİN ŞU ALANLARI DOLDUR:

1. ruya_metni: Temizlenmiş rüya metni (en az 2 kelime)
2. dream_date: Rüyanın görüldüğü tarih (YYYY-MM-DD, metinden çıkar)
3. dil: Dil kodu (en/tr/ru/ar/es/hi/zh/de)
4. arketipler: Jungian arketipler array'i (örn: ["Shadow", "Anima", "Wise Old Man", "Great Mother", "Hero", "Trickster", "Self", "Snake", "Water", "Forest", "Door", "Tower"])
5. duygu: Ana duygu (Fear/Anxiety/Awe/Joy/Confusion/Peace/Sadness/Anger/Disgust/Surprise)
6. motiv: Rüyanın altında yatan psikolojik motivasyon (1 cümle,örn: "Bilinçdışındaki bastırılmış korkuların yüzeye çıkması")
7. jungian_surec: Jungian süreç etiketleri array'i (örn: ["Shadow Integration", "Individuation", "Anima Projection", "Collective Unconscious Activation", "Persona Dissolution", "Self Realization", "Transformation", "Rebirth"])
8. ozet: 2-3 cümlelik DERİN Jungian analiz (arketipler, motiv, süreç dahil)
9. gorsel_prompt: İngilizce AI görsel promptu (surreal, Jungian archetype, cinematic lighting, 8k, dreamlike atmosphere, 60-80 kelime)
10. kaynak_url: Orijinal link
11. konum: Tahmini konum (yoksa "Unknown")

JUNGIAN ARKETİPLER LİSTESİ:
- Shadow (Gölge): Bastırılmış karanlık taraf
- Anima/Animus: İçsel karşı cins
- Wise Old Man/Wise Woman: Bilge rehber
- Great Mother: Ana arketip
- Hero: Kahraman yolculuğu
- Trickster: Hilebaz/dönüştürücü
- Self: Bütünleşmiş benlik
- Persona: Sosyal maske
- Child: İç çocuk/yenilenme

JUNGIAN SÜREÇLER LİSTESİ:
- Shadow Integration: Gölge ile yüzleşme ve bütünleşme
- Individuation: Bireyleşme süreci
- Anima/Animus Integration: İç karşı cins ile bütünleşme
- Collective Unconscious Activation: Kolektif bilinçdışı aktivasyonu
- Persona Dissolution: Sosyal maskenin çözülmesi
- Self Realization: Benlik realization'ı
- Transformation: Dönüşüm
- Rebirth: Yeniden doğuş
- Initiation: İnisiyasyon/geçiş ritüeli
- Nigredo/Albedo/Rubedo: Simyasal dönüşüm aşamaları

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
    """Rüyaları Supabase'e kaydet - GÜVENLİ ALANLAR"""
    import random
    
    # Hayalet hesap ID'leri
    ghost_accounts = [
        '22222222-2222-2222-2222-222222222222',
        '33333333-3333-3333-3333-333333333333',
        '44444444-4444-4444-4444-444444444444',
        '55555555-5555-5555-5555-555555555555',
        '66666666-6666-6666-6666-666666666666',
        '77777777-7777-7777-7777-777777777777',
        '88888888-8888-8888-8888-888888888888',
        '99999999-9999-9999-9999-999999999999',
    ]
    
    saved = 0
    for dream in dreams:
        try:
            ghost_user_id = random.choice(ghost_accounts)
            image_url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(dream['gorsel_prompt'])}?width=768&height=768&nologo=true"
            
            # Sadece Groq'un verdiği alanları ekle
            supabase.table('dreams').insert({
                'user_id': ghost_user_id,
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
                # ai_motiv ve ai_jungian_process: Daha sonra manuel olarak eklenecek
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
