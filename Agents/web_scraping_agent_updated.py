import aiohttp
import asyncio
from bs4 import BeautifulSoup
import pandas as pd
import os
from datetime import datetime

class AI_Tool_Agent:
    def __init__(self, start_url, output_file="ai_tools.csv", interval_seconds=10):
        self.current_url = start_url
        self.output_file = output_file
        self.interval = interval_seconds
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        # Initialize CSV if it doesn't exist
        if not os.path.exists(self.output_file):
            # Added 'Logo' to the columns
            df = pd.DataFrame(columns=['Title', 'Category', 'Description', 'Link', 'Logo', 'Scraped_At'])
            df.to_csv(self.output_file, index=False)

    async def fetch_page(self, session, url):
        """Fetches the HTML content of the page asynchronously."""
        try:
            print(f"[*] Navigating to: {url}")
            async with session.get(url) as response:
                response.raise_for_status()
                html_content = await response.text()
                return BeautifulSoup(html_content, 'html.parser')
        except Exception as e:
            print(f"[!] Error fetching page: {e}")
            return None

    def extract_category(self, post_item):
        """
        Attempts to find the category within the post-item.
        """
        # Common selectors for categories in WordPress themes
        potential_selectors = ['.category', '.cat-links', 'span.term-badge', '.post-category']
        
        for selector in potential_selectors:
            cat_elem = post_item.select_one(selector)
            if cat_elem:
                return cat_elem.get_text(strip=True)
        
        return "Unknown"

    def save_tool(self, tool_data):
        """Appends a single tool's data to the CSV file using Pandas."""
        # Note: Pandas file operations are blocking. In a high-concurrency 
        # environment, you might run this in a thread executor, but for this 
        # use case, direct calling is acceptable.
        df = pd.DataFrame([tool_data])
        # Append to CSV, ignore header if file already exists
        df.to_csv(self.output_file, mode='a', header=not os.path.exists(self.output_file), index=False)
        print(f"[+] Saved: {tool_data['Title']}")

    async def run(self):
        """Main asynchronous execution loop."""
        print("--- Agent Started (Async) ---")
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            while self.current_url:
                soup = await self.fetch_page(session, self.current_url)
                if not soup:
                    break

                # Find all container divs for tools (post-items)
                post_items = soup.find_all('div', class_='post-item')

                if not post_items:
                    print("[!] No items found on this page. Ending.")
                    break

                print(f"[*] Found {len(post_items)} tools on current page. Starting extraction...")

                for item in post_items:
                    # Find the specific element containing the data attributes
                    data_element = item.find('div', class_='share-dialog')

                    if data_element:
                        title = data_element.get('data-title')
                        description = data_element.get('data-description')
                        link = data_element.get('data-url')
                        
                        # Extract Category
                        category = self.extract_category(item)

                        # Extract Logo URL
                        # Looking for <div class="favicon-cat-brand"><img ... src="..."></div>
                        logo_div = item.find('div', class_='favicon-cat-brand')
                        logo_src = "Unknown"
                        if logo_div:
                            img_tag = logo_div.find('img')
                            if img_tag and 'src' in img_tag.attrs:
                                logo_src = img_tag['src']

                        tool_data = {
                            'Title': title,
                            'Category': category,
                            'Description': description,
                            'Link': link,
                            'Logo': logo_src,
                            'Scraped_At': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }

                        self.save_tool(tool_data)
                        
                        # Asynchronous sleep to allow other tasks to run
                        await asyncio.sleep(self.interval)
                    else:
                        continue

                # Pagination Logic
                next_page_link = soup.find('a', class_='next page-numbers')
                
                if next_page_link and 'href' in next_page_link.attrs:
                    self.current_url = next_page_link['href']
                    print("[->] Moving to next page...")
                    await asyncio.sleep(2) 
                else:
                    print("[*] No next page found. Extraction complete.")
                    self.current_url = None

if __name__ == "__main__":
    # URL provided by you
    START_URL = "https://www.aixploria.com/en/free-ai/"
    
    # Initialize the agent
    agent = AI_Tool_Agent(start_url=START_URL, output_file="extracted_ai_tools.csv", interval_seconds=600)
    
    # Start the async event loop
    asyncio.run(agent.run())

