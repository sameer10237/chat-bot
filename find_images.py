import urllib.request
import re
import os

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'}

urls_to_check = ['https://sdit.ac.in/', 'https://sdit.ac.in/about-sdit/', 'https://sdit.ac.in/gallery/']

all_imgs = set()
for page_url in urls_to_check:
    try:
        req = urllib.request.Request(page_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as r:
            html = r.read().decode('utf-8', errors='ignore')
        
        # Find all image URLs
        imgs = re.findall(r'(?:src|href)=["\']([^"\']+\.(?:jpg|jpeg|png|webp))["\']', html, re.IGNORECASE)
        for img in imgs:
            if img.startswith('http'):
                all_imgs.add(img)
            elif img.startswith('/'):
                all_imgs.add('https://sdit.ac.in' + img)
        print(f'Found {len(imgs)} images on {page_url}')
    except Exception as e:
        print(f'Failed {page_url}: {e}')

print("\n=== ALL SDIT IMAGES ===")
for img in sorted(all_imgs):
    print(img)
