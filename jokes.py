import os
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

BASE_URL = "https://www.laughfactory.com/jokes"
OUTPUT_DIR = "jokes"

def get_categories():
    print("Fetching joke categories...")
    try:
        res = requests.get(BASE_URL)
        res.raise_for_status()
    except requests.RequestException as e:
        print(f"Failed to fetch categories: {e}")
        return []

    soup = BeautifulSoup(res.text, "html.parser")
    nav_block = soup.select_one("div.left-navigation-block ul")
    categories = []
    if nav_block:
        for li in nav_block.find_all("li"):
            a = li.find("a")
            if a and a["href"].startswith("https://www.laughfactory.com/jokes/"):
                url = a["href"]
                name = a.select_one("span")
                cat_name = name.text.strip().replace(" ", "_").lower() if name else "unknown"
                print(f"  Found category: {cat_name} ({url})")
                categories.append({
                    "name": cat_name,
                    "url": url
                })
    else:
        print("  No navigation block found.")
    return categories

def extract_category_slug(category_url):
    # e.g. https://www.laughfactory.com/jokes/knock-knock -> knock-knock
    path = urlparse(category_url).path
    parts = path.strip("/").split("/")
    if len(parts) >= 2:
        return parts[1]
    return ""

def scrape_category(category_url, max_loads=10):
    print(f"  Scraping jokes from: {category_url}")
    jokes = []
    session = requests.Session()
    category_slug = extract_category_slug(category_url)
    page = 1

    # Initial request to get first batch of jokes
    try:
        res = session.get(category_url)
        res.raise_for_status()
    except requests.RequestException as e:
        print(f"    Failed to fetch initial jokes: {e}")
        return jokes

    soup = BeautifulSoup(res.text, "html.parser")
    joke_blocks = soup.select("div.jokes-main-pane-block")
    found = 0
    for block in joke_blocks:
        joke_text = block.select_one("div.joke-text-holder p")
        joke = joke_text.text.strip() if joke_text else ""
        # Get username
        username_elem = block.select_one("div.person-avatar-info.small-avatar small")
        username = username_elem.text.strip() if username_elem else "unknown"
        if joke:
            print(f"Joke: {joke}\nUsername: {username}\n{'-'*40}")
            jokes.append({"joke": joke, "username": username})
            found += 1
    print(f"    Found {found} jokes on initial page.")

    # Now simulate pressing "Load More" button up to max_loads times
    for load_num in range(1, max_loads + 1):
        ajax_url = f"https://www.laughfactory.com/jokes/ajax/load_more?page={load_num+1}&category={category_slug}"
        print(f"    Loading more jokes, load {load_num}: {ajax_url}")

        try:
            ajax_res = session.get(ajax_url)
            ajax_res.raise_for_status()
        except requests.RequestException as e:
            print(f"    Failed to load more jokes on load {load_num}: {e}")
            break

        ajax_soup = BeautifulSoup(ajax_res.text, "html.parser")
        new_joke_blocks = ajax_soup.select("div.jokes-main-pane-block")
        if not new_joke_blocks:
            print("    No more jokes returned by load more, stopping.")
            break

        found = 0
        for block in new_joke_blocks:
            joke_text = block.select_one("div.joke-text-holder p")
            joke = joke_text.text.strip() if joke_text else ""
            username_elem = block.select_one("div.person-avatar-info.small-avatar small")
            username = username_elem.text.strip() if username_elem else "unknown"
            if joke and not any(j["joke"] == joke for j in jokes):  # avoid duplicates
                print(f"Joke: {joke}\nUsername: {username}\n{'-'*40}")
                jokes.append({"joke": joke, "username": username})
                found += 1

        print(f"    Found {found} new jokes on load {load_num}.")
        if found == 0:
            print("    No new jokes found, stopping early.")
            break

        time.sleep(1)  # polite delay

    return jokes

def save_jokes(category_name, jokes):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    file_path = os.path.join(OUTPUT_DIR, f"{category_name}.txt")
    print(f"  Saving {len(jokes)} jokes to {file_path}...")
    with open(file_path, "w", encoding="utf-8") as f:
        for i, joke_obj in enumerate(jokes, start=1):
            f.write(f"[{category_name.upper()} #{i}]\nUser: {joke_obj['username']}\n{joke_obj['joke']}\n\n")
    print(f"  Done saving {category_name}.")
    
def main():
    categories = get_categories()
    print(f"Total categories found: {len(categories)}")
    for cat in categories:
        print(f"\nProcessing category: {cat['name']}")
        jokes = scrape_category(cat["url"], max_loads=10)  # you can change max_loads here
        print(f"  Total jokes found: {len(jokes)}")
        save_jokes(cat["name"], jokes)

if __name__ == "__main__":
    main()
