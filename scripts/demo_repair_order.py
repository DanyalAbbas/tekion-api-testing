#!/usr/bin/env python3
import sys, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from tekion_api.config import load_config
from tekion_api.auth import TokenManager
from tekion_api.client import ApiClient
from tekion_api.services.repair_order import RepairOrderService


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Tekion Repair Order Demo")
    sub = parser.add_subparsers(dest="command", required=True)

    search = sub.add_parser("search", help="Search repair orders")
    search.add_argument("--doc-number")
    search.add_argument("--vin")
    search.add_argument("--status")

    get = sub.add_parser("get", help="Get RO by ID"); get.add_argument("--id", required=True)
    cust = sub.add_parser("customer", help="Get RO customer"); cust.add_argument("--ro-id", required=True); cust.add_argument("--rc-id", required=True)
    veh = sub.add_parser("vehicle", help="Get RO vehicle"); veh.add_argument("--ro-id", required=True)
    jobs = sub.add_parser("jobs", help="Get RO jobs"); jobs.add_argument("--ro-id", required=True)

    create = sub.add_parser("create", help="Create RO")
    create.add_argument("--billing-customer", required=True)
    create.add_argument("--primary-customer", required=True)
    create.add_argument("--vin", required=True)
    create.add_argument("--mileage", type=int, default=0)
    create.add_argument("--tag-number")
    create.add_argument("--license-plate")

    create_from = sub.add_parser("create-from-appt", help="Create RO from appointment")
    create_from.add_argument("--appointment-id", required=True)
    create_from.add_argument("--tag-number")

    create_job = sub.add_parser("create-job", help="Create job in RO")
    create_job.add_argument("--ro-id", required=True)
    create_job.add_argument("--concern", required=True)
    create_job.add_argument("--opcode", required=True)
    create_job.add_argument("--labor-amount", type=float, default=100)
    create_job.add_argument("--bill-duration", type=int, default=2000)

    create_op = sub.add_parser("create-operation", help="Create operation in RO job")
    create_op.add_argument("--ro-id", required=True)
    create_op.add_argument("--job-id", required=True)
    create_op.add_argument("--opcode", required=True)
    create_op.add_argument("--labor-amount", type=float, default=100)
    create_op.add_argument("--bill-duration", type=int, default=2000)

    create_parts = sub.add_parser("create-parts", help="Add parts to operation")
    create_parts.add_argument("--ro-id", required=True)
    create_parts.add_argument("--job-id", required=True)
    create_parts.add_argument("--op-id", required=True)

    get_part_p = sub.add_parser("get-part", help="Get part details")
    get_part_p.add_argument("--ro-id", required=True); get_part_p.add_argument("--job-id", required=True)
    get_part_p.add_argument("--op-id", required=True); get_part_p.add_argument("--part-id", required=True)

    get_parts_p = sub.add_parser("get-parts", help="Get all parts in operation")
    get_parts_p.add_argument("--ro-id", required=True); get_parts_p.add_argument("--job-id", required=True)
    get_parts_p.add_argument("--op-id", required=True)

    fees = sub.add_parser("part-fees", help="Get part fees")
    fees.add_argument("--ro-id", required=True); fees.add_argument("--job-id", required=True)
    fees.add_argument("--op-id", required=True); fees.add_argument("--part-id", required=True)

    invs = sub.add_parser("invoices", help="Get RO invoices")
    invs.add_argument("--ro-id", required=True)

    inv = sub.add_parser("invoice", help="Get single invoice")
    inv.add_argument("--ro-id", required=True); inv.add_argument("--invoice-id", required=True)

    status = sub.add_parser("update-status", help="Update RO status")
    status.add_argument("--ro-id", required=True)
    status.add_argument("--status", required=True)
    status.add_argument("--reason")

    args = parser.parse_args()
    config = load_config(); tm = TokenManager(config)
    svc = RepairOrderService(ApiClient(config, tm))

    try:
        if args.command == "search":
            filters = []
            if args.doc_number: filters.append({"field": "documentNumber", "operator": "IN", "values": [args.doc_number]})
            if args.vin: filters.append({"field": "vin", "operator": "EQ", "values": [args.vin]})
            if args.status: filters.append({"field": "status", "operator": "IN", "values": [args.status.upper().split(",")]})
            r = svc.search(filters=filters or None)
            items = r.get("data", [])
            print(f"Found {len(items)} RO(s):" if items else "No ROs found.")
            for ro in items: print(f"  [{ro['id']}] #{ro.get('documentNumber','?')} — {ro.get('status','?')}")
        elif args.command == "get":
            ro = svc.get(args.id).get("data", {})
            print(f"RO #{ro.get('documentNumber','?')} | {ro.get('id')} | {ro.get('status','?')}")
        elif args.command == "customer":
            c = svc.get_customer(args.ro_id, args.rc_id).get("data", {})
            print(f"Customer: {c.get('firstName','')} {c.get('lastName','')} | {c.get('phone','')}")
        elif args.command == "vehicle":
            v = svc.get_vehicle(args.ro_id).get("data", {})
            print(f"Vehicle: {v.get('year','')} {v.get('make','')} {v.get('model','')} — {v.get('vin','')}")
        elif args.command == "jobs":
            for j in svc.get_jobs(args.ro_id).get("data", []):
                print(f"  [{j['id']}] {j.get('taskCode','?')} — {j.get('description','')} [{j.get('status','?')}]")
        elif args.command == "create":
            r = svc.create(billing_customer_id=args.billing_customer, primary_customer_id=args.primary_customer,
                           vin=args.vin, mileage_in=args.mileage, tag_number=args.tag_number,
                           license_plate=args.license_plate)
            print(f"Created RO: {r.get('data',{}).get('id','?')}")
        elif args.command == "create-from-appt":
            r = svc.create_from_appointment(args.appointment_id, args.tag_number)
            print(f"Created RO: {r.get('data',{}).get('id','?')}")
        elif args.command == "create-job":
            r = svc.create_job(args.ro_id, concern_text=args.concern, opcode=args.opcode,
                               labor_sale_amount=args.labor_amount, bill_duration=args.bill_duration)
            print(f"Created Job: {r.get('data',{}).get('id','?')}")
        elif args.command == "create-operation":
            r = svc.create_operation(args.ro_id, args.job_id, opcode=args.opcode,
                                     labor_sale_amount=args.labor_amount, bill_duration=args.bill_duration)
            print(f"Created Operation: {r.get('data',{}).get('id','?')}")
        elif args.command == "create-parts":
            import json
            parts = json.loads(input("Paste parts JSON array: "))
            r = svc.create_operation_parts(args.ro_id, args.job_id, args.op_id, parts)
            print(f"Created {len(r.get('data',[]))} part(s)")
        elif args.command == "get-part":
            p = svc.get_part(args.ro_id, args.job_id, args.op_id, args.part_id).get("data", {})
            print(f"Part: {p.get('partName','?')} | #{p.get('partNumber','?')}")
        elif args.command == "get-parts":
            for p in svc.get_parts(args.ro_id, args.job_id, args.op_id).get("data", []):
                print(f"  [{p['id']}] {p.get('partName','?')}")
        elif args.command == "part-fees":
            for f in svc.get_operation_part_fees(args.ro_id, args.job_id, args.op_id, args.part_id).get("data", []):
                print(f"  {f.get('feeType','?')}: ${f.get('amount',0)}")
        elif args.command == "invoices":
            for inv in svc.get_invoices(args.ro_id).get("data", []):
                print(f"  [{inv['id']}] Total: ${inv.get('totalAmount',0)}")
        elif args.command == "invoice":
            inv = svc.get_invoice(args.ro_id, args.invoice_id).get("data", {})
            print(f"Invoice: {inv.get('id')} | ${inv.get('totalAmount',0)}")
        elif args.command == "update-status":
            r = svc.update_status(args.ro_id, args.status, args.reason)
            print(f"Status updated: {r.get('data',{}).get('status','?')}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
