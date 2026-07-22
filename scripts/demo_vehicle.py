#!/usr/bin/env python3
"""Demo script for testing Tekion Vehicle Inventory APIs.

Usage:
    python scripts/demo_vehicle.py search --vin "1FTEW1E45KFA12349"
    python scripts/demo_vehicle.py get    --id "v-001"
    python scripts/demo_vehicle.py repair-orders --id "v-001"
"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from tekion_api.config import load_config
from tekion_api.auth import TokenManager
from tekion_api.client import ApiClient
from tekion_api.services.vehicle import VehicleService


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Tekion Vehicle Inventory Demo")
    subparsers = parser.add_subparsers(dest="command", required=True)

    search = subparsers.add_parser("search", help="Search vehicles")
    search.add_argument("--vin", help="VIN to search")
    search.add_argument("--make", help="Make filter")
    search.add_argument("--model", help="Model filter")
    search.add_argument("--year", help="Year filter")

    list_all = subparsers.add_parser("list", help="List vehicles with filters")
    list_all.add_argument("--vin", help="VIN filter")
    list_all.add_argument("--make", help="Make filter")
    list_all.add_argument("--model", help="Model filter")
    list_all.add_argument("--year", help="Year filter")
    list_all.add_argument("--status", help="Status filter (STOCKED_IN, SOLD, etc.)")
    list_all.add_argument("--stock-id", help="Stock ID filter")
    list_all.add_argument("--page-token", help="Next page token")

    get = subparsers.add_parser("get", help="Get vehicle by inventory ID")
    get.add_argument("--id", required=True, help="Vehicle inventory ID")

    update = subparsers.add_parser("update", help="Update a vehicle")
    update.add_argument("--id", required=True, help="Vehicle inventory ID")
    update.add_argument("--payload", required=True, help="JSON payload for update")

    subparsers.add_parser("repair-orders", help="Get repair orders for vehicle")
    repair_orders = subparsers.add_parser("repair-orders", help="Get repair orders for vehicle")
    repair_orders.add_argument("--id", required=True, help="Vehicle inventory ID")

    args = parser.parse_args()

    config = load_config()
    token_manager = TokenManager(config)
    client = ApiClient(config, token_manager)
    service = VehicleService(client)

    try:
        if args.command == "search":
            filters = []
            if args.vin:
                filters.append({"operator": "EQ", "field": "vin", "values": [args.vin]})
            if args.make:
                filters.append({"operator": "EQ", "field": "make", "values": [args.make]})
            if args.model:
                filters.append({"operator": "EQ", "field": "model", "values": [args.model]})
            if args.year:
                filters.append({"operator": "EQ", "field": "year", "values": [args.year]})

            result = service.search(filters=filters if filters else None, vin=args.vin)
            vehicles = result.get("data", [])
            if vehicles:
                print(f"Found {len(vehicles)} vehicle(s):")
                for v in vehicles:
                    print(f"  [{v['id']}] {v.get('year','')} {v.get('make','')} {v.get('model','')} — VIN: {v.get('vin','')}")
            else:
                print("No vehicles found.")

        elif args.command == "list":
            params = {}
            if args.vin: params["vin"] = args.vin
            if args.make: params["make"] = args.make
            if args.model: params["model"] = args.model
            if args.year: params["year"] = args.year
            if args.status: params["status"] = args.status
            if args.stock_id: params["stockId"] = args.stock_id
            if args.page_token: params["nextPageToken"] = args.page_token
            result = service.list_all(**params)
            vehicles = result.get("data", [])
            if vehicles:
                print(f"Found {len(vehicles)} vehicle(s):")
                for v in vehicles:
                    print(f"  [{v['id']}] {v.get('year','')} {v.get('make','')} {v.get('model','')} — VIN: {v.get('vin','')}")
            else:
                print("No vehicles found.")

        elif args.command == "get":
            result = service.get(args.id)
            v = result.get("data", {})
            print(f"Vehicle: {v.get('id')}")
            print(f"  VIN:   {v.get('vin')}")
            print(f"  Year:  {v.get('year')}")
            print(f"  Make:  {v.get('make')}")
            print(f"  Model: {v.get('model')}")
            print(f"  Status: {v.get('status')}")

        elif args.command == "update":
            import json
            payload = json.loads(args.payload)
            result = service.update(args.id, payload)
            print(f"Updated vehicle: {args.id}")

        elif args.command == "repair-orders":
            result = service.get_repair_orders(args.id)
            ros = result.get("data", [])
            if ros:
                print(f"Repair orders for vehicle {args.id}:")
                for ro in ros:
                    print(f"  - {ro}")
            else:
                print("No repair orders found.")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
