"""
Inventory Manager - Core logic for inventory management operations
Handles products, suppliers, stock transactions, and inventory updates
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from models import (
    Product, Supplier, StockTransaction, StockAlert, RestockOrder, RestockOrderItem,
    Category, TransactionType, OrderStatus, AlertStatus,
    init_database, get_session, get_engine
)


class InventoryManager:
    """Core inventory management class"""
    
    def __init__(self, db_path: str = "grocery_inventory.db"):
        self.db_path = db_path
        self.engine = init_database(db_path)
        self.session = get_session(self.engine)
        self._observers = []  # For real-time update notifications
    
    def close(self):
        """Close database session"""
        self.session.close()
    
    def refresh_session(self):
        """Refresh the database session"""
        self.session.close()
        self.session = get_session(self.engine)
    
    # ==================== Observer Pattern for Real-time Updates ====================
    
    def add_observer(self, observer):
        """Add observer for real-time inventory updates"""
        self._observers.append(observer)
    
    def remove_observer(self, observer):
        """Remove observer"""
        if observer in self._observers:
            self._observers.remove(observer)
    
    def _notify_observers(self, event_type: str, data: Dict[str, Any]):
        """Notify all observers of inventory changes"""
        for observer in self._observers:
            try:
                observer.on_inventory_update(event_type, data)
            except Exception as e:
                print(f"Error notifying observer: {e}")
    
    # ==================== Supplier Management ====================
    
    def add_supplier(self, name: str, contact_person: str = None, email: str = None,
                     phone: str = None, address: str = None, city: str = None,
                     state: str = None, zip_code: str = None, country: str = "USA",
                     lead_time_days: int = 3) -> Supplier:
        """Add a new supplier"""
        supplier = Supplier(
            name=name,
            contact_person=contact_person,
            email=email,
            phone=phone,
            address=address,
            city=city,
            state=state,
            zip_code=zip_code,
            country=country,
            lead_time_days=lead_time_days
        )
        self.session.add(supplier)
        self.session.commit()
        self._notify_observers("supplier_added", supplier.to_dict())
        return supplier
    
    def get_supplier(self, supplier_id: int) -> Optional[Supplier]:
        """Get supplier by ID"""
        return self.session.query(Supplier).filter(Supplier.id == supplier_id).first()
    
    def get_supplier_by_name(self, name: str) -> Optional[Supplier]:
        """Get supplier by name"""
        return self.session.query(Supplier).filter(Supplier.name == name).first()
    
    def get_all_suppliers(self, active_only: bool = True) -> List[Supplier]:
        """Get all suppliers"""
        query = self.session.query(Supplier)
        if active_only:
            query = query.filter(Supplier.is_active == True)
        return query.order_by(Supplier.name).all()
    
    def update_supplier(self, supplier_id: int, **kwargs) -> Optional[Supplier]:
        """Update supplier information"""
        supplier = self.get_supplier(supplier_id)
        if supplier:
            for key, value in kwargs.items():
                if hasattr(supplier, key):
                    setattr(supplier, key, value)
            self.session.commit()
            self._notify_observers("supplier_updated", supplier.to_dict())
        return supplier
    
    def deactivate_supplier(self, supplier_id: int) -> bool:
        """Deactivate a supplier"""
        supplier = self.get_supplier(supplier_id)
        if supplier:
            supplier.is_active = False
            self.session.commit()
            return True
        return False
    
    # ==================== Product Management ====================
    
    def add_product(self, sku: str, name: str, price: float, cost: float,
                    category: Category = Category.OTHER, description: str = None,
                    unit: str = "piece", min_stock_level: int = 10,
                    max_stock_level: int = 100, reorder_quantity: int = 50,
                    initial_stock: int = 0, supplier_id: int = None,
                    barcode: str = None, brand: str = None, 
                    expiry_days: int = None, location: str = None,
                    is_perishable: bool = False) -> Product:
        """Add a new product to inventory"""
        product = Product(
            sku=sku,
            name=name,
            description=description,
            category=category,
            unit=unit,
            price=price,
            cost=cost,
            current_stock=initial_stock,
            min_stock_level=min_stock_level,
            max_stock_level=max_stock_level,
            reorder_quantity=reorder_quantity,
            supplier_id=supplier_id,
            barcode=barcode,
            brand=brand,
            expiry_days=expiry_days,
            location=location,
            is_perishable=is_perishable
        )
        self.session.add(product)
        self.session.commit()
        
        # Create initial stock transaction if there's initial stock
        if initial_stock > 0:
            self._create_transaction(
                product=product,
                transaction_type=TransactionType.RESTOCK,
                quantity=initial_stock,
                notes="Initial stock"
            )
        
        self._notify_observers("product_added", product.to_dict())
        
        # Check if product is already low stock
        self._check_and_create_alert(product)
        
        return product
    
    def get_product(self, product_id: int) -> Optional[Product]:
        """Get product by ID"""
        return self.session.query(Product).filter(Product.id == product_id).first()
    
    def get_product_by_sku(self, sku: str) -> Optional[Product]:
        """Get product by SKU"""
        return self.session.query(Product).filter(Product.sku == sku).first()
    
    def get_product_by_barcode(self, barcode: str) -> Optional[Product]:
        """Get product by barcode"""
        return self.session.query(Product).filter(Product.barcode == barcode).first()
    
    def get_all_products(self, active_only: bool = True) -> List[Product]:
        """Get all products"""
        query = self.session.query(Product)
        if active_only:
            query = query.filter(Product.is_active == True)
        return query.order_by(Product.name).all()
    
    def get_products_by_category(self, category: Category, active_only: bool = True) -> List[Product]:
        """Get products by category"""
        query = self.session.query(Product).filter(Product.category == category)
        if active_only:
            query = query.filter(Product.is_active == True)
        return query.order_by(Product.name).all()
    
    def get_products_by_supplier(self, supplier_id: int, active_only: bool = True) -> List[Product]:
        """Get products by supplier"""
        query = self.session.query(Product).filter(Product.supplier_id == supplier_id)
        if active_only:
            query = query.filter(Product.is_active == True)
        return query.order_by(Product.name).all()
    
    def search_products(self, search_term: str) -> List[Product]:
        """Search products by name, SKU, or barcode"""
        search_pattern = f"%{search_term}%"
        return self.session.query(Product).filter(
            or_(
                Product.name.ilike(search_pattern),
                Product.sku.ilike(search_pattern),
                Product.barcode.ilike(search_pattern),
                Product.brand.ilike(search_pattern)
            )
        ).all()
    
    def update_product(self, product_id: int, **kwargs) -> Optional[Product]:
        """Update product information"""
        product = self.get_product(product_id)
        if product:
            for key, value in kwargs.items():
                if hasattr(product, key) and key not in ['id', 'created_at', 'current_stock']:
                    setattr(product, key, value)
            self.session.commit()
            self._notify_observers("product_updated", product.to_dict())
        return product
    
    def deactivate_product(self, product_id: int) -> bool:
        """Deactivate a product"""
        product = self.get_product(product_id)
        if product:
            product.is_active = False
            self.session.commit()
            return True
        return False
    
    # ==================== Stock Management ====================
    
    def update_stock(self, product_id: int, quantity_change: int,
                     transaction_type: TransactionType, 
                     reference_number: str = None, notes: str = None,
                     performed_by: str = "System") -> Optional[StockTransaction]:
        """
        Update stock level for a product
        Positive quantity_change = adding stock
        Negative quantity_change = removing stock
        """
        product = self.get_product(product_id)
        if not product:
            return None
        
        previous_stock = product.current_stock
        new_stock = previous_stock + quantity_change
        
        # Prevent negative stock
        if new_stock < 0:
            raise ValueError(f"Insufficient stock. Current: {previous_stock}, Requested change: {quantity_change}")
        
        # Update product stock
        product.current_stock = new_stock
        
        # Create transaction record
        transaction = self._create_transaction(
            product=product,
            transaction_type=transaction_type,
            quantity=quantity_change,
            previous_stock=previous_stock,
            new_stock=new_stock,
            reference_number=reference_number,
            notes=notes,
            performed_by=performed_by
        )
        
        self.session.commit()
        
        # Notify observers of stock change
        self._notify_observers("stock_updated", {
            "product_id": product_id,
            "product_name": product.name,
            "previous_stock": previous_stock,
            "new_stock": new_stock,
            "change": quantity_change,
            "transaction_type": transaction_type.value
        })
        
        # Check for low stock alert
        self._check_and_create_alert(product)
        
        return transaction
    
    def sell_product(self, product_id: int, quantity: int,
                     reference_number: str = None, performed_by: str = "System") -> Optional[StockTransaction]:
        """Record a sale (reduces stock)"""
        return self.update_stock(
            product_id=product_id,
            quantity_change=-abs(quantity),  # Ensure negative
            transaction_type=TransactionType.SALE,
            reference_number=reference_number,
            notes=f"Sale of {quantity} units",
            performed_by=performed_by
        )
    
    def restock_product(self, product_id: int, quantity: int,
                        reference_number: str = None, performed_by: str = "System") -> Optional[StockTransaction]:
        """Restock a product (increases stock)"""
        return self.update_stock(
            product_id=product_id,
            quantity_change=abs(quantity),  # Ensure positive
            transaction_type=TransactionType.RESTOCK,
            reference_number=reference_number,
            notes=f"Restocked {quantity} units",
            performed_by=performed_by
        )
    
    def return_product(self, product_id: int, quantity: int,
                       reference_number: str = None, performed_by: str = "System") -> Optional[StockTransaction]:
        """Process a return (increases stock)"""
        return self.update_stock(
            product_id=product_id,
            quantity_change=abs(quantity),
            transaction_type=TransactionType.RETURN,
            reference_number=reference_number,
            notes=f"Return of {quantity} units",
            performed_by=performed_by
        )
    
    def adjust_stock(self, product_id: int, new_stock_level: int,
                     reason: str = None, performed_by: str = "System") -> Optional[StockTransaction]:
        """Adjust stock to a specific level (for inventory corrections)"""
        product = self.get_product(product_id)
        if not product:
            return None
        
        quantity_change = new_stock_level - product.current_stock
        return self.update_stock(
            product_id=product_id,
            quantity_change=quantity_change,
            transaction_type=TransactionType.ADJUSTMENT,
            notes=f"Stock adjustment: {reason}" if reason else "Stock adjustment",
            performed_by=performed_by
        )
    
    def mark_expired(self, product_id: int, quantity: int,
                     performed_by: str = "System") -> Optional[StockTransaction]:
        """Mark items as expired (reduces stock)"""
        return self.update_stock(
            product_id=product_id,
            quantity_change=-abs(quantity),
            transaction_type=TransactionType.EXPIRED,
            notes=f"Expired: {quantity} units",
            performed_by=performed_by
        )
    
    def mark_damaged(self, product_id: int, quantity: int,
                     notes: str = None, performed_by: str = "System") -> Optional[StockTransaction]:
        """Mark items as damaged (reduces stock)"""
        return self.update_stock(
            product_id=product_id,
            quantity_change=-abs(quantity),
            transaction_type=TransactionType.DAMAGED,
            notes=f"Damaged: {quantity} units. {notes or ''}",
            performed_by=performed_by
        )
    
    # ==================== Stock Queries ====================
    
    def get_low_stock_products(self) -> List[Product]:
        """Get all products that are below minimum stock level"""
        return self.session.query(Product).filter(
            and_(
                Product.is_active == True,
                Product.current_stock <= Product.min_stock_level
            )
        ).order_by(Product.current_stock).all()
    
    def get_out_of_stock_products(self) -> List[Product]:
        """Get all products that are out of stock"""
        return self.session.query(Product).filter(
            and_(
                Product.is_active == True,
                Product.current_stock <= 0
            )
        ).all()
    
    def get_overstocked_products(self) -> List[Product]:
        """Get all products that are above maximum stock level"""
        return self.session.query(Product).filter(
            and_(
                Product.is_active == True,
                Product.current_stock > Product.max_stock_level
            )
        ).all()
    
    def get_stock_value(self) -> Dict[str, float]:
        """Calculate total inventory value"""
        products = self.get_all_products()
        total_cost_value = sum(p.current_stock * p.cost for p in products)
        total_retail_value = sum(p.current_stock * p.price for p in products)
        return {
            "cost_value": round(total_cost_value, 2),
            "retail_value": round(total_retail_value, 2),
            "potential_profit": round(total_retail_value - total_cost_value, 2)
        }
    
    def get_stock_summary(self) -> Dict[str, Any]:
        """Get comprehensive stock summary"""
        products = self.get_all_products()
        return {
            "total_products": len(products),
            "total_units": sum(p.current_stock for p in products),
            "low_stock_count": len(self.get_low_stock_products()),
            "out_of_stock_count": len(self.get_out_of_stock_products()),
            "overstocked_count": len(self.get_overstocked_products()),
            "stock_value": self.get_stock_value()
        }
    
    # ==================== Transaction History ====================
    
    def get_transactions(self, product_id: int = None, 
                         transaction_type: TransactionType = None,
                         start_date: datetime = None, end_date: datetime = None,
                         limit: int = 100) -> List[StockTransaction]:
        """Get transaction history with optional filters"""
        query = self.session.query(StockTransaction)
        
        if product_id:
            query = query.filter(StockTransaction.product_id == product_id)
        if transaction_type:
            query = query.filter(StockTransaction.transaction_type == transaction_type)
        if start_date:
            query = query.filter(StockTransaction.created_at >= start_date)
        if end_date:
            query = query.filter(StockTransaction.created_at <= end_date)
        
        return query.order_by(StockTransaction.created_at.desc()).limit(limit).all()
    
    def get_recent_transactions(self, limit: int = 20) -> List[StockTransaction]:
        """Get most recent transactions"""
        return self.get_transactions(limit=limit)
    
    # ==================== Helper Methods ====================
    
    def _create_transaction(self, product: Product, transaction_type: TransactionType,
                            quantity: int, previous_stock: int = None, new_stock: int = None,
                            reference_number: str = None, notes: str = None,
                            performed_by: str = "System") -> StockTransaction:
        """Create a stock transaction record"""
        if previous_stock is None:
            previous_stock = product.current_stock - quantity
        if new_stock is None:
            new_stock = product.current_stock
        
        transaction = StockTransaction(
            product_id=product.id,
            transaction_type=transaction_type,
            quantity=quantity,
            previous_stock=previous_stock,
            new_stock=new_stock,
            unit_price=product.price,
            total_value=abs(quantity) * product.price,
            reference_number=reference_number,
            notes=notes,
            performed_by=performed_by
        )
        self.session.add(transaction)
        return transaction
    
    def _check_and_create_alert(self, product: Product):
        """Check stock level and create alert if needed"""
        from alert_system import AlertSystem
        alert_system = AlertSystem(self.session)
        alert_system.check_product_stock(product)


if __name__ == "__main__":
    # Quick test
    manager = InventoryManager("test_inventory.db")
    
    # Add a supplier
    supplier = manager.add_supplier(
        name="Fresh Foods Co.",
        contact_person="John Smith",
        email="john@freshfoods.com",
        phone="555-0123"
    )
    print(f"Added supplier: {supplier}")
    
    # Add a product
    product = manager.add_product(
        sku="MILK-001",
        name="Whole Milk 1 Gallon",
        price=4.99,
        cost=2.50,
        category=Category.DAIRY,
        initial_stock=50,
        min_stock_level=10,
        supplier_id=supplier.id
    )
    print(f"Added product: {product}")
    
    # Sell some
    manager.sell_product(product.id, 5)
    print(f"After sale: Stock = {product.current_stock}")
    
    manager.close()
    print("Test completed!")
