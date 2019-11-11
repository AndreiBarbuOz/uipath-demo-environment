
__author__ = "Andrei"
__version__ = "0.0.1"

from pymongo import MongoClient
import os
import requests
import subprocess
import argparse

from msrestazure.azure_active_directory import MSIAuthentication
from azure.mgmt.resource import ResourceManagementClient, SubscriptionClient
from azure.keyvault import KeyVaultClient

def get_secret(key_vault, key_name, key_version):
    # Create MSI Authentication
    credentials = MSIAuthentication()
    client = KeyVaultClient(credentials)
    
    secret_bundle = client.get_secret(key_vault, key_name, key_version )
    secret = secret_bundle.value
    return secret

def get_access_token(refresh_token, client_id, auth_url):
    body = {"grant_type": "refresh_token",
              "refresh_token": refresh_token,
              "client_id": client_id}
    r = requests.post(auth_url + "/oauth/token", json=body)
    print(r.json())
    return r.json()['access_token']

def create_robot(access_token, service_logical_name, orch_url, username, password):
    body = {"Name": "test123", 
            "MachineName": os.environ['COMPUTERNAME'], 
            "Username": os.environ["COMPUTERNAME"] + '\\' + username, 
            "Password": password, 
            "Type": "Development"}
    print(body)
    headers = { "X-UIPATH-TenantName":service_logical_name, 
                "Authorization": "Bearer " + access_token
            }

    print(headers)
    r = requests.post(orch_url + "/odata/Robots", headers=headers, json=body)
    print(r.json())
    os.system("\"C:\\Program Files (x86)\\UiPath\\Studio\\UiRobot.exe\" --connect -url " + orch_url + " -key "+ r.json()["LicenseKey"])

def get_config(mongoUri):
    client = MongoClient(mongoUri)
    col = client.demoVmConfig['config']

    return col.find_one({"id": "test"})['configuration']
    
def main(args):
    config = get_config(args.connString)
    print(config)
    access_token = get_access_token(config['refreshToken'], config['clientId'], config['authUrl'])
#    uri = get_secret('https://test-vault-presales.vault.azure.net/','mongo-db-conn-string','1a775478f0024c2e9d0b2d48b21fa8bb') 
    create_robot(access_token, config['serviceLogicalName'], config['orchUrl'], args.username, args.password)


if __name__ == '__main__': 
    """ This is executed when run from the command line """
    parser = argparse.ArgumentParser(description="Configure UiPath Robot")

    # Optional argument which requires a parameter (eg. -d test)
    parser.add_argument("-c", "--connString", action="store", dest="connString")
    parser.add_argument("-u", "--user", action="store", dest="username")
    parser.add_argument("-p", "--password", action="store", dest="password")

    args = parser.parse_args()
    print(args)
    main(args)

