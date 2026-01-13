"""
Grocery Inventory Management System - Main Application
A comprehensive CLI interface for managing grocery store inventory
"""

import sys
import os
from datetime import datetime
from typing import Optional

# Try to import rich for beautiful console output, fallback to basic if not available
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.prompt import Prompt, IntPrompt, FloatPrompt, Confirm
    from rich.text import Text
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Note: Install 'rich' package for a better UI experience: pip install rich")

from models import Category, TransactionType, OrderStatus, AlertStatus
from inventory_manager import InventoryManager
from alert_system import AlertSystem, ConsoleAlertObserver, InventoryMonitor
from restock_manager import RestockManager, QuickRestock


class GroceryInventoryApp:
    """Main application class for the Grocery Inventory System"""
    
    def __init__(self, db_path: str = "grocery_inventory.db"):
        self.db_path = db_path
        self.inventory = InventoryManager(db_path)
        self.alert_system = AlertSystem(self.inventory.session)
        self.restock_manager = RestockManager(self.inventory.session)
        self.quick_restock = QuickRestock(self.inventory.session)
        self.monitor: Optional[InventoryMonitor] = None
        
        # Setup console
        if RICH_AVAILABLE:
            self.console = Console()
        
        # Add console observer for alerts
        self.alert_system.add_observer(ConsoleAlertObserver())
    
    def clear_screen(self):
        """Clear the terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self, title: str):
        """Print a styled header"""
        if RICH_AVAILABLE:
            self.console.print(Panel(title, style="bold blue", box=box.DOUBLE))
        else:
            print(f"\n{'='*60}")
            print(f"  {title}")
            print(f"{'='*60}\n")
    
    def print_success(self, message: str):
        """Print a success message"""
        if RICH_AVAILABLE:
            self.console.print(f"✅ {message}", style="bold green")
        else:
            print(f"[SUCCESS] {message}")
    
    def print_error(self, message: str):
        """Print an error message"""
        if RICH_AVAILABLE:
            self.console.print(f"❌ {message}", style="bold red")
        else:
            print(f"[ERROR] {message}")
    
    def print_warning(self, message: str):
        """Print a warning message"""
        if RICH_AVAILABLE:
            self.console.print(f"⚠️  {message}", style="bold yellow")
        else:
            print(f"[WARNING] {message}")
    
    def print_info(self, message: str):
        """Print an info message"""
        if RICH_AVAILABLE:
            self.console.print(f"ℹ️  {message}", style="bold cyan")
        else:
            print(f"[INFO] {message}")
    
    def get_input(self, prompt: str, default: str = None) -> str:
        """Get string input from user"""
        if RICH_AVAILABLE:
            return Prompt.ask(prompt, default=default or "")
        else:
            result = input(f"{prompt} [{default or ''}]: ").strip()
            return result if result else (default or "")
    
    def get_int(self, prompt: str, default: int = None) -> int:
        """Get integer input from user"""
        if RICH_AVAILABLE:
            return IntPrompt.ask(prompt, default=default)
        else:
            try:
                result = input(f"{prompt} [{default}]: ").strip()
                return int(result) if result else default
            except ValueError:
                return default
    
    def get_float(self, prompt: str, default: float = None) -> float:
        """Get float input from user"""
        if RICH_AVAILABLE:
            return FloatPrompt.ask(prompt, default=default)
        else:
            try:
                result = input(f"{prompt} [{default}]: ").strip()
                return float(result) if result else default
            except ValueError:
                return default
    
    def confirm(self, prompt: str, default: bool = False) -> bool:
        """Get yes/no confirmation from user"""
        if RICH_AVAILABLE:
            return Confirm.ask(prompt, default=default)
        else:
            result = input(f"{prompt} (y/n) [{('y' if default else 'n')}]: ").strip().lower()
            if not result:
                return default
            return result in ['y', 'yes']
    
    def wait_for_key(self):
        """Wait for user to press Enter"""
        input("\nPress Enter to continue...")
    
    # ==================== Main Menu ====================
    
    def show_main_menu(self):
        """Display the main menu"""
        self.print_header("🛒 Grocery Inventory Management System")
        
        menu_options = [
            ("1", "📦 Product Management"),
            ("2", "🏢 Supplier Management"),
            ("3", "📊 Inventory Operations"),
            ("4", "🔔 Alerts & Notifications"),
            ("5", "📋 Restock Orders"),
            ("6", "📈 Reports & Analytics"),
            ("7", "⚙️  Settings & Tools"),
            ("0", "🚪 Exit")
        ]
        
        if RICH_AVAILABLE:
            table = Table(show_header=False, box=box.ROUNDED)
            table.add_column("Option", style="cyan", width=4)
            table.add_column("Description", style="white")
            for opt, desc in menu_options:
                table.add_row(opt, desc)
            self.console.print(table)
        else:
            for opt, desc in menu_options:
                print(f"  {opt}. {desc}")
        
        return self.get_input("\nSelect option")
    
    def run(self):
        """Main application loop"""
        self.clear_screen()
        
        # Show welcome message
        if RICH_AVAILABLE:
            self.console.print(Panel(
                "[bold green]Welcome to the Grocery Inventory System![/bold green]\n"
                "Manage your store's products, track stock levels, and automate restocking.",
                title="🛒 Grocery Store Inventory",
                box=box.DOUBLE
            ))
        else:
            print("\n" + "="*60)
            print("  Welcome to the Grocery Inventory System!")
            print("  Manage products, track stock, and automate restocking.")
            print("="*60 + "\n")
        
        while True:
            try:
                choice = self.show_main_menu()
                
                if choice == "0":
                    if self.confirm("Are you sure you want to exit?"):
                        self.print_info("Goodbye! 👋")
                        if self.monitor and self.monitor.is_running:
                            self.monitor.stop()
                        self.inventory.close()
                        break
                elif choice == "1":
                    self.product_menu()
                elif choice == "2":
                    self.supplier_menu()
                elif choice == "3":
                    self.inventory_menu()
                elif choice == "4":
                    self.alerts_menu()
                elif choice == "5":
                    self.restock_menu()
                elif choice == "6":
                    self.reports_menu()
                elif choice == "7":
                    self.settings_menu()
                else:
                    self.print_error("Invalid option. Please try again.")
                
            except KeyboardInterrupt:
                print("\n")
                if self.confirm("Exit application?"):
                    self.inventory.close()
                    break
            except Exception as e:
                self.print_error(f"An error occurred: {e}")
                self.wait_for_key()
    
    # ==================== Product Management ====================
    
    def product_menu(self):
        """Product management submenu"""
        while True:
            self.clear_screen()
            self.print_header("📦 Product Management")
            
            options = [
                ("1", "View All Products"),
                ("2", "Add New Product"),
                ("3", "Search Products"),
                ("4", "Update Product"),
                ("5", "View Product Details"),
                ("6", "Deactivate Product"),
                ("0", "Back to Main Menu")
            ]
            
            for opt, desc in options:
                print(f"  {opt}. {desc}")
            
            choice = self.get_input("\nSelect option")
            
            if choice == "0":
                break
            elif choice == "1":
                self.view_all_products()
            elif choice == "2":
                self.add_product()
            elif choice == "3":
                self.search_products()
            elif choice == "4":
                self.update_product()
            elif choice == "5":
                self.view_product_details()
            elif choice == "6":
                self.deactivate_product()
    
    def view_all_products(self):
        """Display all products in a table"""
        self.clear_screen()
        self.print_header("📦 All Products")
        
        products = self.inventory.get_all_products()
        
        if not products:
            self.print_warning("No products found.")
            self.wait_for_key()
            return
        
        if RICH_AVAILABLE:
            table = Table(title=f"Total: {len(products)} products", box=box.ROUNDED)
            table.add_column("ID", style="cyan", justify="right")
            table.add_column("SKU", style="yellow")
            table.add_column("Name", style="white")
            table.add_column("Category", style="magenta")
            table.add_column("Price", style="green", justify="right")
            table.add_column("Stock", justify="right")
            table.add_column("Status", justify="center")
            
            for p in products:
                stock_style = "red" if p.is_out_of_stock else "yellow" if p.is_low_stock else "green"
                status_emoji = "🔴" if p.is_out_of_stock else "🟡" if p.is_low_stock else "🟢"
                table.add_row(
                    str(p.id),
                    p.sku,
                    p.name[:30],
                    p.category.value if p.category else "N/A",
                    f"${p.price:.2f}",
                    f"[{stock_style}]{p.current_stock}[/{stock_style}]",
                    status_emoji
                )
            
            self.console.print(table)
        else:
            print(f"\n{'ID':<4} {'SKU':<12} {'Name':<25} {'Category':<12} {'Price':>8} {'Stock':>6} {'Status':<10}")
            print("-" * 85)
            for p in products:
                status = "OUT" if p.is_out_of_stock else "LOW" if p.is_low_stock else "OK"
                print(f"{p.id:<4} {p.sku:<12} {p.name[:25]:<25} {(p.category.value if p.category else 'N/A'):<12} ${p.price:>7.2f} {p.current_stock:>6} {status:<10}")
        
        self.wait_for_key()
    
    def add_product(self):
        """Add a new product"""
        self.clear_screen()
        self.print_header("➕ Add New Product")
        
        # Get product details
        sku = self.get_input("SKU (unique identifier)")
        if not sku:
            self.print_error("SKU is required.")
            self.wait_for_key()
            return
        
        # Check if SKU exists
        if self.inventory.get_product_by_sku(sku):
            self.print_error(f"Product with SKU '{sku}' already exists.")
            self.wait_for_key()
            return
        
        name = self.get_input("Product Name")
        if not name:
            self.print_error("Product name is required.")
            self.wait_for_key()
            return
        
        description = self.get_input("Description (optional)")
        
        # Category selection
        print("\nCategories:")
        categories = list(Category)
        for i, cat in enumerate(categories, 1):
            print(f"  {i}. {cat.value}")
        cat_idx = self.get_int("Select category", 12) - 1
        category = categories[cat_idx] if 0 <= cat_idx < len(categories) else Category.OTHER
        
        price = self.get_float("Selling Price", 0.00)
        cost = self.get_float("Cost Price", 0.00)
        unit = self.get_input("Unit (piece, lb, kg, etc.)", "piece")
        
        initial_stock = self.get_int("Initial Stock", 0)
        min_stock = self.get_int("Minimum Stock Level", 10)
        max_stock = self.get_int("Maximum Stock Level", 100)
        reorder_qty = self.get_int("Reorder Quantity", 50)
        
        barcode = self.get_input("Barcode (optional)")
        brand = self.get_input("Brand (optional)")
        location = self.get_input("Store Location/Aisle (optional)")
        
        # Supplier selection
        suppliers = self.inventory.get_all_suppliers()
        supplier_id = None
        if suppliers:
            print("\nAvailable Suppliers:")
            for s in suppliers:
                print(f"  {s.id}. {s.name}")
            print("  0. No supplier")
            sup_choice = self.get_int("Select Supplier", 0)
            if sup_choice > 0:
                supplier_id = sup_choice
        
        is_perishable = self.confirm("Is this a perishable item?", False)
        expiry_days = None
        if is_perishable:
            expiry_days = self.get_int("Shelf life in days", 7)
        
        # Confirm and save
        if self.confirm("\nSave this product?", True):
            try:
                product = self.inventory.add_product(
                    sku=sku,
                    name=name,
                    description=description,
                    category=category,
                    price=price,
                    cost=cost,
                    unit=unit,
                    initial_stock=initial_stock,
                    min_stock_level=min_stock,
                    max_stock_level=max_stock,
                    reorder_quantity=reorder_qty,
                    barcode=barcode or None,
                    brand=brand or None,
                    location=location or None,
                    supplier_id=supplier_id,
                    is_perishable=is_perishable,
                    expiry_days=expiry_days
                )
                self.print_success(f"Product '{product.name}' added successfully! (ID: {product.id})")
            except Exception as e:
                self.print_error(f"Failed to add product: {e}")
        
        self.wait_for_key()
    
    def search_products(self):
        """Search for products"""
        self.clear_screen()
        self.print_header("🔍 Search Products")
        
        search_term = self.get_input("Search (name, SKU, or barcode)")
        if not search_term:
            return
        
        products = self.inventory.search_products(search_term)
        
        if not products:
            self.print_warning(f"No products found matching '{search_term}'")
        else:
            self.print_info(f"Found {len(products)} product(s):")
            print()
            for p in products:
                status = "OUT OF STOCK" if p.is_out_of_stock else "LOW STOCK" if p.is_low_stock else "In Stock"
                print(f"  [{p.id}] {p.sku} - {p.name}")
                print(f"      Price: ${p.price:.2f} | Stock: {p.current_stock} | Status: {status}")
                print()
        
        self.wait_for_key()
    
    def update_product(self):
        """Update an existing product"""
        self.clear_screen()
        self.print_header("✏️ Update Product")
        
        product_id = self.get_int("Enter Product ID")
        product = self.inventory.get_product(product_id)
        
        if not product:
            self.print_error(f"Product with ID {product_id} not found.")
            self.wait_for_key()
            return
        
        self.print_info(f"Updating: {product.name} (SKU: {product.sku})")
        print("Leave blank to keep current value.\n")
        
        updates = {}
        
        new_name = self.get_input(f"Name [{product.name}]")
        if new_name:
            updates['name'] = new_name
        
        new_desc = self.get_input(f"Description [{product.description or 'None'}]")
        if new_desc:
            updates['description'] = new_desc
        
        new_price = self.get_input(f"Price [{product.price}]")
        if new_price:
            updates['price'] = float(new_price)
        
        new_cost = self.get_input(f"Cost [{product.cost}]")
        if new_cost:
            updates['cost'] = float(new_cost)
        
        new_min = self.get_input(f"Min Stock Level [{product.min_stock_level}]")
        if new_min:
            updates['min_stock_level'] = int(new_min)
        
        new_max = self.get_input(f"Max Stock Level [{product.max_stock_level}]")
        if new_max:
            updates['max_stock_level'] = int(new_max)
        
        new_reorder = self.get_input(f"Reorder Quantity [{product.reorder_quantity}]")
        if new_reorder:
            updates['reorder_quantity'] = int(new_reorder)
        
        new_location = self.get_input(f"Location [{product.location or 'None'}]")
        if new_location:
            updates['location'] = new_location
        
        if updates and self.confirm("\nSave changes?", True):
            self.inventory.update_product(product_id, **updates)
            self.print_success("Product updated successfully!")
        else:
            self.print_info("No changes made.")
        
        self.wait_for_key()
    
    def view_product_details(self):
        """View detailed product information"""
        self.clear_screen()
        self.print_header("📋 Product Details")
        
        product_id = self.get_int("Enter Product ID")
        product = self.inventory.get_product(product_id)
        
        if not product:
            self.print_error(f"Product with ID {product_id} not found.")
            self.wait_for_key()
            return
        
        if RICH_AVAILABLE:
            details = f"""
