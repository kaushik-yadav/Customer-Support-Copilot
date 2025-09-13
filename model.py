import json
import os
import re
from typing import List

import google.generativeai as genai
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def analyze(ticket_text):
    # creating a class using pydantic basemodel
    class TicketAnalysis(BaseModel):
        topic_tags: List[str]
        sentiment: str
        priority: str

    with open("prompt.txt", "r", encoding="utf-8") as f:
        prompt_template = f.read().strip()

    full_prompt = prompt_template.replace("{INSERT_TICKET_HERE}", ticket_text)

    model = genai.GenerativeModel("gemini-2.0-flash-lite")
    response = model.generate_content(full_prompt)
    llm_output = response.text.strip()
    print("Raw LLM output:\n", llm_output)

    # try extracting the json output
    json_match = re.search(r'\{.*\}', llm_output, re.DOTALL)
    if json_match:
        json_str = json_match.group(0)
        try:
            data = json.loads(json_str)
            ticket_analysis = TicketAnalysis(**data)
            return ticket_analysis

        except (json.JSONDecodeError, ValidationError) as e:
            print("\nError parsing JSON:", e)
            return
    else:
        # Fallback: parse human-readable format
        topic_tags = re.findall(r"\*\*Topic Tags\*\*:\s*(.+)", llm_output)
        sentiment = re.findall(r"\*\*Sentiment\*\*:\s*(.+)", llm_output)
        priority = re.findall(r"\*\*Priority\*\*:\s*(.+)", llm_output)

        ticket_analysis = TicketAnalysis(
            topic_tags=[tag.strip() for tag in topic_tags[0].split(",")] if topic_tags else [],
            sentiment=sentiment[0].strip() if sentiment else "",
            priority=priority[0].strip() if priority else ""
        )
        return ticket_analysis

