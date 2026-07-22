#!/usr/bin/env python3
import sys, argparse, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from tekion_api.config import load_config
from tekion_api.auth import TokenManager
from tekion_api.client import ApiClient
from tekion_api.services.appointment import AppointmentService


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Tekion Appointment Demo")
    sub = parser.add_subparsers(dest="command", required=True)

    slots = sub.add_parser("slots", help="Get available appointment slots")
    slots.add_argument("--shop-id", required=True)
    slots.add_argument("--start", required=True)
    slots.add_argument("--end", required=True)
    slots.add_argument("--make")
    slots.add_argument("--model")
    slots.add_argument("--year", type=int)
    slots.add_argument("--opcodes")

    search = sub.add_parser("search", help="Search appointments")
    search.add_argument("--id")
    search.add_argument("--vin")
    search.add_argument("--customer-id")

    create = sub.add_parser("create", help="Create appointment")
    create.add_argument("--shop-id", required=True)
    create.add_argument("--timestamp", type=int, required=True)
    create.add_argument("--customer", required=True)
    create.add_argument("--vehicle", required=True)

    update = sub.add_parser("update", help="Update appointment")
    update.add_argument("--id", required=True)
    update.add_argument("--shop-id", required=True)
    update.add_argument("--timestamp", type=int, required=True)
    update.add_argument("--customer", required=True)
    update.add_argument("--vehicle", required=True)

    cancel = sub.add_parser("cancel", help="Cancel appointment")
    cancel.add_argument("--id", required=True)
    cancel.add_argument("--reason")

    args = parser.parse_args()
    config = load_config(); tm = TokenManager(config)
    svc = AppointmentService(ApiClient(config, tm))

    try:
        if args.command == "slots":
            opcodes = args.opcodes.split(",") if args.opcodes else None
            r = svc.get_slots(shop_id=args.shop_id, start_date=args.start, end_date=args.end,
                              make=args.make, model=args.model, year=args.year, opcodes=opcodes)
            slots_list = r.get("data", [])
            print(f"Found {len(slots_list)} slot(s):" if slots_list else "No slots available.")
            for s in slots_list:
                print(f"  {s.get('startTime')} — {s.get('endTime')}")
        elif args.command == "search":
            r = svc.search(appointment_id=args.id, vin=args.vin, customer_id=args.customer_id)
            for a in r.get("data", []):
                c = a.get("customer", {}); v = a.get("vehicle", {})
                print(f"  [{a['id']}] {c.get('firstName','')} {c.get('lastName','')} — {v.get('vin','')} [{a.get('status','?')}]")
        elif args.command == "create":
            r = svc.create(shop_id=args.shop_id, appointment_date_time=args.timestamp,
                           customer=json.loads(args.customer), vehicle=json.loads(args.vehicle))
            print(f"Created: {r.get('data',{}).get('id','?')}")
        elif args.command == "update":
            r = svc.update(id=args.id, shop_id=args.shop_id, appointment_date_time=args.timestamp,
                           customer=json.loads(args.customer), vehicle=json.loads(args.vehicle))
            print(f"Updated: {r.get('data',{}).get('id','?')}")
        elif args.command == "cancel":
            r = svc.cancel(args.id, args.reason)
            print(f"Cancelled: {r.get('data',{}).get('id','?')}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