[bold]SKU:[/bold] {product.sku}
[bold]Name:[/bold] {product.name}
[bold]Description:[/bold] {product.description or 'N/A'}
[bold]Category:[/bold] {product.category.value if product.category else 'N/A'}
[bold]Brand:[/bold] {product.brand or 'N/A'}
[bold]Barcode:[/bold] {product.barcode or 'N/A'}

[bold cyan]Pricing:[/bold cyan]
  Selling Price: ${product.price:.2f}
  Cost: ${product.cost:.2f}
  Profit Margin: {product.profit_margin:.1f}%

[bold cyan]Stock Information:[/bold cyan]
  Current Stock: {product.current_stock} {product.unit}
  Min Level: {product.min_stock_level}
  Max Level: {product.max_stock_level}
  Reorder Qty: {product.reorder_quantity}
  Status: {product.stock_status}

[bold cyan]Other:[/bold cyan]
  Location: {product.location or 'N/A'}
  Perishable: {'Yes' if product.is_perishable else 'No'}
  Shelf Life: {product.expiry_days or 'N/A'} days
  Supplier: {product.supplier.name if product.supplier else 'N/A'}
  Active: {'Yes' if product.is_active else 'No'}
"""
            self.console.print(Panel(details, title=f"Product #{product.id}", box=box.ROUNDED))
        else:
            print(f"\n{'='*50}")
            print(f"Product #{product.id}")
            print(f"{'='*50}")
            print(f"SKU: {product.sku}")
            print(f"Name: {product.name}")
            print(f"Category: {product.category.value if product.category else 'N/A'}")
            print(f"Price: ${product.price:.2f} | Cost: ${product.cost:.2f}")
            print(f"Stock: {product.current_stock} | Status: {product.stock_status}")
            print(f"Supplier: {product.supplier.name if product.supplier else 'N/A'}")
        
        # Show recent transactions
        print("\n📜 Recent Transactions:")
        transactions = self.inventory.get_transactions(product_id=product_id, limit=5)
        if transactions:
            for t in transactions:
                print(f"  {t.created_at.strftime('%Y-%m-%d %H:%M')} | {t.transaction_type.value} | Qty: {t.quantity:+d} | Stock: {t.previous_stock} → {t.new_stock}")
        else:
            print("  No transactions recorded.")
        
        self.wait_for_key()
    
    def deactivate_product(self):
        """Deactivate a product"""
        self.clear_screen()
        self.print_header("🗑️ Deactivate Product")
        
        product_id = self.get_int("Enter Product ID")
        product = self.inventory.get_product(product_id)
        
        if not product:
            self.print_error(f"Product with ID {product_id} not found.")
            self.wait_for_key()
            return
        
        self.print_warning(f"You are about to deactivate: {product.name} (SKU: {product.sku})")
        
        if self.confirm("Are you sure?", False):
            self.inventory.deactivate_product(product_id)
            self.print_success("Product deactivated successfully!")
        else:
            self.print_info("Cancelled.")
        
        self.wait_for_key()
    
    # ==================== Supplier Management ====================
    
    def supplier_menu(self):
        """Supplier management submenu"""
        while True:
            self.clear_screen()
            self.print_header("🏢 Supplier Management")
            
            options = [
                ("1", "View All Suppliers"),
                ("2", "Add New Supplier"),
                ("3", "Update Supplier"),
                ("4", "View Supplier Products"),
                ("5", "Deactivate Supplier"),
                ("0", "Back to Main Menu")
            ]
            
            for opt, desc in options:
                print(f"  {opt}. {desc}")
            
            choice = self.get_input("\nSelect option")
            
            if choice == "0":
                break
            elif choice == "1":
                self.view_all_suppliers()
            elif choice == "2":
                self.add_supplier()
            elif choice == "3":
                self.update_supplier()
            elif choice == "4":
                self.view_supplier_products()
            elif choice == "5":
                self.deactivate_supplier()
    
    def view_all_suppliers(self):
        """Display all suppliers"""
        self.clear_screen()
        self.print_header("🏢 All Suppliers")
        
        suppliers = self.inventory.get_all_suppliers()
        
        if not suppliers:
            self.print_warning("No suppliers found.")
            self.wait_for_key()
            return
        
        if RICH_AVAILABLE:
            table = Table(box=box.ROUNDED)
            table.add_column("ID", style="cyan", justify="right")
            table.add_column("Name", style="white")
            table.add_column("Contact", style="yellow")
            table.add_column("Email", style="green")
            table.add_column("Phone", style="magenta")
            table.add_column("Lead Time", justify="right")
            
            for s in suppliers:
                table.add_row(
                    str(s.id),
                    s.name,
                    s.contact_person or "N/A",
                    s.email or "N/A",
                    s.phone or "N/A",
                    f"{s.lead_time_days} days"
                )
            
            self.console.print(table)
        else:
            print(f"\n{'ID':<4} {'Name':<25} {'Contact':<20} {'Email':<25} {'Lead Time':>10}")
            print("-" * 90)
            for s in suppliers:
                print(f"{s.id:<4} {s.name:<25} {(s.contact_person or 'N/A'):<20} {(s.email or 'N/A'):<25} {s.lead_time_days:>6} days")
        
        self.wait_for_key()
    
    def add_supplier(self):
        """Add a new supplier"""
        self.clear_screen()
        self.print_header("➕ Add New Supplier")
        
        name = self.get_input("Supplier Name")
        if not name:
            self.print_error("Supplier name is required.")
            self.wait_for_key()
            return
        
        contact_person = self.get_input("Contact Person (optional)")
        email = self.get_input("Email (optional)")
        phone = self.get_input("Phone (optional)")
        address = self.get_input("Address (optional)")
        city = self.get_input("City (optional)")
        state = self.get_input("State (optional)")
        zip_code = self.get_input("ZIP Code (optional)")
        country = self.get_input("Country", "USA")
        lead_time = self.get_int("Lead Time (days)", 3)
        
        if self.confirm("\nSave this supplier?", True):
            try:
                supplier = self.inventory.add_supplier(
                    name=name,
                    contact_person=contact_person or None,
                    email=email or None,
                    phone=phone or None,
                    address=address or None,
                    city=city or None,
                    state=state or None,
                    zip_code=zip_code or None,
                    country=country,
                    lead_time_days=lead_time
                )
                self.print_success(f"Supplier '{supplier.name}' added successfully! (ID: {supplier.id})")
            except Exception as e:
                self.print_error(f"Failed to add supplier: {e}")
        
        self.wait_for_key()
    
    def update_supplier(self):
        """Update supplier information"""
        self.clear_screen()
        self.print_header("✏️ Update Supplier")
        
        supplier_id = self.get_int("Enter Supplier ID")
        supplier = self.inventory.get_supplier(supplier_id)
        
        if not supplier:
            self.print_error(f"Supplier with ID {supplier_id} not found.")
            self.wait_for_key()
            return
        
        self.print_info(f"Updating: {supplier.name}")
        print("Leave blank to keep current value.\n")
        
        updates = {}
        
        new_name = self.get_input(f"Name [{supplier.name}]")
        if new_name:
            updates['name'] = new_name
        
        new_contact = self.get_input(f"Contact Person [{supplier.contact_person or 'None'}]")
        if new_contact:
            updates['contact_person'] = new_contact
        
        new_email = self.get_input(f"Email [{supplier.email or 'None'}]")
        if new_email:
            updates['email'] = new_email
        
        new_phone = self.get_input(f"Phone [{supplier.phone or 'None'}]")
        if new_phone:
            updates['phone'] = new_phone
        
        new_lead = self.get_input(f"Lead Time Days [{supplier.lead_time_days}]")
        if new_lead:
            updates['lead_time_days'] = int(new_lead)
        
        if updates and self.confirm("\nSave changes?", True):
            self.inventory.update_supplier(supplier_id, **updates)
            self.print_success("Supplier updated successfully!")
        else:
            self.print_info("No changes made.")
        
        self.wait_for_key()
    
    def view_supplier_products(self):
        """View products from a specific supplier"""
        self.clear_screen()
        self.print_header("📦 Supplier Products")
        
        supplier_id = self.get_int("Enter Supplier ID")
        supplier = self.inventory.get_supplier(supplier_id)
        
        if not supplier:
            self.print_error(f"Supplier with ID {supplier_id} not found.")
            self.wait_for_key()
            return
        
        products = self.inventory.get_products_by_supplier(supplier_id)
        
        self.print_info(f"Products from: {supplier.name}")
        
        if not products:
            self.print_warning("No products from this supplier.")
        else:
            print(f"\nTotal: {len(products)} product(s)\n")
            for p in products:
                status = "🔴" if p.is_out_of_stock else "🟡" if p.is_low_stock else "🟢"
                print(f"  {status} [{p.id}] {p.sku} - {p.name} | Stock: {p.current_stock}")
        
        self.wait_for_key()
    
    def deactivate_supplier(self):
        """Deactivate a supplier"""
        self.clear_screen()
        self.print_header("🗑️ Deactivate Supplier")
        
        supplier_id = self.get_int("Enter Supplier ID")
        supplier = self.inventory.get_supplier(supplier_id)
        
        if not supplier:
            self.print_error(f"Supplier with ID {supplier_id} not found.")
            self.wait_for_key()
            return
        
        self.print_warning(f"You are about to deactivate: {supplier.name}")
        
        if self.confirm("Are you sure?", False):
            self.inventory.deactivate_supplier(supplier_id)
            self.print_success("Supplier deactivated successfully!")
        else:
            self.print_info("Cancelled.")
        
        self.wait_for_key()
    
    # ==================== Inventory Operations ====================
    
    def inventory_menu(self):
        """Inventory operations submenu"""
        while True:
            self.clear_screen()
            self.print_header("📊 Inventory Operations")
            
            options = [
                ("1", "Record Sale"),
                ("2", "Quick Restock"),
                ("3", "Process Return"),
                ("4", "Adjust Stock"),
                ("5", "Mark Expired/Damaged"),
                ("6", "View Low Stock"),
                ("7", "View Transaction History"),
                ("0", "Back to Main Menu")
            ]
            
            for opt, desc in options:
                print(f"  {opt}. {desc}")
            
            choice = self.get_input("\nSelect option")
            
            if choice == "0":
                break
            elif choice == "1":
                self.record_sale()
            elif choice == "2":
                self.quick_restock_menu()
            elif choice == "3":
                self.process_return()
            elif choice == "4":
                self.adjust_stock()
            elif choice == "5":
                self.mark_expired_damaged()
            elif choice == "6":
                self.view_low_stock()
            elif choice == "7":
                self.view_transactions()
    
    def record_sale(self):
        """Record a product sale"""
        self.clear_screen()
        self.print_header("💰 Record Sale")
        
        product_id = self.get_int("Enter Product ID")
        product = self.inventory.get_product(product_id)
        
        if not product:
            self.print_error(f"Product with ID {product_id} not found.")
            self.wait_for_key()
            return
        
        self.print_info(f"Product: {product.name}")
        self.print_info(f"Current Stock: {product.current_stock} {product.unit}")
        
        quantity = self.get_int("Quantity sold", 1)
        
        if quantity > product.current_stock:
            self.print_error(f"Insufficient stock! Only {product.current_stock} available.")
            self.wait_for_key()
            return
        
        reference = self.get_input("Receipt/Reference Number (optional)")
        
        try:
            transaction = self.inventory.sell_product(
                product_id=product_id,
                quantity=quantity,
                reference_number=reference or None
            )
            self.print_success(f"Sale recorded! New stock: {product.current_stock}")
        except Exception as e:
            self.print_error(f"Failed to record sale: {e}")
        
        self.wait_for_key()
    
    def quick_restock_menu(self):
        """Quick restock options"""
        self.clear_screen()
        self.print_header("📦 Quick Restock")
        
        print("  1. Restock Single Product")
        print("  2. Restock All Low Stock Products")
        print("  0. Back")
        
        choice = self.get_input("\nSelect option")
        
        if choice == "1":
            product_id = self.get_int("Enter Product ID")
            product = self.inventory.get_product(product_id)
            
            if not product:
                self.print_error(f"Product with ID {product_id} not found.")
                self.wait_for_key()
                return
            
            self.print_info(f"Product: {product.name}")
            self.print_info(f"Current Stock: {product.current_stock}")
            self.print_info(f"Suggested Reorder Qty: {product.reorder_quantity}")
            
            quantity = self.get_int("Quantity to add", product.reorder_quantity)
            
            transaction = self.quick_restock.quick_restock_product(product_id, quantity)
            if transaction:
                self.print_success(f"Restocked! New stock: {product.current_stock}")
            
        elif choice == "2":
            low_stock = self.inventory.get_low_stock_products()
            if not low_stock:
                self.print_info("No products are low on stock.")
                self.wait_for_key()
                return
            
            self.print_warning(f"{len(low_stock)} products are low on stock:")
            for p in low_stock[:10]:
                print(f"  - {p.name}: {p.current_stock}/{p.min_stock_level}")
            
            if self.confirm("\nRestock all these products?", False):
                transactions = self.quick_restock.quick_restock_all_low()
                self.print_success(f"Restocked {len(transactions)} products!")
        
        self.wait_for_key()
    
    def process_return(self):
        """Process a product return"""
        self.clear_screen()
        self.print_header("↩️ Process Return")
        
        product_id = self.get_int("Enter Product ID")
        product = self.inventory.get_product(product_id)
        
        if not product:
            self.print_error(f"Product with ID {product_id} not found.")
            self.wait_for_key()
            return
        
        self.print_info(f"Product: {product.name}")
        
        quantity = self.get_int("Quantity returned", 1)
        reference = self.get_input("Original Receipt/Reference (optional)")
        
        try:
            transaction = self.inventory.return_product(
                product_id=product_id,
                quantity=quantity,
                reference_number=reference or None
            )
            self.print_success(f"Return processed! New stock: {product.current_stock}")
        except Exception as e:
            self.print_error(f"Failed to process return: {e}")
        
        self.wait_for_key()
    
    def adjust_stock(self):
        """Adjust stock to a specific level"""
        self.clear_screen()
        self.print_header("🔧 Adjust Stock")
        
        product_id = self.get_int("Enter Product ID")
        product = self.inventory.get_product(product_id)
        
        if not product:
            self.print_error(f"Product with ID {product_id} not found.")
            self.wait_for_key()
            return
        
        self.print_info(f"Product: {product.name}")
        self.print_info(f"Current Stock: {product.current_stock}")
        
        new_stock = self.get_int("New Stock Level")
        reason = self.get_input("Reason for adjustment")
        
        try:
            transaction = self.inventory.adjust_stock(
                product_id=product_id,
                new_stock_level=new_stock,
                reason=reason
            )
            self.print_success(f"Stock adjusted! New stock: {product.current_stock}")
        except Exception as e:
            self.print_error(f"Failed to adjust stock: {e}")
        
        self.wait_for_key()
    
    def mark_expired_damaged(self):
        """Mark items as expired or damaged"""
        self.clear_screen()
        self.print_header("⚠️ Mark Expired/Damaged")
        
        print("  1. Mark as Expired")
        print("  2. Mark as Damaged")
        print("  0. Back")
        
        choice = self.get_input("\nSelect option")
        
        if choice == "0":
            return
        
        product_id = self.get_int("Enter Product ID")
        product = self.inventory.get_product(product_id)
        
        if not product:
            self.print_error(f"Product with ID {product_id} not found.")
            self.wait_for_key()
            return
        
        self.print_info(f"Product: {product.name}")
        self.print_info(f"Current Stock: {product.current_stock}")
        
        quantity = self.get_int("Quantity to remove", 1)
        
        if quantity > product.current_stock:
            self.print_error(f"Cannot remove more than current stock ({product.current_stock})")
            self.wait_for_key()
            return
        
        try:
            if choice == "1":
                transaction = self.inventory.mark_expired(product_id, quantity)
                self.print_success(f"Marked {quantity} units as expired. New stock: {product.current_stock}")
            else:
                notes = self.get_input("Damage description (optional)")
                transaction = self.inventory.mark_damaged(product_id, quantity, notes)
                self.print_success(f"Marked {quantity} units as damaged. New stock: {product.current_stock}")
        except Exception as e:
            self.print_error(f"Failed: {e}")
        
        self.wait_for_key()
    
    def view_low_stock(self):
        """View all low stock products"""
        self.clear_screen()
        self.print_header("📉 Low Stock Products")
        
        low_stock = self.inventory.get_low_stock_products()
        out_of_stock = self.inventory.get_out_of_stock_products()
        
        if RICH_AVAILABLE:
            if out_of_stock:
                self.console.print("\n[bold red]🔴 OUT OF STOCK[/bold red]")
                for p in out_of_stock:
                    self.console.print(f"  [{p.id}] {p.sku} - {p.name}")
            
            low_only = [p for p in low_stock if p not in out_of_stock]
            if low_only:
                self.console.print("\n[bold yellow]🟡 LOW STOCK[/bold yellow]")
                for p in low_only:
                    self.console.print(f"  [{p.id}] {p.sku} - {p.name} | Stock: {p.current_stock}/{p.min_stock_level}")
            
            if not low_stock:
                self.console.print("[bold green]✅ All products are well-stocked![/bold green]")
        else:
            print(f"\nOut of Stock: {len(out_of_stock)}")
            for p in out_of_stock:
                print(f"  [OUT] {p.sku} - {p.name}")
            
            low_only = [p for p in low_stock if p not in out_of_stock]
            print(f"\nLow Stock: {len(low_only)}")
            for p in low_only:
                print(f"  [LOW] {p.sku} - {p.name} | {p.current_stock}/{p.min_stock_level}")
        
        self.wait_for_key()
    
    def view_transactions(self):
        """View transaction history"""
        self.clear_screen()
        self.print_header("📜 Transaction History")
        
        product_id = self.get_input("Product ID (leave blank for all)")
        product_id = int(product_id) if product_id else None
        
        limit = self.get_int("Number of transactions to show", 20)
        
        transactions = self.inventory.get_transactions(
            product_id=product_id,
            limit=limit
        )
        
        if not transactions:
            self.print_warning("No transactions found.")
            self.wait_for_key()
            return
        
        if RICH_AVAILABLE:
            table = Table(box=box.ROUNDED)
            table.add_column("Date", style="cyan")
            table.add_column("Product", style="white")
            table.add_column("Type", style="yellow")
            table.add_column("Qty", justify="right")
            table.add_column("Stock", justify="center")
            table.add_column("By", style="magenta")
            
            for t in transactions:
                qty_style = "green" if t.quantity > 0 else "red"
                table.add_row(
                    t.created_at.strftime("%Y-%m-%d %H:%M"),
                    t.product.name[:20] if t.product else "N/A",
                    t.transaction_type.value,
                    f"[{qty_style}]{t.quantity:+d}[/{qty_style}]",
                    f"{t.previous_stock} → {t.new_stock}",
                    t.performed_by or "System"
                )
            
            self.console.print(table)
        else:
            print(f"\n{'Date':<18} {'Product':<20} {'Type':<12} {'Qty':>6} {'Stock':>10}")
            print("-" * 70)
            for t in transactions:
                print(f"{t.created_at.strftime('%Y-%m-%d %H:%M'):<18} {(t.product.name[:20] if t.product else 'N/A'):<20} {t.transaction_type.value:<12} {t.quantity:>+6} {t.previous_stock:>4} → {t.new_stock:<4}")
        
        self.wait_for_key()
    
    # ==================== Alerts Menu ====================
    
    def alerts_menu(self):
        """Alerts management submenu"""
        while True:
            self.clear_screen()
            self.print_header("🔔 Alerts & Notifications")
            
            # Show alert summary
            summary = self.alert_system.get_alert_summary()
            if summary['total_active'] > 0:
                self.print_warning(f"Active Alerts: {summary['total_active']}")
                print(f"  🔴 Out of Stock: {summary['out_of_stock']}")
                print(f"  🟠 Critical Low: {summary['critical_low']}")
                print(f"  🟡 Low Stock: {summary['low_stock']}")
            else:
                self.print_success("No active alerts!")
            
            print()
            options = [
                ("1", "View Active Alerts"),
                ("2", "Acknowledge Alert"),
                ("3", "Resolve Alert"),
                ("4", "Check All Products Now"),
                ("5", "Start Background Monitor"),
                ("6", "Stop Background Monitor"),
                ("0", "Back to Main Menu")
            ]
            
            for opt, desc in options:
                print(f"  {opt}. {desc}")
            
            choice = self.get_input("\nSelect option")
            
            if choice == "0":
                break
            elif choice == "1":
                self.view_active_alerts()
            elif choice == "2":
                self.acknowledge_alert()
            elif choice == "3":
                self.resolve_alert()
            elif choice == "4":
                self.check_all_now()
            elif choice == "5":
                self.start_monitor()
            elif choice == "6":
                self.stop_monitor()
    
    def view_active_alerts(self):
        """View all active alerts"""
        self.clear_screen()
        self.print_header("🔔 Active Alerts")
        
        alerts = self.alert_system.get_active_alerts()
        
        if not alerts:
            self.print_success("No active alerts!")
            self.wait_for_key()
            return
        
        for alert in alerts:
            icon = "🔴" if alert.alert_type == "OUT_OF_STOCK" else "🟠" if alert.alert_type == "CRITICAL_LOW" else "🟡"
            print(f"\n{icon} Alert #{alert.id}")
            print(f"   Type: {alert.alert_type}")
            print(f"   Product: {alert.product.name if alert.product else 'N/A'}")
            print(f"   Message: {alert.message}")
            print(f"   Created: {alert.created_at.strftime('%Y-%m-%d %H:%M')}")
            print(f"   Status: {alert.status.value}")
        
        self.wait_for_key()
    
    def acknowledge_alert(self):
        """Acknowledge an alert"""
        alert_id = self.get_int("Enter Alert ID")
        user = self.get_input("Your name")
        
        if self.alert_system.acknowledge_alert(alert_id, user):
            self.print_success("Alert acknowledged!")
        else:
            self.print_error("Failed to acknowledge alert.")
        
        self.wait_for_key()
    
    def resolve_alert(self):
        """Resolve an alert"""
        alert_id = self.get_int("Enter Alert ID")
        
        if self.alert_system.resolve_alert(alert_id):
            self.print_success("Alert resolved!")
        else:
            self.print_error("Failed to resolve alert.")
        
        self.wait_for_key()
    
    def check_all_now(self):
        """Check all products for alerts"""
        products = self.inventory.get_all_products()
        new_alerts = self.alert_system.check_all_products(products)
        
        if new_alerts:
            self.print_warning(f"Generated {len(new_alerts)} new alert(s)!")
        else:
            self.print_success("All products checked. No new alerts.")
        
        self.wait_for_key()
    
    def start_monitor(self):
        """Start background inventory monitor"""
        if self.monitor and self.monitor.is_running:
            self.print_warning("Monitor is already running!")
        else:
            interval = self.get_int("Check interval (seconds)", 60)
            self.monitor = InventoryMonitor(self.db_path, interval)
            self.monitor.add_observer(ConsoleAlertObserver())
            self.monitor.start()
            self.print_success("Background monitor started!")
        
        self.wait_for_key()
    
    def stop_monitor(self):
        """Stop background inventory monitor"""
        if self.monitor and self.monitor.is_running:
            self.monitor.stop()
            self.print_success("Monitor stopped.")
        else:
            self.print_warning("Monitor is not running.")
        
        self.wait_for_key()
    
    # ==================== Restock Orders Menu ====================
    
    def restock_menu(self):
        """Restock orders submenu"""
        while True:
            self.clear_screen()
            self.print_header("📋 Restock Orders")
            
            # Show pending orders count
            pending = self.restock_manager.get_pending_orders()
            if pending:
                self.print_info(f"Pending Orders: {len(pending)}")
            
            options = [
                ("1", "View Restock Suggestions"),
                ("2", "Create Manual Order"),
                ("3", "Auto-Create Orders (Low Stock)"),
                ("4", "View All Orders"),
                ("5", "View Order Details"),
                ("6", "Update Order Status"),
                ("7", "Receive Order"),
                ("8", "Cancel Order"),
                ("0", "Back to Main Menu")
            ]
            
            for opt, desc in options:
                print(f"  {opt}. {desc}")
            
            choice = self.get_input("\nSelect option")
            
            if choice == "0":
                break
            elif choice == "1":
                self.view_restock_suggestions()
            elif choice == "2":
                self.create_manual_order()
            elif choice == "3":
                self.auto_create_orders()
            elif choice == "4":
                self.view_all_orders()
            elif choice == "5":
                self.view_order_details()
            elif choice == "6":
                self.update_order_status()
            elif choice == "7":
                self.receive_order()
            elif choice == "8":
                self.cancel_order()
    
    def view_restock_suggestions(self):
        """View products that need restocking"""
        self.clear_screen()
        self.print_header("💡 Restock Suggestions")
        
        suggestions = self.restock_manager.get_restock_suggestions()
        
        if not suggestions:
            self.print_success("All products are well-stocked!")
            self.wait_for_key()
            return
        
        if RICH_AVAILABLE:
            table = Table(box=box.ROUNDED)
            table.add_column("Product", style="white")
            table.add_column("SKU", style="cyan")
            table.add_column("Stock", justify="right")
            table.add_column("Min", justify="right")
            table.add_column("Suggested Qty", justify="right")
            table.add_column("Est. Cost", justify="right", style="green")
            table.add_column("Urgency", justify="center")
            table.add_column("Supplier", style="yellow")
            
            for s in suggestions:
                urgency_color = "red" if s['urgency'] == 'CRITICAL' else "yellow" if s['urgency'] == 'HIGH' else "white"
                table.add_row(
                    s['product_name'][:25],
                    s['sku'],
                    str(s['current_stock']),
                    str(s['min_stock_level']),
                    str(s['suggested_quantity']),
                    f"${s['estimated_cost']:.2f}",
                    f"[{urgency_color}]{s['urgency']}[/{urgency_color}]",
                    s['supplier_name'][:20]
                )
            
            self.console.print(table)
        else:
            print(f"\n{'Product':<25} {'Stock':>6} {'Min':>5} {'Suggested':>10} {'Urgency':<10}")
            print("-" * 65)
            for s in suggestions:
                print(f"{s['product_name'][:25]:<25} {s['current_stock']:>6} {s['min_stock_level']:>5} {s['suggested_quantity']:>10} {s['urgency']:<10}")
        
        self.wait_for_key()
    
    def create_manual_order(self):
        """Create a manual restock order"""
        self.clear_screen()
        self.print_header("📝 Create Manual Order")
        
        # Select supplier
        suppliers = self.inventory.get_all_suppliers()
        if not suppliers:
            self.print_error("No suppliers available. Please add a supplier first.")
            self.wait_for_key()
            return
        
        print("Available Suppliers:")
        for s in suppliers:
            print(f"  {s.id}. {s.name}")
        
        supplier_id = self.get_int("Select Supplier ID")
        supplier = self.inventory.get_supplier(supplier_id)
        
        if not supplier:
            self.print_error("Invalid supplier ID.")
            self.wait_for_key()
            return
        
        # Show supplier's products
        products = self.inventory.get_products_by_supplier(supplier_id)
        if not products:
            self.print_error(f"No products from {supplier.name}.")
            self.wait_for_key()
            return
        
        print(f"\nProducts from {supplier.name}:")
        for p in products:
            print(f"  {p.id}. {p.sku} - {p.name} (Stock: {p.current_stock})")
        
        # Add items to order
        items = []
        while True:
            product_id = self.get_input("\nProduct ID (or 'done' to finish)")
            if product_id.lower() == 'done':
                break
            
            try:
                pid = int(product_id)
                product = self.inventory.get_product(pid)
                if product and product.supplier_id == supplier_id:
                    quantity = self.get_int("Quantity", product.reorder_quantity)
                    items.append({'product_id': pid, 'quantity': quantity})
                    self.print_success(f"Added: {product.name} x {quantity}")
                else:
                    self.print_error("Invalid product or not from this supplier.")
            except ValueError:
                self.print_error("Invalid input.")
        
        if not items:
            self.print_warning("No items added. Order cancelled.")
            self.wait_for_key()
            return
        
        notes = self.get_input("Order notes (optional)")
        
        if self.confirm("\nCreate this order?", True):
            try:
                order = self.restock_manager.create_restock_order(
                    supplier_id=supplier_id,
                    items=items,
                    notes=notes
                )
                self.print_success(f"Order created! Order #: {order.order_number}")
                self.print_info(f"Total: ${order.total_amount:.2f}")
                self.print_info(f"Expected delivery: {order.expected_delivery.strftime('%Y-%m-%d')}")
            except Exception as e:
                self.print_error(f"Failed to create order: {e}")
        
        self.wait_for_key()
    
    def auto_create_orders(self):
        """Automatically create orders for low-stock products"""
        self.clear_screen()
        self.print_header("🤖 Auto-Create Restock Orders")
        
        suggestions = self.restock_manager.get_restock_suggestions()
        
        if not suggestions:
            self.print_success("All products are well-stocked!")
            self.wait_for_key()
            return
        
        self.print_warning(f"{len(suggestions)} products need restocking.")
        
        if self.confirm("Create orders for all low-stock products?", False):
            orders = self.restock_manager.create_auto_restock_order()
            
            if orders:
                self.print_success(f"Created {len(orders)} order(s):")
                for order in orders:
                    print(f"  - {order.order_number} | {order.supplier.name} | ${order.total_amount:.2f}")
            else:
                self.print_warning("No orders created (products may not have suppliers assigned).")
        
        self.wait_for_key()
    
    def view_all_orders(self):
        """View all restock orders"""
        self.clear_screen()
        self.print_header("📋 All Restock Orders")
        
        orders = self.restock_manager.get_orders(limit=50)
        
        if not orders:
            self.print_warning("No orders found.")
            self.wait_for_key()
            return
        
        if RICH_AVAILABLE:
            table = Table(box=box.ROUNDED)
            table.add_column("Order #", style="cyan")
            table.add_column("Supplier", style="white")
            table.add_column("Status", justify="center")
            table.add_column("Items", justify="right")
            table.add_column("Total", justify="right", style="green")
            table.add_column("Order Date", style="yellow")
            
            for o in orders:
                status_color = {
                    OrderStatus.PENDING: "yellow",
                    OrderStatus.CONFIRMED: "blue",
                    OrderStatus.SHIPPED: "magenta",
                    OrderStatus.DELIVERED: "green",
                    OrderStatus.CANCELLED: "red"
                }.get(o.status, "white")
                
                table.add_row(
                    o.order_number,
                    o.supplier.name[:20] if o.supplier else "N/A",
                    f"[{status_color}]{o.status.value}[/{status_color}]",
                    str(len(o.items)),
                    f"${o.total_amount:.2f}" if o.total_amount else "N/A",
                    o.order_date.strftime("%Y-%m-%d") if o.order_date else "N/A"
                )
            
            self.console.print(table)
        else:
            print(f"\n{'Order #':<20} {'Supplier':<20} {'Status':<12} {'Total':>10} {'Date':<12}")
            print("-" * 80)
            for o in orders:
                print(f"{o.order_number:<20} {(o.supplier.name[:20] if o.supplier else 'N/A'):<20} {o.status.value:<12} ${o.total_amount:>9.2f} {o.order_date.strftime('%Y-%m-%d'):<12}")
        
        self.wait_for_key()
    
    def view_order_details(self):
        """View details of a specific order"""
        self.clear_screen()
        self.print_header("📄 Order Details")
        
        order_number = self.get_input("Enter Order Number")
        order = self.restock_manager.get_order_by_number(order_number)
        
        if not order:
            self.print_error(f"Order '{order_number}' not found.")
            self.wait_for_key()
            return
        
        print(f"\n{'='*50}")
        print(f"Order: {order.order_number}")
        print(f"Status: {order.status.value}")
        print(f"Supplier: {order.supplier.name if order.supplier else 'N/A'}")
        print(f"Order Date: {order.order_date.strftime('%Y-%m-%d %H:%M') if order.order_date else 'N/A'}")
        print(f"Expected Delivery: {order.expected_delivery.strftime('%Y-%m-%d') if order.expected_delivery else 'N/A'}")
        if order.actual_delivery:
            print(f"Actual Delivery: {order.actual_delivery.strftime('%Y-%m-%d')}")
        print(f"Notes: {order.notes or 'None'}")
        print(f"{'='*50}")
        
        print("\nOrder Items:")
        for item in order.items:
            received = f" (Received: {item.quantity_received})" if item.quantity_received else ""
            print(f"  - {item.product.name if item.product else 'N/A'}")
            print(f"    SKU: {item.product.sku if item.product else 'N/A'} | Qty: {item.quantity_ordered}{received} | Unit: ${item.unit_cost:.2f} | Total: ${item.total_price:.2f}")
        
        print(f"\n{'='*50}")
        print(f"ORDER TOTAL: ${order.total_amount:.2f}")
        print(f"{'='*50}")
        
        self.wait_for_key()
    
    def update_order_status(self):
        """Update order status"""
        self.clear_screen()
        self.print_header("📝 Update Order Status")
        
        order_number = self.get_input("Enter Order Number")
        order = self.restock_manager.get_order_by_number(order_number)
        
        if not order:
            self.print_error(f"Order '{order_number}' not found.")
            self.wait_for_key()
            return
        
        self.print_info(f"Current Status: {order.status.value}")
        
        print("\nAvailable actions:")
        if order.status == OrderStatus.PENDING:
            print("  1. Confirm Order")
        if order.status == OrderStatus.CONFIRMED:
            print("  2. Mark as Shipped")
        print("  0. Cancel")
        
        choice = self.get_input("Select action")
        
        if choice == "1" and order.status == OrderStatus.PENDING:
            if self.restock_manager.confirm_order(order.id):
                self.print_success("Order confirmed!")
            else:
                self.print_error("Failed to confirm order.")
        elif choice == "2" and order.status == OrderStatus.CONFIRMED:
            if self.restock_manager.mark_shipped(order.id):
                self.print_success("Order marked as shipped!")
            else:
                self.print_error("Failed to update order.")
        
        self.wait_for_key()
    
    def receive_order(self):
        """Receive an order and update inventory"""
        self.clear_screen()
        self.print_header("📥 Receive Order")
        
        order_number = self.get_input("Enter Order Number")
        order = self.restock_manager.get_order_by_number(order_number)
        
        if not order:
            self.print_error(f"Order '{order_number}' not found.")
            self.wait_for_key()
            return
        
        if order.status not in [OrderStatus.CONFIRMED, OrderStatus.SHIPPED]:
            self.print_error(f"Cannot receive order with status: {order.status.value}")
            self.wait_for_key()
            return
        
        self.print_info(f"Receiving order: {order.order_number}")
        print("\nOrder Items:")
        for item in order.items:
            print(f"  - {item.product.name}: {item.quantity_ordered} units")
        
        if self.confirm("\nReceive all items as ordered?", True):
            success, transactions = self.restock_manager.receive_order(order.id)
            if success:
                self.print_success(f"Order received! {len(transactions)} products restocked.")
            else:
                self.print_error("Failed to receive order.")
        else:
            # Custom receiving
            self.print_info("Enter received quantities (leave blank for ordered quantity):")
            received_items = []
            for item in order.items:
                qty = self.get_input(f"  {item.product.name} [{item.quantity_ordered}]")
                received_qty = int(qty) if qty else item.quantity_ordered
                received_items.append({
                    'product_id': item.product_id,
                    'quantity_received': received_qty
                })
            
            success, transactions = self.restock_manager.receive_order(order.id, received_items)
            if success:
                self.print_success(f"Order received! {len(transactions)} products restocked.")
            else:
                self.print_error("Failed to receive order.")
        
        self.wait_for_key()
    
    def cancel_order(self):
        """Cancel a restock order"""
        self.clear_screen()
        self.print_header("❌ Cancel Order")
        
        order_number = self.get_input("Enter Order Number")
        order = self.restock_manager.get_order_by_number(order_number)
        
        if not order:
            self.print_error(f"Order '{order_number}' not found.")
            self.wait_for_key()
            return
        
        if order.status not in [OrderStatus.PENDING, OrderStatus.CONFIRMED]:
            self.print_error(f"Cannot cancel order with status: {order.status.value}")
            self.wait_for_key()
            return
        
        reason = self.get_input("Reason for cancellation")
        
        if self.confirm("Are you sure you want to cancel this order?", False):
            if self.restock_manager.cancel_order(order.id, reason):
                self.print_success("Order cancelled!")
            else:
                self.print_error("Failed to cancel order.")
        
        self.wait_for_key()
    
    # ==================== Reports Menu ====================
    
    def reports_menu(self):
        """Reports and analytics submenu"""
        while True:
            self.clear_screen()
            self.print_header("📈 Reports & Analytics")
            
            options = [
                ("1", "Inventory Summary"),
                ("2", "Stock Value Report"),
                ("3", "Low Stock Report"),
                ("4", "Category Summary"),
                ("5", "Supplier Performance"),
                ("6", "Order Summary"),
                ("0", "Back to Main Menu")
            ]
            
            for opt, desc in options:
                print(f"  {opt}. {desc}")
            
            choice = self.get_input("\nSelect option")
            
            if choice == "0":
                break
            elif choice == "1":
                self.inventory_summary_report()
            elif choice == "2":
                self.stock_value_report()
            elif choice == "3":
                self.low_stock_report()
            elif choice == "4":
                self.category_summary()
            elif choice == "5":
                self.supplier_performance()
            elif choice == "6":
                self.order_summary_report()
    
    def inventory_summary_report(self):
        """Display inventory summary"""
        self.clear_screen()
        self.print_header("📊 Inventory Summary")
        
        summary = self.inventory.get_stock_summary()
        
        if RICH_AVAILABLE:
            self.console.print(Panel(f"""
