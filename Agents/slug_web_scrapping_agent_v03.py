# import aiohttp
# import asyncio
# from bs4 import BeautifulSoup
# import os
# import re
# import json
# from datetime import datetime

# class AI_Tool_Agent:
#     def __init__(self, start_url, output_file="ai_tools.json", interval_seconds=3600):
#         self.current_url = start_url
#         self.output_file = output_file
#         self.interval = interval_seconds
#         self.headers = {
#             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
#         }

#         # Initialize JSON file if it doesn't exist
#         if not os.path.exists(self.output_file):
#             with open(self.output_file, 'w') as f:
#                 json.dump([], f)
#             print(f"[Scraper] Created output file: {self.output_file}")

#     def create_slug(self, text):
#         """Generates a URL-friendly slug from the title."""
#         if not isinstance(text, str):
#             return "unknown-tool"
#         text = text.lower()
#         text = re.sub(r'[^a-z0-9\s-]', '', text)
#         text = re.sub(r'\s+', '-', text).strip('-')
#         return text

#     async def fetch_page(self, session, url):
#         """Fetches the HTML content of the page asynchronously."""
#         try:
#             print(f"[Scraper] Navigating to: {url}")
#             async with session.get(url) as response:
#                 response.raise_for_status()
#                 html_content = await response.text()
#                 return BeautifulSoup(html_content, 'html.parser')
#         except Exception as e:
#             print(f"[Scraper] Error fetching page: {e}")
#             return None

#     def extract_category(self, post_item):
#         """Attempts to find the category within the post-item."""
#         potential_selectors = ['.category', '.cat-links', 'span.term-badge', '.post-category']
#         for selector in potential_selectors:
#             cat_elem = post_item.select_one(selector)
#             if cat_elem:
#                 return cat_elem.get_text(strip=True)
#         return "Unknown"

#     def get_existing_slugs(self):
#         """Returns a set of slugs already saved in the JSON file."""
#         try:
#             with open(self.output_file, 'r') as f:
#                 data = json.load(f)
#             return {entry.get('Slug') for entry in data}
#         except Exception:
#             return set()

#     def append_to_json(self, entry):
#         """
#         Appends a fully-merged entry (scraper + generator data) to the JSON file.
#         Reads the current list, appends, then writes back atomically.
#         """
#         try:
#             with open(self.output_file, 'r') as f:
#                 data = json.load(f)
#         except Exception:
#             data = []

#         data.append(entry)

#         with open(self.output_file, 'w') as f:
#             json.dump(data, f, indent=4)

#         print(f"[Scraper] Saved to JSON: {entry['Title']} (Slug: {entry['Slug']})")

#     async def run(self, generator=None):
#         """
#         Main asynchronous execution loop.
#         Optionally accepts a ContentGenerator instance.
#         For each scraped tool, it calls the generator to enrich the data,
#         then writes the merged record to the shared JSON file.
#         """
#         print("--- Scraping Agent Started ---")

#         async with aiohttp.ClientSession(headers=self.headers) as session:
#             while self.current_url:
#                 soup = await self.fetch_page(session, self.current_url)
#                 if not soup:
#                     break

#                 post_items = soup.find_all('div', class_='post-item')
#                 if not post_items:
#                     print("[Scraper] No items found on this page. Ending.")
#                     break

#                 print(f"[Scraper] Found {len(post_items)} tools. Processing...")

#                 existing_slugs = self.get_existing_slugs()

#                 for item in post_items:
#                     data_element = item.find('div', class_='share-dialog')

#                     if not data_element:
#                         continue

#                     title = data_element.get('data-title')
#                     description = data_element.get('data-description')
#                     category = self.extract_category(item)

#                     # Extract the direct tool link from the visit button
#                     visit_btn = item.find('a', class_='visit-site-button4')
#                     link = visit_btn['href'] if visit_btn and visit_btn.get('href') else "Unknown"
#                     slug = self.create_slug(title)

#                     # Skip if already processed
#                     if slug in existing_slugs:
#                         print(f"[Scraper] Skipping duplicate: {title}")
#                         continue

#                     # Extract Logo URL
#                     logo_src = "Unknown"
#                     logo_div = item.find('div', class_='favicon-cat-brand')
#                     if logo_div:
#                         img_tag = logo_div.find('img')
#                         if img_tag and 'src' in img_tag.attrs:
#                             logo_src = img_tag['src']

#                     # --- Build the base scraped record ---
#                     scraped_data = {
#                         'Title': title,
#                         'Slug': slug,
#                         'Category': category,
#                         'Description': description,
#                         'Link': link,
#                         'Logo': logo_src,
#                         'Scraped_At': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#                     }

#                     # --- Enrich with generator if provided ---
#                     if generator:
#                         generated_data = generator.generate_and_parse(title, description, slug)
#                         # Merge: scraper fields + generator fields into one record
#                         merged_entry = {**scraped_data, **generated_data}
#                     else:
#                         merged_entry = scraped_data

#                     # --- Write the complete merged record to shared JSON ---
#                     self.append_to_json(merged_entry)
#                     existing_slugs.add(slug)

#                     print(f"[Scraper] Waiting {self.interval} seconds before next extraction...")
#                     await asyncio.sleep(self.interval)

#                 next_page_link = soup.find('a', class_='next page-numbers')
#                 if next_page_link and 'href' in next_page_link.attrs:
#                     self.current_url = next_page_link['href']
#                     await asyncio.sleep(2)
#                 else:
#                     self.current_url = None

#         print("--- Scraping Agent Finished ---")


