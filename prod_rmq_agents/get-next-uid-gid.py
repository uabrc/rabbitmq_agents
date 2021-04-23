#!/usr/bin/env python
import sys
import json
import ldap
import time
import logging
import argparse
import rc_util
from os import popen
from rc_rmq import RCRMQ
import rabbit_config as rcfg

task = "create_account"

# Instantiate rabbitmq object
rc_rmq = RCRMQ({"exchange": "RegUsr", "exchange_type": "topic"})

args = rc_util.get_args()

# Logger
logger = rc_util.get_logger()

# Account creation
def create_account(msg):

    logger.info(f"Account creation request received: {msg}")
    username = msg["username"]
    uid = msg["uid"]
    email = msg["email"]
    fullname = msg["fullname"]
    msg["success"] = False

    # Bright command to create user
    cmd = "/cm/local/apps/cmd/bin/cmsh -c "
    cmd += f'"user; add {username}; set id {uid}; set email {email}; set commonname \\"{fullname}\\"; '
    cmd += 'commit;"'

    if not args.dry_run:
        popen(cmd)
        time.sleep(rcfg.Delay)
    logger.info(f"Bright command to create user:{cmd}")


# Define your callback function
def resolve_uid_gid(ch, method, properties, body):

    # Retrieve message
    msg = json.loads(body)
    logger.info("Received {}".format(msg))
    username = msg["username"]
    msg["success"] = False

    # Determine next available UID
    try:
        user_exists_cmd = f"/usr/bin/getent passwd {username}"
        user_exists = popen(user_exists_cmd).read().rstrip()

        if user_exists:
            logger.info("The user, {} already exists".format(username))
            msg["uid"] = user_exists.split(":")[2]
            msg["gid"] = user_exists.split(":")[3]

        else:
            cmd_uid = "/usr/bin/getent passwd | \
                awk -F: '($3>10000) && ($3<20000) && ($3>maxuid) { maxuid=$3; } END { print maxuid+1; }'"
            msg["uid"] = popen(cmd_uid).read().rstrip()
            logger.info(f"UID query: {cmd_uid}")

            cmd_gid = "/usr/bin/getent group | \
                awk -F: '($3>10000) && ($3<20000) && ($3>maxgid) { maxgid=$3; } END { print maxgid+1; }'"
            msg["gid"] = popen(cmd_gid).read().rstrip()
            logger.info(f"GID query: {cmd_gid}")

            create_account(msg)
        msg["task"] = task
        msg["success"] = True
    except Exception as exception:
        msg["success"] = False
        msg[
            "errmsg"
        ] = f"Exception raised during account creation, check logs for stack trace"
        logger.error("", exc_info=True)

    # Acknowledge message
    ch.basic_ack(delivery_tag=method.delivery_tag)

    # Send confirm message
    logger.debug("rc_rmq.publish_msg()")
    rc_rmq.publish_msg(
        {"routing_key": "confirm." + msg["queuename"], "msg": msg}
    )
    logger.info("confirmation sent")


logger.info("Start listening to queue: {}".format(task))
rc_rmq.start_consume(
    {"queue": task, "routing_key": "request.*", "cb": resolve_uid_gid}
)

logger.info("Disconnected")
rc_rmq.disconnect()
