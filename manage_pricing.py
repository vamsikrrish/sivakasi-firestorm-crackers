#!/usr/bin/env python3
"""
Firestorm Crackers - Centralized Pricing & Catalog Management Tool
===================================================================
Easily manage, bulk-discount, surge-price, or update individual prices
across products.json, index.html, and product.html with a single command.

Usage:
  python3 manage_pricing.py --summary
  python3 manage_pricing.py --reduce 25
  python3 manage_pricing.py --increase 10
  python3 manage_pricing.py --set <product_id> <new_price>
  python3 manage_pricing.py --export-csv [filename.csv]
  python3 manage_pricing.py --import-csv <filename.csv>
  python3 manage_pricing.py --sync
"""

import sys
import json
import re
import csv
import argparse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PRODUCTS_JSON = BASE_DIR / "products.json"
INDEX_HTML = BASE_DIR / "index.html"
PRODUCT_HTML = BASE_DIR / "product.html"

COMBO_CATEGORY = "Firestorm Special Assorted Combos"

def load_products():
    with open(PRODUCTS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)

def save_products(products):
    with open(PRODUCTS_JSON, "w", encoding="utf-8") as f:
        json.dump(products, f, indent=2, ensure_ascii=False)
    print(f"✓ Saved {len(products)} products to products.json")

def sync_html_files(products):
    json_compact = json.dumps(products, ensure_ascii=False)
    
    # Sync index.html
    if INDEX_HTML.exists():
        with open(INDEX_HTML, "r", encoding="utf-8") as f:
            idx = f.read()
        new_idx, count = re.subn(r'const DEFAULT_PRODUCTS = (\[.*?\]);', f'const DEFAULT_PRODUCTS = {json_compact};', idx)
        if count:
            with open(INDEX_HTML, "w", encoding="utf-8") as f:
                f.write(new_idx)
            print("✓ Synchronized index.html (const DEFAULT_PRODUCTS updated)")
        else:
            print("⚠ Warning: const DEFAULT_PRODUCTS pattern not found in index.html")

    # Sync product.html
    if PRODUCT_HTML.exists():
        with open(PRODUCT_HTML, "r", encoding="utf-8") as f:
            pdp = f.read()
        new_pdp, count = re.subn(r'const DEFAULT_PRODUCTS = (\[.*?\]);', f'const DEFAULT_PRODUCTS = {json_compact};', pdp)
        if count:
            with open(PRODUCT_HTML, "w", encoding="utf-8") as f:
                f.write(new_pdp)
            print("✓ Synchronized product.html (const DEFAULT_PRODUCTS updated)")
        else:
            print("⚠ Warning: const DEFAULT_PRODUCTS pattern not found in product.html")

def display_summary(products):
    print("=" * 70)
    print("FIRESTORM CRACKERS CATALOG SUMMARY")
    print("=" * 70)
    print(f"Total Products: {len(products)}")
    combos = [p for p in products if p.get("category") == COMBO_CATEGORY]
    individual = [p for p in products if p.get("category") != COMBO_CATEGORY]
    print(f"Assorted Combos: {len(combos)}")
    for c in combos:
        print(f"  • ID {c['id']}: {c['name']} -> ₹{c['price']} (Retail/MRP: ₹{c.get('originalPrice', '-')})")
    print(f"Individual Cracker Items: {len(individual)}")
    prices = [p["price"] for p in individual]
    print(f"Individual Price Range: ₹{min(prices)} to ₹{max(prices)} (Average: ₹{sum(prices)/len(prices):.1f})")
    print("=" * 70)

def reduce_prices(percent, include_combos=False):
    products = load_products()
    multiplier = (100.0 - percent) / 100.0
    updated_count = 0
    
    for p in products:
        if not include_combos and p.get("category") == COMBO_CATEGORY:
            continue
        old_price = p["price"]
        new_price = max(1, int(round(old_price * multiplier)))
        p["price"] = new_price
        updated_count += 1
    
    save_products(products)
    sync_html_files(products)
    print(f"✓ Successfully reduced {updated_count} product prices by {percent}%")
    display_summary(products)

