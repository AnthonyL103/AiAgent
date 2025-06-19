from openai import OpenAI
import json
import os
import pandas as pd
from dotenv import load_dotenv

load_dotenv()


client = OpenAI(api_key=os.getenv("API_KEY"))

def safe_json_dumps(obj):
    return json.dumps(obj, allow_nan=False)

df = pd.read_csv('/Users/anthonyli/VDBSimSearchDemo/backend/DataRetrievalTools/testlog.csv', names=[
    'timestamp_full', 'timestamp_simple', 'unknown1', 'unknown2', 'unknown3', 
    'SeverityText', 'unknown4', 'ServiceName', 'message', 'schema_url', 'metadata_json', 
    'unknown5', 'class_name', 'unknown6', 'unknown7', 'order_result_json'
])

def apply_filters(df, filters, aggregation=None):
    """Apply filters to the dataframe and return results"""
    filtered_df = df.copy()
    
    timestamp_range = filters.get("timestamp_full_range")
    if timestamp_range:
        start_time = timestamp_range.get("start")
        end_time = timestamp_range.get("end")
        
        if start_time:
            filtered_df = filtered_df[pd.to_datetime(filtered_df['timestamp_full']) >= pd.to_datetime(start_time)]
        
        if end_time:
            filtered_df = filtered_df[pd.to_datetime(filtered_df['timestamp_full']) <= pd.to_datetime(end_time)]
    
    for key, value in filters.items():
        if key.endswith("_exact"):
            column_name = key.replace("_exact", "")
            if column_name in filtered_df.columns:
                filtered_df = filtered_df[filtered_df[column_name] == value]
    
    if aggregation:
        return apply_aggregation(filtered_df, aggregation)
    
    return {
        "type": "filtered_logs",
        "count": len(filtered_df),
        "logs": filtered_df.to_dict('records')[:100]  
    }

def apply_aggregation(df, aggregation):
    """Apply aggregation operations to the dataframe"""
    group_by = aggregation.get("group_by")
    count = aggregation.get("count", False)
    time_bucket = aggregation.get("time_bucket")
    
    if not group_by:
        return {"error": "group_by is required for aggregation"}
    
    if group_by not in df.columns:
        return {"error": f"Column {group_by} not found"}
    
    if time_bucket and group_by == "timestamp_full":
        freq_map = {
            "1m": "1T", "5m": "5T", "15m": "15T", "30m": "30T",
            "1h": "1H", "2h": "2H", "6h": "6H", "12h": "12H",
            "1d": "1D"
        }
        freq = freq_map.get(time_bucket, "1H")
        
        df['timestamp_dt'] = pd.to_datetime(df['timestamp_full'])
        df['time_bucket'] = df['timestamp_dt'].dt.floor(freq)
        group_by = "time_bucket"
    
    if count:
        result = df.groupby(group_by).size().reset_index(name='count')
        return {
            "type": "aggregation",
            "group_by": group_by,
            "time_bucket": time_bucket,
            "results": result.to_dict('records')
        }
    else:
        grouped = df.groupby(group_by)
        result = []
        for name, group in grouped:
            result.append({
                group_by: name,
                "count": len(group),
                "sample_logs": group.head(3).to_dict('records')
            })
        
        return {
            "type": "grouped_logs",
            "group_by": group_by,
            "results": result
        }

async def getquery(prompt, context=None):
    user_prompt = json.dumps(prompt)
    if context:
        context_info = f"Discovered patterns: {context}"
    else:
        context_info = "No prior context available"
        
    system_prompt = f"""
You are a data query generator. Generate a QueryPlan JSON object for filtering and analyzing data.

{context_info}

Your QueryPlan should have this format:

        For simple counting (total count):
        {{
            "aggregation": {{
                "count": true
            }}
        }}

        For counting by groups:
        {{
            "aggregation": {{
                "group_by": "ServiceName",
                "count": true
            }}
        }}

        For timestamp filtering:
        {{
            "filters": {{
                "timestamp_full_range": {{ "start": "YYYY-MM-DD HH:MM:SS", "end": "YYYY-MM-DD HH:MM:SS" }}
            }}
        }}

        For exact matches (use ACTUAL column names from context):
        {{
            "filters": {{
                "SeverityText_exact": "INFO"
            }}
        }}

        Output ONLY the JSON object. No explanations.
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
    try:
        response_text = response_text.strip()
        print("LLM Response:", response_text)
        
        if response_text.startswith("```json"):
            response_text = response_text[len("```json"):].strip()
        if response_text.endswith("```"):
            response_text = response_text[:-3].strip()

        query_plan = json.loads(response_text)
    except json.JSONDecodeError as e:
        print("Invalid JSON response:", e)
        query_plan = {}

    filters = query_plan.get("filters", {})
    aggregation = query_plan.get("aggregation")
    
    print(f"Applying filters: {filters}")
    if aggregation:
        print(f"Applying aggregation: {aggregation}")
    
    results = apply_filters(df, filters, aggregation)
    
    return results


if __name__ == "__main__":
    import asyncio
    prompt = "Count the number of logs with severity INFO and group by ServiceName"
    context = {
        "discovered_patterns": "ServiceName: Accounting, Ad; SeverityText: INFO, WARN"
    }
    
    result = asyncio.run(getquery(prompt, context))
    print("Query Result:", json.dumps(result, indent=2))
