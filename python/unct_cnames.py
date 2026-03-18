from pathlib import Path
from selenium import webdriver
from bs4 import BeautifulSoup
import time

# Step 1: Download all HTML files
driver = webdriver.Chrome()
driver.get('https://uninfo.org/all-countries')
time.sleep(5)
soup = BeautifulSoup(driver.page_source, 'html.parser')
country_links = [a['href'] for a in soup.find_all('a', href=True) if '/v2/location/' in a['href']]
print(f"Found {len(country_links)} countries\n")

Path('data/downloads').mkdir(parents=True, exist_ok=True)
for i, link in enumerate(country_links, 1):
    country_id = link.split('/')[-1]
    print(f"{i}/{len(country_links)}: Downloading {country_id}...")
    driver.get(f"https://uninfo.org{link}")
    time.sleep(2)
    Path(f'data/downloads/{country_id}.html').write_text(driver.page_source)

driver.quit()
print(f"\n✓ Downloaded {len(country_links)} HTML files\n")

# Step 2: Parse local HTML files
cnames = []
for html_file in sorted(Path('data/downloads').glob('*.html')):
    if html_file.name in ['all-countries.html', 'moldova.html']:
        continue
    soup = BeautifulSoup(html_file.read_text(), 'html.parser')
    unct_div = soup.find('div', string=lambda t: t and 'UNCT Website' in t)
    if unct_div:
        unct_link = unct_div.find_next('a', href=True)
        if unct_link:
            cname = unct_link['href'].replace('https://', '').replace('http://', '').replace('www.', '').rstrip('/')
            cnames.append(cname)
            print(f"{html_file.stem}: {cname}")

Path('public/data/cnames.txt').write_text('\n'.join(cnames))
print(f"\n✓ Saved {len(cnames)} websites to cnames.txt")