# if __name__ == "__main__":
#     # When run standalone (without generator), only scraped fields are saved.
#     # To use with generator, import ContentGenerator and pass an instance below.
#     from slug_generator_agent_v03 import ContentGenerator

#     START_URL = "https://www.aixploria.com/en/free-ai/"
#     generator = ContentGenerator(output_json="ai_tools.json")
#     agent = AI_Tool_Agent(start_url=START_URL, output_file="ai_tools.json", interval_seconds=5)
#     asyncio.run(agent.run(generator=generator))



import aiohttp
import asyncio
from bs4 import BeautifulSoup
import os
import re
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor


class AI_Tool_Agent:
    def __init__(self, start_url, output_file="ai_tools.json", interval_seconds=3600):
        self.current_url = start_url
        self.output_file = output_file
        self.interval = interval_seconds
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        # Shared thread pool for offloading blocking generator calls
        self._executor = ThreadPoolExecutor()

        # Initialize JSON file if it doesn't exist
        if not os.path.exists(self.output_file):
            with open(self.output_file, 'w') as f:
                json.dump([], f)
            print(f"[Scraper] Created output file: {self.output_file}")

    def create_slug(self, text):
        """Generates a URL-friendly slug from the title."""
        if not isinstance(text, str):
            return "unknown-tool"
        text = text.lower()
        text = re.sub(r'[^a-z0-9\s-]', '', text)
        text = re.sub(r'\s+', '-', text).strip('-')
        return text

    async def fetch_page(self, session, url):
        """Fetches the HTML content of the page asynchronously."""
        try:
            print(f"[Scraper] Navigating to: {url}")
            async with session.get(url) as response:
                response.raise_for_status()
                html_content = await response.text()
                return BeautifulSoup(html_content, 'html.parser')
        except Exception as e:
            print(f"[Scraper] Error fetching page: {e}")
            return None

    def extract_category(self, post_item):
        """Attempts to find the category within the post-item."""
        potential_selectors = ['.category', '.cat-links', 'span.term-badge', '.post-category']
        for selector in potential_selectors:
            cat_elem = post_item.select_one(selector)
            if cat_elem:
                return cat_elem.get_text(strip=True)
        return "Unknown"

    def get_existing_slugs(self):
        """Returns a set of slugs already saved in the JSON file."""
        try:
            with open(self.output_file, 'r') as f:
                data = json.load(f)
            return {entry.get('Slug') for entry in data}
        except Exception:
            return set()

    def append_to_json(self, entry):
        """
        Appends a fully-merged entry (scraper + generator data) to the JSON file.
        Reads the current list, appends, then writes back atomically.
        """
        try:
            with open(self.output_file, 'r') as f:
                data = json.load(f)
        except Exception:
            data = []

        data.append(entry)

        with open(self.output_file, 'w') as f:
            json.dump(data, f, indent=4)

        print(f"[Scraper] Saved to JSON: {entry['Title']} (Slug: {entry['Slug']})")

    async def run(self, generator=None):
        """
        Main asynchronous execution loop.

        Accepts an optional ContentGenerator instance. For each scraped tool:
          1. Scraper builds the raw data dict.
          2. Generator.generate_and_parse() is offloaded to a thread executor
             (it is a blocking SDK call) so the async event loop is never blocked.
          3. Both dicts are merged and written to the shared JSON file in one shot.
        """
        print("--- Scraping Agent Started ---")

        loop = asyncio.get_event_loop()

        async with aiohttp.ClientSession(headers=self.headers) as session:
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

                    # Extract the direct tool link from the visit button
                    visit_btn = item.find('a', class_='visit-site-button4')
                    link = visit_btn['href'] if visit_btn and visit_btn.get('href') else "Unknown"

                    slug = self.create_slug(title)

                    # Skip duplicates
                    if slug in existing_slugs:
                        print(f"[Scraper] Skipping duplicate: {title}")
                        continue

                    # Extract Logo URL
                    logo_src = "Unknown"
                    logo_div = item.find('div', class_='favicon-cat-brand')
                    if logo_div:
                        img_tag = logo_div.find('img')
                        if img_tag and 'src' in img_tag.attrs:
                            logo_src = img_tag['src']

                    # Build the base scraped record
                    scraped_data = {
                        'Title':       title,
                        'Slug':        slug,
                        'Category':    category,
                        'Description': description,
                        'Link':        link,
                        'Logo':        logo_src,
                        'Scraped_At':  datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }

                    # Enrich with generator if provided.
                    # generate_and_parse() is a blocking call (Agno/Gemini SDK),
                    # so we offload it to a thread executor to keep the event loop free.
                    if generator:
                        print(f"[Scraper] Handing off to Generator: {title}")
                        generated_data = await loop.run_in_executor(
                            self._executor,
                            generator.generate_and_parse,
                            title,
                            description,
                            slug
                        )
                        merged_entry = {**scraped_data, **generated_data}
                    else:
                        merged_entry = scraped_data

                    # Write the complete merged record to the shared JSON file
                    self.append_to_json(merged_entry)
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
    # Run scraper+generator standalone (without Telegram poster)
    from slug_generator_agent_v03 import ContentGenerator

    START_URL   = "https://www.aixploria.com/en/free-ai/"
    OUTPUT_FILE = "ai_tools.json"

    generator = ContentGenerator(output_json=OUTPUT_FILE)
    scraper   = AI_Tool_Agent(start_url=START_URL, output_file=OUTPUT_FILE)

    asyncio.run(scraper.run(generator=generator))