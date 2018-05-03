# Load Testing Setup Script

This script creates a specified number of accounts (50 by default), users (50 per account by default), a specified number of queues (10 per account by default, maximum 10) and devices (one per user).
It then creates callflows for logging in and out of the created queues via extensions and callflows for joining the queues via an external number (either one external number per queue or via a menu where each menu option corresponds to a queue).

python uuid.uuid4() is used to randomize content in json fields in requests that need to be unique e.g. a user's username, sip credentials.

This script generates files in the directory it is placed in:
- numbers.txt is the list of numbers that have been assigned. The script uses this file to avoid collisions on the server. If this file gets deleted, collisions may occur when trying to add an external number. In the case of numbers.txt being deleted, put a number which has a higher numerical value than any on the server.
- edr_load_test.log contains the logging info of the runs of the script and may contain useful information when problemshooting.
- JSON files whose names start with 'test_info' contain information about accounts, users, devices and queues created during previous runs of the script. At the top level of these files are accounts, represented by key-value pairs where keys are account ids and values are account documents with extra information. Within an account document, a 'users' key is added. This contains key-value pairs of user ids (keys) and user documents with additional information, about a 'device' that has been created and assigned to the user. The SIP credentials of the devices can be used for testing by using them to log in to a sip device. Accounts also have information about queues added to them, as well as callflows to log in, log out and call into queues.

## Setting up

pip install -r requirements.txt

## Configuration

Edit config.py

1. Set CROSSBAR_URL

## Running

Minimum python version: 2.7

`python run.py [OPTIONS]`

e.g. `python run.py --accounts=10 --users=20 --queues=5 --num-per-queue`

Run with option `--help` to see a list of options.

