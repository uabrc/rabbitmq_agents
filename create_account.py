#!/usr/bin/env python
import sys
import rc_util

if len(sys.argv) < 2:
    print("Usage: {} USERNAME [EMAIL] [FULL_NAME] [REASON]".format(sys.argv[0]), file=sys.stderr)
    exit(1)

domain = 'uab.edu'
user_name = sys.argv[1]
email = sys.argv[2] if len(sys.argv) >= 3 else ''
full_name = sys.argv[3] if len(sys.argv) >= 4 else ''
reason    = sys.argv[4] if len(sys.argv) >= 5 else ''

if email == '':
    if '@' in user_name:
        email = user_name
    else:
        email = user_name + '@' + domain

rc_util.add_account(user_name, email=email, full=full_name, reason=reason)
print("Account requested for user: {}".format(user_name))

print("Waiting for confirmation...")
rc_util.consume(user_name)
