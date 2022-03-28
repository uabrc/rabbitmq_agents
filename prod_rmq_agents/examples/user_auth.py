#!/usr/bin/env python3
import os
import sys

sys.path.insert(1, os.path.join(sys.path[0], "../.."))
import rc_util


remote_user = sys.argv[1]

result = rc_util.check_user(remote_user)

if result == "ok":
    print(remote_user)
else:
    print()
