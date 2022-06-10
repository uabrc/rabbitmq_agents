#!/usr/bin/env python
import copy
import json
import signal
import smtplib
from datetime import datetime

import dataset
import mail_config as mail_cfg
from jinja2 import Template

import rabbit_config as rcfg
import rc_util
from rc_rmq import RCRMQ

task = "task_manager"
timeout = 30

args = rc_util.get_args()
logger = rc_util.get_logger(args)

db = dataset.connect(f"sqlite:///{rcfg.db_path}/user_reg.db")
table = db["users"]

record = {
    "uid": -1,
    "gid": -1,
    "email": "",
    "reason": "",
    "fullname": "",
    "last_update": datetime.now(),
    "errmsg": None,
    "waiting": set(),
    "request": {"create_account": None},
    "verify": {
        "git_commit": None,
        "dir_verify": None,
        "subscribe_mail_list": None,
    },
    "notify": {"notify_user": None},
    "reported": False,
}

# Currently tracking users
tracking = {}

# Instantiate rabbitmq object
rc_rmq = RCRMQ({"exchange": "RegUsr", "exchange_type": "topic"})


def notify_admin(username, user_record):
    receivers = [rcfg.Admin_email]

    result = (
        "SUCCESS"
        if user_record["request"]["create_account"]
        and user_record["verify"]["git_commit"]
        and user_record["verify"]["dir_verify"]
        and user_record["verify"]["subscribe_mail_list"]
        and user_record["notify"]["notify_user"]
        else "FAILED"
    )

    message = Template(mail_cfg.UserReportHead).render(
        username=username, fullname=user_record["fullname"], result=result
    )
    if user_record["reported"]:
        message += " (Duplicate)"
    message += f""" \n
    User Creation Report for user {username}
    uid: {user_record["uid"]}, gid: {user_record["gid"]}
    Tasks:
    'create_account':      {user_record["request"]["create_account"]}
    'git_commit':          {user_record["verify"]["git_commit"]}
    'dir_verify':          {user_record["verify"]["dir_verify"]}
    'subscribe_mail_list': {user_record["verify"]["subscribe_mail_list"]}
    'notify_user':         {user_record["notify"]["notify_user"]}
    """
    if user_record["errmsg"]:
        message += """

        Error(s):
        """
        for msg in user_record["errmsg"]:
            message += msg + "\n"

    if args.dry_run:
        logger.info(f"smtp = smtplib.SMTP({rcfg.Mail_server})")
        logger.info(
            f"smtp.sendmail({rcfg.Sender}, {rcfg.Admin_email}, message)"
        )
        logger.info(message)

    else:
        smtp = smtplib.SMTP(rcfg.Mail_server)
        smtp.sendmail(rcfg.Sender, receivers, message)

        logger.debug(f"User report sent to: {rcfg.Admin_email}")


def insert_db(username, msg):
    # Search username in db
    record = table.find_one(username=username)

    if not record:
        # SQL insert
        table.insert(
            {
                "username": username,
                "uid": msg.get("uid", -1),
                "gid": msg.get("gid", -1),
                "email": msg.get("email", ""),
                "reason": msg.get("reason", ""),
                "fullname": msg.get("fullname", ""),
                "create_account": None,
                "git_commit": None,
                "dir_verify": None,
                "subscribe_mail_list": None,
                "notify_user": None,
                "sent": None,
                "reported": False,
                "last_update": datetime.now(),
                "queuename": msg.get("queuename", ""),
            }
        )


def update_db(username, data):
    obj = {"username": username, **data}
    table.update(obj, ["username"])


