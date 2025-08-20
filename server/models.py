from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime

Base = declarative_base()

class Device(Base):
    __tablename__ = "devices"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, unique=True, nullable=False)
    public_key = Column(Text, nullable=True)
    token = Column(String, unique=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, nullable=False)
    role = Column(String, nullable=False)  # 'user' | 'assistant' | 'anchor'
    text = Column(Text, nullable=False)
    symbols = Column(Text, default="[]")   # JSON array string
    created_at = Column(DateTime, default=datetime.utcnow)
