import aiohttp
import asyncio
from bs4 import BeautifulSoup
import os
import re
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# CONFIG — set these in your .env file
# NPOINT_ENDPOINT_ID  →  the ID from your npoint URL
#                        e.g. for https://api.npoint.io/abc123  →  abc123
# NPOINT_SECRET_TOKEN →  the secret token npoint gives you to
#                        authenticate POST requests (Optional)
# ============================================================


class AI_Tool_Agent:
    def __init__(self, start_url, output_file="ai_tools.json", interval_seconds=3600):
        self.current_url      = start_url
        self.output_file      = output_file
        self.interval         = interval_seconds
        self.npoint_id        = os.getenv("NPOINT_ENDPOINT_ID")
        self.npoint_token     = os.getenv("NPOINT_SECRET_TOKEN") # [FIXED] Uncommented
        self.npoint_api_url   = f"https://api.npoint.io/{self.npoint_id}" if self.npoint_id else None
        self._executor        = ThreadPoolExecutor()
        self.headers          = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        # [FIXED] Safely check variables without causing an AttributeError
        if not self.npoint_id:
            print("[Scraper] WARNING: NPOINT_ENDPOINT_ID missing from .env. Changes will be saved locally but NOT synced to npoint.")

        # Initialize local JSON file if it doesn't exist
        if not os.path.exists(self.output_file):
            with open(self.output_file, 'w') as f:
                json.dump([], f)
            print(f"[Scraper] Created output file: {self.output_file}")

    # ------------------------------------------------------------------
    # Slug helper
    # ------------------------------------------------------------------

    def create_slug(self, text):
        if not isinstance(text, str):
            return "unknown-tool"
        text = text.lower()
        text = re.sub(r'[^a-z0-9\s-]', '', text)
        text = re.sub(r'\s+', '-', text).strip('-')
        return text

    # ------------------------------------------------------------------
    # Page fetching
    # ------------------------------------------------------------------

    async def fetch_page(self, session, url):
        try:
            print(f"[Scraper] Navigating to: {url}")
            async with session.get(url) as response:
                response.raise_for_status()
                return BeautifulSoup(await response.text(), 'html.parser')
        except Exception as e:
            print(f"[Scraper] Error fetching page: {e}")
            return None

    def extract_category(self, post_item):
        for selector in ['.category', '.cat-links', 'span.term-badge', '.post-category']:
            cat_elem = post_item.select_one(selector)
            if cat_elem:
                return cat_elem.get_text(strip=True)
        return "Unknown"

    # ------------------------------------------------------------------
    # Local JSON helpers
    # ------------------------------------------------------------------

    def get_existing_slugs(self):
        try:
            with open(self.output_file, 'r') as f:
                data = json.load(f)
            return {entry.get('Slug') for entry in data}
        except Exception:
            return set()

    def save_locally(self, data):
        """Write the full data list to the local JSON file."""
        with open(self.output_file, 'w') as f:
            # Used indent=4 to keep the local JSON pretty-printed
            json.dump(data, f, indent=4)

    def append_to_local(self, entry):
        """Append a single merged entry to the local JSON file."""
        try:
            with open(self.output_file, 'r') as f:
                data = json.load(f)
        except Exception:
            data = []

        data.append(entry)
        self.save_locally(data)
        print(f"[Scraper] Saved locally: {entry['Title']} (Slug: {entry['Slug']})")
        return data  # return full list so we can push it to npoint immediately

    # ------------------------------------------------------------------
    # npoint sync — push the full updated list via POST
    # ------------------------------------------------------------------

    async def push_to_npoint(self, session, data):
        """
        Pushes the complete JSON list to npoint via a POST request.
        Auth header uses the secret token from .env (if provided).
        """
        if not self.npoint_api_url:
            return 

        # 1. Match your manual script's successful headers
        headers = {
            "Content-Type": "application/json"
        }
        
        if self.npoint_token:
            headers["x-access-token"] = self.npoint_token

        try:
            print(f"[Scraper] Pushing {len(data)} record(s) to npoint...")
            # 2. Use PUT to ensure the entire array replaces the old bin content
            async with session.post(self.npoint_api_url, json=data, headers=headers) as response:
                if response.status == 200:
                    print("[Scraper] npoint sync successful.")
                else:
                    text = await response.text()
                    print(f"[Scraper] npoint sync failed ({response.status}): {text}")
        except Exception as e:
            print(f"[Scraper] npoint sync error: {e}")
    # ------------------------------------------------------------------
    # Main async loop
    # ------------------------------------------------------------------

    async def run(self, generator=None, extra_urls = None):
        """
        For each scraped tool:
          1. Build raw scraped_data dict.
          2. Offload generator.generate_and_parse() to a thread executor.
          3. Merge both dicts into one record.
          4. Append to local JSON file.
          5. Push the full updated list to npoint immediately.
        """

        url_queue = [self.current_url] + (extra_urls or [])
        print("--- Scraping Agent Started ---")

        loop = asyncio.get_event_loop()

        async with aiohttp.ClientSession(headers=self.headers) as session:
            for start_url in url_queue:
                self.current_url = start_url
                print(f"\n[Scraper] === Starting URL: {self.current_url} ===")
                while self.current_url:
                    soup = await self.fetch_page(session, self.current_url)
                    if not soup:
                        break

                    post_items = soup.find_all('div', class_='post-item')
                    if not post_items:
                        print("[Scraper] No items found on this page. Ending.")
                        break

                    print(f"[Scraper] Found {len(post_items)} tools. Processing...")
                    existing_slugs = self.get_existing_slugs()

                    for item in post_items:
                        data_element = item.find('div', class_='share-dialog')
                        if not data_element:
                            continue

                        title       = data_element.get('data-title')
                        description = data_element.get('data-description')
                        category    = self.extract_category(item)

                        # Extract direct tool link from the visit button
                        visit_btn = item.find('a', class_='visit-site-button4')
                        link = visit_btn['href'] if visit_btn and visit_btn.get('href') else "Unknown"

                        slug = self.create_slug(title)

                        if slug in existing_slugs:
                            print(f"[Scraper] Skipping duplicate: {title}")
                            continue

                        # Extract logo
                        logo_src = "Unknown"
                        logo_div = item.find('div', class_='favicon-cat-brand')
                        if logo_div:
                            img_tag = logo_div.find('img')
                            if img_tag and 'src' in img_tag.attrs:
                                logo_src = img_tag['src']

                        scraped_data = {
                            'Title':       title,
                            'Slug':        slug,
                            'Category':    category,
                            'Description': description,
                            'Link':        link,
                            'Logo':        logo_src,
                            'Scraped_At':  datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }

                        # Offload blocking generator call to thread executor
                        if generator:
                            print(f"[Scraper] Handing off to Generator: {title}")
                            generated_data = await loop.run_in_executor(
                                self._executor,
                                generator.generate_and_parse,
                                title, description, slug
                            )
                            merged_entry = {**scraped_data, **generated_data}
                        else:
                            merged_entry = scraped_data

                        # Save locally AND push to npoint in one step
                        updated_data = self.append_to_local(merged_entry)
                        await self.push_to_npoint(session, updated_data)

                        existing_slugs.add(slug)

                        print(f"[Scraper] Waiting {self.interval} seconds before next extraction...")
                        await asyncio.sleep(self.interval)

                    next_page_link = soup.find('a', class_='next page-numbers')
                    if next_page_link and 'href' in next_page_link.attrs:
                        self.current_url = next_page_link['href']
                        await asyncio.sleep(2)
                    else:
                        self.current_url = None

            self._executor.shutdown(wait=False)
            print("--- Scraping Agent Finished ---")


if __name__ == "__main__":
    from slug_generator_agent_v03 import ContentGenerator
    from telegram_poster_agent import TelegramAutoPoster

    START_URL   = "https://www.aixploria.com/en/free-ai/"
    OUTPUT_FILE = "ai_tools.json"

    generator = ContentGenerator(output_json=OUTPUT_FILE)
    scraper   = AI_Tool_Agent(start_url=START_URL, output_file=OUTPUT_FILE, interval_seconds=50)
    poster    = TelegramAutoPoster(json_file=OUTPUT_FILE)

    async def main():
        await asyncio.gather(
            scraper.run(generator=generator, extra_urls=["https://www.aixploria.com/en/ai-freemium/"]),
            poster.monitor_and_post_async(),
        )

    asyncio.run(main())