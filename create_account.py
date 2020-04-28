#!/usr/bin/env python3
import rc_util
import argparse

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

rc_util.add_account(args.username, email=args.email, full=args.full_name, reason=args.reason)
print(f'Account for {args.username} requested.')

print("Waiting for confirmation...")
rc_util.consume(args.username)
