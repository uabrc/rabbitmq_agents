#!/usr/bin/env python
import sys
import json
import smtplib
import logging
import argparse
from email.message import EmailMessage
from rc_rmq import RCRMQ

task = 'subscribe_mail_list'

# Instantiate rabbitmq object
rc_rmq = RCRMQ({'exchange': 'RegUsr', 'exchange_type': 'topic'})

# Parse arguments
parser = argparse.ArgumentParser()
parser.add_argument('-v', '--verbose', action='store_true', help='verbose output')
parser.add_argument('-n', '--dry-run', action='store_true', help='enable dry run mode')
args = parser.parse_args()

#Default Log level
log_lvl = logging.WARNING

if args.verbose:
   log_lvl = logging.DEBUG
if args.dry_run:
   log_lvl = logging.INFO

# Logger
logging.basicConfig(format='%(asctime)s %(levelname)s [%(module)s] - %(message)s', level=log_lvl)
logger = logging.getLogger(__name__)

# Define your callback function
def mail_list_subscription(ch, method, properties, body):

    # Retrieve message
    msg = json.loads(body)
    logger.info("Received msg {}".format(msg))
    username = msg['username']
    fullname = msg['fullname']
    email = msg['email']

    mail_list_admin = 'admin@uab.edu' #change this during deploy
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

logger.info("Start listening to queue: {}".format(task))
rc_rmq.start_consume({
    'queue': task,      # Define your Queue name
    'routing_key': "create.*", # Define your routing key
    'cb': mail_list_subscription # Pass in callback function you just define
})

logger.info("Disconnected")
rc_rmq.disconnect()
