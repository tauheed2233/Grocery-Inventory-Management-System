"""
Database Models for Grocery Inventory System
Defines Product, Supplier, StockTransaction, and RestockOrder models
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, Enum as SQLEnum
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.sql import func
import enum

Base = declarative_base()


class Category(enum.Enum):
    """Product categories for a grocery store"""
    PRODUCE = "Produce"
    DAIRY = "Dairy"
    MEAT = "Meat"
    BAKERY = "Bakery"
    FROZEN = "Frozen"
    BEVERAGES = "Beverages"
    SNACKS = "Snacks"
    CANNED_GOODS = "Canned Goods"
    CONDIMENTS = "Condiments"
    HOUSEHOLD = "Household"
    PERSONAL_CARE = "Personal Care"
    OTHER = "Other"


class TransactionType(enum.Enum):
    """Types of stock transactions"""
    SALE = "Sale"
    RESTOCK = "Restock"
    RETURN = "Return"
    ADJUSTMENT = "Adjustment"
    EXPIRED = "Expired"
    DAMAGED = "Damaged"


class OrderStatus(enum.Enum):
    """Status of restock orders"""
    PENDING = "Pending"
    CONFIRMED = "Confirmed"
    SHIPPED = "Shipped"
    DELIVERED = "Delivered"
    CANCELLED = "Cancelled"


class AlertStatus(enum.Enum):
    """Status of stock alerts"""
    ACTIVE = "Active"
    ACKNOWLEDGED = "Acknowledged"
    RESOLVED = "Resolved"


class Supplier(Base):
    """Supplier model - stores supplier information"""
    __tablename__ = "suppliers"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    contact_person = Column(String(100))
    email = Column(String(100))
    phone = Column(String(20))
    address = Column(Text)
    city = Column(String(50))
    state = Column(String(50))
    zip_code = Column(String(20))
    country = Column(String(50), default="USA")
    is_active = Column(Boolean, default=True)
    lead_time_days = Column(Integer, default=3)  # Average days for delivery
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    products = relationship("Product", back_populates="supplier")
    restock_orders = relationship("RestockOrder", back_populates="supplier")
    
    def __repr__(self):
        return f"<Supplier(id={self.id}, name='{self.name}')>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "contact_person": self.contact_person,
            "email": self.email,
            "phone": self.phone,
            "address": self.address,
            "city": self.city,
            "state": self.state,
            "zip_code": self.zip_code,
            "country": self.country,
            "is_active": self.is_active,
            "lead_time_days": self.lead_time_days
        }


class Product(Base):
    """Product model - stores product information and current stock level"""
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sku = Column(String(50), unique=True, nullable=False)  # Stock Keeping Unit
    name = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(SQLEnum(Category), default=Category.OTHER)
    unit = Column(String(20), default="piece")  # piece, lb, kg, oz, etc.
    price = Column(Float, nullable=False)
    cost = Column(Float, nullable=False)  # Purchase cost from supplier
    
    # Stock information
    current_stock = Column(Integer, default=0)
    min_stock_level = Column(Integer, default=10)  # Low stock threshold
    max_stock_level = Column(Integer, default=100)  # Maximum storage capacity
    reorder_quantity = Column(Integer, default=50)  # Default quantity to reorder
    
    # Product details
    barcode = Column(String(50))
    brand = Column(String(100))
    expiry_days = Column(Integer)  # Shelf life in days
    location = Column(String(50))  # Aisle/shelf location in store
    
    # Status
    is_active = Column(Boolean, default=True)
    is_perishable = Column(Boolean, default=False)
    
    # Foreign keys
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    supplier = relationship("Supplier", back_populates="products")
    transactions = relationship("StockTransaction", back_populates="product")
    alerts = relationship("StockAlert", back_populates="product")
    restock_order_items = relationship("RestockOrderItem", back_populates="product")
    
    def __repr__(self):
        return f"<Product(id={self.id}, sku='{self.sku}', name='{self.name}', stock={self.current_stock})>"
    
    @property
    def is_low_stock(self) -> bool:
        """Check if product is below minimum stock level"""
        return self.current_stock <= self.min_stock_level
    
    @property
    def is_out_of_stock(self) -> bool:
        """Check if product is out of stock"""
        return self.current_stock <= 0
    
    @property
    def stock_status(self) -> str:
        """Get human-readable stock status"""
        if self.is_out_of_stock:
            return "Out of Stock"
        elif self.is_low_stock:
            return "Low Stock"
        elif self.current_stock >= self.max_stock_level:
            return "Overstocked"
        return "In Stock"
    
    @property
    def profit_margin(self) -> float:
        """Calculate profit margin percentage"""
        if self.cost > 0:
            return ((self.price - self.cost) / self.cost) * 100
        return 0
    
    def to_dict(self):
        return {
            "id": self.id,
            "sku": self.sku,
            "name": self.name,
            "description": self.description,
            "category": self.category.value if self.category else None,
            "unit": self.unit,
            "price": self.price,
            "cost": self.cost,
            "current_stock": self.current_stock,
            "min_stock_level": self.min_stock_level,
            "max_stock_level": self.max_stock_level,
            "reorder_quantity": self.reorder_quantity,
            "stock_status": self.stock_status,
            "supplier_id": self.supplier_id,
            "is_active": self.is_active
        }


class StockTransaction(Base):
    """Stock Transaction model - tracks all inventory movements"""
    __tablename__ = "stock_transactions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    transaction_type = Column(SQLEnum(TransactionType), nullable=False)
    quantity = Column(Integer, nullable=False)  # Positive for additions, negative for deductions
    previous_stock = Column(Integer, nullable=False)
    new_stock = Column(Integer, nullable=False)
    unit_price = Column(Float)  # Price at time of transaction
    total_value = Column(Float)  # Total value of transaction
    reference_number = Column(String(50))  # Order ID, Invoice number, etc.
    notes = Column(Text)
    performed_by = Column(String(100))  # User who performed the transaction
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    product = relationship("Product", back_populates="transactions")
    
    def __repr__(self):
        return f"<StockTransaction(id={self.id}, product_id={self.product_id}, type={self.transaction_type.value}, qty={self.quantity})>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "product_name": self.product.name if self.product else None,
            "transaction_type": self.transaction_type.value,
            "quantity": self.quantity,
            "previous_stock": self.previous_stock,
            "new_stock": self.new_stock,
            "unit_price": self.unit_price,
            "total_value": self.total_value,
            "reference_number": self.reference_number,
            "notes": self.notes,
            "performed_by": self.performed_by,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class StockAlert(Base):
    """Stock Alert model - stores low stock and other alerts"""
    __tablename__ = "stock_alerts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    alert_type = Column(String(50), nullable=False)  # LOW_STOCK, OUT_OF_STOCK, EXPIRING_SOON
    message = Column(Text, nullable=False)
    status = Column(SQLEnum(AlertStatus), default=AlertStatus.ACTIVE)
    stock_level_at_alert = Column(Integer)
    acknowledged_by = Column(String(100))
    acknowledged_at = Column(DateTime)
    resolved_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    product = relationship("Product", back_populates="alerts")
    
    def __repr__(self):
        return f"<StockAlert(id={self.id}, product_id={self.product_id}, type='{self.alert_type}')>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "product_name": self.product.name if self.product else None,
            "alert_type": self.alert_type,
            "message": self.message,
            "status": self.status.value,
            "stock_level_at_alert": self.stock_level_at_alert,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class RestockOrder(Base):
    """Restock Order model - manages orders placed to suppliers"""
    __tablename__ = "restock_orders"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_number = Column(String(50), unique=True, nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING)
    total_amount = Column(Float, default=0)
    notes = Column(Text)
    
    # Dates
    order_date = Column(DateTime, default=func.now())
    expected_delivery = Column(DateTime)
    actual_delivery = Column(DateTime)
    
    # Tracking
    created_by = Column(String(100))
    updated_by = Column(String(100))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    supplier = relationship("Supplier", back_populates="restock_orders")
    items = relationship("RestockOrderItem", back_populates="order", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<RestockOrder(id={self.id}, order_number='{self.order_number}', status={self.status.value})>"
    
    def calculate_total(self):
        """Calculate total order amount from items"""
        self.total_amount = sum(item.total_price for item in self.items)
        return self.total_amount
    
    def to_dict(self):
        return {
            "id": self.id,
            "order_number": self.order_number,
            "supplier_id": self.supplier_id,
            "supplier_name": self.supplier.name if self.supplier else None,
            "status": self.status.value,
            "total_amount": self.total_amount,
            "order_date": self.order_date.isoformat() if self.order_date else None,
            "expected_delivery": self.expected_delivery.isoformat() if self.expected_delivery else None,
            "items_count": len(self.items),
            "notes": self.notes
        }


class RestockOrderItem(Base):
    """Restock Order Item model - individual items in a restock order"""
    __tablename__ = "restock_order_items"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("restock_orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity_ordered = Column(Integer, nullable=False)
    quantity_received = Column(Integer, default=0)
    unit_cost = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    
    # Relationships
    order = relationship("RestockOrder", back_populates="items")
    product = relationship("Product", back_populates="restock_order_items")
    
    def __repr__(self):
        return f"<RestockOrderItem(id={self.id}, product_id={self.product_id}, qty={self.quantity_ordered})>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "order_id": self.order_id,
            "product_id": self.product_id,
            "product_name": self.product.name if self.product else None,
            "product_sku": self.product.sku if self.product else None,
            "quantity_ordered": self.quantity_ordered,
            "quantity_received": self.quantity_received,
            "unit_cost": self.unit_cost,
            "total_price": self.total_price
        }


# Database setup functions
def get_engine(db_path: str = "grocery_inventory.db"):
    """Create and return database engine"""
    return create_engine(f"sqlite:///{db_path}", echo=False)


def get_session(engine):
    """Create and return database session"""
    Session = sessionmaker(bind=engine)
    return Session()


def init_database(db_path: str = "grocery_inventory.db"):
    """Initialize database and create all tables"""
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)
    return engine


if __name__ == "__main__":
    # Test database creation
    engine = init_database()
    print("Database initialized successfully!")
