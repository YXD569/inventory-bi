from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from datetime import datetime, timedelta, time

from . import models, schemas
from .database import Base, engine, get_db

Base.metadata.create_all(bind=engine)
app = FastAPI(title="小微零售进销存与库存分析")

# ---------- 序列化工具 ----------
def order_dict(o: models.PurchaseOrder):
    return {
        "id": o.id, "supplier_id": o.supplier_id, "supplier_name": o.supplier.name if o.supplier else "",
        "warehouse_id": o.warehouse_id, "warehouse_name": o.warehouse.name if o.warehouse else "",
        "status": o.status, "total_amount": round(o.total_amount or 0, 2),
        "expected_date": o.expected_date.isoformat() if o.expected_date else None,
        "created_at": o.created_at.isoformat() if o.created_at else None,
        "received_at": o.received_at.isoformat() if o.received_at else None,
        "remark": o.remark or "",
        "items": [{"product_id": i.product_id, "product_name": i.product.name if i.product else "", "quantity": i.quantity, "unit_price": i.unit_price} for i in o.items],
    }

def load_order(db: Session, order_id: int):
    return db.query(models.PurchaseOrder).options(
        joinedload(models.PurchaseOrder.items).joinedload(models.PurchaseOrderItem.product),
        joinedload(models.PurchaseOrder.supplier), joinedload(models.PurchaseOrder.warehouse)
    ).filter(models.PurchaseOrder.id == order_id).first()

# ---------- 基础数据查询 ----------
@app.get("/api/health")
def health(): return {"status": "ok"}

@app.get("/api/suppliers")
def list_suppliers(db: Session = Depends(get_db)):
    return [{"id": s.id, "name": s.name, "contact": s.contact, "expected_days": s.expected_days} for s in db.query(models.Supplier).all()]

@app.get("/api/products")
def list_products(db: Session = Depends(get_db)):
    return [{"id": p.id, "name": p.name, "sku": p.sku, "category": p.category, "unit": p.unit, "safety_stock": p.safety_stock, "price": p.price} for p in db.query(models.Product).all()]

@app.get("/api/warehouses")
def list_warehouses(db: Session = Depends(get_db)):
    return [{"id": w.id, "name": w.name, "location": w.location} for w in db.query(models.Warehouse).all()]

# ---------- 基础数据增删改 ----------
@app.post("/api/suppliers")
def create_supplier(data: dict, db: Session = Depends(get_db)):
    db.add(models.Supplier(name=data["name"], contact=data.get("contact", ""), expected_days=data.get("expected_days", 3)))
    db.commit(); return {"message": "success"}

@app.put("/api/suppliers/{item_id}")
def update_supplier(item_id: int, data: dict, db: Session = Depends(get_db)):
    item = db.get(models.Supplier, item_id)
    if not item: raise HTTPException(status_code=404, detail="不存在")
    item.name = data.get("name", item.name); item.contact = data.get("contact", item.contact); item.expected_days = data.get("expected_days", item.expected_days)
    db.commit(); return {"message": "success"}

@app.delete("/api/suppliers/{item_id}")
def delete_supplier(item_id: int, db: Session = Depends(get_db)):
    item = db.get(models.Supplier, item_id)
    if item: db.delete(item); db.commit()
    return {"message": "success"}

@app.post("/api/warehouses")
def create_warehouse(data: dict, db: Session = Depends(get_db)):
    db.add(models.Warehouse(name=data["name"], location=data.get("location", "")))
    db.commit(); return {"message": "success"}

@app.put("/api/warehouses/{item_id}")
def update_warehouse(item_id: int, data: dict, db: Session = Depends(get_db)):
    item = db.get(models.Warehouse, item_id)
    if not item: raise HTTPException(status_code=404, detail="不存在")
    item.name = data.get("name", item.name); item.location = data.get("location", item.location)
    db.commit(); return {"message": "success"}

@app.delete("/api/warehouses/{item_id}")
def delete_warehouse(item_id: int, db: Session = Depends(get_db)):
    item = db.get(models.Warehouse, item_id)
    if item: db.delete(item); db.commit()
    return {"message": "success"}

@app.post("/api/products")
def create_product(data: dict, db: Session = Depends(get_db)):
    db.add(models.Product(name=data["name"], sku=data["sku"], category=data.get("category", ""), unit=data.get("unit", "个"), safety_stock=data.get("safety_stock", 10), price=data.get("price", 0.0)))
    db.commit(); return {"message": "success"}

