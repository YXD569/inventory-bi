import random
from datetime import datetime, timedelta

from app.database import SessionLocal, engine, Base
from app import models

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

db = SessionLocal()

# 供应商
s1 = models.Supplier(name="华东办公用品", contact="张经理", expected_days=3)
s2 = models.Supplier(name="深圳数码供应链", contact="李经理", expected_days=5)
db.add_all([s1, s2])
db.commit()

# 商品
products = [
    models.Product(name="A4复印纸", sku="P-A4", category="办公耗材", unit="包", safety_stock=20, price=22.0),
    models.Product(name="中性笔", sku="P-PEN", category="办公耗材", unit="盒", safety_stock=50, price=3.5),
    models.Product(name="无线鼠标", sku="P-MOUSE", category="数码配件", unit="个", safety_stock=15, price=59.0),
    models.Product(name="机械键盘", sku="P-KB", category="数码配件", unit="个", safety_stock=10, price=199.0),
    models.Product(name="显示器", sku="P-MON", category="数码设备", unit="台", safety_stock=8, price=899.0),
    models.Product(name="笔记本", sku="P-NB", category="文具", unit="本", safety_stock=30, price=8.0),
]
db.add_all(products)
db.commit()

p = {x.sku: x for x in products}

# 仓库
w1 = models.Warehouse(name="西安主仓", location="西安")
w2 = models.Warehouse(name="北京分仓", location="北京")
db.add_all([w1, w2])
db.commit()

# 当前库存
inventory_rows = [
    (w1, p["P-A4"], 50),
    (w1, p["P-PEN"], 80),
    (w1, p["P-MOUSE"], 25),
    (w1, p["P-KB"], 5),
    (w1, p["P-MON"], 12),
    (w1, p["P-NB"], 60),
    (w2, p["P-A4"], 10),
    (w2, p["P-PEN"], 30),
    (w2, p["P-MOUSE"], 8),
    (w2, p["P-KB"], 2),
    (w2, p["P-MON"], 3),
    (w2, p["P-NB"], 20),
]
for wh, product, qty in inventory_rows:
    db.add(models.Inventory(warehouse_id=wh.id, product_id=product.id, quantity=qty))
db.commit()

# 历史销售出库记录，用于看板
random.seed(42)
for _ in range(30):
    product = random.choice([p["P-A4"], p["P-PEN"], p["P-NB"]])
    wh = random.choice([w1, w2])
    qty = random.randint(1, 5)
    days_ago = random.randint(1, 20)
    db.add(
        models.StockMovement(
            warehouse_id=wh.id,
            product_id=product.id,
            movement_type="OUT",
            quantity=qty,
            ref_type="SEED",
            created_at=datetime.utcnow() - timedelta(days=days_ago),
            note="示例销售出库",
        )
    )
db.commit()

now = datetime.utcnow()

# 已入库采购单：准时
po1 = models.PurchaseOrder(
    supplier_id=s1.id,
    warehouse_id=w1.id,
    status="RECEIVED",
    total_amount=100 * 18.0 + 200 * 2.5,
    created_at=now - timedelta(days=10),
    expected_date=now - timedelta(days=7),
    received_at=now - timedelta(days=8),
    remark="示例：准时到货采购单",
)
po1.items.append(models.PurchaseOrderItem(product_id=p["P-A4"].id, quantity=100, unit_price=18.0))
po1.items.append(models.PurchaseOrderItem(product_id=p["P-PEN"].id, quantity=200, unit_price=2.5))
po1.approvals.append(models.ApprovalRecord(action="APPROVED", created_at=now - timedelta(days=9)))
po1.approvals.append(models.ApprovalRecord(action="RECEIVED", created_at=now - timedelta(days=8)))
db.add(po1)

# 已入库采购单：迟到
po2 = models.PurchaseOrder(
    supplier_id=s2.id,
    warehouse_id=w2.id,
    status="RECEIVED",
    total_amount=30 * 45.0 + 10 * 120.0,
    created_at=now - timedelta(days=12),
    expected_date=now - timedelta(days=7),
    received_at=now - timedelta(days=5),
    remark="示例：迟到采购单",
)
po2.items.append(models.PurchaseOrderItem(product_id=p["P-MOUSE"].id, quantity=30, unit_price=45.0))
po2.items.append(models.PurchaseOrderItem(product_id=p["P-KB"].id, quantity=10, unit_price=120.0))
po2.approvals.append(models.ApprovalRecord(action="APPROVED", created_at=now - timedelta(days=11)))
po2.approvals.append(models.ApprovalRecord(action="RECEIVED", created_at=now - timedelta(days=5)))
db.add(po2)

# 待审批采购单
po3 = models.PurchaseOrder(
    supplier_id=s1.id,
    warehouse_id=w1.id,
    status="PENDING_APPROVAL",
    total_amount=100 * 6.5,
    created_at=now - timedelta(days=1),
    expected_date=now + timedelta(days=2),
    remark="示例：待审批采购单",
)
po3.items.append(models.PurchaseOrderItem(product_id=p["P-NB"].id, quantity=100, unit_price=6.5))
db.add(po3)

# 已审批待入库采购单
po4 = models.PurchaseOrder(
    supplier_id=s2.id,
    warehouse_id=w1.id,
    status="APPROVED",
    total_amount=5 * 850.0,
    created_at=now - timedelta(days=2),
    expected_date=now + timedelta(days=3),
    remark="示例：已审批待入库",
)
po4.items.append(models.PurchaseOrderItem(product_id=p["P-MON"].id, quantity=5, unit_price=850.0))
po4.approvals.append(models.ApprovalRecord(action="APPROVED", created_at=now - timedelta(days=1)))
db.add(po4)

db.commit()
db.close()

print("示例数据初始化完成。")
print("运行：uvicorn app.main:app --reload")
print("打开：http://127.0.0.1:8000/")