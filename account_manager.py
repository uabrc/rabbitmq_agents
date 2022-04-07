#!/usr/bin/env python3
import json
import rc_util
import argparse
import signal
import uuid
import  

parser = argparse.ArgumentParser(description = "Account management driver script")
parser.add_argument("username", help="Username that should be locked/unlocked")
parser.add_argument("action", help="Choose lock or unlock action to be taken")
parser.add_argument("service", nargs='*', help="List one or more services to be blocked")
parser.add_argument(
    "-a", "--all", help="Block all services")
parser.add_argument(
    "-v", "--verbose", action="store_true", help="verbose output")
parser.add_argument(
    "-n", "--dry-run", action="store_true", help="enable dry run mode"
)
args = parser.parse_args()

timeout = 60

username = args.username
action = args.action
service = args.service

corr_id = str(uuid.uuid4())
callback_queue = rc_rmq.bind_queue(exclusive=True)

msg = {}

if args.all is not None:
    # send a broadcast message to all agents
        rc_rmq.publish_msg(
            {
                "routing_key": f"{action}.{username}",
                "msg":  {"username": username, "action": action, "service": service},
            }
        )
else:
    for each_service in service:
        if action == 'lock':
            rc_rmq.publish_msg(
                {
                    "routing_key": f"{service}.{username}",
                    "props": pika.BasicProperties(
                             correlation_id=corr_id, reply_to=callback_queue
                             ),
                    "msg":  {"username": username, "action": action, "service": service},
                }
            )
        elif action == 'unlock':
            rc_rmq.publish_msg(
                {
                    "routing_key": f"{service}.{username}",
                    "props": pika.BasicProperties(
                             correlation_id=corr_id, reply_to=callback_queue
                             ),
                    "msg":  {"username": username, "action": action, "service": service},
                }
            )

def timeout_handler(signum, frame):
    print("Process timeout, there's some issue with agents")
    rc_util.rc_rmq.stop_consume()


def callback(channel, method, properties, body):
    msg = json.loads(body)
    username = msg["username"]
    msg["success"] = false

    if msg["success"]:
        print(f"Account for {username} has been blocked :.")
    else:
        print(f"There's some issue in account management agents for {username}")
        errmsg = msg.get("errmsg", [])
        for err in errmsg:
            print(err)

    rc_util.rc_rmq.stop_consume()
    rc_util.rc_rmq.disconnect()


print(f"{args.action} action for {args.username} requested.")

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
