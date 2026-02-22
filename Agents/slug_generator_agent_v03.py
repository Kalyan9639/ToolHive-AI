import time
import os
import re
import json
from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.google import Gemini
from agno.tools.duckduckgo import DuckDuckGoTools

load_dotenv()

class ContentGenerator:
    def __init__(self, output_json="ai_tools.json"):
        self.output_json = output_json

        # Initialize the Agno Agent
        # Note: CsvTools removed since we no longer use a CSV as input.
        # DuckDuckGo is sufficient for research.
        self.agent = Agent(
            model=Gemini(id="gemini-2.5-flash-lite"),
            tools=[DuckDuckGoTools()],
            description="You are an expert AI analyst who researches tools and writes concise, structured reports.",
            instructions=[
                "Use DuckDuckGo to search for the specific AI tool mentioned.",
                "Do not invent features; if information is missing, state that.",
                "STRICT FORMATTING RULE: You must output only the report section names in MARKDOWN format using specific headers (## or ###).",
                "DON'T USE MARKDOWN for other texts except section headings in the report."
            ],
            markdown=False
        )

    def generate_and_parse(self, tool_name, tool_desc, tool_slug):
        """
        Calls the AI agent to generate Key Features, Pros, and Cons for a tool.
        Returns a dict with those fields (and a Generated_At timestamp).
        This is called by the scraper inline — before writing to JSON.
        """
        print(f"\n[Generator] Researching: {tool_name}...")

        prompt = f"""
        Research the AI tool named "{tool_name}".
        Context provided: "{tool_desc}".

        You MUST generate the report using the following Markdown headers EXACTLY.
        Do not add any introductory text before the first header.

        ## Key Features
        (List 5 distinct bullet points)

        ## Pros
        (List 3-4 points)

        ## Cons
        (List 3-4 points)

        Focus on accuracy and strictly follow this format for Regex parsing.
        Include no preamble and no postamble.
        """

        try:
            response = self.agent.run(prompt)
            content = response.content
        except Exception as e:
            print(f"[!] Error generating content for {tool_name}: {e}")
            content = ""

        # Parse sections with Regex
        features_match = re.search(r"##\s*Key Features(.*?)(?=##|$)", content, re.DOTALL | re.IGNORECASE)
        pros_match     = re.search(r"##\s*Pros(.*?)(?=##\s*Cons|$)", content, re.DOTALL | re.IGNORECASE)
        cons_match     = re.search(r"##\s*Cons(.*?)(?=##|$)", content, re.DOTALL | re.IGNORECASE)

        generated_data = {
            'Key Features': features_match.group(1).strip() if features_match else "N/A",
            'Pros':         pros_match.group(1).strip()     if pros_match     else "N/A",
            'Cons':         cons_match.group(1).strip()     if cons_match     else "N/A",
            'Generated_At': time.strftime("%Y-%m-%d %H:%M:%S")
        }

        print(f"[Generator] Content ready for: {tool_name}")
        return generated_data


# ---------------------------------------------------------------------------
# Standalone mode: monitor the shared JSON for records that are missing
# generator fields and enrich them on-the-fly.
# Useful if the generator crashed mid-run and left incomplete records.
# ---------------------------------------------------------------------------
class StandaloneGeneratorMonitor:
    """
    Watches ai_tools.json for entries that have no 'Key Features' field
    (i.e. scraper ran but generator didn't process them yet) and fills them in.
    """
    def __init__(self, json_file="ai_tools.json", check_interval=5):
        self.json_file = json_file
        self.check_interval = check_interval
        self.generator = ContentGenerator(output_json=json_file)

    def run(self):
        print("--- Standalone Generator Monitor Started ---")
        print(f"[*] Watching {self.json_file} for un-enriched entries...")

        while True:
            if os.path.exists(self.json_file):
                try:
                    with open(self.json_file, 'r') as f:
                        data = json.load(f)

                    updated = False
                    for i, entry in enumerate(data):
                        # If Key Features is missing, this entry needs enrichment
                        if not entry.get('Key Features'):
                            tool_name = entry.get('Title', 'Unknown')
                            tool_desc = entry.get('Description', '')
                            tool_slug = entry.get('Slug', '')

                            generated_data = self.generator.generate_and_parse(tool_name, tool_desc, tool_slug)
                            data[i] = {**entry, **generated_data}
                            updated = True

                    if updated:
                        with open(self.json_file, 'w') as f:
                            json.dump(data, f, indent=4)
                        print("[Generator] JSON file updated with enriched entries.")

                except json.JSONDecodeError:
                    pass  # File may be mid-write; skip this cycle
                except Exception as e:
                    print(f"[Generator] Unexpected error: {e}")

            time.sleep(self.check_interval)


if __name__ == "__main__":
    monitor = StandaloneGeneratorMonitor()
    monitor.run()