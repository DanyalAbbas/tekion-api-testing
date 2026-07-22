#!/usr/bin/env python3
import sys, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from tekion_api.config import load_config
from tekion_api.auth import TokenManager
from tekion_api.client import ApiClient
from tekion_api.services.support import SupportService


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Tekion Support Demo")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("transport-types", help="List transportation types")
    get = sub.add_parser("transport-type", help="Get transportation type")
    get.add_argument("--id", required=True)

    args = parser.parse_args()
    config = load_config(); tm = TokenManager(config)
    svc = SupportService(ApiClient(config, tm))

    try:
        if args.command == "transport-types":
            for t in svc.get_transportation_types().get("data", []):
                print(f"  [{t['id']}] {t.get('name','?')} ({t.get('type','?')})")
        elif args.command == "transport-type":
            t = svc.get_transportation_type(args.id).get("data", {})
            print(f"  {t.get('name','?')} | Type: {t.get('type','?')} | {t.get('description','')}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
