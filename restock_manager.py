"""
Restock Manager - Handles restocking processes, purchase orders, and supplier orders
Automates the restocking workflow from order creation to inventory update
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple
from sqlalchemy.orm import Session
import uuid

from models import (
    Product, Supplier, RestockOrder, RestockOrderItem, StockTransaction,
    OrderStatus, TransactionType, Category,
    get_session, get_engine, init_database
)


class RestockManager:
    """Manages the restocking process and purchase orders"""
    
    def __init__(self, session: Session):
        self.session = session
    
    # ==================== Order Number Generation ====================
    
    def _generate_order_number(self) -> str:
        """Generate a unique order number"""
        date_part = datetime.now().strftime("%Y%m%d")
        unique_part = uuid.uuid4().hex[:6].upper()
        return f"PO-{date_part}-{unique_part}"
    
    # ==================== Restock Order Management ====================
    
    def create_restock_order(self, supplier_id: int, 
                             items: List[Dict[str, int]],
                             notes: str = None,
                             created_by: str = "System") -> Optional[RestockOrder]:
        """
        Create a new restock order
        
        Args:
            supplier_id: ID of the supplier
            items: List of dicts with 'product_id' and 'quantity'
            notes: Optional notes for the order
            created_by: User creating the order
        
        Returns:
            Created RestockOrder or None if failed
        """
        supplier = self.session.query(Supplier).filter(Supplier.id == supplier_id).first()
        if not supplier:
            raise ValueError(f"Supplier with ID {supplier_id} not found")
        
        # Calculate expected delivery based on supplier lead time
        expected_delivery = datetime.now() + timedelta(days=supplier.lead_time_days)
        
        # Create the order
        order = RestockOrder(
            order_number=self._generate_order_number(),
            supplier_id=supplier_id,
            status=OrderStatus.PENDING,
            notes=notes,
            expected_delivery=expected_delivery,
            created_by=created_by
        )
        self.session.add(order)
        self.session.flush()  # Get the order ID
        
        # Add items to the order
        total_amount = 0
        for item in items:
            product = self.session.query(Product).filter(
                Product.id == item['product_id']
            ).first()
            
            if not product:
                raise ValueError(f"Product with ID {item['product_id']} not found")
            
            if product.supplier_id != supplier_id:
                raise ValueError(
                    f"Product '{product.name}' is not from supplier '{supplier.name}'"
                )
            
            quantity = item['quantity']
            unit_cost = product.cost
            total_price = quantity * unit_cost
            
            order_item = RestockOrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity_ordered=quantity,
                unit_cost=unit_cost,
                total_price=total_price
            )
            self.session.add(order_item)
            total_amount += total_price
        
        order.total_amount = total_amount
        self.session.commit()
        
        return order
    
    def create_auto_restock_order(self, supplier_id: int = None,
                                   created_by: str = "System") -> List[RestockOrder]:
        """
        Automatically create restock orders for all low-stock products
        Groups products by supplier
        
        Args:
            supplier_id: Optional - only create order for specific supplier
            created_by: User creating the orders
        
        Returns:
            List of created RestockOrders
        """
        # Find all low-stock products
        query = self.session.query(Product).filter(
            Product.is_active == True,
            Product.current_stock <= Product.min_stock_level,
            Product.supplier_id.isnot(None)
        )
        
        if supplier_id:
            query = query.filter(Product.supplier_id == supplier_id)
        
        low_stock_products = query.all()
        
        if not low_stock_products:
            return []
        
        # Group products by supplier
        supplier_products: Dict[int, List[Product]] = {}
        for product in low_stock_products:
            if product.supplier_id not in supplier_products:
                supplier_products[product.supplier_id] = []
            supplier_products[product.supplier_id].append(product)
        
        # Create orders for each supplier
        orders = []
        for sup_id, products in supplier_products.items():
            items = [
                {
                    'product_id': p.id,
                    'quantity': p.reorder_quantity
                }
                for p in products
            ]
            
            try:
                order = self.create_restock_order(
                    supplier_id=sup_id,
                    items=items,
                    notes="Auto-generated order for low-stock items",
                    created_by=created_by
                )
                orders.append(order)
            except Exception as e:
                print(f"Error creating order for supplier {sup_id}: {e}")
        
        return orders
    
    def get_order(self, order_id: int) -> Optional[RestockOrder]:
        """Get restock order by ID"""
        return self.session.query(RestockOrder).filter(
            RestockOrder.id == order_id
        ).first()
    
    def get_order_by_number(self, order_number: str) -> Optional[RestockOrder]:
        """Get restock order by order number"""
        return self.session.query(RestockOrder).filter(
            RestockOrder.order_number == order_number
        ).first()
    
    def get_orders(self, status: OrderStatus = None, 
                   supplier_id: int = None,
                   limit: int = 50) -> List[RestockOrder]:
        """Get restock orders with optional filters"""
        query = self.session.query(RestockOrder)
        
        if status:
            query = query.filter(RestockOrder.status == status)
        if supplier_id:
            query = query.filter(RestockOrder.supplier_id == supplier_id)
        
        return query.order_by(RestockOrder.order_date.desc()).limit(limit).all()
    
    def get_pending_orders(self) -> List[RestockOrder]:
        """Get all pending orders"""
        return self.get_orders(status=OrderStatus.PENDING)
    
    def get_orders_by_supplier(self, supplier_id: int) -> List[RestockOrder]:
        """Get all orders for a supplier"""
        return self.get_orders(supplier_id=supplier_id)
    
    # ==================== Order Status Management ====================
    
    def confirm_order(self, order_id: int, updated_by: str = "System") -> bool:
        """Mark order as confirmed (sent to supplier)"""
        order = self.get_order(order_id)
        if order and order.status == OrderStatus.PENDING:
            order.status = OrderStatus.CONFIRMED
            order.updated_by = updated_by
            self.session.commit()
            return True
        return False
    
    def mark_shipped(self, order_id: int, updated_by: str = "System") -> bool:
        """Mark order as shipped"""
        order = self.get_order(order_id)
        if order and order.status == OrderStatus.CONFIRMED:
            order.status = OrderStatus.SHIPPED
            order.updated_by = updated_by
            self.session.commit()
            return True
        return False
    
    def receive_order(self, order_id: int, 
                      received_items: List[Dict[str, int]] = None,
                      updated_by: str = "System") -> Tuple[bool, List[StockTransaction]]:
        """
        Receive an order and update inventory
        
        Args:
            order_id: ID of the order
            received_items: Optional list of dicts with 'product_id' and 'quantity_received'
                           If not provided, assumes full quantities received
            updated_by: User receiving the order
        
        Returns:
            Tuple of (success, list of stock transactions created)
        """
        order = self.get_order(order_id)
        if not order or order.status not in [OrderStatus.CONFIRMED, OrderStatus.SHIPPED]:
            return False, []
        
        transactions = []
        
        # Process each item
        for item in order.items:
            # Determine quantity received
            if received_items:
                received_info = next(
                    (ri for ri in received_items if ri['product_id'] == item.product_id),
                    None
                )
                quantity_received = received_info['quantity_received'] if received_info else item.quantity_ordered
            else:
                quantity_received = item.quantity_ordered
            
            # Update item record
            item.quantity_received = quantity_received
            
            # Update product stock
            product = item.product
            previous_stock = product.current_stock
            product.current_stock += quantity_received
            
            # Create stock transaction
            transaction = StockTransaction(
                product_id=product.id,
                transaction_type=TransactionType.RESTOCK,
                quantity=quantity_received,
                previous_stock=previous_stock,
                new_stock=product.current_stock,
                unit_price=item.unit_cost,
                total_value=quantity_received * item.unit_cost,
                reference_number=order.order_number,
                notes=f"Received from order {order.order_number}",
                performed_by=updated_by
            )
            self.session.add(transaction)
            transactions.append(transaction)
        
        # Update order status
        order.status = OrderStatus.DELIVERED
        order.actual_delivery = datetime.now()
        order.updated_by = updated_by
        
        self.session.commit()
        
        return True, transactions
    
    def cancel_order(self, order_id: int, reason: str = None,
                     updated_by: str = "System") -> bool:
        """Cancel an order"""
        order = self.get_order(order_id)
        if order and order.status in [OrderStatus.PENDING, OrderStatus.CONFIRMED]:
            order.status = OrderStatus.CANCELLED
            order.updated_by = updated_by
            if reason:
                order.notes = f"{order.notes or ''}\nCancelled: {reason}"
            self.session.commit()
            return True
        return False
    
    # ==================== Order Analysis ====================
    
    def get_restock_suggestions(self) -> List[Dict]:
        """Get suggestions for products that need restocking"""
        products = self.session.query(Product).filter(
            Product.is_active == True,
            Product.current_stock <= Product.min_stock_level
        ).order_by(Product.current_stock).all()
        
        suggestions = []
        for product in products:
            shortage = product.min_stock_level - product.current_stock
            supplier = product.supplier
            
            suggestions.append({
                'product_id': product.id,
                'product_name': product.name,
                'sku': product.sku,
                'current_stock': product.current_stock,
                'min_stock_level': product.min_stock_level,
                'shortage': shortage,
                'suggested_quantity': product.reorder_quantity,
                'supplier_id': supplier.id if supplier else None,
                'supplier_name': supplier.name if supplier else 'No supplier',
                'estimated_cost': product.reorder_quantity * product.cost,
                'urgency': 'CRITICAL' if product.current_stock == 0 else 
                          'HIGH' if product.current_stock < product.min_stock_level * 0.5 else 'MEDIUM'
            })
        
        return suggestions
    
    def get_order_summary(self) -> Dict:
        """Get summary of all orders"""
        all_orders = self.session.query(RestockOrder).all()
        
        summary = {
            'total_orders': len(all_orders),
            'pending': 0,
            'confirmed': 0,
            'shipped': 0,
            'delivered': 0,
            'cancelled': 0,
            'total_value_pending': 0,
            'total_value_delivered': 0
        }
        
        for order in all_orders:
            if order.status == OrderStatus.PENDING:
                summary['pending'] += 1
                summary['total_value_pending'] += order.total_amount or 0
            elif order.status == OrderStatus.CONFIRMED:
                summary['confirmed'] += 1
                summary['total_value_pending'] += order.total_amount or 0
            elif order.status == OrderStatus.SHIPPED:
                summary['shipped'] += 1
            elif order.status == OrderStatus.DELIVERED:
                summary['delivered'] += 1
                summary['total_value_delivered'] += order.total_amount or 0
            elif order.status == OrderStatus.CANCELLED:
                summary['cancelled'] += 1
        
        return summary
    
    def get_supplier_order_history(self, supplier_id: int) -> Dict:
        """Get order history statistics for a supplier"""
        orders = self.session.query(RestockOrder).filter(
            RestockOrder.supplier_id == supplier_id
        ).all()
        
        delivered_orders = [o for o in orders if o.status == OrderStatus.DELIVERED]
        
        # Calculate average delivery time
        delivery_times = []
        for order in delivered_orders:
            if order.actual_delivery and order.order_date:
                delta = order.actual_delivery - order.order_date
                delivery_times.append(delta.days)
        
        avg_delivery_time = sum(delivery_times) / len(delivery_times) if delivery_times else 0
        
        return {
            'total_orders': len(orders),
            'delivered_orders': len(delivered_orders),
            'cancelled_orders': len([o for o in orders if o.status == OrderStatus.CANCELLED]),
            'total_value': sum(o.total_amount or 0 for o in delivered_orders),
            'average_delivery_days': round(avg_delivery_time, 1)
        }


class QuickRestock:
    """Utility class for quick restocking operations"""
    
    def __init__(self, session: Session):
        self.session = session
        self.restock_manager = RestockManager(session)
    
    def quick_restock_product(self, product_id: int, quantity: int = None,
                              performed_by: str = "System") -> Optional[StockTransaction]:
        """
        Quick restock a single product without creating a full order
        Useful for manual restocking or direct deliveries
        """
        product = self.session.query(Product).filter(Product.id == product_id).first()
        if not product:
            return None
        
        # Use reorder quantity if not specified
        if quantity is None:
            quantity = product.reorder_quantity
        
        previous_stock = product.current_stock
        product.current_stock += quantity
        
        transaction = StockTransaction(
            product_id=product.id,
            transaction_type=TransactionType.RESTOCK,
            quantity=quantity,
            previous_stock=previous_stock,
            new_stock=product.current_stock,
            unit_price=product.cost,
            total_value=quantity * product.cost,
            notes="Quick restock",
            performed_by=performed_by
        )
        self.session.add(transaction)
        self.session.commit()
        
        return transaction
    
    def quick_restock_all_low(self, performed_by: str = "System") -> List[StockTransaction]:
        """Quick restock all low-stock products to their reorder quantity"""
        low_stock = self.session.query(Product).filter(
            Product.is_active == True,
            Product.current_stock <= Product.min_stock_level
        ).all()
        
        transactions = []
        for product in low_stock:
            transaction = self.quick_restock_product(
                product_id=product.id,
                performed_by=performed_by
            )
            if transaction:
                transactions.append(transaction)
        
        return transactions


if __name__ == "__main__":
    # Test the restock manager
    from models import init_database, get_session, Category
    
    engine = init_database("test_restock.db")
    session = get_session(engine)
    
    # Create a supplier
    supplier = Supplier(
        name="Test Supplier",
        contact_person="John",
        email="john@supplier.com",
        lead_time_days=3
    )
    session.add(supplier)
    session.commit()
    
    # Create products
    product1 = Product(
        sku="TEST-001",
        name="Test Product 1",
        price=10.00,
        cost=5.00,
        current_stock=5,
        min_stock_level=10,
        reorder_quantity=50,
        supplier_id=supplier.id,
        category=Category.OTHER
    )
    product2 = Product(
        sku="TEST-002",
        name="Test Product 2",
        price=15.00,
        cost=8.00,
        current_stock=3,
        min_stock_level=10,
        reorder_quantity=30,
        supplier_id=supplier.id,
        category=Category.OTHER
    )
    session.add_all([product1, product2])
    session.commit()
    
    # Test restock manager
    restock_mgr = RestockManager(session)
    
    # Get suggestions
    suggestions = restock_mgr.get_restock_suggestions()
    print(f"Restock suggestions: {len(suggestions)} products need restocking")
    
    # Create auto restock order
    orders = restock_mgr.create_auto_restock_order()
    print(f"Created {len(orders)} auto restock orders")
    
    if orders:
        order = orders[0]
        print(f"Order: {order.order_number}, Total: ${order.total_amount:.2f}")
        
        # Confirm and receive
        restock_mgr.confirm_order(order.id)
        success, transactions = restock_mgr.receive_order(order.id)
        print(f"Order received: {success}, {len(transactions)} products restocked")
    
    session.close()
    print("Restock manager test completed!")
