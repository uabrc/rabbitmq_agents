#!/usr/bin/env python
import json
import subprocess
import sys

from rc_rmq import RCRMQ

task = "slurm_account"

# Instantiate rabbitmq object
rc_rmq = RCRMQ({"exchange": "RegUsr", "exchange_type": "topic"})


def slurm_account_create(ch, method, properties, body):
    msg = json.loads(body)
    print(f"Message received {msg}")
    username = msg["username"]
    success = False
    try:
        subprocess.call(
            [
                "sudo",
                "sacctmgr",
                "add",
                "account",
                username,
                "-i",
                "Descripition: Add user",
            ]
        )
        subprocess.call(
            [
                "sudo",
                "sacctmgr",
                "add",
                "user",
                username,
                "account=" + username,
                "-i",
            ]
        )
        print(f"SLURM account for user {username} has been added")
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
    {"queue": task, "routing_key": "create.*", "cb": slurm_account_create}
)
