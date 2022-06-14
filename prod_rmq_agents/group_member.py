#!/usr/bin/env python
import os
import json
import pika
import shlex
import rc_util
from subprocess import Popen,PIPE
from pathlib import Path
from rc_rmq import RCRMQ
import rabbit_config as rcfg

task = "group_member"

args = rc_util.get_args()
logger = rc_util.get_logger(args)

# Instantiate rabbitmq object
rc_rmq = RCRMQ({"exchange": rcfg.Exchange, "exchange_type": "topic"})


def group_member(ch, method, properties, body):
    msg = json.loads(body)
    username = msg["username"]
    action = msg["action"]
    msg["task"] = task
    state = msg["state"]

    try:
        if 'remove' in msg["groups"]:
            for each_group in msg["groups"]["remove"]:
                logger.debug(f'Removing user {username} from group {each_group}')
                if str(rcfg.bright_cm_version).split(".")[0] == "8":
                    grp_remove_user_cmd = f'/cm/local/apps/cmd/bin/cmsh -n -c "group; removefrom {each_group} groupmembers {username}; commit;"'
                else:
                    grp_remove_user_cmd = f'/cm/local/apps/cmd/bin/cmsh -n -c "group; removefrom {each_group} members {username}; commit;"'

                proc = Popen(shlex.split(grp_remove_user_cmd), stdout=PIPE, stderr=PIPE)
                out,err = proc.communicate()
                logger.info(f'Running command: {grp_remove_user_cmd}')
                logger.debug(f'Result: {err}')
                logger.info(f'User {username} is removed from {each_group} group')

        if 'add' in msg["groups"]:
            for each_group in msg["groups"]["add"]:
                logger.debug(f'Adding user {username} to group {each_group}')
                if str(rcfg.bright_cm_version).split(".")[0] == "8":
                    grp_add_user_cmd = f'/cm/local/apps/cmd/bin/cmsh -n -c "group; append {each_group} groupmembers {username}; commit;"'
                else:
                    grp_add_user_cmd = f'/cm/local/apps/cmd/bin/cmsh -n -c "group; append {each_group} members {username}; commit;"'

                proc = Popen(shlex.split(grp_add_user_cmd), stdout=PIPE, stderr=PIPE)
                logger.info(f'Running command: {grp_add_user_cmd}')
                out,err = proc.communicate()
                logger.debug(f'Result: {err}')
                logger.info(f'User {username} is added to {each_group} group')


        msg["success"] = True

    except Exception:
        msg["success"] = False
        msg["errmsg"] = "Exception raised, while adding user to group {groupname}, check the logs for stack trace"
        logger.error("", exc_info=True)


    corr_id = properties.correlation_id
    reply_to = properties.reply_to

    logger.debug(f'corr_id: {corr_id} \n reply_to: {reply_to}')
    # send response to the callback queue
    if reply_to:
        props = pika.BasicProperties(correlation_id=corr_id)
        logger.debug("Sending confirmation back to reply_to")
        rc_rmq.publish_msg(
            {
             "routing_key": reply_to,
             "props": props,
             "msg": msg
            }
        )
    else:
        print("Error: no reply_to")

    logger.debug(f'User {username} confirmation sent from {task}')

    ch.basic_ack(delivery_tag=method.delivery_tag)


logger.info(f"Start listening to queue: {task}")
rc_rmq.bind_queue(queue=task, routing_key='group_member.*', durable=True)

rc_rmq.start_consume(
    {"queue": task, "cb": group_member}
)

logger.info("Disconnected")
rc_rmq.disconnect()      

