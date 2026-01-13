"""
Alert System - Handles low-stock alerts, notifications, and monitoring
Provides real-time alerts for inventory status changes
"""

import threading
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Callable, Any
from sqlalchemy.orm import Session

from models import (
    Product, StockAlert, AlertStatus,
    get_session, get_engine
)


class AlertObserver:
    """Base class for alert observers"""
    
    def on_alert(self, alert_type: str, product: Product, message: str):
        """Called when an alert is triggered"""
        raise NotImplementedError


class ConsoleAlertObserver(AlertObserver):
    """Prints alerts to console"""
    
    def on_alert(self, alert_type: str, product: Product, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n{'='*60}")
        print(f"⚠️  ALERT [{timestamp}]")
        print(f"Type: {alert_type}")
        print(f"Product: {product.name} (SKU: {product.sku})")
        print(f"Message: {message}")
        print(f"{'='*60}\n")


class EmailAlertObserver(AlertObserver):
    """Sends alerts via email"""
    
    def __init__(self, smtp_server: str, smtp_port: int, 
                 sender_email: str, sender_password: str,
                 recipient_emails: List[str]):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.recipient_emails = recipient_emails
    
    def on_alert(self, alert_type: str, product: Product, message: str):
        """Send email alert"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = ', '.join(self.recipient_emails)
            msg['Subject'] = f"🚨 Inventory Alert: {alert_type} - {product.name}"
            
            body = f"""
            <html>
            <body>
            <h2>Inventory Alert</h2>
            <p><strong>Alert Type:</strong> {alert_type}</p>
            <p><strong>Product:</strong> {product.name}</p>
            <p><strong>SKU:</strong> {product.sku}</p>
            <p><strong>Current Stock:</strong> {product.current_stock}</p>
            <p><strong>Minimum Stock Level:</strong> {product.min_stock_level}</p>
            <p><strong>Message:</strong> {message}</p>
            <p><strong>Time:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            <hr>
            <p><em>This is an automated message from the Grocery Inventory System.</em></p>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(body, 'html'))
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            print(f"Email alert sent to {', '.join(self.recipient_emails)}")
        except Exception as e:
            print(f"Failed to send email alert: {e}")


class CallbackAlertObserver(AlertObserver):
    """Calls a custom callback function on alert"""
    
    def __init__(self, callback: Callable[[str, Product, str], None]):
        self.callback = callback
    
    def on_alert(self, alert_type: str, product: Product, message: str):
        self.callback(alert_type, product, message)


