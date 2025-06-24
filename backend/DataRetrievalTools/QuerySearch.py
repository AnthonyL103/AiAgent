from openai import OpenAI
import json
import os
import pandas as pd
from dotenv import load_dotenv
from clickhouse_driver import Client

load_dotenv()


client = OpenAI(api_key=os.getenv("API_KEY"))

dbclient = Client(host='localhost', port=9000, user='AgentDemo', password='ILoveAgents45867760')

def safe_json_dumps(obj):
    return json.dumps(obj, allow_nan=False)

def apply_query(query):
    """Apply filters to the dataframe and return results"""
    
    queryresult = dbclient.execute(query)
    
    
    return queryresult



async def getquery(prompt, context=None):
    user_prompt = json.dumps(prompt)
    if context:
        context_info = f"Discovered patterns: {context}"
    else:
        context_info = "No prior context available"
    
        
    system_prompt = f"""
        You are a data query generator. Generate an SQL Query in a JSON object for filtering and analyzing data in Clickhouse based on the prompt and context given.
        Context represents existing logs than can help you identify what tags/keywords to query for. Userprompt comes from your manager, and you must construct a query to fit their demands.

        {context_info}
        
        Limitations:
        
        -Do not perform any Create, Update, and Delete operations.
        -You are purely for read operations.


        Output ONLY the Query. No explanations.
        """

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0
    )

    response_text = response.choices[0].message.content
    
    
    
    results = apply_query(response_text)
    
    return results


