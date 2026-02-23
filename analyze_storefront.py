#!/usr/bin/env python3
import json

def analyze_storefront():
    with open('catalog/storefront.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    print('=== STOREFRONT ANALYSIS ===')
    print(f'Updated: {data.get("meta", {}).get("updatedAt", "N/A")}')
    print(f'Currency: {data.get("pricing", {}).get("currency", "N/A")}')
    print(f'Fixed Price: ${data.get("pricing", {}).get("fixedPrice", "N/A")} MXN')
    print()

    # Location data
    location = data.get('location', {})
    print('=== LOCATION DATA ===')
    print(f'Name: {location.get("name", "N/A")}')
    print(f'Address: {location.get("address", "N/A")}')
    print(f'Phone: {location.get("phone", "N/A")}')
    print(f'Place ID: {location.get("placeId", "N/A")}')
    print(f'Photos: {len(location.get("photos", []))}')
    print(f'Instagram Photos: {len(location.get("instagramPhotos", []))}')
    print()

    # Catalog analysis
    catalog = data.get('catalog', [])
    print('=== CATALOG ANALYSIS ===')
    print(f'Total Categories: {len(catalog)}')

    zones = {}
    categories_by_zone = {}

    for category in catalog:
        zone = category.get('zone', 'Unknown')
        zones[zone] = zones.get(zone, 0) + 1
        if zone not in categories_by_zone:
            categories_by_zone[zone] = []
        categories_by_zone[zone].append(category.get('name', 'Unknown'))

    print()
    print('=== ZONES BREAKDOWN ===')
    for zone, count in zones.items():
        print(f'{zone}: {count} categories')
        for cat in categories_by_zone[zone]:
            print(f'  - {cat}')
        print()

    # Products analysis
    total_products = 0
    for category in catalog:
        total_products += category.get('refs', 0)

    print('=== PRODUCTS SUMMARY ===')
    print(f'Total Products: {total_products}')
    print(f'Products per Category: {total_products / len(catalog) if catalog else 0:.1f} average')

if __name__ == '__main__':
    analyze_storefront()