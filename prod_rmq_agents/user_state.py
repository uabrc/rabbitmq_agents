#!/usr/bin/env python
import json
import rc_util
import dataset
import pika
from rc_rmq import RCRMQ
from datetime import datetime
import rabbit_config as rcfg

task = "user_state"

args = rc_util.get_args()
logger = rc_util.get_logger(args)

db = dataset.connect(f"sqlite:///{rcfg.db_path}/user_reg.db")
table = db["user_state"]

# Instantiate rabbitmq object
rc_rmq = RCRMQ({"exchange": rcfg.Exchange, "exchange_type": "topic"})


def user_state(ch, method, properties, body):
    msg = json.loads(body)
    username = msg["username"]
    op = msg["op"]
    msg["success"] = False
    errmsg = ""

    props = pika.BasicProperties(correlation_id=properties.correlation_id)

    try:

        if op == "get":
            errmsg = "Getting latest state of {username}"
            record = table.find_one(username=username, order_by="-date")

            if record:
                msg["state"] = record["state"]
                logger.debug(
                    f'The latest state of {username} is {msg["state"]}'
                )
            else:
                msg["state"] = "no-account"

        elif op == "post":
            state = msg["state"]
            errmsg = "Updating state of {username} to {state}"
            table.insert(
                {"username": username, "state": state, "date": datetime.now()}
            )
            logger.debug(f"User {username} state updates to {state}")

        msg["success"] = True
    except Exception:
        logger.error("", exc_info=True)
        msg["errmsg"] = errmsg if errmsg else "Unexpected error"

    # Send response
    rc_rmq.publish_msg(
        {"routing_key": properties.reply_to, "msg": msg, "props": props}
    )

    # Acknowledge the message
    ch.basic_ack(delivery_tag=method.delivery_tag)


if __name__ == "__main__":
    logger.info(f"Start listening to queue: {task}")
    rc_rmq.start_consume({"queue": task, "cb": user_state})

    logger.info("Disconnected")
    rc_rmq.disconnect()