def increase_prices(percent, include_combos=False):
    products = load_products()
    multiplier = (100.0 + percent) / 100.0
    updated_count = 0
    
    for p in products:
        if not include_combos and p.get("category") == COMBO_CATEGORY:
            continue
        old_price = p["price"]
        new_price = max(1, int(round(old_price * multiplier)))
        p["price"] = new_price
        updated_count += 1
    
    save_products(products)
    sync_html_files(products)
    print(f"✓ Successfully increased {updated_count} product prices by {percent}%")
    display_summary(products)

def set_product_price(product_id, new_price):
    products = load_products()
    found = False
    for p in products:
        if p["id"] == product_id:
            old_price = p["price"]
            p["price"] = int(new_price)
            found = True
            print(f"✓ Updated ID {product_id} ({p['name']}): ₹{old_price} -> ₹{new_price}")
            break
    if not found:
        print(f"✗ Error: Product with ID {product_id} not found.")
        return
    save_products(products)
    sync_html_files(products)

def export_csv(filename="prices.csv"):
    products = load_products()
    filepath = BASE_DIR / filename
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "name", "category", "price", "originalPrice", "unit"])
        for p in products:
            writer.writerow([
                p.get("id"),
                p.get("name"),
                p.get("category"),
                p.get("price"),
                p.get("originalPrice"),
                p.get("unit")
            ])
    print(f"✓ Exported {len(products)} products to {filepath}")
    print(f"  You can edit this in Excel / Google Sheets and re-import with:")
    print(f"  python3 manage_pricing.py --import-csv {filename}")

def import_csv(filename="prices.csv"):
    filepath = BASE_DIR / filename
    if not filepath.exists():
        print(f"✗ File not found: {filepath}")
        return
    
    products = load_products()
    prod_map = {p["id"]: p for p in products}
    updated_count = 0
    
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                pid = int(row["id"])
                new_price = int(float(row["price"]))
                if pid in prod_map:
                    if prod_map[pid]["price"] != new_price:
                        prod_map[pid]["price"] = new_price
                        updated_count += 1
                    if "originalPrice" in row and row["originalPrice"]:
                        prod_map[pid]["originalPrice"] = int(float(row["originalPrice"]))
            except Exception as e:
                print(f"⚠ Skipping row {row}: {e}")
                
    save_products(products)
    sync_html_files(products)
    print(f"✓ Successfully imported {filepath}. Updated {updated_count} product prices.")
    display_summary(products)

def main():
    parser = argparse.ArgumentParser(description="Manage Firestorm Crackers Pricing")
    parser.add_argument("--summary", action="store_true", help="Show pricing summary")
    parser.add_argument("--reduce", type=float, metavar="PCT", help="Reduce prices by PCT percent (combos excluded)")
    parser.add_argument("--increase", type=float, metavar="PCT", help="Increase prices by PCT percent (combos excluded)")
    parser.add_argument("--include-combos", action="store_true", help="Include combos in bulk percent reduction/increase")
    parser.add_argument("--set", nargs=2, metavar=("ID", "PRICE"), help="Set price for specific product ID")
    parser.add_argument("--sync", action="store_true", help="Sync products.json directly to index.html and product.html")
    parser.add_argument("--export-csv", nargs="?", const="prices.csv", help="Export products to CSV")
    parser.add_argument("--import-csv", metavar="FILE", help="Import updated prices from CSV")
    
    args = parser.parse_args()
    
    if args.summary:
        display_summary(load_products())
    elif args.reduce is not None:
        reduce_prices(args.reduce, include_combos=args.include_combos)
    elif args.increase is not None:
        increase_prices(args.increase, include_combos=args.include_combos)
    elif args.set is not None:
        set_product_price(int(args.set[0]), int(args.set[1]))
    elif args.export_csv:
        export_csv(args.export_csv)
    elif args.import_csv:
        import_csv(args.import_csv)
    elif args.sync:
        products = load_products()
        sync_html_files(products)
        display_summary(products)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
