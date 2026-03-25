from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
import sqlite3
import json
from datetime import datetime, timedelta
from twilio.request_validator import RequestValidator
import os

# Updated for Vercel deploy

app = FastAPI()
DB_PATH = "failover.db"
validator = RequestValidator(os.environ.get('TWILIO_AUTH_TOKEN', ''))


class FailoverData(BaseModel):
    ticketId: str
    callSid: str
    data: dict


@app.post("/")
async def store_data(data: FailoverData, request: Request):
    # Twilio validation (add headers check)
    if not os.environ.get('TWILIO_AUTH_TOKEN'):
        raise HTTPException(403, "No auth")

    # Store with TTL check
    conn = sqlite3.connect(DB_PATH)
    expires = (datetime.utcnow() + timedelta(hours=24)).timestamp()
    conn.execute("CREATE TABLE IF NOT EXISTS data (ticketId TEXT PRIMARY KEY, callSid TEXT, data TEXT, expires REAL)")
    conn.execute("INSERT OR REPLACE INTO data VALUES (?, ?, ?, ?)",
                 (data.ticketId, data.callSid, json.dumps(data.data), expires))
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
