#!/usr/bin/env python3
import os
import sys
import subprocess

sys.path.insert(1, os.path.join(sys.path[0], "../.."))
import rc_util


# During migration of this new script for ood
# e.g. not all of users are in the db
migration = True
# migration = False  # uncomment after migration's done
remote_user = sys.argv[1]

result = rc_util.check_user(remote_user)

if result == "ok":
    print(remote_user)
else:
    if migration:
        rc = subprocess.run(["getent", "passwd", remote_user]).returncode
        if rc == 0:
            rc_util.update_user(remote_user, "ok")
            print(remote_user)
            sys.exit()
    print()
