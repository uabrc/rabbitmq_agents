#!/usr/bin/env python3
import sys
import rc_util
import subprocess

# During migration of this new script for ood
# e.g. not all of users are in the db
migration = True
default_state = "ok"
# migration = False  # uncomment after migration's done
remote_user = sys.argv[1]

result = rc_util.check_state(remote_user)

if result == "ok":
    print(remote_user)
else:
    if migration and result == "no-account":
        rc = subprocess.run(
            ["getent", "passwd", remote_user], stdout=subprocess.DEVNULL
        ).returncode
        if rc == 0:
            rc_util.update_state(remote_user, default_state)
            print(remote_user)
            sys.exit()
    print()