@app.put("/api/products/{item_id}")
def update_product(item_id: int, data: dict, db: Session = Depends(get_db)):
    item = db.get(models.Product, item_id)
    if not item: raise HTTPException(status_code=404, detail="不存在")
    item.name = data.get("name", item.name); item.sku = data.get("sku", item.sku); item.price = data.get("price", item.price); item.safety_stock = data.get("safety_stock", item.safety_stock)
    db.commit(); return {"message": "success"}

@app.delete("/api/products/{item_id}")
def delete_product(item_id: int, db: Session = Depends(get_db)):
    item = db.get(models.Product, item_id)
    if item: db.delete(item); db.commit()
    return {"message": "success"}

# ---------- 采购流程 ----------
@app.get("/api/purchase-orders")
def list_purchase_orders(db: Session = Depends(get_db)):
    orders = db.query(models.PurchaseOrder).options(joinedload(models.PurchaseOrder.items).joinedload(models.PurchaseOrderItem.product), joinedload(models.PurchaseOrder.supplier), joinedload(models.PurchaseOrder.warehouse)).order_by(models.PurchaseOrder.id.desc()).all()
    return [order_dict(o) for o in orders]

@app.post("/api/purchase-orders")
def create_purchase_order(payload: schemas.PurchaseOrderCreate, db: Session = Depends(get_db)):
    supplier = db.get(models.Supplier, payload.supplier_id); warehouse = db.get(models.Warehouse, payload.warehouse_id)
    if not supplier or not warehouse or not payload.items: raise HTTPException(status_code=400, detail="参数错误")
    order = models.PurchaseOrder(supplier_id=payload.supplier_id, warehouse_id=payload.warehouse_id, status="PENDING_APPROVAL", expected_date=datetime.utcnow() + timedelta(days=supplier.expected_days), remark=payload.remark or "")
    total = 0.0
    for item in payload.items:
        product = db.get(models.Product, item.product_id)
        total += item.quantity * item.unit_price
        order.items.append(models.PurchaseOrderItem(product_id=item.product_id, quantity=item.quantity, unit_price=item.unit_price))
    order.total_amount = total
    db.add(order); db.commit()
    return order_dict(load_order(db, order.id))

@app.post("/api/purchase-orders/{order_id}/approve")
def approve_order(order_id: int, db: Session = Depends(get_db)):
    order = db.get(models.PurchaseOrder, order_id)
    if not order or order.status != "PENDING_APPROVAL": raise HTTPException(status_code=400, detail="不可审批")
    order.status = "APPROVED"; order.approvals.append(models.ApprovalRecord(action="APPROVED", comment="审批通过")); db.commit()
    return order_dict(load_order(db, order_id))

@app.post("/api/purchase-orders/{order_id}/reject")
def reject_order(order_id: int, db: Session = Depends(get_db)):
    order = db.get(models.PurchaseOrder, order_id)
    if not order or order.status != "PENDING_APPROVAL": raise HTTPException(status_code=400, detail="不可驳回")
    order.status = "REJECTED"; order.approvals.append(models.ApprovalRecord(action="REJECTED", comment="审批驳回")); db.commit()
    return order_dict(load_order(db, order_id))

@app.post("/api/purchase-orders/{order_id}/receive")
def receive_order(order_id: int, db: Session = Depends(get_db)):
    order = db.get(models.PurchaseOrder, order_id)
    if not order or order.status != "APPROVED": raise HTTPException(status_code=400, detail="不可入库")
    for item in order.items:
        inv = db.query(models.Inventory).filter(models.Inventory.warehouse_id == order.warehouse_id, models.Inventory.product_id == item.product_id).first()
        if not inv: inv = models.Inventory(warehouse_id=order.warehouse_id, product_id=item.product_id, quantity=0); db.add(inv)
        inv.quantity += item.quantity
        db.add(models.StockMovement(warehouse_id=order.warehouse_id, product_id=item.product_id, movement_type="IN", quantity=item.quantity, ref_type="PURCHASE_ORDER", ref_id=order.id, note=f"采购入库：{order.id}"))
    order.status = "RECEIVED"; order.received_at = datetime.utcnow(); order.approvals.append(models.ApprovalRecord(action="RECEIVED", comment="确认入库")); db.commit()
    return order_dict(load_order(db, order_id))

# ---------- 库存与销售 ----------
@app.get("/api/inventory")
def list_inventory(db: Session = Depends(get_db)):
    return [{"id": inv.id, "warehouse_id": inv.warehouse_id, "warehouse_name": inv.warehouse.name if inv.warehouse else "", "product_id": inv.product_id, "product_name": inv.product.name if inv.product else "", "quantity": inv.quantity, "safety_stock": inv.product.safety_stock if inv.product else 0, "stock_value": round(inv.quantity * (inv.product.price if inv.product else 0), 2)} for inv in db.query(models.Inventory).all()]

