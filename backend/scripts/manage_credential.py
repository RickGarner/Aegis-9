from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.credential_broker import (  # noqa: E402
    CredentialBrokerError,
    delete_windows_credential,
    read_windows_credential,
    write_windows_credential,
)
from app.authorization import AuthorizationError, RoleAuthorizer  # noqa: E402
from app.config import get_settings  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage an A.E.G.I.S.-9 protected Windows credential.")
    parser.add_argument("action", choices=("set", "status", "delete"))
    parser.add_argument("--target", default="Aegis-9/MoveIT/ReadOnly")
    parser.add_argument("--username", help="Account name; the password is always requested privately.")
    args = parser.parse_args()
    try:
        RoleAuthorizer(get_settings().role_mapping_path).require("credentials.manage")
        if args.action == "status":
            value = read_windows_credential(args.target)
            print(f"Credential {'is configured' if value else 'is not configured'} for target {args.target}.")
        elif args.action == "delete":
            print(f"Credential {'deleted' if delete_windows_credential(args.target) else 'was not present'} for target {args.target}.")
        else:
            username = args.username or input("Credential username: ").strip()
            password = getpass.getpass("Credential password (input hidden): ")
            confirmation = getpass.getpass("Confirm password: ")
            if password != confirmation:
                print("Passwords did not match; nothing was stored.", file=sys.stderr)
                return 2
            write_windows_credential(args.target, username, password)
            print(f"Credential stored for target {args.target}. The secret was not displayed.")
        return 0
    except (AuthorizationError, CredentialBrokerError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
