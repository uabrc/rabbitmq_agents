import errno
import functools
import os
import signal
import logging
import argparse
import pika
import pwd
import uuid
from rc_rmq import RCRMQ
import json
from urllib.parse import quote
from time import sleep
import rabbit_config as rcfg

rc_rmq = RCRMQ({"exchange": "RegUsr", "exchange_type": "topic"})
tasks = {
    "create_account": None,
    "git_commit": None,
    "dir_verify": None,
    "subscribe_mail_list": None,
    "notify_user": None,
}
logger_fmt = "%(asctime)s [%(module)s] - %(message)s"


class TimeoutError(Exception):
    pass


# From https://stackoverflow.com/questions/2281850
def timeout(seconds=30, error_message=os.strerror(errno.ETIME)):
    def decorator(func):
        def _handle_timeout(signum, frame):
            raise TimeoutError(error_message)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.alarm(seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result

        return wrapper

    return decorator


def add_account(
    username, queuename, email, full="", reason="", updated_by="", host=""
):
    rc_rmq.publish_msg(
        {
            "routing_key": "request." + queuename,
            "msg": {
                "username": username,
                "email": email,
                "fullname": full,
                "reason": reason,
                "queuename": queuename,
                "updated_by": updated_by,
                "host": host,
            },
        }
    )
    rc_rmq.disconnect()


def certify_account(
    username, queuename, state="ok", service="all", updated_by="", host=""
):
    rc_rmq.publish_msg(
        {
            "routing_key": "acctmgr.request." + queuename,
            "msg": {
                "username": username,
                "service": service,
                "state": state,
                "queuename": queuename,
                "updated_by": updated_by,
                "host": host,
            },
        }
    )
    rc_rmq.disconnect()


def worker(ch, method, properties, body):
    msg = json.loads(body)
    username = msg["username"]

    if msg["success"]:
        print(f"Account for {username} has been created.")
    else:
        print(f"There's some issue while creating account for {username}")
        errmsg = msg.get("errmsg", [])
        for err in errmsg:
            print(err)

    rc_rmq.stop_consume()
    rc_rmq.delete_queue()


def consume(
    queuename,
    routing_key="",
    callback=worker,
    bind=True,
    durable=True,
    exclusive=False,
    debug=False,
):
    if routing_key == "":
        routing_key = "complete." + queuename

    if debug:
        sleep(5)
    else:
        rc_rmq.start_consume(
            {
                "queue": queuename,
                "routing_key": routing_key,
                "bind": bind,
                "durable": durable,
                "exclusive": exclusive,
                "cb": callback,
            }
        )
        rc_rmq.disconnect()

    return {"success": True}


def get_args():
    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="verbose output"
    )
    parser.add_argument(
        "-n", "--dry-run", action="store_true", help="enable dry run mode"
    )
    return parser.parse_args()


def get_logger(args=None):
    if args is None:
        args = get_args()

    logger_lvl = logging.WARNING

    if args.verbose:
        logger_lvl = logging.DEBUG

    if args.dry_run:
        logger_lvl = logging.INFO

    logging.basicConfig(format=logger_fmt, level=logger_lvl)
    return logging.getLogger(__name__)


def encode_name(uname):
    uname_quote = quote(uname)
    if "." in uname_quote:
        uname_quote = uname_quote.replace(".", "%2E")
    return uname_quote


@timeout(rcfg.Function_timeout)
def check_state(username, debug=False):
    corr_id = str(uuid.uuid4())
    result = ""
    rpc_queue = "user_state"

    def handler(ch, method, properties, body):
        if debug:
            print("Message received:")
            print(body)

        nonlocal corr_id
        nonlocal result
        msg = json.loads(body)

        if corr_id == properties.correlation_id:
            if not msg["success"]:
                print("Something's wrong, please try again.")
            else:
                result = msg.get("state")

            rc_rmq.stop_consume()
            rc_rmq.disconnect()

    callback_queue = rc_rmq.bind_queue(exclusive=True)

    if debug:
        print(f"Checking state of user {username}")
        print(f"Callback queue: {callback_queue}, correlation_id: {corr_id}")

    rc_rmq.publish_msg(
        {
            "routing_key": rpc_queue,
            "props": pika.BasicProperties(
                correlation_id=corr_id, reply_to=callback_queue
            ),
            "msg": {"op": "get", "username": username},
        }
    )

    rc_rmq.start_consume(
        {
            "queue": callback_queue,
            "exclusive": True,
            "bind": False,
            "cb": handler,
        }
    )

    return result


@timeout(rcfg.Function_timeout)
def update_state(username, state, updated_by="", host="", debug=False):

    if state not in rcfg.Valid_state:
        print(f"Invalid state '{state}'")
        return False

    corr_id = str(uuid.uuid4())
    result = ""
    rpc_queue = "user_state"

    def handler(ch, method, properties, body):
        if debug:
            print("Message received:")
            print(body)

        nonlocal corr_id
        nonlocal result
        msg = json.loads(body)

        if corr_id == properties.correlation_id:
            if not msg["success"]:
                print("Something's wrong, please try again.")

            result = msg["success"]
            rc_rmq.stop_consume()
            rc_rmq.disconnect()

    callback_queue = rc_rmq.bind_queue(exclusive=True)

    rc_rmq.publish_msg(
        {
            "routing_key": rpc_queue,
            "props": pika.BasicProperties(
                reply_to=callback_queue, correlation_id=corr_id
            ),
            "msg": {
                "op": "post",
                "username": username,
                "state": state,
                "updated_by": updated_by,
                "host": host,
            },
        }
    )

    rc_rmq.start_consume(
        {
            "queue": callback_queue,
            "exclusive": True,
            "bind": False,
            "cb": handler,
        }
    )

    return result


def get_caller_info():
    username = pwd.getpwuid(os.getuid()).pw_name
    hostname = os.uname().nodename
    return (username, hostname)
