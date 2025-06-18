

'''
def safe_json_dumps(obj):
    return json.dumps(obj, allow_nan=False)


def promptEmbedding(prompt):
    print(prompt)
    embedding = model.encode([prompt], normalize_embeddings=True)
    return embedding[0].astype('float32')



def getquery(prompt):
    user_prompt = json.dumps(prompt)
    system_prompt = """
    You are a log retrieval AI agent. You will be given a user query.

    Your job is to generate a QueryPlan JSON object that can be used to search a CSV file econtaining log data.

    The CSV has the following columns:

    'timestamp_full', 'timestamp_simple', 'unknown1', 'unknown2', 'unknown3', 
    'SeverityText', 'unknown4', 'ServiceName', 'message', 'schema_url', 'metadata_json', 
    'unknown5', 'class_name', 'unknown6', 'unknown7', 'order_result_json'

    Your QueryPlan should have this format:
    
    timestamp format for the logs is written as: "2025-06-08 10:37:37.043446300"
    
    if no start or end needed, just use null

    {
    "filters": {
        "timestamp_full_range": { "start": , "end": },   
        }
    },
    "semantic_query": string    // A semantic text string to be used for vector search which embeds the SeverityText + ServiceName + message + process_runtime_name 
    }

    SeverityText can be:
    -WARN
    -INFO
    
    ServiceName can be:
    -Accounting
    -Ad
    
    Message can be:
    
    -High cpu-load
    -Targeted ad request received
    -Non-targeted ad request received
    -Order Details 
    
    Process_runtime_name can be:
    -OpenJDK Runtime Environment
    -.NET
    
    Instructions:
    - All logs are from June 8th, 2025.
    - Based on the options and the structure of how the embeddings are made, create the best semantic search prompt based on the user prompt if needed.
    - If the user query mentions a time window (e.g. "yesterday", "last 2 hours"), extract it as timestamp_full_range.
    - The semantic_query shoul only be for natural language related queries, leave it empty otherwise.

    Output ONLY the JSON object. Do not include explanations.
    """






    response = client.chat.completions.create(model="gpt-4o",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ],
    temperature=0)

    response_text = response.choices[0].message.content
    try:
        response_text = response_text.strip()
        print("response",response_text)
        if response_text.startswith("```json"):
            response_text = response_text[len("```json"):].strip()

        if response_text.endswith("```"):
            response_text = response_text[:-3].strip()

        response_json = json.loads(response_text)
    except json.JSONDecodeError as e:
        print("not valid json response")
        response_json = {}


    print(response_text)
    filters = response_json.get("filters", {})
    semantic_query = response_json.get("semantic_query", "")

    print("results", filters, semantic_query)


    return filters, semantic_query
'''
