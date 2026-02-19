import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
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
            df = pd.DataFrame(columns=['Title', 'Category', 'Description', 'Link', 'Scraped_At'])
            df.to_csv(self.output_file, index=False)

    def fetch_page(self, url):
        """Fetches the HTML content of the page."""
        try:
            print(f"[*] Navigating to: {url}")
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            print(f"[!] Error fetching page: {e}")
            return None

    def extract_category(self, post_item):
        """
        Attempts to find the category within the post-item.
        Note: Since the specific HTML for category wasn't provided, 
        this looks for common class names. You may need to inspect the 
        site's 'post-item' HTML to find the exact class for the category tag.
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
        df = pd.DataFrame([tool_data])
        # Append to CSV, ignore header if file already exists
        df.to_csv(self.output_file, mode='a', header=not os.path.exists(self.output_file), index=False)
        print(f"[+] Saved: {tool_data['Title']}")

    def run(self):
        """Main execution loop."""
        print("--- Agent Started ---")
        
        while self.current_url:
            soup = self.fetch_page(self.current_url)
            if not soup:
                break

            # Find all container divs for tools (post-items)
            # We look for the parent 'post-item' as you mentioned
            post_items = soup.find_all('div', class_='post-item')

            if not post_items:
                print("[!] No items found on this page. Ending.")
                break

            print(f"[*] Found {len(post_items)} tools on current page. Starting extraction...")

            for item in post_items:
                # Find the specific element containing the data attributes
                # You mentioned class="share-dialog hide"
                data_element = item.find('div', class_='share-dialog')

                if data_element:
                    title = data_element.get('data-title')
                    description = data_element.get('data-description')
                    link = data_element.get('data-url')
                    
                    # Try to extract category from the parent 'item'
                    category = self.extract_category(item)

                    tool_data = {
                        'Title': title,
                        'Category': category,
                        'Description': description,
                        'Link': link,
                        'Scraped_At': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }

                    self.save_tool(tool_data)
                    
                    # Wait for the specified interval before extracting the next one
                    time.sleep(self.interval)
                else:
                    # Fallback if the share-dialog div isn't found in a post-item
                    continue

            # Pagination Logic
            # Look for the 'next page-numbers' link
            next_page_link = soup.find('a', class_='next page-numbers')
            
            if next_page_link and 'href' in next_page_link.attrs:
                self.current_url = next_page_link['href']
                print("[->] Moving to next page...")
                # Optional: Add a small delay between page loads to be polite
                time.sleep(2) 
            else:
                print("[*] No next page found. Extraction complete.")
                self.current_url = None

if __name__ == "__main__":
    # URL provided by you
    START_URL = "https://www.aixploria.com/en/free-ai/"
    
    # Initialize the agent
    # interval_seconds=5 means it waits 5 seconds between each tool extraction
    agent = AI_Tool_Agent(start_url=START_URL, output_file="extracted_ai_tools.csv", interval_seconds=5)
    
    # Start the agent
    agent.run()