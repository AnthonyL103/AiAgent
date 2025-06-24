import pandas as pd
from clickhouse_driver import Client
from datetime import datetime

client = Client(host='localhost', port=9000, user='AgentDemo', password='ILoveAgents45867760')
print(client.execute('SELECT 1'))

column_names = [
    'timestamp_full', 'timestamp_simple', 'TraceId', 'SpanId', 'TraceFlags',
    'SeverityText', 'SeverityNumber', 'ServiceName', 'Message', 'ResourceSchemaUrl',
    'ResourceAttributes', 'ScopeSchemaUrl', 'ScopeName', 'ScopeVersion',
    'ScopeAttributes', 'LogAttributes'
]

df= pd.read_csv('testlog.csv', names=column_names)

insert_query = """
INSERT INTO logs (
    timestamp_full, timestamp_simple, TraceId, SpanId, TraceFlags,
    SeverityText, ServiceName, Message, ResourceSchemaUrl,
    ResourceAttributes, ScopeSchemaUrl, ScopeName, ScopeVersion,
    ScopeAttributes, LogAttributes
) VALUES
"""

rows = []
for row in df.itertuples(index=False):
    ts = row.timestamp_full
    if "." in ts:
        main, frac = ts.split(".")
        ts = f"{main}.{frac[:6]}"  
    timestamp_full_dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S.%f")
    rows.append((
        timestamp_full_dt or "", str(row.timestamp_simple) or "", str(row.TraceId) or "", str(row.SpanId) or "", str(row.TraceFlags) or "",
        str(row.SeverityText) or "", str(row.ServiceName) or "", str(row.Message) or "", row.ResourceSchemaUrl or "",
        str(row.ResourceAttributes) or "", str(row.ScopeSchemaUrl) or "", str(row.ScopeName) or "", str(row.ScopeVersion) or "",
        str(row.ScopeAttributes) or "", str(row.LogAttributes) or ""
    ))
    

client.execute(insert_query, rows)
