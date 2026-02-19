import asyncio
import threading
import time
from slug_generator_agent import ContentGenerator
from slug_web_scrapping_agent import AI_Tool_Agent

# 1. Wrapper function to run the synchronous Generator Agent
def run_generator_thread():
    print("[Orchestrator] Starting Generator Agent in background thread...")
    # Initialize and start the generator
    # This will run in its own loop and won't block the scraper
    generator = ContentGenerator(
        input_csv="extracted_ai_tools.csv", 
        output_json="generated_content.json"
    )
    generator.start_monitoring(check_interval=5)

# 2. Main Async function to run the Scraping Agent
async def main():
    # Start the generator thread as a daemon (it closes when the main script closes)
    gen_thread = threading.Thread(target=run_generator_thread, daemon=True)
    gen_thread.start()

    # Give the thread a moment to initialize
    await asyncio.sleep(1)

    print("[Orchestrator] Starting Scraping Agent in main async loop...")
    
    START_URL = "https://www.aixploria.com/en/free-ai/"
    # Scrape every 600 seconds (10 minutes)
    scraper = AI_Tool_Agent(
        start_url=START_URL, 
        output_file="extracted_ai_tools.csv", 
        interval_seconds=600
    )
    
    # This will run indefinitely
    await scraper.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[Orchestrator] Shutting down agents...")