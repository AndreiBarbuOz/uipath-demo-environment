
__author__ = "Andrei"
__version__ = "0.0.1"

from pymongo import MongoClient
import subprocess
import argparse
import json

from msrestazure.azure_active_directory import MSIAuthentication
from azure.mgmt.resource import ResourceManagementClient, SubscriptionClient
from azure.keyvault import KeyVaultClient

import orch_setup 


local_config_path = 'c:\\UiPath\\config\\dsf.json'

def get_secret(key_vault, key_name, key_version):
    # Create MSI Authentication
    credentials = MSIAuthentication()
    client = KeyVaultClient(credentials)
    
    secret_bundle = client.get_secret(key_vault, key_name, key_version )
    secret = secret_bundle.value
    return secret


def get_local_config(path):
    with open(path) as json_file:
        data = json.load(json_file)
    return data

def write_local_config(path, data):
    with open(path, 'w') as json_file:
        json.dump(data, json_file)

def get_config(mongoUri):
    client = MongoClient(mongoUri)
    col = client.demoVmConfig['config']

    return col.find_one({"id": "test"})['configuration']
    
def main(args):
    # read/write local config
    local_config = get_local_config(local_config_path)
    write_local_config(local_config_path, local_config)
    
    # fetch config and connect robot
    config = get_config(local_config['mongoDBConnectionString'])
    print(config)
    orch = orch_setup.CloudOrchHelper(config['authUrl'], config['clientId'],
                                     config['refreshToken'], config['orchUrl'], config['serviceLogicalName'])
    orch_setup.setup_dsf_folder(
        orch, args.password, config['processes'], config['assets'])

#    uri = get_secret('https://test-vault-presales.vault.azure.net/','mongo-db-conn-string','1a775478f0024c2e9d0b2d48b21fa8bb') 

if __name__ == '__main__': 
    """ This is executed when run from the command line """
    parser = argparse.ArgumentParser(description="Configure UiPath Robot")

    # Optional argument which requires a parameter (eg. -d test)
    parser.add_argument("-p", "--password", action="store", dest="password")

    args = parser.parse_args()
    print(args)
    main(args)


