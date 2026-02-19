# from agno.agent import Agent
# from agno.models.google import Gemini
# from agno.tools.duckduckgo import DuckDuckGoTools
# from agno.tools.csv_toolkit import CsvTools
# from dotenv import load_dotenv

# load_dotenv()

# agent=Agent(
#     name="AI Tool Content Generator",
#     model=Gemini(id="gemini-2.5-flash-lite"),
#     tools=[CsvTools(csvs=['jobs.csv'])],
#     description="",
#     instructions="",
#     markdown=True
# )

# response = agent.print_response("""
# Draft me web page content for the 1st job present in the jobs.csv file. Use all columns to create the content. Your response must be in HTML format and should be suitable for a web page. 
# It should be engaging and informative, and should include a summary of the job description, key responsibilities, and required qualifications. 
# Use the latest news and trends to make the content relevant and appealing to potential candidates.
# Only use the given information from the CSV file to create the content. Do not include any information that is not present in the CSV file.
# Include no preamble or postamble, just the content for the web page.
# """)

# --------------------------------------------------------------------


import pandas as pd
import time
import os
import re
from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.google import Gemini  # You can switch this to Gemini or others
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.csv_toolkit import CsvTools 

load_dotenv()

class ContentGenerator:
    def __init__(self, input_csv="extracted_ai_tools.csv", output_csv="generated_content.csv"):
        self.input_csv = input_csv
        self.output_csv = output_csv
        self.last_processed_index = -1
        
        # Initialize the Agno Agent
        self.agent = Agent(
            model=Gemini(id="gemini-2.5-flash-lite"),
            tools=[DuckDuckGoTools(), CsvTools(csvs=[input_csv])],
            description="You are an expert AI analyst who researches tools and writes concise, structured reports.",
            instructions=[
                "Use DuckDuckGo to search for the specific AI tool mentioned.",
                "Verify the tool's details from the provided CSV context if needed.",
                "Do not invent features; if information is missing, state that.",
                "STRICT FORMATTING RULE: You must output the only report sections names in MARKDOWN format using specific headers(## or ###)."
                "DON'T USE MARKDOWN for other texts except section headings in the report"
            ],
            markdown=False
        )

        # Initialize Output CSV
        if not os.path.exists(self.output_csv):
            df = pd.DataFrame(columns=[
                'Tool Name', 'Overview', 'Key Features', 'Usage', 'Pros', 'Cons', 'Generated_At'
            ])
            df.to_csv(self.output_csv, index=False)
            print(f"[Generator] Created output file: {self.output_csv}")

    def get_new_rows(self):
        """Checks the input CSV for new rows since the last check."""
        if not os.path.exists(self.input_csv):
            return pd.DataFrame()

        try:
            df = pd.read_csv(self.input_csv)
            # If this is the first run, process everything or start from now? 
            # Let's assume we process everything currently in the file if index is -1
            if self.last_processed_index == -1:
                # If file exists but we haven't processed anything, start from beginning
                # or you can set self.last_processed_index = len(df) - 1 to skip existing
                pass 
            
            if len(df) > self.last_processed_index + 1:
                new_data = df.iloc[self.last_processed_index + 1:]
                self.last_processed_index = len(df) - 1
                return new_data
            
        except pd.errors.EmptyDataError:
            return pd.DataFrame()
        
        return pd.DataFrame()

    def generate_content(self, tool_name, tool_desc):
        """Uses the Agno agent to generate the report."""
        print(f"\n[Generator] Researching: {tool_name}...")
        
        prompt = f"""
        Research the AI tool named "{tool_name}". 
        Context provided from scraper: "{tool_desc}".
        
        You MUST generate the report using the following Markdown headers EXACTLY. 
        Do not add any introductory text before the first header.
        
        ## Overview
        (Write 3-4 lines summarizing what it is)
        
        ## Key Features
        (List 5 distinct bullet points)
        
        ## Usage
        (List 5-6 distinct bullet points on how people use this tool)
        
        ## Pros
        (List 3-4 points)
        
        ## Cons
        (List 3-4 points)
        
        Focus on accuracy and strictly follow this format for Regex parsing.
        Include no preamble and postamble.
        """

        try:
            # Run the agent
            response = self.agent.run(prompt)
            return response.content
        except Exception as e:
            print(f"[!] Error generating content: {e}")
            return "Generation Failed"

    def parse_and_save(self, tool_name, content):
        """Parses the agent output using Regex and saves to CSV."""
        
        # Regex patterns to extract sections
        # We look for content starting after a specific header and ending before the next header (##) or end of string
        overview_match = re.search(r"##\s*Overview(.*?)(?=##|$)", content, re.DOTALL | re.IGNORECASE)
        features_match = re.search(r"##\s*Key Features(.*?)(?=##|$)", content, re.DOTALL | re.IGNORECASE)
        usage_match = re.search(r"##\s*Usage(.*?)(?=##|$)", content, re.DOTALL | re.IGNORECASE)
        pros_match = re.search(r"##\s*Pros(.*?)(?=##\s*Cons|$)", content, re.DOTALL | re.IGNORECASE)
        cons_match = re.search(r"##\s*Cons(.*?)(?=##|$)", content, re.DOTALL | re.IGNORECASE)

        entry = {
            'Tool Name': tool_name,
            'Overview': overview_match.group(1).strip() if overview_match else "N/A",
            'Key Features': features_match.group(1).strip() if features_match else "N/A",
            'Usage': usage_match.group(1).strip() if usage_match else "N/A",
            'Pros': pros_match.group(1).strip() if pros_match else "N/A",
            'Cons': cons_match.group(1).strip() if cons_match else "N/A",
            'Generated_At': time.strftime("%Y-%m-%d %H:%M:%S")
        }

        df = pd.DataFrame([entry])
        df.to_csv(self.output_csv, mode='a', header=not os.path.exists(self.output_csv), index=False)
        print(f"[Generator] Saved report for {tool_name}")

    def start_monitoring(self, check_interval=2):
        print(f"--- Generator Agent Started ---")
        print(f"[*] Watching {self.input_csv} for updates...")

        while True:
            new_rows = self.get_new_rows()
            
            if not new_rows.empty:
                print(f"[*] Detected {len(new_rows)} new tool(s).")
                
                for index, row in new_rows.iterrows():
                    tool_name = row['Title']
                    tool_desc = row['Description'] # Use the description from scraper as context
                    
                    content = self.generate_content(tool_name, tool_desc)
                    self.parse_and_save(tool_name, content)
            
            time.sleep(check_interval)

if __name__ == "__main__":
    generator = ContentGenerator()
    generator.start_monitoring()