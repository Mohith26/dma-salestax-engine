"""Small FastAPI wrapper around the determination engine."""
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .dataset import load
from .engine import DeterminationError, determine_invoice

app = FastAPI(title="TaxGrid", version="1.0")


class Line(BaseModel):
    line_id: Optional[str] = None
    category: str
    unit_price_cents: int = Field(ge=0)
    quantity: int = Field(ge=1)


class Invoice(BaseModel):
    invoice_id: Optional[str] = None
    date: str
    ship_from: str
    ship_to: str
    transaction_type: str = "sale"
    exemption_certificate: Optional[str] = None
    lines: List[Line]


@app.post("/determine")
def determine(invoice: Invoice):
    try:
        return determine_invoice(invoice.model_dump(), load())
    except (DeterminationError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.get("/health")
def health():
    ds = load()
    return {"status": "ok", "jurisdictions": len(ds.jurisdictions)}
