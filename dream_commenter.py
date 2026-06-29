import requests
import json
import os
import random
from datetime import datetime
from supabase import create_client

# API anahtarları
GROQ_KEY = os.environ.get('GROQ_KEY')
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

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

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_recent_dreams():
    """Son 10 rüyayı çek"""
    response = supabase.table('dreams').select('*').order('created_at', desc=True).limit(10).execute()
    return response.data

def generate_jungian_comment(dream):
    """Groq ile Jungian yorum üret"""
    prompt = f"""Sen Jungian psikoloji uzmanısın. Aşağıdaki rüya için kısa bir Jungian yorum yaz (2-3 cümle).

RÜYA: {dream['content']}
ARKETİPLER: {', '.join(dream['ai_archetypes'])}
DUYGU: {dream['ai_sentiment']}

YORUM:"""
    
    response = requests.post(
        'https://api.groq.com/openai/v1/chat/completions',
        headers={
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + GROQ_KEY
        },
        json={
            'model': 'llama-3.1-8b-instant',
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': 0.7,
            'max_tokens': 200
        },
        timeout=30
    )
    
    data = response.json()
    return data['choices'][0]['message']['content']

def add_comment(dream_id, user_id, comment):
    """Yorum ekle"""
    supabase.table('comments').insert({
        'dream_id': dream_id,
        'user_id': user_id,
        'content': comment,
        'created_at': datetime.now().isoformat()
    }).execute()

def main():
    print(f"\n{'='*60}")
    print(f"[{datetime.now()}] 💬 RÜYA YORUMCU BAŞLATILIYOR")
    print(f"{'='*60}\n")
    
    dreams = get_recent_dreams()
    print(f"✅ {len(dreams)} rüya bulundu\n")
    
    commented = 0
    for dream in dreams:
        try:
            # Rastgele hayalet hesap seç
            commenter_id = random.choice(ghost_accounts)
            
            # Jungian yorum üret
            comment = generate_jungian_comment(dream)
            
            # Yorum ekle
            add_comment(dream['id'], commenter_id, comment)
            
            commented += 1
            print(f"✅ Yorum eklendi: {comment[:50]}...")
        except Exception as e:
            print(f"❌ Yorum hatası: {e}")
    
    print(f"\n✅ Toplam {commented} yorum eklendi")
    print(f"{'='*60}\n")

if __name__ == '__main__':
    main()
