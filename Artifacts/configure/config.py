
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

class CloudOrchHelper:
    def __init__(self, auth_url, client_id, refresh_token, orch_url, service_logical_name, organization_unit_id):
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.auth_url = auth_url
        self.service_logical_name = service_logical_name
        self.orch_url = orch_url
        self.organization_unit_id = organization_unit_id
        self.login()
    

    def _get_access_token(self):
        body = {"grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "client_id": self.client_id}
        r = requests.post(self.auth_url + "/oauth/token", json=body)
        print(r.json())
        return r.json()['access_token']

    def _get_default_headers(self):
        return {"X-UIPATH-TenantName": self.service_logical_name,
                "Authorization": "Bearer " + self.access_token,
                "X-UIPATH-OrganizationUnitId": self.organization_unit_id
                }

    def login(self):
        self.access_token = self._get_access_token()
    
    def create_and_connect_robot(self, username, password):
        body = {"Name": (os.environ["COMPUTERNAME"] + '_' + username)[0:19],
                "MachineName": os.environ['COMPUTERNAME'],
                "Username": os.environ["COMPUTERNAME"] + '\\' + username,
                "Password": password,
                "Type": "Development"}
        print(body)
        headers = self._get_default_headers()
        print(headers)
        r = requests.post(self.orch_url + "/odata/Robots", headers=headers, json=body)
        print(r.json())
        os.system("\"C:\\Program Files (x86)\\UiPath\\Studio\\UiRobot.exe\" --connect -url " +
                self.orch_url + " -key " + r.json()["LicenseKey"])
        return r.json()["Id"]
    
    def add_robot_to_environment(self, robot_id, environment_id):
        body = {"robotId": str(robot_id)}
        print(body)
        headers = self._get_default_headers()
        print(headers)
        requests.post(self.orch_url + "/odata/Environments(" + str(environment_id) +
                    ")/UiPath.Server.Configuration.OData.AddRobot", headers=headers, json=body)

    def get_release_key_for_process(self, processName):
        headers = self._get_default_headers()
        print(headers)
        r = requests.get(self.orch_url + "/odata/Releases?$filter=ProcessKey eq '" +
                        processName + "'", headers=headers)
        print(r.json())
        return r.json()["value"][0]["Key"]

    def start_process(self, release_key, robot_id, input_arguments):
        body = {
            "startInfo": {
                "ReleaseKey": release_key,
                "Strategy": "Specific",
                "RobotIds": [robot_id],
                "Source": "Manual",
                "InputArguments": input_arguments
            }
        }
        print(body)
        headers = self._get_default_headers()
        print(headers)
        requests.post(self.orch_url + "/odata/Jobs/UiPath.Server.Configuration.OData.StartJobs",
                          headers=headers, json=body)


def get_secret(key_vault, key_name, key_version):
    # Create MSI Authentication
    credentials = MSIAuthentication()
    client = KeyVaultClient(credentials)
    
    secret_bundle = client.get_secret(key_vault, key_name, key_version )
    secret = secret_bundle.value
    return secret


   

def get_config(mongoUri):
    client = MongoClient(mongoUri)
    col = client.demoVmConfig['config']

    return col.find_one({"id": "test"})['configuration']
    
def main(args):
    config = get_config(args.connString)
    print(config)
    orch = CloudOrchHelper(config['authUrl'], config['clientId'], config['refreshToken'], config['orchUrl'], config['serviceLogicalName'], config["organizationUnitID"])
    robot_id = orch.create_and_connect_robot(args.username, args.password)
    orch.add_robot_to_environment(robot_id, config['environment'])
    release_key = orch.get_release_key_for_process("DSF_Init")
    orch.start_process(release_key, robot_id, "{'UserName': 'DSF_" + os.environ["COMPUTERNAME"] + "_" + args.username + "'}")

#    uri = get_secret('https://test-vault-presales.vault.azure.net/','mongo-db-conn-string','1a775478f0024c2e9d0b2d48b21fa8bb') 

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

