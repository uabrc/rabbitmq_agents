#!/usr/bin/env python
import sys
import rc_util

if len(sys.argv) < 2:
    print("Usage: {} USERNAME [FULL_NAME] [REASON]".format(sys.argv[0]), file=sys.stderr)
    exit(1)

user_name = sys.argv[1]
full_name = sys.argv[2] if len(sys.argv) >= 3 else ''
reason    = sys.argv[3] if len(sys.argv) >= 4 else ''

rc_util.add_account(user_name, full=full_name, reason=reason)
print("Account requested for user: {}".format(user_name))

print("Waiting for confirmation...")
rc_util.consume(user_name)
