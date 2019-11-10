
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

def create_robot(access_token, service_logical_name, orch_url):
    body = {"Name": "test123", 
            "MachineName": os.environ['COMPUTERNAME'], 
            "Username": os.environ["USERDOMAIN"] + '\\' + os.environ["USERNAME"], 
            "Password": "!QAZxsw23edc", 
            "Type": "Development"}
    print(body)
    headers = { "X-UIPATH-TenantName":service_logical_name, 
                "Authorization": "Bearer " + access_token
            }

    print(headers)
    r = requests.post(orch_url + "/odata/Robots", headers=headers, json=body)
    print(r.json())
    os.system("\"C:\\Program Files (x86)\\UiPath\\Studio\\UiRobot.exe\" --connect -url " + orch_url + " -key "+ r.json()["LicenseKey"])



def main():
    uri = get_secret('https://test-vault-presales.vault.azure.net/','mongo-db-conn-string','1a775478f0024c2e9d0b2d48b21fa8bb') 
    client = MongoClient(uri)
    col = client.demoVmConfig['config']

    config = col.find_one({"id": "test"})['configuration']
    
    print(config)
    access_token = get_access_token(config['refreshToken'], config['clientId'], config['authUrl'])
    create_robot(access_token, config['serviceLogicalName'], config['orchUrl'])

def main1(args):
    """ Main entry point of the app """
    print("hello world")
    print(args)

if __name__ == '__main__': 
    """ This is executed when run from the command line """
    parser = argparse.ArgumentParser()

    # Required positional argument
    parser.add_argument("arg", help="Required positional argument")

    # Optional argument flag which defaults to False
    parser.add_argument("-f", "--flag", action="store_true", default=False)

    # Optional argument which requires a parameter (eg. -d test)
    parser.add_argument("-n", "--name", action="store", dest="name")

    # Optional verbosity counter (eg. -v, -vv, -vvv, etc.)
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Verbosity (-v, -vv, etc)")

    # Specify output of "--version"
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s (version {version})".format(version=__version__))

    args = parser.parse_args()
    main1(args)