class AlertSystem:
    """Manages inventory alerts and notifications"""
    
    ALERT_LOW_STOCK = "LOW_STOCK"
    ALERT_OUT_OF_STOCK = "OUT_OF_STOCK"
    ALERT_CRITICAL_LOW = "CRITICAL_LOW"
    ALERT_EXPIRING_SOON = "EXPIRING_SOON"
    
    def __init__(self, session: Session):
        self.session = session
        self._observers: List[AlertObserver] = []
        self._alert_cooldown: Dict[int, datetime] = {}  # Prevent alert spam
        self.cooldown_minutes = 30  # Minimum time between alerts for same product
    
    def add_observer(self, observer: AlertObserver):
        """Add an alert observer"""
        self._observers.append(observer)
    
    def remove_observer(self, observer: AlertObserver):
        """Remove an alert observer"""
        if observer in self._observers:
            self._observers.remove(observer)
    
    def _notify_observers(self, alert_type: str, product: Product, message: str):
        """Notify all observers of an alert"""
        for observer in self._observers:
            try:
                observer.on_alert(alert_type, product, message)
            except Exception as e:
                print(f"Error notifying alert observer: {e}")
    
    def _can_send_alert(self, product_id: int, alert_type: str) -> bool:
        """Check if enough time has passed since last alert for this product"""
        key = f"{product_id}_{alert_type}"
        if key in self._alert_cooldown:
            last_alert = self._alert_cooldown[key]
            if datetime.now() - last_alert < timedelta(minutes=self.cooldown_minutes):
                return False
        return True
    
    def _record_alert_sent(self, product_id: int, alert_type: str):
        """Record that an alert was sent"""
        key = f"{product_id}_{alert_type}"
        self._alert_cooldown[key] = datetime.now()
    
    def check_product_stock(self, product: Product) -> Optional[StockAlert]:
        """Check a single product's stock level and create alert if needed"""
        if not product.is_active:
            return None
        
        alert_type = None
        message = None
        
        if product.is_out_of_stock:
            alert_type = self.ALERT_OUT_OF_STOCK
            message = f"Product '{product.name}' is OUT OF STOCK! Immediate restocking required."
        elif product.current_stock <= product.min_stock_level * 0.5:
            alert_type = self.ALERT_CRITICAL_LOW
            message = f"Product '{product.name}' is critically low. Stock: {product.current_stock}, Minimum: {product.min_stock_level}"
        elif product.is_low_stock:
            alert_type = self.ALERT_LOW_STOCK
            message = f"Product '{product.name}' is running low. Stock: {product.current_stock}, Minimum: {product.min_stock_level}"
        
        if alert_type and message:
            # Check for existing active alert
            existing_alert = self.session.query(StockAlert).filter(
                StockAlert.product_id == product.id,
                StockAlert.alert_type == alert_type,
                StockAlert.status == AlertStatus.ACTIVE
            ).first()
            
            if not existing_alert:
                # Create new alert in database
                alert = StockAlert(
                    product_id=product.id,
                    alert_type=alert_type,
                    message=message,
                    stock_level_at_alert=product.current_stock,
                    status=AlertStatus.ACTIVE
                )
                self.session.add(alert)
                self.session.commit()
                
                # Notify observers if cooldown allows
                if self._can_send_alert(product.id, alert_type):
                    self._notify_observers(alert_type, product, message)
                    self._record_alert_sent(product.id, alert_type)
                
                return alert
        else:
            # Stock is OK, resolve any active alerts
            self._resolve_alerts_for_product(product.id)
        
        return None
    
    def check_all_products(self, products: List[Product]) -> List[StockAlert]:
        """Check all products and return list of new alerts"""
        alerts = []
        for product in products:
            alert = self.check_product_stock(product)
            if alert:
                alerts.append(alert)
        return alerts
    
    def get_active_alerts(self) -> List[StockAlert]:
        """Get all active alerts"""
        return self.session.query(StockAlert).filter(
            StockAlert.status == AlertStatus.ACTIVE
        ).order_by(StockAlert.created_at.desc()).all()
    
    def get_alerts_by_type(self, alert_type: str) -> List[StockAlert]:
        """Get alerts by type"""
        return self.session.query(StockAlert).filter(
            StockAlert.alert_type == alert_type,
            StockAlert.status == AlertStatus.ACTIVE
        ).all()
    
    def get_alert(self, alert_id: int) -> Optional[StockAlert]:
        """Get alert by ID"""
        return self.session.query(StockAlert).filter(StockAlert.id == alert_id).first()
    
    def acknowledge_alert(self, alert_id: int, acknowledged_by: str) -> bool:
        """Acknowledge an alert"""
        alert = self.get_alert(alert_id)
        if alert and alert.status == AlertStatus.ACTIVE:
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_by = acknowledged_by
            alert.acknowledged_at = datetime.now()
            self.session.commit()
            return True
        return False
    
    def resolve_alert(self, alert_id: int) -> bool:
        """Manually resolve an alert"""
        alert = self.get_alert(alert_id)
        if alert and alert.status != AlertStatus.RESOLVED:
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.now()
            self.session.commit()
            return True
        return False
    
    def _resolve_alerts_for_product(self, product_id: int):
        """Resolve all active alerts for a product (when stock is OK)"""
        alerts = self.session.query(StockAlert).filter(
            StockAlert.product_id == product_id,
            StockAlert.status.in_([AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED])
        ).all()
        
        for alert in alerts:
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.now()
        
        if alerts:
            self.session.commit()
    
    def get_alert_summary(self) -> Dict[str, int]:
        """Get summary of alerts by type"""
        active_alerts = self.get_active_alerts()
        summary = {
            "total_active": len(active_alerts),
            "out_of_stock": 0,
            "critical_low": 0,
            "low_stock": 0,
            "expiring_soon": 0
        }
        
        for alert in active_alerts:
            if alert.alert_type == self.ALERT_OUT_OF_STOCK:
                summary["out_of_stock"] += 1
            elif alert.alert_type == self.ALERT_CRITICAL_LOW:
                summary["critical_low"] += 1
            elif alert.alert_type == self.ALERT_LOW_STOCK:
                summary["low_stock"] += 1
            elif alert.alert_type == self.ALERT_EXPIRING_SOON:
                summary["expiring_soon"] += 1
        
        return summary


