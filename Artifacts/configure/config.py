
__author__ = "Andrei"
__version__ = "0.0.1"

from pymongo import MongoClient
import subprocess
import argparse
import json
import os
import time
import shutil

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

def copy_sap_config(username):
    shutil.copyfile("C:\\Temp\\configFiles\\SAPUILandscape.xml", "c:\\Users\\" + username + "\\" + "AppData\\Roaming\\SAP\\Common\\SAPUILandscape.xml")
    
def main(args):
    # read/write local config
    local_config = get_local_config(local_config_path)
    
    # start robot service
    os.system("sc.exe start UiRobotSvc")
    time.sleep(15)

    # fetch config and connect robot
    config = get_config(local_config['mongoDBConnectionString'])
    orch = orch_setup.CloudOrchHelper(args.username, config['authUrl'], config['clientId'],
                                     config['refreshToken'], config['orchUrl'], config['serviceLogicalName'])
    orch_setup.setup_dsf_folder(
        orch, args.password, args.ms_account_user, args.ms_account_pw, config['processes'], config['assets'])

    # copy sap config
    print(orch.username)
    copy_sap_config(args.username)

    local_config['EnvironmentId'] = orch.environment_id
    local_config['EnvironmentName'] = orch.environment_name
    local_config['FolderName'] = orch.folder_name
    local_config['OrganizationUnitID'] = orch.organization_unit_id
    local_config['SAPUserName'] = orch.sap_user_name
    local_config['MSAccount'] = args.ms_account_user
    write_local_config(local_config_path, local_config)

#    uri = get_secret('https://test-vault-presales.vault.azure.net/','mongo-db-conn-string','1a775478f0024c2e9d0b2d48b21fa8bb') 

if __name__ == '__main__': 
    """ This is executed when run from the command line """
    parser = argparse.ArgumentParser(description="Configure UiPath Robot")

    # Optional argument which requires a parameter (eg. -d test)
    parser.add_argument("-u", "--username", action="store", dest="username")
    parser.add_argument("-p", "--password", action="store", dest="password")
    parser.add_argument("--ms_account_user", action="store", dest="ms_account_user")
    parser.add_argument("--ms_account_pw", action="store", dest="ms_account_pw")

    args = parser.parse_args()
    main(args)


