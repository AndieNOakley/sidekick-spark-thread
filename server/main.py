from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import secrets, json
from sqlalchemy.orm import Session
from .database import init_db, get_db
from .models import Device, Message

app = FastAPI(title="Sidekick Spark Thread API", version="0.1")

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
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing token")
    token = authorization.split(" ", 1)[1]
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
