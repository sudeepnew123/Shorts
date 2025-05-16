import yt_dlp

# Your desired channel URL (Shorts only)
CHANNEL_URL = "https://youtube.com/@uljhansuljhan?si=AsEspvgsyuX1axu-"

def get_random_short():
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'skip_download': True,
        'force_generic_extractor': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(CHANNEL_URL, download=False)
        entries = info.get("entries", [])
        shorts = [f"https://youtube.com/shorts/{e['id']}" for e in entries if "/shorts/" in e['url']]
        return random.choice(shorts) if shorts else "No shorts found!"
