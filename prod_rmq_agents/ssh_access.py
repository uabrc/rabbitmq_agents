#!/usr/bin/env python
import os
import json
import pika
import uuid
import rc_util
from subprocess import Popen,PIPE
from pathlib import Path
from rc_rmq import RCRMQ
import rabbit_config as rcfg

task = "ssh_access"

args = rc_util.get_args()
logger = rc_util.get_logger(args)

# Instantiate rabbitmq object
rc_rmq = RCRMQ({"exchange": rcfg.Exchange, "exchange_type": "topic"})

print("ssh_agent entered")

def ssh_access(ch, method, properties, body):
    msg = json.loads(body)
    routing_key = method.routing_key
    username = msg["username"]
    action = msg["action"]
    msg["task"] = task
    queuename = msg["queuename"]
    state = msg["state"]
    lock_groups = rcfg.lock_groups

    global corr_id
    try:
    # check if it's a response from group_member_agent
        if routing_key == task:
            print("routing_key matches")
            print(f"corr_id sent by group_member agent: {properties.correlation_id}")
            if corr_id == properties.correlation_id:
                print(f'group_member agent confirmation msg["success"]: {msg["success"]}')
                # forward confirmation response to acct_mgmt_workflow agent
                rc_rmq.publish_msg(
                   {
                    "routing_key": f'acctmgr.done.{queuename}',
                    "msg": msg
                   }
                )
                logger.debug(f'User {username} confirmation sent for {action}ing {task}')
                
        else:
            corr_id = str(uuid.uuid4())
            print(f'corr_id generated: {corr_id}')

            if state == 'certification':
                msg["action"] = "add"
                msg["groupnames"] = [lock_groups[state]]

            elif state == 'hold':
                msg["action"] = "add"
                msg["groupnames"] = [lock_groups[state]]

            elif state == 'pre_certification':
                msg["action"] = "add"
                msg["groupnames"] = [lock_groups[state]]

            elif state == 'ok':
                msg["action"] = "remove"
                proc = Popen(['/usr/bin/groups', username], stdout=PIPE, stderr=PIPE)
                out,err = proc.communicate()
 
                user_group_list = out.decode().strip().split(":")[1].split()
 
                """
                  Filter the lock group a user is in and assign to msg["groupnames"]
                  lambda function returns common elements between two lists. For all
                  the true values by returned lambda function for common elements 
                  corresponding values are included as a list by filter function.
                """
                msg["groupnames"] = list(filter(lambda x:x in list(lock_groups.values()),user_group_list))
 
            #msg["success"] = True
 
            # send a message to group_member.py agent
            logger.info(f"Request sent to add user {username} to {msg['groupnames']} group")
            print(f"sending msg to group agent {msg}")
            rc_rmq.publish_msg(
                {
                   "routing_key": f'group_member.{queuename}',
                   "props": pika.BasicProperties(
                                correlation_id = corr_id,
                                reply_to = task,
                                ),
                   "msg": msg
                }
            )
 
    except Exception:
        msg["success"] = False
        msg["errmsg"] = "Exception raised in ssh_access agent, check the logs for stack trace"
        logger.error("", exc_info=True)

    ch.basic_ack(delivery_tag=method.delivery_tag)


logger.info(f"Start listening to queue: {task}")
rc_rmq.bind_queue(queue=task, routing_key='lock.*', durable=True)
rc_rmq.bind_queue(queue=task, routing_key='unlock.*', durable=True)
rc_rmq.bind_queue(queue=task, routing_key='ssh.*', durable=True)
rc_rmq.bind_queue(queue=task, routing_key=task, durable=True)

rc_rmq.start_consume(
    {"queue": task, "cb": ssh_access}
)

logger.info("Disconnected")
rc_rmq.disconnect()
