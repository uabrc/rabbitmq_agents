#!/bin/sh
username="$1"
usage() {
  echo "Usage: $0 USERNAME"
}
if [[ "$EUID" -ne 0 ]]; then
  echo "This script must be run as root!"
  exit 1
fi
if [ -z "$username" ]; then
  usage
  exit 1
fi
if id "$username" &>/dev/null; then
  echo "Deleting nginx process running under user: ${username}"
  kill -9 ` ps -ef | grep 'nginx' | grep  ${username} | awk '{print $2}'`
  echo "Deleted process"
else
  echo "user: ${username} not found."
  exit 1
fi
