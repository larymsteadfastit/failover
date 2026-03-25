import json
import sqlite3
from datetime import datetime, timedelta
import os

def handler(request):
    method = request['method']
    path = request['path']
    
    conn = sqlite3.connect('/tmp/failover.db')
    conn.execute("CREATE TABLE IF NOT EXISTS data (ticketId TEXT PRIMARY KEY, callSid TEXT, data TEXT, expires REAL)")
    
    if method == 'POST' and path == '/':
        body = json.loads(request['body'])
        ticket_id = body['ticketId']
        call_sid = body['callSid']
        expires = (datetime.utcnow() + timedelta(hours=24)).timestamp()
        conn.execute("INSERT OR REPLACE INTO data VALUES (?, ?, ?, ?)", 
                     (ticket_id, call_sid, json.dumps(body.get('data', {})), expires))
        conn.commit()
        return {'statusCode': 200, 'body': json.dumps({'status': 'stored'})}
    
    elif method == 'GET' and path.startswith('/'):
        ticket_id = path[1:]
        cur = conn.execute("SELECT data FROM data WHERE ticketId=? AND expires > ?", 
                           (ticket_id, datetime.utcnow().timestamp()))
        row = cur.fetchone()
        if row:
            conn.execute("DELETE FROM data WHERE ticketId=?", (ticket_id,))
            conn.commit()
            return {'statusCode': 200, 'body': row[0]}
        return {'statusCode': 404, 'body': json.dumps({'error': 'not found'})}
    
    conn.close()
    return {'statusCode': 404}
