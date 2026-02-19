# ------------------------------------------------------------------------


import aiohttp
import asyncio
from bs4 import BeautifulSoup
import pandas as pd
import os
import re
from datetime import datetime

class AI_Tool_Agent:
    def __init__(self, start_url, output_file="extracted_ai_tools.csv", interval_seconds=3600):
        self.current_url = start_url
        self.output_file = output_file
        self.interval = interval_seconds
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        # Initialize CSV if it doesn't exist
        # Added 'Slug' to the column list
        if not os.path.exists(self.output_file):
            df = pd.DataFrame(columns=['Title', 'Slug', 'Category', 'Description', 'Link', 'Logo', 'Scraped_At'])
            df.to_csv(self.output_file, index=False)

    def create_slug(self, text):
        """Generates a URL-friendly slug from the title."""
        if not text:
            return "unknown-tool"
        # Convert to lowercase
        text = text.lower()
        # Remove special characters (keep alphanumeric and spaces)
        text = re.sub(r'[^a-z0-9\s-]', '', text)
        # Replace spaces (and multiple spaces) with hyphens
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

    def save_tool(self, tool_data):
        """Appends a single tool's data to the CSV file."""
        df = pd.DataFrame([tool_data])
        
        # Ensure column order matches init
        columns = ['Title', 'Slug', 'Category', 'Description', 'Link', 'Logo', 'Scraped_At']
        df = df[columns]
        
        # Append to CSV
        df.to_csv(self.output_file, mode='a', header=not os.path.exists(self.output_file), index=False)
        print(f"[Scraper] Saved: {tool_data['Title']} (Slug: {tool_data['Slug']})")

    async def run(self):
        """Main asynchronous execution loop."""
        print("--- Scraping Agent Started ---")
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            while self.current_url:
                soup = await self.fetch_page(session, self.current_url)
                if not soup:
                    break

                post_items = soup.find_all('div', class_='post-item')
                if not post_items:
                    print("[Scraper] No items found on this page. Ending.")
                    break

                print(f"[Scraper] Found {len(post_items)} tools. processing...")

                for item in post_items:
                    data_element = item.find('div', class_='share-dialog')

                    if data_element:
                        title = data_element.get('data-title')
                        description = data_element.get('data-description')
                        link = data_element.get('data-url')
                        category = self.extract_category(item)

                        # Generate Slug
                        slug = self.create_slug(title)

                        # Extract Logo URL
                        logo_div = item.find('div', class_='favicon-cat-brand')
                        logo_src = "Unknown"
                        if logo_div:
                            img_tag = logo_div.find('img')
                            if img_tag and 'src' in img_tag.attrs:
                                logo_src = img_tag['src']

                        tool_data = {
                            'Title': title,
                            'Slug': slug,
                            'Category': category,
                            'Description': description,
                            'Link': link,
                            'Logo': logo_src,
                            'Scraped_At': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }

                        self.save_tool(tool_data)
                        
                        # Wait for the interval
                        print(f"[Scraper] Waiting {self.interval} seconds before next extraction...")
                        await asyncio.sleep(self.interval)
                    else:
                        continue

                next_page_link = soup.find('a', class_='next page-numbers')
                if next_page_link and 'href' in next_page_link.attrs:
                    self.current_url = next_page_link['href']
                    await asyncio.sleep(2) 
                else:
                    self.current_url = None

if __name__ == "__main__":
    START_URL = "https://www.aixploria.com/en/free-ai/"
    agent = AI_Tool_Agent(start_url=START_URL, interval_seconds=3600)
    asyncio.run(agent.run())