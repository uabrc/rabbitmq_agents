#!/usr/bin/env python
import json
import dataset
import rc_util
from rc_rmq import RCRMQ
import rabbit_config as rcfg
from datetime import datetime

task = "accept_use_policy"
timeout = 30

args = rc_util.get_args()
logger = rc_util.get_logger(args)

db = dataset.connect(f"sqlite:///{rcfg.db_path}/user_reg.db")
table = db["user_policy"]

# Instantiate rabbitmq object
rc_rmq = RCRMQ({"exchange": "RegUsr", "exchange_type": "topic"})


def accept_user_policy(ch, method, properties, body):
    msg = json.loads(body)
    username = msg["username"]
    msg["task"] = task
    msg["success"] = False

    try:
        # Inactivate old record
        inactivate_data = dict(username=username, active=False)
        table.update(inactivate_data, ["username"])

        # Add latest record
        table.insert(
            {
                "username": username,
                "active": msg.get("aup", False),
                "date": datetime.now(),
            }
        )

        msg["success"] = True
    except Exception:
        logger.error("", exc_info=True)

    # Send confirm message
    logger.debug("rc_rmq.publish_msge()")
    rc_rmq.publish_msg(
        {"routing_key": "confirm." + msg["queuename"], "msg": msg}
    )
    logger.info("confirmation sent")

    # Acknowledge message
    logger.debug("ch.basic_ack()")
    ch.basic_ack(delivery_tag=method.delivery_tag)


logger.info("Start listening to queue: %s", task)
rc_rmq.start_consume(
    {"queue": task, "routing_key": "aup.*", "cb": accept_user_policy}
)

logger.info("Disconnected")
rc_rmq.disconnect()