[bold cyan]Total Products:[/bold cyan] {summary['total_products']}
[bold cyan]Total Units in Stock:[/bold cyan] {summary['total_units']}

[bold yellow]Stock Status:[/bold yellow]
  🔴 Out of Stock: {summary['out_of_stock_count']}
  🟡 Low Stock: {summary['low_stock_count']}
  🟢 Overstocked: {summary['overstocked_count']}

[bold green]Inventory Value:[/bold green]
  Cost Value: ${summary['stock_value']['cost_value']:,.2f}
  Retail Value: ${summary['stock_value']['retail_value']:,.2f}
  Potential Profit: ${summary['stock_value']['potential_profit']:,.2f}
""", title="Inventory Summary", box=box.ROUNDED))
        else:
            print(f"\nTotal Products: {summary['total_products']}")
            print(f"Total Units: {summary['total_units']}")
            print(f"\nStock Status:")
            print(f"  Out of Stock: {summary['out_of_stock_count']}")
            print(f"  Low Stock: {summary['low_stock_count']}")
            print(f"  Overstocked: {summary['overstocked_count']}")
            print(f"\nInventory Value:")
            print(f"  Cost: ${summary['stock_value']['cost_value']:,.2f}")
            print(f"  Retail: ${summary['stock_value']['retail_value']:,.2f}")
            print(f"  Profit: ${summary['stock_value']['potential_profit']:,.2f}")
        
        self.wait_for_key()
    
    def stock_value_report(self):
        """Display stock value by product"""
        self.clear_screen()
        self.print_header("💰 Stock Value Report")
        
        products = self.inventory.get_all_products()
        products_sorted = sorted(products, key=lambda p: p.current_stock * p.price, reverse=True)
        
        total_cost = 0
        total_retail = 0
        
        if RICH_AVAILABLE:
            table = Table(box=box.ROUNDED)
            table.add_column("Product", style="white")
            table.add_column("Stock", justify="right")
            table.add_column("Cost/Unit", justify="right")
            table.add_column("Price/Unit", justify="right")
            table.add_column("Total Cost", justify="right", style="yellow")
            table.add_column("Total Retail", justify="right", style="green")
            
            for p in products_sorted[:20]:
                cost_value = p.current_stock * p.cost
                retail_value = p.current_stock * p.price
                total_cost += cost_value
                total_retail += retail_value
                
                table.add_row(
                    p.name[:30],
                    str(p.current_stock),
                    f"${p.cost:.2f}",
                    f"${p.price:.2f}",
                    f"${cost_value:.2f}",
                    f"${retail_value:.2f}"
                )
            
            self.console.print(table)
            self.console.print(f"\n[bold]Total Cost Value:[/bold] ${total_cost:,.2f}")
            self.console.print(f"[bold]Total Retail Value:[/bold] ${total_retail:,.2f}")
            self.console.print(f"[bold green]Potential Profit:[/bold green] ${total_retail - total_cost:,.2f}")
        else:
            print(f"\n{'Product':<30} {'Stock':>6} {'Cost':>10} {'Retail':>10}")
            print("-" * 60)
            for p in products_sorted[:20]:
                cost_value = p.current_stock * p.cost
                retail_value = p.current_stock * p.price
                total_cost += cost_value
                total_retail += retail_value
                print(f"{p.name[:30]:<30} {p.current_stock:>6} ${cost_value:>9.2f} ${retail_value:>9.2f}")
            print("-" * 60)
            print(f"{'TOTAL':<30} {'':>6} ${total_cost:>9.2f} ${total_retail:>9.2f}")
        
        self.wait_for_key()
    
    def low_stock_report(self):
        """Detailed low stock report"""
        self.clear_screen()
        self.print_header("📉 Low Stock Report")
        
        suggestions = self.restock_manager.get_restock_suggestions()
        
        if not suggestions:
            self.print_success("All products are well-stocked!")
            self.wait_for_key()
            return
        
        critical = [s for s in suggestions if s['urgency'] == 'CRITICAL']
        high = [s for s in suggestions if s['urgency'] == 'HIGH']
        medium = [s for s in suggestions if s['urgency'] == 'MEDIUM']
        
        print(f"\n🔴 CRITICAL ({len(critical)} products - OUT OF STOCK):")
        for s in critical:
            print(f"   {s['sku']} - {s['product_name']}")
            print(f"      Supplier: {s['supplier_name']} | Suggested: {s['suggested_quantity']} units | Cost: ${s['estimated_cost']:.2f}")
        
        print(f"\n🟠 HIGH ({len(high)} products - Below 50% minimum):")
        for s in high:
            print(f"   {s['sku']} - {s['product_name']} | Stock: {s['current_stock']}/{s['min_stock_level']}")
        
        print(f"\n🟡 MEDIUM ({len(medium)} products - Below minimum):")
        for s in medium:
            print(f"   {s['sku']} - {s['product_name']} | Stock: {s['current_stock']}/{s['min_stock_level']}")
        
        total_cost = sum(s['estimated_cost'] for s in suggestions)
        print(f"\n{'='*50}")
        print(f"Total Estimated Restock Cost: ${total_cost:,.2f}")
        
        self.wait_for_key()
    
    def category_summary(self):
        """Summary by category"""
        self.clear_screen()
        self.print_header("📁 Category Summary")
        
        products = self.inventory.get_all_products()
        
        # Group by category
        categories = {}
        for p in products:
            cat = p.category.value if p.category else "Other"
            if cat not in categories:
                categories[cat] = {'count': 0, 'stock': 0, 'value': 0}
            categories[cat]['count'] += 1
            categories[cat]['stock'] += p.current_stock
            categories[cat]['value'] += p.current_stock * p.price
        
        if RICH_AVAILABLE:
            table = Table(box=box.ROUNDED)
            table.add_column("Category", style="cyan")
            table.add_column("Products", justify="right")
            table.add_column("Total Stock", justify="right")
            table.add_column("Total Value", justify="right", style="green")
            
            for cat, data in sorted(categories.items()):
                table.add_row(
                    cat,
                    str(data['count']),
                    str(data['stock']),
                    f"${data['value']:,.2f}"
                )
            
            self.console.print(table)
        else:
            print(f"\n{'Category':<20} {'Products':>10} {'Stock':>10} {'Value':>15}")
            print("-" * 60)
            for cat, data in sorted(categories.items()):
                print(f"{cat:<20} {data['count']:>10} {data['stock']:>10} ${data['value']:>14,.2f}")
        
        self.wait_for_key()
    
    def supplier_performance(self):
        """Supplier performance report"""
        self.clear_screen()
        self.print_header("🏢 Supplier Performance")
        
        suppliers = self.inventory.get_all_suppliers()
        
        for supplier in suppliers:
            history = self.restock_manager.get_supplier_order_history(supplier.id)
            products = self.inventory.get_products_by_supplier(supplier.id)
            
            print(f"\n{'='*50}")
            print(f"📦 {supplier.name}")
            print(f"{'='*50}")
            print(f"  Products: {len(products)}")
            print(f"  Total Orders: {history['total_orders']}")
            print(f"  Delivered: {history['delivered_orders']}")
            print(f"  Cancelled: {history['cancelled_orders']}")
            print(f"  Total Value: ${history['total_value']:,.2f}")
            print(f"  Avg Delivery: {history['average_delivery_days']} days (Lead time: {supplier.lead_time_days})")
        
        self.wait_for_key()
    
    def order_summary_report(self):
        """Order summary report"""
        self.clear_screen()
        self.print_header("📋 Order Summary")
        
        summary = self.restock_manager.get_order_summary()
        
        if RICH_AVAILABLE:
            self.console.print(Panel(f"""
