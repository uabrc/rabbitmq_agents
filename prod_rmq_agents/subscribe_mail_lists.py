#!/usr/bin/env python
import json
import smtplib
from email.message import EmailMessage

import rabbit_config as rcfg
import rc_util
from rc_rmq import RCRMQ

task = "subscribe_mail_list"

# Instantiate rabbitmq object
rc_rmq = RCRMQ({"exchange": "RegUsr", "exchange_type": "topic"})

# Parse arguments
args = rc_util.get_args()

# Logger
logger = rc_util.get_logger()  # Define your callback function


def mail_list_subscription(ch, method, properties, body):

    # Retrieve message
    msg = json.loads(body)
    logger.info("Received msg {}".format(msg))
    username = msg["username"]
    fullname = msg["fullname"]
    email = msg["email"]

    mail_list_admin = rcfg.Sender
    mail_list = rcfg.Mail_list
    mail_list_bcc = rcfg.Mail_list_bcc
    server = rcfg.Mail_server

    listserv_cmd = (
        f"QUIET ADD hpc-announce {email} {fullname}\n"
        f"QUIET ADD hpc-users {email} {fullname}"
    )

    logger.info("Adding user{} to mail list".format(username))
    msg["success"] = False
    try:
        # Create a text/plain message
        email_msg = EmailMessage()

        email_msg["From"] = mail_list_admin
        email_msg["To"] = mail_list
        email_msg["Subject"] = ""
        email_msg["Bcc"] = mail_list_bcc

        # Create an smtp object and send email
        s = smtplib.SMTP(server)

        email_msg.set_content(listserv_cmd)
        if not args.dry_run:
            s.send_message(email_msg)
        logger.info(
            f"This email will add user {username} to listserv \n{email_msg}"
        )

        s.quit()
        msg["task"] = task
        msg["success"] = True
    except Exception:
        logger.error("", exc_info=True)

    # Acknowledge message
    ch.basic_ack(delivery_tag=method.delivery_tag)

    # send confirm message
    logger.debug("rc_rmq.publish_msg()")
    rc_rmq.publish_msg(
        {"routing_key": "confirm." + msg["queuename"], "msg": msg}
    )
    logger.info("confirmation sent")


logger.info("Start listening to queue: {}".format(task))
rc_rmq.start_consume(
    {
        "queue": task,  # Define your Queue name
        "routing_key": "verify.*",  # Define your routing key
        "cb": mail_list_subscription,  # Pass callback function you just define
    }
)

logger.info("Disconnected")
rc_rmq.disconnect()
