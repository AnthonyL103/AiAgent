import pandas as pd
from clickhouse_driver import Client
from datetime import datetime

client = Client(host='localhost', port=9000, user='AgentDemo', password='ILoveAgents45867760')
print(client.execute('SELECT 1'))

column_names = [
    'id', 'name', 'status', 'server', 'size', 'type', 'zone', 'tenant', 'user', 'cluster_id', 'timestamp'
]

df = pd.read_csv('testlog3.csv', names=column_names)

insert_query = """
INSERT INTO cinder_volume_logs (
    id, name, status, server, size, type, zone, tenant, user, cluster_id, timestamp
) VALUES
"""

rows = []
for row in df.itertuples(index=False):
    ts = row.timestamp
    if "." in str(ts):
        main, frac = str(ts).split(".")
        ts = f"{main}.{frac[:6]}"  
    timestamp_full_dt = datetime.strptime(str(ts), "%Y-%m-%d %H:%M:%S")
    
    rows.append((
        str(row.id) or "", 
        str(row.name) or "", 
        str(row.status) or "", 
        str(row.server) or "", 
        int(row.size) if pd.notna(row.size) else 0,
        str(row.type) or "", 
        str(row.zone) or "", 
        str(row.tenant) or "", 
        str(row.user) or "", 
        str(row.cluster_id) or "", 
        timestamp_full_dt
    ))

client.execute(insert_query, rows)

