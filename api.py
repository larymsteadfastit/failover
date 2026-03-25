import json
import sqlite3
from datetime import datetime, timedelta

def handler(request):
    path = request.get('path', '')
    method = request.get('method', '')
    
    if method == 'POST' and path == '/':
        body = json.loads(request['body'])
        ticket_id = body['ticketId']
        data_str = json.dumps(body.get('data', {}))
        expires = datetime.utcnow().timestamp() + 86400  # 24h
        
        conn = sqlite3.connect('/tmp/failover.db')
        conn.execute('CREATE TABLE IF NOT EXISTS data (ticketId TEXT PRIMARY KEY, data TEXT, expires REAL)')
        conn.execute('INSERT OR REPLACE INTO data VALUES (?, ?, ?)', (ticket_id, data_str, expires))
        conn.commit()
        conn.close()
        return {'statusCode': 200, 'headers': {'Content-Type': 'application/json'}, 'body': json.dumps({'status': 'stored'})}
    
    if method == 'GET' and path.startswith('/'):
        ticket_id = path[1:]
        conn = sqlite3.connect('/tmp/failover.db')
        cur = conn.execute('SELECT data FROM data WHERE ticketId=? AND expires > ?', (ticket_id, datetime.utcnow().timestamp()))
        row = cur.fetchone()
        if row:
            conn.execute('DELETE FROM data WHERE ticketId=?', (ticket_id,))
            conn.commit()
            return {'statusCode': 200, 'headers': {'Content-Type': 'application/json'}, 'body': row[0]}
        conn.close()
        return {'statusCode': 404, 'body': json.dumps({'error': 'not found'})}
    
    return {'statusCode': 404, 'body': 'Method not allowed'}

# Vercel auto-calls handler
