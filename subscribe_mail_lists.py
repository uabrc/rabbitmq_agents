#!/usr/bin/env python
import sys
import json
import smtplib
import logging
import argparse
import rc_util
from email.message import EmailMessage
from rc_rmq import RCRMQ

task = 'subscribe_mail_list'

# Instantiate rabbitmq object
rc_rmq = RCRMQ({'exchange': 'RegUsr', 'exchange_type': 'topic'})

# Parse arguments
args = rc_util.get_args()

# Logger
logger = rc_util.get_logger()# Define your callback function

def mail_list_subscription(ch, method, properties, body):

    # Retrieve message
    msg = json.loads(body)
    logger.info("Received msg {}".format(msg))
    username = msg['username']
    fullname = msg['fullname']
    email = msg['email']

    mail_list_admin = 'root@localhost' #change this during deploy
    mail_list = 'LISTSERV@LISTSERV.UAB.EDU'

    listserv_cmd = {}
    listserv_cmd['hpc_announce'] = f'QUIET ADD hpc-announce {email} {fullname}'
    listserv_cmd['hpc_users'] = f'QUIET ADD hpc-users {email} {fullname}'

    logger.info("Adding user{} to mail list".format(username))
    success = False
    try:
        # Create a text/plain message
        email_msg = EmailMessage()

        email_msg['From'] = mail_list_admin
        email_msg['To'] = mail_list
        email_msg['Subject'] = ''

        # Create an smtp object and send email
        s = smtplib.SMTP('localhost')

        for key,value in listserv_cmd.items():
            email_msg.set_content(value)
            if not args.dry_run:
                s.send_message(email_msg)
            logging.info(f'This email will add user {username} to {key}\n{email_msg}')

        s.quit()
        msg['task'] = task
        msg['success'] = True
    except Exception:
        logger.exception("Fatal error:")

    # Acknowledge message
    ch.basic_ack(delivery_tag=method.delivery_tag)

    # send confirm message
    logger.debug('rc_rmq.publish_msg()')
    rc_rmq.publish_msg({
        'routing_key': 'confirm.' + username,
        'msg': msg
    })
    logger.info('confirmation sent')

logger.info("Start listening to queue: {}".format(task))
rc_rmq.start_consume({
    'queue': task,      # Define your Queue name
    'routing_key': "create.*", # Define your routing key
    'cb': mail_list_subscription # Pass in callback function you just define
})

logger.info("Disconnected")
rc_rmq.disconnect()
