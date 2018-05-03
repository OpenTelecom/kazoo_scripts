#!/usr/bin/env python2

"""
Script Name: Load Testing Setup
Source Name: run.py
Author: Lubomira Tzankov
"""

import config
import crossbar_api
import logging
import argparse
import uuid
import time
import json

# Globals
api = crossbar_api.CrossbarAPI()

test_info = {} # will contain all accounts, users, etc

logging.basicConfig(level=logging.INFO)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
log = logging.getLogger("run")
hdlr = logging.FileHandler('./edr_load_test.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
log.addHandler(hdlr)

def create_account(uuid_seed):
    name_and_realm = 'test_account_{}'.format(uuid_seed)
    data = {
        'name': name_and_realm,
        'language': 'en-nz',
        'realm': name_and_realm
    }
    response = api.put('accounts', data)
    test_info[response['id']] = data
    return response

def generate_users(account_id):
    for i in xrange(args.users):
        last_name = 'User_{}'.format(uuid.uuid4()).replace('_', '') # remove underscores to pass validation
        email = '{}@test.com'.format(last_name)
        data = {
            'first_name': 'Test',
            'last_name': last_name,
            'email': email,
            'username': email,
            'password': '123456789'
        }
        response = api.put('accounts/{}/users'.format(account_id), data)
    generated_users = api.get('accounts/{}/users'.format(account_id))
    # convert list of users into dict where key is user id and value is user doc.
    generated_users_dict = {}
    for user in generated_users:
        generated_users_dict[user['id']] = user
    print(generated_users_dict)
    test_info[account_id]['users'] = generated_users_dict
    return generated_users

def create_device(ownerid, accountid):
    name_uuid = str(uuid.uuid4())
    data = {
        'name': 'test_device_{}'.format(name_uuid),
        'owner_id': ownerid,
        'sip': {
            'expire_seconds': 300,
            'invite_format': 'contact',
            'method': 'password',
            'username': name_uuid[:32],
            'password': name_uuid[:32] # 32 char limit on password
        }
    }
    response = api.put('accounts/{}/devices'.format(accountid), data)
    # get index of owner in user list so that device can be added to that user
    test_info[accountid]['users'][ownerid]['device'] = response
    return data

def add_external_num(account_id):
    # Get last number and generate next number by incrementing
    number_list = []
    with open('numberlist.txt', 'a+') as numbers_file:
        number_list = numbers_file.read().rstrip().split('\n')
        number_list = filter(None, number_list) # remove empty strings
    data = {}
    lastnum = 999999999
    if len(number_list) > 0:
        lastnum = number_list[-1]
    number_to_add = str(long(lastnum) + 1)
    number_list.append(number_to_add)
    with open('numberlist.txt', 'a+') as number_file:
        number_file.writelines(['\n{}'.format(number_to_add)])
    api.put('accounts/{}/phone_numbers/%2B{}'.format(account_id, number_to_add), data)
    log.info('Successfully added number {} to account {}.'.format(number_to_add, account_id))
    api.put('accounts/{}/phone_numbers/%2B{}/activate'.format(account_id, number_to_add), data)
    log.info('Successfully activated number {} on account {}.'.format(number_to_add, account_id))
    test_info[account_id]['external_number'] = number_to_add
    return number_to_add

def create_queues(account_id):
    for i in xrange(args.queues):
        data = {
            'name': 'Test Queue {}'.format(uuid.uuid4())
        }
        api.put('accounts/{}/queues'.format(account_id), data)
    queues = api.get('accounts/{}/queues'.format(account_id))
    test_info[account_id]['queues'] = queues

"""For each queue in account, create login callflow and logout callflow."""
def create_login_logout_callflows(account):
    queues = api.get('accounts/{}/queues'.format(account))
    test_info[account]['callflows'] = []
    for index, queue in enumerate(queues):
        # create login callflow
        data = {
            'flow': {
                'data': {
                    'action': 'login',
                    'id': queue['id']
                },
                'module': 'acdc_queue',
                'children': {}
            },
            'numbers': [str(5000 + 2 * index - 1)]
        }
        log.info(data)
        callflow = api.put('accounts/{}/callflows'.format(account), data)
        test_info[account]['callflows'].append(callflow)
        # create logout callflow
        data = {
            'flow': {
                'data': {
                    'action': 'logout',
                    'id': queue['id']
                },
                'module': 'acdc_queue',
                'children': {}
            },
            'numbers': [str(5000 + 2 * index)]
        }
        callflow = api.put('accounts/{}/callflows'.format(account), data)
        test_info[account]['callflows'].append(callflow)

def create_queues_menu_callflow(account):
    queues = api.get('accounts/{}/queues'.format(account))
    # create menu
    data = {
        'allow_record_from_offnet': False,
        'hunt': False,
        'max_extension_length': 4,
        'media': {
            'exit_media': True,
            'invalid_media': True,
            'transfer_media': True
        },
        'name': 'menu_{}'.format(uuid.uuid4()),
        'retries': '3',
        'suppress_media': False,
        'timeout': 10000
    }
    response = api.put('accounts/{}/menus'.format(account), data)

    # put menu into callflow where each option is a queue to join
    options = {}
    for index, queue in enumerate(queues):
        options[str(index)] = {
            'children': {},
            'data': {
                'id': queue['id']
            },
            'module': 'acdc_member'
        }
    callflow = {
        'flow': {
            'children': options,
            'data': {
                'id': response['id']
            },
            'module': 'menu',
        },
        'numbers': [external_num]
    }
    response = api.put('accounts/{}/callflows'.format(account), callflow)
    test_info[account]['queue_callflow'] = response

def link_number_to_queue(account, number, queue_id):
    callflow_data = {
        'flow': {
            'children': {},
            'data': {
                'id': queue_id
            },
            'module': 'acdc_member'
        },
        'numbers': [number]
    }
    print(account)
    response = api.put('accounts/{}/callflows'.format(account), callflow_data)
    test_info[account]['queue_callflows'][number] = response

# allows usage of different boolean formats for flag
def str2bool(v):
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

if __name__ == '__main__':

    # Set up argparse to take command line arguments
    parser = argparse.ArgumentParser(description='Set up for realistic call testing for EDR.')
    parser.add_argument('--accounts', metavar='-n', type=int, default=50,
                            help='an integer stating how many accounts to create during test setup. Defaults to 50.')
    parser.add_argument('--users', metavar='-u', type=int, default=50,
                            help='an integer stating how many users to create per account during test setup. Defaults to 50.')
    parser.add_argument('--queues', metavar='-q', type=int, default=10, choices=range(1,11),
                            help='an integer stating how many queues to create per account during test setup. Defaults to 10. Must be between 1 and 10 to have enough options to map to in a menu (keys 0 to 9).')
    parser.add_argument('--num-per-queue', type=str2bool, nargs='?', default=False, metavar='-npq', dest='num_per_queue',help='overrides the default queue access which uses a single external number per account, with a menu where each option directs to a queue. Instead creates an external number per queue, which when called, joins the caller to the queue. ')

    args = parser.parse_args()

    #Need to authenticate as superduper admin for some of the api calls e.g. numbers
    print('Please log in as a super duper admin.')
    api.log_in()

    # Create accounts and perform setup
    accounts = []
    log.info('Creating {} accounts...'.format(args.accounts))
    for i in xrange(args.accounts):
        # generate account, generate and use unique uuid in account fields
        account = create_account(uuid.uuid4())
        log.info('Account created: {}'.format(account))
        accountid = account['id']
        accounts.append(account)
        # generate users for account
        log.info('Creating users for account {}...'.format(accountid))
        users = generate_users(accountid)
        log.info('Users created: {}'.format(users))
        # add a new device to every user
        log.info('Adding a device to every user in the account...')
        for j in xrange(args.users):
            response = create_device(users[j]['id'], accountid)
            log.info(response)

        #if --num-per-queue specified, create external number per queue for joining, otherwise use menu options.
        if args.num_per_queue:
            log.info('Creating {} number(s) and queue(s), one to one...'.format(args.queues))
            external_nums = []
            create_queues(accountid)
            queues = api.get('accounts/{}/queues'.format(accountid))
            test_info[accountid]['queue_callflows'] = {}
            for k, queue in enumerate(queues):
                external_num = add_external_num(accountid)
                external_nums.append(external_num)
                link_number_to_queue(accountid, external_num, queue['id'])
                log.info('Linked number {} to queue {} on account {}.'.format(external_num, queue['id'], account))
        else:
            # add external number to account
            log.info('Adding an external number to the account...')
            external_num = add_external_num(accountid)
            # create queues for account
            log.info('Creating {} queues for the account...'.format(args.queues))
            create_queues(accountid)
            # create login/logout callflows
            log.info('Creating callflows to log in and log out of each queue...')
            create_login_logout_callflows(accountid)
            # create queues menu callflow
            log.info('Creating callflow on external number to menu for joining queues...')
            create_queues_menu_callflow(accountid)
            log.info('Finished setup of account {}.'.format(accountid))

    # Print test_info to file
    with open('test_info_{}.json'.format(time.time()), 'w') as test_data_output:
        test_data_output.write(json.dumps(test_info, indent=4))

    log.info('Finished performing setup for load testing.')
