from sqlalchemy import (
    Column, Integer, String, Float, DateTime,
    ForeignKey, Text, UniqueConstraint
)
from sqlalchemy.orm import relationship
from datetime import datetime

from .database import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    contact = Column(String(100), default="")
    expected_days = Column(Integer, default=3)


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    sku = Column(String(50), unique=True, nullable=False)
    category = Column(String(50), default="")
    unit = Column(String(20), default="个")
    safety_stock = Column(Integer, default=10)
    price = Column(Float, default=0.0)


class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    location = Column(String(100), default="")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    status = Column(String(30), default="PENDING_APPROVAL")
    total_amount = Column(Float, default=0.0)
    expected_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    received_at = Column(DateTime, nullable=True)
    remark = Column(Text, default="")

    supplier = relationship("Supplier")
    warehouse = relationship("Warehouse")
    items = relationship(
        "PurchaseOrderItem",
        back_populates="order",
        cascade="all, delete-orphan"
    )
    approvals = relationship(
        "ApprovalRecord",
        back_populates="order",
        cascade="all, delete-orphan"
    )


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)

    order = relationship("PurchaseOrder", back_populates="items")
    product = relationship("Product")


class ApprovalRecord(Base):
    __tablename__ = "approval_records"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False)
    action = Column(String(30), nullable=False)
    comment = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    order = relationship("PurchaseOrder", back_populates="approvals")


class Inventory(Base):
    __tablename__ = "inventory"
    __table_args__ = (
        UniqueConstraint("warehouse_id", "product_id", name="uq_inventory_wh_product"),
    )

    id = Column(Integer, primary_key=True, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=0)

    warehouse = relationship("Warehouse")
    product = relationship("Product")


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    movement_type = Column(String(10), nullable=False)  # IN / OUT
    quantity = Column(Integer, nullable=False)
    ref_type = Column(String(30), default="")
    ref_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    note = Column(Text, default="")