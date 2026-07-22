#!/usr/bin/env python3
"""Demo script for testing Tekion Customer APIs against the sandbox.

Usage:
    python scripts/demo_customer.py search --phone "5551234567"
    python scripts/demo_customer.py get    --id "cust-123"
    python scripts/demo_customer.py create --first "John" --last "Doe" --phone "5551234567"

Requires environment variables or .env file:
    TEKION_APP_ID, TEKION_SECRET_KEY, TEKION_DEALER_ID
"""
import sys
import argparse
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

from tekion_api.config import load_config
from tekion_api.auth import TokenManager
from tekion_api.client import ApiClient
from tekion_api.services.customer import CustomerService


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Tekion Customer API Demo")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # search
    search_parser = subparsers.add_parser("search", help="Search customers")
    search_parser.add_argument("--phone", help="Phone number to search")
    search_parser.add_argument("--email", help="Email to search")
    search_parser.add_argument("--name", help="Name to search (general search term)")

    # get
    get_parser = subparsers.add_parser("get", help="Get customer by ID")
    get_parser.add_argument("--id", required=True, help="Customer ID")

    # create
    create_parser = subparsers.add_parser("create", help="Create a new customer")
    create_parser.add_argument("--first", required=True, help="First name")
    create_parser.add_argument("--last", required=True, help="Last name")
    create_parser.add_argument("--phone", required=True, help="Phone number")
    create_parser.add_argument("--country-code", type=int, default=1, help="Country code (default: 1)")

    args = parser.parse_args()

    # Boot the stack
    config = load_config()
    token_manager = TokenManager(config)
    client = ApiClient(config, token_manager)
    customer_service = CustomerService(client)

    try:
        if args.command == "search":
            params = {}
            if args.phone:
                params["phone"] = args.phone
            if args.email:
                params["email"] = args.email
            if args.name:
                params["search"] = args.name

            if not params:
                print("Error: provide at least one of --phone, --email, or --name")
                sys.exit(1)

            customers = customer_service.search_customers(**params)
            if customers:
                print(f"Found {len(customers)} customer(s):")
                for c in customers:
                    vehicle_str = ""
                    if c.vehicles:
                        vins = ", ".join(f"{v.year} {v.make} {v.model} ({v.vin})" for v in c.vehicles)
                        vehicle_str = f" — Vehicles: {vins}"
                    print(f"  [{c.id}] {c.first_name} {c.last_name} — {c.phone} — {c.email}{vehicle_str}")
            else:
                print("No customers found.")

        elif args.command == "get":
            customer = customer_service.get_customer(args.id)
            print(f"Customer: {customer.first_name} {customer.last_name}")
            print(f"  ID:     {customer.id}")
            print(f"  Phone:  {customer.phone}")
            print(f"  Email:  {customer.email}")
            print(f"  Type:   {customer.customer_type}")
            print(f"  Status: {customer.status}")
            if customer.vehicles:
                print(f"  Vehicles ({len(customer.vehicles)}):")
                for v in customer.vehicles:
                    print(f"    {v.year} {v.make} {v.model} — VIN: {v.vin}")

        elif args.command == "create":
            customer = customer_service.create_customer(
                first_name=args.first,
                last_name=args.last,
                phone=args.phone,
                country_code=args.country_code,
            )
            print(f"Created customer: [{customer.id}] {customer.first_name} {customer.last_name}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
