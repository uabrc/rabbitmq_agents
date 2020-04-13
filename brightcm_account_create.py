#!/usr/bin/env python
import sys
import json
import logging
import argparse
import rc_util
from os import popen
from rc_rmq import RCRMQ

task = 'bright_account'

# Instantiate rabbitmq object
rc_rmq = RCRMQ({'exchange': 'RegUsr', 'exchange_type': 'topic'})

# Parse arguments
args = rc_util.get_args()

# Logger
logger = rc_util.get_logger()

# Define your callback function
def bright_account_create(ch, method, properties, body):
    # Retrieve message
    msg = json.loads(body)
    logger.info("Received {}".format(msg))
    username = msg['username']
    uid = msg['uid']
    email = msg['email']
    fullname = msg['fullname']
    success = False
    try:
        # Bright command to create user
        cmd = '/cm/local/apps/cmd/bin/cmsh -c '
        cmd += f'"user; add {username}; set userid {uid}; set email {email}; set commonname \\"{fullname}\\"; '
        cmd += 'commit;"'

        if not args.dry_run:
            popen(cmd)
        logger.info(f'Bright command to create user:{cmd}')
        success = True
    except Exception:
        logger.exception("Fatal error:")

    # Acknowledge message
    ch.basic_ack(delivery_tag=method.delivery_tag)

    # send confirm message
    logger.debug('rc_rmq.publish_msg()')
    rc_rmq.publish_msg({
        'routing_key': 'confirm.' + username,
        'msg': {
            'task': task,
            'success': success
        }
    })
    logger.info('confirmation sent')

    if success:
        # send create message to verify dir permissions agent
        logger.debug(f'The task {task} finished successfully')
        rc_rmq.publish_msg({
            'routing_key': 'verify.' + username,
            'msg': msg
        })
        logger.info('verify msg sent to next agent')

logger.info("Start listening to queue: {}".format(task))
rc_rmq.start_consume({
    'queue': task,
    'routing_key': "create.*",
    'cb': bright_account_create
})

logger.info("Disconnected")
rc_rmq.disconnect()
