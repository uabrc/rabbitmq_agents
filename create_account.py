#!/usr/bin/env python3
import json
import sys
import rc_util
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('username', help='username that will be created')
parser.add_argument('email', nargs='?', default='', help="User's email")
parser.add_argument('full_name', nargs='?', default='', help="User's full name")
parser.add_argument('reason', nargs='?', default='', help='Reason of requesting')
parser.add_argument('--domain', default='localhost', help='domain of email')
parser.add_argument('-v', '--verbose', action='store_true', help='verbose output')
parser.add_argument('-n', '--dry-run', action='store_true', help='enable dry run mode')
args = parser.parse_args()

logger = rc_util.get_logger(args)

if args.email == '':
    args.email = args.username
    if '@' not in args.email:
        args.email = args.username + '@' + args.domain

def callback(channel, method, properties, body):
    msg = json.loads(body)
    username = msg['username']

    if msg['success']:
        print(f'Account for {username} has been created.')
    else:
        print(f"There's some issue while creating account for {username}")
        errmsg = msg.get('errmsg', [])
        for err in errmsg:
            print(err)

    rc_util.rc_rmq.stop_consume()
    rc_util.rc_rmq.delete_queue()


rc_util.add_account(args.username, email=args.email, full=args.full_name, reason=args.reason)
logger.info(f'Account for {args.username} requested.')

logger.info('Waiting for completion...')
rc_util.consume(args.username, routing_key=f'complete.{args.username}', callback=callback)
