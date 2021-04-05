#!/usr/bin/env python
import sys
import json
import rc_util
import smtplib
import dataset
from rc_rmq import RCRMQ
from jinja2 import Template
from datetime import datetime
import rabbit_config as rcfg
import mail_config as mail_cfg
task = 'notify_user'

args = rc_util.get_args()
logger = rc_util.get_logger(args)

db = dataset.connect(f'sqlite:///.agent_db/user_reg.db')
table = db['users']

# Instantiate rabbitmq object
rc_rmq = RCRMQ({'exchange': 'RegUsr', 'exchange_type': 'topic'})

# Email instruction to user
def notify_user(ch, method, properties, body):
    msg = json.loads(body)
    username = msg['username']
    user_email = msg['email']
    msg['task'] = task
    msg['success'] = False
    errmsg = ""

    try:

        # Search username in database
        record = table.find_one(username=username)

        if record['sent'] is not None:
            errmsg = 'Updating database counter'
            # Update counter
            count = record['count']
            if args.dry_run:
                logger.info('Update counter in database')

            else:
                table.update({
                    'username': username,
                    'count': count + 1
                }, ['username'])

            logger.debug(f'User {username} counter updated to {count + 1}')

        else:
            # Send email to user
            receivers = [user_email, rcfg.Admin_email]
            message = Template(mail_cfg.Whole_mail).render(username=username, to=user_email)

            if args.dry_run:
                logger.info(f'smtp = smtplib.SMTP({rcfg.Mail_server})')
                logger.info(f'smtp.sendmail({rcfg.Sender}, {receivers}, message)')
                logger.info(f"table.update({{'username': {username}, 'count': 1, 'sent_at': datetime.now()}}, ['username'])")

            else:
                errmsg = 'Sending email to user'
                smtp = smtplib.SMTP(rcfg.Mail_server)
                smtp.sendmail(rcfg.Sender, receivers, message)

                logger.debug(f'Email sent to: {user_email}')

                errmsg = 'Updating database email sent time'
                table.update({
                    'username': username,
                    'count': 1,
                    'sent': datetime.now()
                }, ['username'])

                logger.debug(f'User {username} inserted into database')

        msg['success'] = True
    except Exception as exception:
        logger.error('', exc_info=True)
        msg['errmsg'] = errmsg if errmsg else 'Unexpected error'

    # Send confirm message
    rc_rmq.publish_msg({
        'routing_key': 'confirm.' + username,
        'msg': msg
    })

    logger.debug(f'User {username} confirmation sent')

    # Acknowledge the message
    ch.basic_ack(delivery_tag=method.delivery_tag)


if __name__ == "__main__":
    logger.info(f'Start listening to queue: {task}')
    rc_rmq.start_consume({
        'queue': task,
        'routing_key': "notify.*",
        'cb': notify_user
    })

    logger.info('Disconnected')
    rc_rmq.disconnect()