[bold cyan]Total Orders:[/bold cyan] {summary['total_orders']}

[bold]Order Status:[/bold]
  ⏳ Pending: {summary['pending']}
  ✓ Confirmed: {summary['confirmed']}
  🚚 Shipped: {summary['shipped']}
  ✅ Delivered: {summary['delivered']}
  ❌ Cancelled: {summary['cancelled']}

[bold green]Financial:[/bold green]
  Pending Value: ${summary['total_value_pending']:,.2f}
  Delivered Value: ${summary['total_value_delivered']:,.2f}
""", title="Order Summary", box=box.ROUNDED))
        else:
            print(f"\nTotal Orders: {summary['total_orders']}")
            print(f"\nOrder Status:")
            print(f"  Pending: {summary['pending']}")
            print(f"  Confirmed: {summary['confirmed']}")
            print(f"  Shipped: {summary['shipped']}")
            print(f"  Delivered: {summary['delivered']}")
            print(f"  Cancelled: {summary['cancelled']}")
            print(f"\nPending Value: ${summary['total_value_pending']:,.2f}")
            print(f"Delivered Value: ${summary['total_value_delivered']:,.2f}")
        
        self.wait_for_key()
    
    # ==================== Settings Menu ====================
    
    def settings_menu(self):
        """Settings and tools submenu"""
        while True:
            self.clear_screen()
            self.print_header("⚙️ Settings & Tools")
            
            options = [
                ("1", "Add Sample Data"),
                ("2", "Export Data (Coming Soon)"),
                ("3", "Database Info"),
                ("0", "Back to Main Menu")
            ]
            
            for opt, desc in options:
                print(f"  {opt}. {desc}")
            
            choice = self.get_input("\nSelect option")
            
            if choice == "0":
                break
            elif choice == "1":
                self.add_sample_data()
            elif choice == "2":
                self.print_info("Export functionality coming soon!")
                self.wait_for_key()
            elif choice == "3":
                self.show_database_info()
    
    def add_sample_data(self):
        """Add sample data for testing"""
        self.clear_screen()
        self.print_header("📥 Add Sample Data")
        
        if self.confirm("This will add sample suppliers and products. Continue?", False):
            try:
                # Add sample suppliers
                suppliers_data = [
                    ("Fresh Farms Produce", "John Smith", "john@freshfarms.com", "555-0101", 2),
                    ("Dairy Direct", "Mary Johnson", "mary@dairydirect.com", "555-0102", 3),
                    ("Baker's Best", "Bob Williams", "bob@bakersbest.com", "555-0103", 1),
                    ("Meat Masters", "Sarah Davis", "sarah@meatmasters.com", "555-0104", 2),
                    ("Beverage Distributors", "Mike Brown", "mike@bevdist.com", "555-0105", 4),
                ]
                
                suppliers = []
                for name, contact, email, phone, lead_time in suppliers_data:
                    if not self.inventory.get_supplier_by_name(name):
                        supplier = self.inventory.add_supplier(
                            name=name,
                            contact_person=contact,
                            email=email,
                            phone=phone,
                            lead_time_days=lead_time
                        )
                        suppliers.append(supplier)
                        print(f"  ✓ Added supplier: {name}")
                
                # Add sample products
                products_data = [
                    # Produce
                    ("PRD-001", "Organic Bananas", Category.PRODUCE, 0.99, 0.50, "lb", 50, 30, 100),
                    ("PRD-002", "Fresh Apples", Category.PRODUCE, 1.49, 0.80, "lb", 40, 25, 80),
                    ("PRD-003", "Baby Spinach", Category.PRODUCE, 3.99, 2.00, "bag", 25, 15, 50),
                    # Dairy
                    ("DRY-001", "Whole Milk 1 Gallon", Category.DAIRY, 4.99, 2.50, "gallon", 30, 20, 60),
                    ("DRY-002", "Large Eggs Dozen", Category.DAIRY, 5.99, 3.00, "dozen", 40, 25, 80),
                    ("DRY-003", "Cheddar Cheese Block", Category.DAIRY, 6.99, 3.50, "block", 20, 10, 40),
                    # Bakery
                    ("BKR-001", "White Bread Loaf", Category.BAKERY, 2.99, 1.50, "loaf", 50, 30, 100),
                    ("BKR-002", "Croissants 6-Pack", Category.BAKERY, 5.99, 3.00, "pack", 20, 10, 40),
                    # Meat
                    ("MET-001", "Ground Beef 1lb", Category.MEAT, 7.99, 4.00, "lb", 30, 15, 60),
                    ("MET-002", "Chicken Breast 2lb", Category.MEAT, 9.99, 5.00, "lb", 25, 15, 50),
                    # Beverages
                    ("BEV-001", "Bottled Water 24-Pack", Category.BEVERAGES, 5.99, 3.00, "pack", 60, 40, 120),
                    ("BEV-002", "Orange Juice 64oz", Category.BEVERAGES, 4.99, 2.50, "bottle", 30, 20, 60),
                    ("BEV-003", "Cola 12-Pack", Category.BEVERAGES, 6.99, 3.50, "pack", 50, 30, 100),
                ]
                
                # Map categories to suppliers
                category_supplier = {
                    Category.PRODUCE: 0,
                    Category.DAIRY: 1,
                    Category.BAKERY: 2,
                    Category.MEAT: 3,
                    Category.BEVERAGES: 4,
                }
                
                for sku, name, category, price, cost, unit, stock, min_lvl, max_lvl in products_data:
                    if not self.inventory.get_product_by_sku(sku):
                        supplier_idx = category_supplier.get(category, 0)
                        supplier_id = suppliers[supplier_idx].id if supplier_idx < len(suppliers) else None
                        
                        product = self.inventory.add_product(
                            sku=sku,
                            name=name,
                            category=category,
                            price=price,
                            cost=cost,
                            unit=unit,
                            initial_stock=stock,
                            min_stock_level=min_lvl,
                            max_stock_level=max_lvl,
                            reorder_quantity=max_lvl - min_lvl,
                            supplier_id=supplier_id
                        )
                        print(f"  ✓ Added product: {name}")
                
                self.print_success("Sample data added successfully!")
            except Exception as e:
                self.print_error(f"Error adding sample data: {e}")
        
        self.wait_for_key()
    
    def show_database_info(self):
        """Show database information"""
        self.clear_screen()
        self.print_header("🗄️ Database Information")
        
        products = self.inventory.get_all_products(active_only=False)
        suppliers = self.inventory.get_all_suppliers(active_only=False)
        transactions = self.inventory.get_transactions(limit=1000)
        alerts = self.alert_system.get_active_alerts()
        orders = self.restock_manager.get_orders(limit=1000)
        
        print(f"\nDatabase: {self.db_path}")
        print(f"\nRecord Counts:")
        print(f"  Products: {len(products)}")
        print(f"  Suppliers: {len(suppliers)}")
        print(f"  Transactions: {len(transactions)}")
        print(f"  Active Alerts: {len(alerts)}")
        print(f"  Restock Orders: {len(orders)}")
        
        self.wait_for_key()


def main():
    """Main entry point"""
    print("Starting Grocery Inventory System...")
    app = GroceryInventoryApp()
    app.run()


if __name__ == "__main__":
    main()
