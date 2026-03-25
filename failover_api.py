import json
import os
import sqlite3
from datetime import datetime, timedelta
from twilio.request_validator import RequestValidator
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from typing import Dict

app = FastAPI()

class FailoverData(BaseModel):
    ticketId: str
    callSid: str
    data: Dict

DB_PATH = "/tmp/failover.db"  # Vercel writable tmp
validator = RequestValidator(os.environ.get('TWILIO_AUTH_TOKEN', ''))

@app.post("/")
async def store_data(data: FailoverData, request: Request):
    # Twilio validation
    if os.environ.get('TWILIO_AUTH_TOKEN'):
        twilio_sig = request.headers.get('x-twilio-signature', '')
        if not validator.validate(request.url.path, request.query_params, twilio_sig):
            raise HTTPException(403, "Invalid signature")
    
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS data (ticketId TEXT PRIMARY KEY, callSid TEXT, data TEXT, expires REAL)")
    expires = (datetime.utcnow() + timedelta(hours=24)).timestamp()
    conn.execute("INSERT OR REPLACE INTO data VALUES (?, ?, ?, ?)", 
                 (data.ticketId, data.callSid, json.dumps(data.dict()['data']), expires))
    conn.commit()
    conn.close()
    return {"status": "stored"}

@app.get("/{ticket_id}")
async def get_data(ticket_id: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("SELECT data FROM data WHERE ticketId=? AND expires > ?", 
                       (ticket_id, datetime.utcnow().timestamp()))
    row = cur.fetchone()
    if row:
        conn.execute("DELETE FROM data WHERE ticketId=?", (ticket_id,))
        conn.commit()
        return json.loads(row[0])
    conn.close()
    raise HTTPException(404, "not found")
