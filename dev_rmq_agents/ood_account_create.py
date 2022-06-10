#!/usr/bin/env python
import json
import subprocess
import sys

from rc_rmq import RCRMQ

task = "ood_account"

# Instantiate rabbitmq object
rc_rmq = RCRMQ({"exchange": "RegUsr", "exchange_type": "topic"})


def ood_account_create(ch, method, properties, body):
    msg = json.loads(body)
    print(f"Message received {msg}")
    username = msg["username"]
    user_uid = str(msg["uid"])
    user_gid = str(msg["gid"])
    success = False
    try:
        subprocess.call(["sudo", "groupadd", "-r", "-g", user_gid, username])
        subprocess.call(
            ["sudo", "useradd", "-u", user_uid, "-g", user_gid, username]
        )
        print(f"[{task}]: User {username} has been added")
        success = True
    except Exception:
        e = sys.exc_info()[0]
        print(f"[{task}]: Error: {e}")

    ch.basic_ack(delivery_tag=method.delivery_tag)

    # send confirm message
    rc_rmq.publish_msg(
        {
            "routing_key": "confirm." + username,
            "msg": {"task": task, "success": success},
        }
    )


print(f"Start listening to queue: {task}")
rc_rmq.start_consume(
    {"queue": task, "routing_key": "create.*", "cb": ood_account_create}
)
