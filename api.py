import json
import sqlite3
from datetime import datetime, timedelta
import os

app = {}  # Dummy for auto-detect

def handler(request):
    if request['method'] == 'POST':
        body = json.loads(request['body'])
        ticket_id = body['ticketId']
        conn = sqlite3.connect('/tmp/data.db')
        conn.execute('CREATE TABLE IF NOT EXISTS failover (ticketId TEXT PRIMARY KEY, data TEXT, expires REAL)')
        expires = (datetime.utcnow() + timedelta(hours=24)).timestamp()
        conn.execute('INSERT OR REPLACE INTO failover VALUES (?, ?, ?)', 
                     (ticket_id, json.dumps(body['data']), expires))
        conn.commit()
        conn.close()
        return {'statusCode': 200, 'body': json.dumps({'status': 'stored'})}
    
    if request['method'] == 'GET':
        ticket_id = request['path'][1:]
        conn = sqlite3.connect('/tmp/data.db')
        cur = conn.execute('SELECT data FROM failover WHERE ticketId=? AND expires > ?', 
                           (ticket_id, datetime.utcnow().timestamp()))
        row = cur.fetchone()
        if row:
            conn.execute('DELETE FROM failover WHERE ticket_id=?', (ticket_id,))
            conn.commit()
            return {'statusCode': 200, 'body': row[0]}
        conn.close()
        return {'statusCode': 404, 'body': 'Not found'}
    
    return {'statusCode': 404}