@app.post("/api/sales-out")
def sales_out(payload: schemas.SaleOutCreate, db: Session = Depends(get_db)):
    inv = db.query(models.Inventory).filter(models.Inventory.warehouse_id == payload.warehouse_id, models.Inventory.product_id == payload.product_id).first()
    if not inv or inv.quantity < payload.quantity: raise HTTPException(status_code=400, detail="库存不足")
    inv.quantity -= payload.quantity
    db.add(models.StockMovement(warehouse_id=payload.warehouse_id, product_id=payload.product_id, movement_type="OUT", quantity=payload.quantity, ref_type="SALES_OUT", note=payload.note or "销售出库")); db.commit()
    return {"message": "成功"}

# ---------- 数据看板 ----------
@app.get("/api/dashboard/summary")
def dashboard_summary(db: Session = Depends(get_db)):
    inventory = db.query(models.Inventory).all()
    total_qty = sum(i.quantity for i in inventory)
    total_value = sum(i.quantity * (i.product.price if i.product else 0) for i in inventory)
    low_stock_count = len([i for i in inventory if i.product and i.quantity < i.product.safety_stock])
    pending_count = db.query(models.PurchaseOrder).filter(models.PurchaseOrder.status == "PENDING_APPROVAL").count()
    cutoff = datetime.utcnow() - timedelta(days=30)
    outbound_30d = db.query(func.coalesce(func.sum(models.StockMovement.quantity), 0)).filter(models.StockMovement.movement_type == "OUT", models.StockMovement.created_at >= cutoff).scalar() or 0
    return {"total_qty": total_qty, "total_value": round(total_value, 2), "low_stock_count": low_stock_count, "pending_approval_count": pending_count, "outbound_30d": int(outbound_30d), "turnover_rate": round(float(outbound_30d) / max(total_qty, 1), 2)}

@app.get("/api/dashboard/slow-moving")
def dashboard_slow_moving(db: Session = Depends(get_db)):
    cutoff = datetime.utcnow() - timedelta(days=30); result = []
    for inv in db.query(models.Inventory).all():
        if inv.quantity <= 0: continue
        out_qty = db.query(func.coalesce(func.sum(models.StockMovement.quantity), 0)).filter(models.StockMovement.warehouse_id == inv.warehouse_id, models.StockMovement.product_id == inv.product_id, models.StockMovement.movement_type == "OUT", models.StockMovement.created_at >= cutoff).scalar() or 0
        if out_qty == 0: result.append({"warehouse_name": inv.warehouse.name if inv.warehouse else "", "product_name": inv.product.name if inv.product else "", "quantity": inv.quantity, "stock_value": round(inv.quantity * (inv.product.price if inv.product else 0), 2)})
    return result

@app.get("/api/dashboard/low-stock")
def dashboard_low_stock(db: Session = Depends(get_db)):
    return [{"warehouse_name": inv.warehouse.name if inv.warehouse else "", "product_name": inv.product.name, "quantity": inv.quantity, "safety_stock": inv.product.safety_stock, "gap": inv.product.safety_stock - inv.quantity} for inv in db.query(models.Inventory).all() if inv.product and inv.quantity < inv.product.safety_stock]

@app.get("/api/dashboard/supplier-timeliness")
def dashboard_supplier_timeliness(db: Session = Depends(get_db)):
    orders = db.query(models.PurchaseOrder).options(joinedload(models.PurchaseOrder.supplier)).filter(models.PurchaseOrder.status == "RECEIVED").all()
    agg = {}
    for o in orders:
        name = o.supplier.name if o.supplier else "未知"
        if name not in agg: agg[name] = {"supplier_name": name, "total": 0, "on_time": 0}
        agg[name]["total"] += 1
        if o.received_at and o.expected_date and o.received_at <= o.expected_date: agg[name]["on_time"] += 1
    return [{"supplier_name": v["supplier_name"], "total": v["total"], "on_time": v["on_time"], "rate": round(v["on_time"] / v["total"] * 100, 1) if v["total"] else 0} for v in agg.values()]

@app.get("/api/dashboard/trend")
def dashboard_trend(db: Session = Depends(get_db)):
    result = []
    for i in range(6, -1, -1):
        day = (datetime.utcnow() - timedelta(days=i)).date(); start = datetime.combine(day, time.min); end = start + timedelta(days=1)
        qty = db.query(func.coalesce(func.sum(models.StockMovement.quantity), 0)).filter(models.StockMovement.movement_type == "OUT", models.StockMovement.created_at >= start, models.StockMovement.created_at < end).scalar() or 0
        result.append({"date": day.strftime("%m-%d"), "quantity": int(qty)})
    return result

app.mount("/", StaticFiles(directory="static", html=True), name="static")