#!/usr/bin/env python3
import rc_util
import argparse

logger = rc_util.get_logger()

parser = argparse.ArgumentParser()
parser.add_argument('username', help='username that will be created')
parser.add_argument('email', nargs='?', default='', help="User's email")
parser.add_argument('full_name', nargs='?', default='', help="User's full name")
parser.add_argument('reason', nargs='?', default='', help='Reason of requesting')
parser.add_argument('--domain', default='localhost', help='domain of email')
args = parser.parse_args()

if args.email == '':
    args.email = args.username
    if '@' not in args.email:
        args.email = args.username + '@' + args.domain

def callback(channel, method, properties, body):
    msg = json.loads(body)
    username = msg['username']

    logger.info(f'Account for {username} has been created.')

    rc_rmq.stop_consume()
    rc_rmq.delete_queue()


rc_util.add_account(args.username, email=args.email, full=args.full_name, reason=args.reason)
logger.info(f'Account for {args.username} requested.')

logger.info('Waiting for completion...')
rc_util.consume(args.username, routing_key=f'complete.{args.username}', callback=callback)
