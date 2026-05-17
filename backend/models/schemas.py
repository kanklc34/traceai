from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime

class SpanCreate(BaseModel):
    span_id: str
    operation: str
    status: str
    latency_ms: float
    span_metadata: Optional[Dict] = None

class TraceIngest(BaseModel):
    trace_id: str
    service: str
    timestamp: datetime
    spans: List[SpanCreate]

class TraceResponse(BaseModel):
    trace_id: str
    status: str
    message: str
