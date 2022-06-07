#!/usr/bin/env python
import json
import subprocess
import sys
from pwd import getpwnam

from rc_rmq import RCRMQ

task = "ohpc_account"

# Instantiate rabbitmq object
rc_rmq = RCRMQ({"exchange": "RegUsr", "exchange_type": "topic"})


def ohpc_account_create(ch, method, properties, body):
    msg = json.loads(body)
    print(f"Message received {msg}")
    username = msg["username"]
    success = False
    try:
        subprocess.call(["sudo", "useradd", username])
        print(f"[{task}]: User {username} has been added")
        success = True
    except Exception:
        e = sys.exc_info()[0]
        print(f"[{task}]: Error: {e}")

    ch.basic_ack(delivery_tag=method.delivery_tag)
    msg["uid"] = getpwnam(username).pw_uid
    msg["gid"] = getpwnam(username).pw_gid

    # send confirm message
    rc_rmq.publish_msg(
        {
            "routing_key": "confirm." + username,
            "msg": {"task": task, "success": success},
        }
    )

    if success:
        # send create message to other agent
        rc_rmq.publish_msg({"routing_key": "create." + username, "msg": msg})


print(f"Start Listening to queue: {task}")
rc_rmq.start_consume(
    {"queue": task, "routing_key": "request.*", "cb": ohpc_account_create}
)