def task_manager(ch, method, properties, body):
    msg = json.loads(body)
    queuename = method.routing_key.split(".")[1]
    username = msg["username"]
    task_name = msg["task"]
    success = msg["success"]
    send = completed = terminated = False
    routing_key = ""

    if username in tracking:
        current = tracking[username]

    else:
        user_db = table.find_one(username=username)

        current = tracking[username] = copy.deepcopy(record)
        current["errmsg"] = []
        current["queuename"] = (
            user_db["queuename"] if user_db else msg["queuename"]
        )
        current["uid"] = user_db["uid"] if user_db else msg["uid"]
        current["gid"] = user_db["gid"] if user_db else msg["gid"]
        current["email"] = user_db["email"] if user_db else msg["email"]
        current["reason"] = user_db["reason"] if user_db else msg["reason"]
        current["fullname"] = (
            user_db["fullname"] if user_db else msg["fullname"]
        )

        if user_db:
            # Restore task status
            current["request"]["create_account"] = user_db["create_account"]
            current["verify"]["git_commit"] = user_db["git_commit"]
            current["verify"]["dir_verify"] = user_db["dir_verify"]
            current["verify"]["subscribe_mail_list"] = user_db[
                "subscribe_mail_list"
            ]
            current["notify"]["notify_user"] = user_db["notify_user"]

            current["reported"] = user_db["reported"]

            for t in ["git_commit", "dir_verify", "subscribe_mail_list"]:
                if user_db[t] is None:
                    current["waiting"].add(t)

            if not current["waiting"] and user_db["notify_user"] is None:
                current["waiting"].add("notify_user")

            logger.debug(f"Loaded user {username} from DB")

        else:
            insert_db(username, msg)

            logger.debug(f"Tracking user {username}")

    current["last_update"] = datetime.now()

    # Update Database
    update_db(
        username,
        {task_name: success, "last_update": current["last_update"]},
    )

    # Save error message if the task was failed
    if not success:
        errmsg = msg.get("errmsg", "")
        if errmsg:
            current["errmsg"].append(f"{task_name}: {errmsg}")

    # Define message that's going to be published
    message = {
        "username": username,
        "queuename": queuename,
        "uid": current["uid"],
        "gid": current["gid"],
        "email": current["email"],
        "reason": current["reason"],
        "fullname": current["fullname"],
    }

    try:
        if task_name in current["request"]:
            current["request"][task_name] = success
            routing_key = "verify." + queuename

            # Terminate the process if failed
            if not success:
                terminated = True
                routing_key = "complete." + queuename
                message["success"] = False
                message["errmsg"] = current["errmsg"]

            send = True
            current["waiting"] = {
                "git_commit",
                "dir_verify",
                "subscribe_mail_list",
            }
            logger.debug(f"Request level {task_name}? {success}")

        elif task_name in current["verify"]:
            current["verify"][task_name] = success
            current["waiting"].discard(task_name)
            routing_key = "notify." + queuename

            if not current["waiting"]:
                send = True
                current["waiting"] = {"notify_user"}

            # Terminate if dir_verify failed and all agents has responsed
            if send and not current["verify"]["dir_verify"]:
                terminated = True
                routing_key = "complete." + queuename
                message["success"] = False
                message["errmsg"] = current["errmsg"]

            logger.debug(f"Verify level {task_name}? {success}")

        elif task_name in current["notify"]:
            current["notify"][task_name] = success
            current["waiting"].discard(task_name)
            routing_key = "complete." + queuename
            message["success"] = success
            message["errmsg"] = current["errmsg"]

            send = True

            # The whole creation process has completed
            completed = True

            logger.debug(f"Notify level {task_name}? {success}")

    except Exception:
        logger.error("", exc_info=True)

    if send:
        # Send trigger message
        rc_rmq.publish_msg({"routing_key": routing_key, "msg": message})

        logger.debug(f"Trigger message '{routing_key}' sent")

        logger.debug("Previous level messages acknowledged")

    # Send report to admin
    if completed or terminated:

        notify_admin(username, current)

        update_db(username, {"reported": True})

        rc_util.update_state(
            username, "ok", msg.get("updated_by"), msg.get("host")
        )

        tracking.pop(username)

        logger.debug("Admin report sent")

    # Acknowledge message
    ch.basic_ack(method.delivery_tag)


def timeout_handler(signum, frame):
    current_time = datetime.now()
    for user in tuple(tracking):
        delta = current_time - tracking[user]["last_update"]

        if delta.seconds > timeout:

            rc_rmq.publish_msg(
                {
                    "routing_key": "complete." + user,
                    "msg": {
                        "username": user,
                        "success": False,
                        "errmsg": [
                            "Timeout on "
                            + ", ".join(tracking[user]["waiting"])
                        ],
                    },
                }
            )

            notify_admin(user, tracking[user])

            update_db(user, {"reported": True})

            tracking.pop(user)


# Set initial timeout timer
signal.signal(signal.SIGALRM, timeout_handler)
signal.setitimer(signal.ITIMER_REAL, timeout, timeout)

logger.info(f"Start listening to queue: {task}")
rc_rmq.start_consume(
    {"queue": task, "routing_key": "confirm.*", "cb": task_manager}
)

logger.info("Disconnected")
rc_rmq.disconnect()
