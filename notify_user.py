#!/usr/bin/env python
import sys
import json
import rc_util
import smtplib
from rc_rmq import RCRMQ
from jinja2 import Template
import mail_config as mail_cfg

task = 'notify_user'

args = rc_util.get_args()
logger = rc_util.get_logger(args)

# Instantiate rabbitmq object
rc_rmq = RCRMQ({'exchange': 'RegUsr', 'exchange_type': 'topic'})

# Email instruction to user
def notify_user(ch, method, properties, body):
    msg = json.loads(body)
    username = msg['username']
    user_email = msg['email']
    msg['task'] = task
    msg['success'] = False

    try:
        #Send email to user
        receiver = [user_mail, mail_cfg.My_mail]
        message = Template(mail_cfg.Whole_mail).render(username=username, to=user_email)

        if args.dry_run:
            logger.info("smtp.sendmail(sender, receiver, message)")

        else:
            smtp = smtplib.SMTP(mail_cfg.Server)
            smtp.sendmail(sender, receiver, message)

        msg['success'] = True
    except Exception as exception:
        logger.error('', exc_info=True)

    # send confirm message
    rc_rmq.publish_msg({
        'routing_key': 'confirm.' + username,
        'msg': msg
    })

    # acknowledge the message
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
