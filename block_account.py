#!/usr/bin/env python3
import json
import rc_util
import argparse
import signal

parser = argparse.ArgumentParser()
parser.add_argument("username", help="username that will be created")
parser.add_argument(
    "-v", "--verbose", action="store_true", help="verbose output"
)
parser.add_argument(
    "-n", "--dry-run", action="store_true", help="enable dry run mode"
)
args = parser.parse_args()

timeout = 60

callback_queue = rc_rmq.bind_queue(exclusive=True)

def timeout_handler(signum, frame):
    print("Process timeout, there's some issue with agents")
    rc_util.rc_rmq.stop_consume()


def callback(channel, method, properties, body):
    msg = json.loads(body)
    username = msg["username"]

    if msg["success"]:
        print(f"Account for {username} has been blocked :.")
    else:
        print(f"There's some issue while blocking account for {username}")
        errmsg = msg.get("errmsg", [])
        for err in errmsg:
            print(err)

    rc_util.rc_rmq.stop_consume()
    rc_util.rc_rmq.delete_queue()


rc_util.block_account(
    args.username,
    queuename=queuename,
    email=args.email,
    full=args.full_name,
    reason=args.reason,
)
print(f"Lock action for {args.username} requested.")

# Set initial timeout timer
signal.signal(signal.SIGALRM, timeout_handler)
signal.setitimer(signal.ITIMER_REAL, timeout)

print("Waiting for completion...")
rc_util.consume(
    callback_queue, routing_key=f"complete.{queuename}", callback=callback
)
