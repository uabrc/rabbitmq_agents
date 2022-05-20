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

task = "acctmgr"

# Instantiate rabbitmq object
rc_rmq = RCRMQ({"exchange": rcfg.Exchange, "exchange_type": "topic"})

tracking = {}

def manage_acct(ch, method, properties, body):
    msg = json.loads(body)
    op = method.routing_key.split(".")[1]
    username = msg["username"]
    state = msg["state"]
    service = msg["service"]
    queuename = msg["queuename"]

    try:
        if username in tracking:
            current = tracking[username]
        else:
            current =  tracking[username] = {}

        if op == 'request':
            if state == 'hold' or state == 'certification':
                msg["action"] = "lock"
            elif state == 'ok':
                msg["action"] = "unlock"
            else:
                print("Invalid state provided. Check the help menu.")

            if service == 'all':
                current["new_jobs"] = None
                current["expire_account"] = None
                # send a broadcast message to all agents
                rc_rmq.publish_msg(
                    {
                        "routing_key": f"{msg['action']}.{queuename}",
                        "msg":  msg,
                    }
                )
            else:
                for each_service in service:
                    current[each_service] = None
                    rc_rmq.publish_msg(
                        {
                            "routing_key": f"{each_service}.{queuename}",
                            "msg": msg
                        }
                    )


        elif op == 'done':
            # Check if each task/agent returned success
            current[msg["task"]] = msg["success"]

            done = True

            for task in current.keys():
                if current[task] is None:
                    done = False

            if done:
                rc_util.update_state(
                    username, state, msg.get("updated_by"), msg.get("host")
                )

                # Send done msg to account_manager.py
                rc_rmq.publish_msg(
                    {
                        "routing_key": f'certified.{queuename}',
                        "msg": msg,
                    }
                )

        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception:
            msg["errmsg"] = "Exception raised in account manager workflow agent , check the logs for stack trace"
            logger.error("", exc_info=True)

rc_rmq.bind_queue(queue=task, routing_key='acctmgr.request.*', durable=True)
rc_rmq.bind_queue(queue=task, routing_key='acctmgr.done.*', durable=True)

print("Waiting for completion...")
rc_rmq.start_consume(
    {"queue": task, "cb": manage_acct}
)

