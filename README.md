# Grocery Inventory System

A command-line inventory management system for grocery stores built with Python.

## Features

- **Product Management**: Add, update, search, and deactivate products
- **Supplier Management**: Manage supplier information and relationships
- **Stock Tracking**: Track stock levels with automatic low-stock alerts
- **Restock Orders**: Create and manage purchase orders to suppliers
- **Transaction History**: Full audit trail of all inventory movements
- **Reports**: Inventory summaries, stock value reports, and analytics

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

## Project Structure

```
grocery-inventory-system/
-- main.py              # Main application entry point
-- models.py            # Database models (Product, Supplier, etc.)
-- inventory_manager.py # Core inventory operations
-- alert_system.py      # Low-stock alerts and notifications
-- restock_manager.py   # Purchase order management
-- requirements.txt     # Python dependencies
```