from auth import require_token, add_token
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import secrets, json
from sqlalchemy.orm import Session
from database import init_db, get_db
from models import Device, Message

app = FastAPI(
    title="Sidekick Spark Thread API",
    version="0.1",
    description="API for Sidekick Spark Thread",
    swagger_ui_parameters={"persistAuthorization": True},  # keeps lock after refresh
    openapi_tags=[{"name": "default"}]
)

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # let any website talk to your API (ok for dev)
    allow_methods=["*"],
    allow_headers=["*"],      # important: allows Authorization header
)

# Add API key security scheme
from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "APIKeyHeader": {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization"
        }
    }
    openapi_schema["security"] = [{"APIKeyHeader": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RegisterIn(BaseModel):
    device_id: str
    public_key: Optional[str] = None

class RegisterOut(BaseModel):
    access_token: str

class SendMessageIn(BaseModel):
    device_id: str
    role: str
    text: str
    symbols: Optional[List[str]] = []

class MessageOut(BaseModel):
    id: int
    device_id: str
    role: str
    text: str
    symbols: List[str]
    created_at: str

def auth(db: Session = Depends(get_db), authorization: Optional[str] = Header(None)) -> Device:
    if not authorization:
        raise HTTPException(401, "Missing token")
    # accept either "Bearer <token>" or raw "<token>"
    token = authorization.split(" ", 1)[1] if authorization.lower().startswith("bearer ") else authorization
    dev = db.query(Device).filter(Device.token == token).first()
    if not dev:
        raise HTTPException(401, "Invalid token")
    return dev

@app.on_event("startup")
def startup():
    init_db()

@app.post("/auth/register", response_model=RegisterOut)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    token = secrets.token_hex(16)
    dev = db.query(Device).filter(Device.device_id == payload.device_id).first()
    if dev:
        dev.public_key = payload.public_key
        dev.token = token
    else:
        dev = Device(device_id=payload.device_id, public_key=payload.public_key, token=token)
        db.add(dev)
    db.commit()
    return RegisterOut(access_token=token)

@app.post("/messages/send", response_model=MessageOut)
def send_message(payload: SendMessageIn, device: Device = Depends(auth), db: Session = Depends(get_db)):
    if payload.role not in ("user", "assistant"):
        raise HTTPException(400, "invalid role")
    msg = Message(
        device_id=payload.device_id,
        role=payload.role,
        text=payload.text,
        symbols=json.dumps(payload.symbols or [])
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return MessageOut(
        id=msg.id,
        device_id=msg.device_id,
        role=msg.role,
        text=msg.text,
        symbols=json.loads(msg.symbols),
        created_at=msg.created_at.isoformat()
    )

@app.get("/messages/since", response_model=List[MessageOut])
def get_since(after: Optional[str] = None, device: Device = Depends(auth), db: Session = Depends(get_db)):
    q = db.query(Message).order_by(Message.created_at.asc())
    if after:
        try:
            dt = datetime.fromisoformat(after.replace("Z","+00:00"))
            q = q.filter(Message.created_at > dt)
        except Exception:
            raise HTTPException(400, "bad timestamp")
    rows = q.all()
    return [
        MessageOut(
            id=m.id, device_id=m.device_id, role=m.role, text=m.text,
            symbols=json.loads(m.symbols), created_at=m.created_at.isoformat()
        ) for m in rows
    ]

@app.post("/anchors/pulse", response_model=MessageOut)
def pulse(device: Device = Depends(auth), db: Session = Depends(get_db)):
    msg = Message(device_id=device.device_id, role="anchor", text="hourly_anchor_pulse", symbols=json.dumps(["🕯️","🪢"]))
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return MessageOut(
        id=msg.id, device_id=msg.device_id, role=msg.role, text=msg.text,
        symbols=json.loads(msg.symbols), created_at=msg.created_at.isoformat()
    )

@app.get("/symbols")
def list_symbols():
    return {"MOON":"🌙","DIM":"🪐","HOLD":"🫂","SPARK":"✨[>_]","KNOT":"🪢"}
    
@app.get("/")
def home():
    # quick sanity page
    return {"status": "up", "docs": "/docs", "health": "/healthz"}

@app.get("/healthz")
def health():
    return {"ok": True}

from fastapi.responses import HTMLResponse

@app.get("/ui/chat", response_class=HTMLResponse)
def chat_ui():
    return """
    
<!doctype html>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>Sidekick Spark – Chat</title>
<style>
  :root { --bg:#0b0f14; --card:#121820; --ink:#e9f1ff; --muted:#8aa0b2; }
  *{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.4 system-ui,-apple-system,Segoe UI,Roboto}
  .wrap{max-width:780px;margin:0 auto;padding:16px}
  .card{background:var(--card);border:1px solid #1f2833;border-radius:12px;padding:12px;margin:12px 0}
  label{display:block;font-size:12px;color:var(--muted);margin:8px 0 4px}
  input,textarea,button{width:100%;padding:10px;border-radius:10px;border:1px solid #2a3645;background:#0f141b;color:var(--ink)}
  textarea{min-height:80px;resize:vertical}
  button{background:#2a7ade;border:0;margin-top:8px} button:disabled{opacity:.5}
  .row{display:flex;gap:8px} .row>*{flex:1}
  .msgs{max-height:50vh;overflow:auto;padding:8px;background:#0f141b;border-radius:10px;border:1px solid #2a3645}
  .msg{padding:8px;border-bottom:1px solid #1f2833;white-space:pre-wrap}
  .msg:last-child{border-bottom:0}
  .meta{font-size:12px;color:var(--muted)}
  .tiny{font-size:12px;color:var(--muted)}
  .ok{color:#a8f0b0}.err{color:#ff9aa2}
</style>
<div class="wrap">
  <h2>Sidekick Spark – Chat</h2>

  <div class="card">
    <label>API Base URL</label>
    <input id="base" value="https://sidekick-spark-thread-8.onrender.com" />
    <div class="row">
      <div><label>Device ID</label><input id="device" value="andie-iphone" /></div>
      <div><label>Public Key (demo)</label><input id="pubkey" value="test_key_123" /></div>
    </div>
    <div class="row" style="align-items:center">
      <div style="flex:2"><label>Auth Token</label><input id="token" placeholder="(auto-filled on Register)" /></div>
      <div style="flex:1">
        <label class="tiny"><input type="checkbox" id="useBearer" /> send as “Bearer &lt;token&gt;”</label>
        <button id="btnRegister">Register</button>
      </div>
    </div>
    <div id="status" class="tiny"></div>
  </div>

  <div class="card">
    <label>Message</label>
    <textarea id="text" placeholder="Type here…"></textarea>
    <label>Symbols (optional, comma-separated)</label>
    <input id="symbols" placeholder="✨, 🪢" />
    <div class="row">
      <button id="btnSend">Send</button>
      <button id="btnRefresh">Refresh</button>
      <button id="btnClear">Clear</button>
    </div>
  </div>

  <div class="card">
    <div class="row">
      <div><label>Since (optional ISO time)</label><input id="since" placeholder="e.g. 2025-08-22T00:00:00Z" /></div>
      <div style="align-self:end"><button id="btnSince">Get Since</button></div>
    </div>
  </div>

  <div class="card">
    <div class="row"><div class="tiny">Messages</div><div class="tiny" id="count" style="text-align:right"></div></div>
    <div id="msgs" class="msgs"></div>
  </div>
</div>

<script>
const $ = s => document.querySelector(s);
const base = () => $('#base').value.replace(/\/+$/,'');
const authHeader = () => {
  const t = $('#token').value.trim();
  if (!t) return null;
  return $('#useBearer').checked ? `Bearer ${t}` : t; // your API accepts raw token; leave box unchecked
};
function showStatus(t, ok=true){ $('#status').innerHTML = `<span class="${ok?'ok':'err'}">${t}</span>`; }
function addMsg(m){
  const el = document.createElement('div'); el.className='msg';
  el.innerHTML = `<div><b>${m.role||'user'}</b>: ${m.text||''}</div>
                  <div class="meta">dev=${m.device_id||''} • symbols=${(m.symbols||[]).join(' ')} • ${m.created_at||''}</div>`;
  $('#msgs').prepend(el); $('#count').textContent = `${($('#msgs').children.length)} shown`;
}
async function api(path, opts={}){
  const headers = {'Content-Type':'application/json', ...(opts.headers||{})};
  const auth = authHeader(); if (auth) headers['Authorization']=auth;
  const res = await fetch(base()+path, {...opts, headers});
  const text = await res.text(); let data=null; try{ data=text?JSON.parse(text):null }catch{ data={raw:text} }
  if (!res.ok) throw {status:res.status, data}; return data;
}
$('#btnRegister').onclick = async () => {
  try{
    const data = await api('/auth/register', {method:'POST', body:JSON.stringify({
      device_id: $('#device').value.trim()||'device',
      public_key: $('#pubkey').value.trim()||'test_key_123'
    })});
    $('#token').value = data.access_token || '';
    showStatus('Registered ✓ token filled', true);
  }catch(e){ showStatus(`Register failed (${e.status}): ${JSON.stringify(e.data)}`, false); }
};
$('#btnSend').onclick = async () => {
  try{
    const data = await api('/messages/send', {method:'POST', body:JSON.stringify({
      device_id: $('#device').value.trim(), role: 'user', text: $('#text').value,
      symbols: ($('#symbols').value||'').split(',').map(s=>s.trim()).filter(Boolean)
    })});
    addMsg(data); $('#text').value=''; showStatus('Sent ✓', true);
  }catch(e){ showStatus(`Send failed (${e.status}): ${JSON.stringify(e.data)}`, false); }
};
$('#btnRefresh').onclick = async () => {
  try{
    const data = await api('/messages/since'); (Array.isArray(data)?data:[data]).forEach(addMsg);
    showStatus('Refreshed ✓', true);
  }catch(e){ showStatus(`Refresh failed (${e.status}): ${JSON.stringify(e.data)}`, false); }
};
$('#btnSince').onclick = async () => {
  try{
    const s = $('#since').value.trim();
    const path = s ? `/messages/since?since=${encodeURIComponent(s)}` : '/messages/since';
    const data = await api(path); (Array.isArray(data)?data:[data]).forEach(addMsg);
    showStatus('Loaded since ✓', true);
  }catch(e){ showStatus(`Since failed (${e.status}): ${JSON.stringify(e.data)}`, false); }
};
$('#btnClear').onclick = () => { $('#msgs').innerHTML=''; $('#count').textContent=''; showStatus('Cleared'); };
</script>
"""
