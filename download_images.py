import urllib.request
import os

os.makedirs('chatbot_app/static/images', exist_ok=True)

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://sdit.ac.in/'
}

# Key campus/college images found from the website
images = [
    ('https://sdit.ac.in/wp-content/themes/shridevi-child/images/sdit-about.jpg', 'sdit_about.jpg'),
    ('https://sdit.ac.in/wp-content/themes/shridevi-child/images/sdit-bannerr-2.jpg', 'sdit_banner2.jpg'),
    ('https://sdit.ac.in/wp-content/themes/shridevi-child/images/sdit-bannerr-3.jpg', 'sdit_banner3.jpg'),
    ('https://sdit.ac.in/wp-content/themes/shridevi-child/images/sdit-d-banner1.jpg', 'sdit_banner1.jpg'),
    ('https://sdit.ac.in/wp-content/themes/shridevi-child/images/sdit-logo.png', 'sdit_logo.png'),
    ('https://sdit.ac.in/wp-content/uploads/2025/02/sdit-banner4.jpg', 'sdit_banner4.jpg'),
    ('https://sdit.ac.in/wp-content/themes/shridevi-child/images/sdit-mobile-banner1.jpg', 'sdit_mobile_banner1.jpg'),
]

downloaded = []
for url, filename in images:
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            data = response.read()
            filepath = f'chatbot_app/static/images/{filename}'
            with open(filepath, 'wb') as f:
                f.write(data)
            size_kb = len(data) // 1024
            print(f'OK: {filename} ({size_kb} KB)')
            downloaded.append(filename)
    except Exception as e:
        print(f'FAIL: {filename} -> {e}')

print(f'\nDownloaded {len(downloaded)}/{len(images)} images')
print('Files:', downloaded)