class InventoryMonitor:
    """Background monitor for real-time inventory checking"""
    
    def __init__(self, db_path: str = "grocery_inventory.db", 
                 check_interval: int = 60):
        """
        Initialize the inventory monitor
        
        Args:
            db_path: Path to the database
            check_interval: Seconds between stock checks
        """
        self.db_path = db_path
        self.check_interval = check_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._observers: List[AlertObserver] = []
    
    def add_observer(self, observer: AlertObserver):
        """Add an alert observer"""
        self._observers.append(observer)
    
    def start(self):
        """Start the background monitor"""
        if self._running:
            print("Monitor is already running")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        print(f"Inventory monitor started. Checking every {self.check_interval} seconds.")
    
    def stop(self):
        """Stop the background monitor"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        print("Inventory monitor stopped.")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        from models import Product, init_database, get_session
        
        engine = init_database(self.db_path)
        
        while self._running:
            try:
                session = get_session(engine)
                alert_system = AlertSystem(session)
                
                # Add observers to alert system
                for observer in self._observers:
                    alert_system.add_observer(observer)
                
                # Check all active products
                products = session.query(Product).filter(Product.is_active == True).all()
                new_alerts = alert_system.check_all_products(products)
                
                if new_alerts:
                    print(f"[Monitor] Generated {len(new_alerts)} new alerts")
                
                session.close()
            except Exception as e:
                print(f"[Monitor] Error during check: {e}")
            
            # Wait for next check
            time.sleep(self.check_interval)
    
    @property
    def is_running(self) -> bool:
        return self._running


# Utility functions for quick alert setup

def setup_console_alerts(alert_system: AlertSystem):
    """Add console alert observer to alert system"""
    alert_system.add_observer(ConsoleAlertObserver())


def setup_email_alerts(alert_system: AlertSystem, smtp_server: str, smtp_port: int,
                       sender_email: str, sender_password: str, recipient_emails: List[str]):
    """Add email alert observer to alert system"""
    email_observer = EmailAlertObserver(
        smtp_server=smtp_server,
        smtp_port=smtp_port,
        sender_email=sender_email,
        sender_password=sender_password,
        recipient_emails=recipient_emails
    )
    alert_system.add_observer(email_observer)


if __name__ == "__main__":
    # Test the alert system
    from models import init_database, get_session, Product, Category
    
    engine = init_database("test_alerts.db")
    session = get_session(engine)
    
    # Create alert system with console observer
    alert_system = AlertSystem(session)
    alert_system.add_observer(ConsoleAlertObserver())
    
    # Create a low-stock product for testing
    product = Product(
        sku="TEST-001",
        name="Test Product",
        price=5.99,
        cost=3.00,
        current_stock=3,
        min_stock_level=10,
        category=Category.OTHER
    )
    session.add(product)
    session.commit()
    
    # Check the product (should trigger alert)
    alert = alert_system.check_product_stock(product)
    print(f"Alert created: {alert}")
    
    # Get active alerts
    active = alert_system.get_active_alerts()
    print(f"Active alerts: {len(active)}")
    
    # Get summary
    summary = alert_system.get_alert_summary()
    print(f"Alert summary: {summary}")
    
    session.close()
    print("Alert system test completed!")
