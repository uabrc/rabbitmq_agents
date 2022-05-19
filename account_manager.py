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

queuename = rc_util.encode_name(args.username)

username = args.username
state = args.state
service = args.service

# Instantiate rabbitmq object
rc_rmq = RCRMQ({"exchange": rcfg.Exchange, "exchange_type": "topic"})

msg = {}
msg["username"] = username
msg["state"] = state
msg["service"] = service
msg["queuename"] = queuename
msg["updated_by"], msg["host"] = rc_util.get_caller_info()

# publish msg with acctmgr.{uname} routing key.
rc_rmq.publish_msg(
    {
        "routing_key": f'acctmgr.request.{queuename}',
        "msg": msg,
    }
)


def timeout_handler(signum, frame):
    print("Process timeout, there's some issue with agents")
    rc_rmq.stop_consume()


def callback(ch, method, properties, body):
    msg = json.loads(body)
    username = msg["username"]

    if msg["success"]:
        print(f"Account for {username} has been {msg['action']}ed.\n Updating the user state in DB")
    else:
        print(f"There's some issue in account management agents for {username}")
        errmsg = msg.get("errmsg", [])
        for err in errmsg:
            print(err)


    ch.basic_ack(delivery_tag=method.delivery_tag)
    rc_rmq.stop_consume()
    rc_rmq.delete_queue(queuename)

print(f"Request {username} account state set to {state}.")

# Set initial timeout timer
signal.signal(signal.SIGALRM, timeout_handler)
signal.setitimer(signal.ITIMER_REAL, timeout)

print("Waiting for completion...")
rc_rmq.start_consume(
    {
        "queue": queuename,
        "routing_key": f'certified.{queuename}',
        "cb": callback,
    }
)
