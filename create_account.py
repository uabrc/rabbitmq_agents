#!/usr/bin/env python3
import json
import rc_util
import argparse
import signal
import sys

parser = argparse.ArgumentParser()
parser.add_argument("username", help="username that will be created")
parser.add_argument("email", nargs="?", default="", help="User's email")
parser.add_argument(
    "full_name", nargs="?", default="", help="User's full name"
)
parser.add_argument(
    "reason", nargs="?", default="", help="Reason of requesting"
)
parser.add_argument(
    "-A", "--accept", action="store_true", help="Accept user policy"
)
parser.add_argument("--domain", default="localhost", help="domain of email")
parser.add_argument(
    "-v", "--verbose", action="store_true", help="verbose output"
)
parser.add_argument(
    "-n", "--dry-run", action="store_true", help="enable dry run mode"
)
args = parser.parse_args()

timeout = 60

queuename = rc_util.encode_name(args.username)

if not args.accept:
    question = "Attention: User Policy is not accepted, continue?"
    reply = str(raw_input(question+' (y/n): ')).lower().strip()
    if reply[0] != 'y':
        sys.exit(0)

if args.email == "":
    args.email = args.username
    if "@" not in args.email:
        args.email = args.username + "@" + args.domain


def timeout_handler(signum, frame):
    print("Process timeout, there's might some issue with agents")
    rc_util.rc_rmq.stop_consume()


def callback(channel, method, properties, body):
    msg = json.loads(body)
    username = msg["username"]

    if msg["success"]:
        print(f"Account for {username} has been created.")
    else:
        print(f"There's some issue while creating account for {username}")
        errmsg = msg.get("errmsg", [])
        for err in errmsg:
            print(err)

    rc_util.rc_rmq.stop_consume()
    rc_util.rc_rmq.delete_queue()


rc_util.add_account(
    args.username,
    queuename=queuename,
    email=args.email,
    full=args.full_name,
    reason=args.reason,
    aup=args.accept,
)
print(f"Account for {args.username} requested.")

# Set initial timeout timer
signal.signal(signal.SIGALRM, timeout_handler)
signal.setitimer(signal.ITIMER_REAL, timeout)

print("Waiting for completion...")
rc_util.consume(
    queuename, routing_key=f"complete.{queuename}", callback=callback
)
