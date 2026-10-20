from pydantic import BaseModel
from typing import List, Optional


class PurchaseItemCreate(BaseModel):
    product_id: int
    quantity: int
    unit_price: float


class PurchaseOrderCreate(BaseModel):
    supplier_id: int
    warehouse_id: int
    items: List[PurchaseItemCreate]
    remark: Optional[str] = ""


class SaleOutCreate(BaseModel):
    warehouse_id: int
    product_id: int
    quantity: int
    note: Optional[str] = ""