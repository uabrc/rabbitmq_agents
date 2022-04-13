#!/usr/bin/env python3
import json
import rc_util
import argparse
import signal
import uuid
import pika
import rc_util
from rc_rmq import RCRMQ
import rabbit_config as rcfg
import time

parser = argparse.ArgumentParser(description = "Account management driver script")
parser.add_argument(
    "username", help="Username that should be locked/unlocked")
parser.add_argument(
    "state", help="Choose from states (ok,block,certify) to put the user in")
parser.add_argument(
    "-s", "--service", nargs='+', default='all', choices=['ssh', 'newjobs', 'expiration', 'all'], help="List one or more services to be blocked (default: %(default)s)")
parser.add_argument(
    "-v", "--verbose", action="store_true", help="verbose output")
parser.add_argument(
    "-n", "--dry-run", action="store_true", help="enable dry run mode"
)
args = parser.parse_args()

timeout = 60

username = args.username
state = args.state
service = args.service

corr_id = str(uuid.uuid4())

# Instantiate rabbitmq object
rc_rmq = RCRMQ({"exchange": rcfg.Exchange, "exchange_type": "topic"})
callback_queue = rc_rmq.bind_queue(exclusive=True)

msg = {}

if state == 'blocked' or state == 'certification':
    action = "lock"
elif state == 'ok':
    action = "unlock"
else:
    print("Invalid state provided. Check the help menu.")

if args.service == 'all':
    # send a broadcast message to all agents
        rc_rmq.publish_msg(
            {
                "routing_key": f"{action}.{username}",
                "props": pika.BasicProperties(
                         correlation_id=corr_id, reply_to=callback_queue
                         ),
                "msg":  {"username": username, "action": action, "service": service},
            }
        )
else:
    for each_service in service:
        rc_rmq.publish_msg(
            {
                "routing_key": f"{each_service}.{username}",
                "props": pika.BasicProperties(
                         correlation_id=corr_id, reply_to=callback_queue
                         ),
                "msg":  {"username": username, "action": action, "service": service},
            }
        )

def timeout_handler(signum, frame):
    print("Process timeout, there's some issue with agents")
    rc_rmq.stop_consume()


def callback(channel, method, properties, body):
    msg = json.loads(body)
    username = msg["username"]

    if msg["success"]:
        print(f"Account for {username} has been {action}ed.\n Updating the user state in DB")
        rc_util.update_state(username, state)
    else:
        print(f"There's some issue in account management agents for {username}")
        errmsg = msg.get("errmsg", [])
        for err in errmsg:
            print(err)

    rc_rmq.stop_consume()
    rc_rmq.disconnect()

print(f"{action} action for {args.username} requested.")

# Set initial timeout timer
signal.signal(signal.SIGALRM, timeout_handler)
signal.setitimer(signal.ITIMER_REAL, timeout)

print("Waiting for completion...")
rc_rmq.start_consume(
    {
        "queue": callback_queue,
        "exclusive": True,
        "bind": False,
        "cb": callback,
    }
)
