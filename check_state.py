#!/usr/bin/env python3
import sys
import rc_util

remote_user = sys.argv[1]

result = rc_util.check_state(remote_user)

print(result)
