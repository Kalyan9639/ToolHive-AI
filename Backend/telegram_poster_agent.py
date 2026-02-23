import json
import asyncio
import os
import aiohttp
from dotenv import load_dotenv

load_dotenv()


class TelegramAutoPoster:
    def __init__(self, json_file="ai_tools.json", state_file="last_posted_index.txt"):
        self.json_file   = json_file
        self.state_file  = state_file
        self.bot_token   = os.getenv("TELEGRAM_BOT_TOKEN")
        self.channel_id  = os.getenv("TELEGRAM_CHANNEL_ID")
        self.api_url     = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

        if not self.bot_token or not self.channel_id:
            raise ValueError("Missing Telegram credentials in .env file.")

    # ------------------------------------------------------------------
    # State helpers (synchronous — just file I/O, fine to call from async)
    # ------------------------------------------------------------------

    def get_last_posted_index(self):
        """Reads the state file to track progress."""
        if os.path.exists(self.state_file):
            with open(self.state_file, "r") as f:
                try:
                    return int(f.read().strip())
                except ValueError:
                    return -1
        return -1

    def update_last_posted_index(self, index):
        """Saves progress so we don't double-post after a crash."""
        with open(self.state_file, "w") as f:
            f.write(str(index))

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    def format_message(self, tool_name, category, description, slug):
        """Constructs the Telegram post message."""
        words      = str(description).split()
        short_desc = " ".join(words[:10])

        return (
            f"🚀 {tool_name}\n\n"
            f"🧠 Category: {category}\n"
            f"✨ {short_desc}\n"
            f"💰 Free/Freemium\n"
            f"🔗 Details:\n"
            f"https://tool-hive-ai.vercel.app/?slug={slug}"
        )

    # ------------------------------------------------------------------
    # Guard: only post once both agents have written their data
    # ------------------------------------------------------------------

    def is_fully_enriched(self, tool):
        """A record is complete when the generator has added Key Features."""
        key_features = tool.get("Key Features", "")
        return bool(key_features) and key_features != "N/A"

    # ------------------------------------------------------------------
    # Async HTTP post to Telegram
    # ------------------------------------------------------------------

    async def post_to_telegram(self, session, message):
        """Sends the message to Telegram using an async aiohttp session."""
        payload = {
            "chat_id": self.channel_id,
            "text":    message,
            "disable_web_page_preview": False
        }
        try:
            async with session.post(self.api_url, json=payload) as response:
                if response.status != 200:
                    text = await response.text()
                    print(f"[!] Telegram Rejected Post: {text}")
                    return False
                return True
        except Exception as e:
            print(f"[!] Connection Error: {e}")
            return False

    # ------------------------------------------------------------------
    # Main async monitoring loop
    # ------------------------------------------------------------------

    async def monitor_and_post_async(self, check_interval=30):
        """
        Async loop — watches the shared JSON for fully-enriched entries
        and posts them to Telegram. Runs concurrently with the scraper.
        """
        print("--- Telegram Auto-Poster Started ---")

        async with aiohttp.ClientSession() as session:
            while True:
                if os.path.exists(self.json_file):
                    try:
                        with open(self.json_file, "r") as f:
                            data = json.load(f)

                        last_index = self.get_last_posted_index()

                        if len(data) > last_index + 1:
                            for i in range(last_index + 1, len(data)):
                                tool = data[i]

                                # Wait for generator data before posting
                                if not self.is_fully_enriched(tool):
                                    print(f"[Poster] Waiting — '{tool.get('Title', '?')}' not fully enriched yet.")
                                    break

                                t_name = tool.get("Title", "Unknown")
                                t_slug = tool.get("Slug", "")
                                t_desc = tool.get("Description", "")
                                t_cat  = str(tool.get("Category", "AI Tool")).replace("#", "").strip()

                                message = self.format_message(t_name, t_cat, t_desc, t_slug)

                                print(f"[*] Posting: {t_name}...")
                                if await self.post_to_telegram(session, message):
                                    print(f"[+] Success.")
                                    self.update_last_posted_index(i)
                                    # Yield control back to the event loop while waiting
                                    await asyncio.sleep(5)
                                else:
                                    print(f"[-] Failed. Retrying in next cycle.")
                                    break

                    except json.JSONDecodeError:
                        pass  # File may be mid-write; skip this cycle
                    except Exception as e:
                        print(f"[Poster] Unexpected error: {e}")

                await asyncio.sleep(check_interval)


if __name__ == "__main__":
    # Master entrypoint — run this file to start everything.
    # Launches scraper+generator and Telegram poster concurrently.
    from slug_web_scrapping_agent_v04 import AI_Tool_Agent
    from slug_generator_agent_v03 import ContentGenerator

    START_URL   = "https://www.aixploria.com/en/free-ai/"
    OUTPUT_FILE = "ai_tools.json"

    generator = ContentGenerator(output_json=OUTPUT_FILE)
    scraper   = AI_Tool_Agent(start_url=START_URL, output_file=OUTPUT_FILE, interval_seconds=28800) # Scrape every 8 hours
    poster    = TelegramAutoPoster(json_file=OUTPUT_FILE)

    async def main():
        """Run scraper+generator and Telegram poster concurrently."""
        await asyncio.gather(
            scraper.run(generator=generator),  # scrapes and enriches tools
            poster.monitor_and_post_async(),   # watches JSON and posts to Telegram
        )

    asyncio.run(main())