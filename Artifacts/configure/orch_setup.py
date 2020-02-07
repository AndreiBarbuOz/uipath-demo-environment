import requests
import os
import getpass

class CloudOrchHelper:
    def __init__(self, username, auth_url, client_id, refresh_token, orch_url, service_logical_name):
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.auth_url = auth_url.rstrip("/")
        self.service_logical_name = service_logical_name
        self.orch_url = orch_url.rstrip("/")

        # filled in later
        self.organization_unit_id = None
        self.environment_id = None
        self.environment_name = None
        # note: sap user name has to be 12 chars max so we make it unique by using the env id
        self.sap_user_name = None

        self.username = username
        self.machine_name = os.environ['COMPUTERNAME']
        self.robot_name = (self.machine_name + '_' + self.username)[0:19]
        self.full_username = self.machine_name + '\\' + self.username
        self.folder_name = "DSF_" + self.robot_name
        

        self.login()

    def _getAbsoluteEndpoint(self, relative_endpoint):
        return self.orch_url + relative_endpoint

    def _get_access_token(self):
        body = {"grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "client_id": self.client_id}
        r = requests.post(self.auth_url + "/oauth/token", json=body)
        return r.json()['access_token']

    def _get_default_headers(self):
        return {"X-UIPATH-TenantName": self.service_logical_name,
                "Authorization": "Bearer " + self.access_token,
                "X-UIPATH-OrganizationUnitId": self.organization_unit_id
                }

    def post(self, relative_endpoint, body):
        headers = self._get_default_headers()
        return requests.post(self._getAbsoluteEndpoint(relative_endpoint),
                          headers=headers, json=body)

    def get(self, relative_endpoint):
        headers = self._get_default_headers()
        return requests.get(self._getAbsoluteEndpoint(relative_endpoint), headers=headers)

    def login(self):
        self.access_token = self._get_access_token()

    def _create_folder(self, foldername):
        print("Creating folder")
        body = {
            "DisplayName": foldername,
            "ProvisionType": "Manual",
            "PermissionModel": "InheritFromTenant"
        }
        print(body)
        r = self.post("/odata/Folders", body)
        r = r.json()
        print(r)
        self.organization_unit_id = str(r["Id"])
        self.sap_user_name = "DSF_" + self.organization_unit_id 
        return str(r["Id"])

    def create_folder(self):
        return self._create_folder(self.folder_name)

    def create_and_connect_robot(self, password):
        print("Creating robot")
        body = {"Name": self.robot_name,
                "MachineName": self.machine_name,
                "Username": self.full_username,
                "Password": password,
                "Type": "Development",
                "ExecutionSettings": {
                    "LoginToConsole": False
                }
            }
        print(body)
        r = self.post("/odata/Robots", body)
        r = r.json()
        print(r)
        print("Connecting robot")
        license_key = r["LicenseKey"]
        os.system(
            f"\"C:\\Program Files (x86)\\UiPath\\Studio\\UiRobot.exe\" --connect -url {self.orch_url} -key {license_key}")
        return (r["Id"], r["UserId"])

    def assign_user_role(self, user_id, role_id):
        print("Assigning user role")
        body = {
            "addedUserIds": [
                user_id
            ],
            "removedUserIds": []
        }
        print(body)
        self.post(f"/odata/Roles({role_id})/UiPath.Server.Configuration.OData.SetUsers", body)

    def create_environment(self, environment_name):
        print("Creating environment")
        self.environment_name = environment_name
        body = {"Name": environment_name}
        print(body)
        r = self.post("/odata/Environments", body)
        r = r.json()
        self.environment_id = r["Id"]
        return r["Id"]

    def add_robot_to_environment(self, robot_id, environment_id):
        print("Adding robot to environment")
        body = {"robotId": str(robot_id)}
        print(body)
        self.post(f"/odata/Environments({str(environment_id)})/UiPath.Server.Configuration.OData.AddRobot", body)

    def download_package(self, key, target_path):
        print("Downloading package")
        r = self.get(f"/odata/Processes/UiPath.Server.Configuration.OData.DownloadPackage(key='{key}')")
        with open(target_path, 'wb') as f:
            f.write(r.content)

    def upload_package(self, source_path):
        print("Uploading package")
        headers = self._get_default_headers()
        files = {'upload_file': open(source_path, 'rb')}
        r = requests.post(
            self.orch_url + "/odata/Processes/UiPath.Server.Configuration.OData.UploadPackage", headers=headers, files=files)
        print(r.json())

    def publish_release(self, process_key, process_version):
        print(f"Publishing release {process_key}")
        body = {
            "Name": process_key + "_" + self.environment_name,
            "ProcessKey": process_key,
            "ProcessVersion": process_version,
            "EnvironmentId": self.environment_id
        }
        print(body)
        r = self.post("/odata/Releases", body=body)
        print(r.json())
        return r.json()["Key"]

    def create_asset(self, asset_data):
        print(f"Creating asset %s" % asset_data["Name"])
        body = asset_data
        print(body)
        r = self.post("/odata/Assets", body=body)
        print(r.json())
        return r.json()
    
    def get_role_id(self, role_name):
        r = self.get(f"/odata/Roles?$filter=Name eq '{role_name}'")
        print(r.json())
        return r.json()["value"][0]["Id"]

    def get_latest_process_version_by_package_name(self, package_name):
        r = self.get(f"/odata/Processes?$filter=Id eq '{package_name}'")
        print(r.json())
        first_process = r.json()["value"][0]
        return first_process["Version"]

    def get_latest_release_for_process(self, process_key):
        r = self.get(f"/odata/Releases?$filter=ProcessKey eq '{process_key}'")
        print(r.json())
        first_release = r.json()["value"][0]
        return (first_release["Key"], first_release["ProcessVersion"])

    def start_process(self, release_key, robot_id, input_arguments):
        print("Starting process")
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
        print(self.post("/odata/Jobs/UiPath.Server.Configuration.OData.StartJobs", body).json())

def setup_dsf_folder(orchHelper, password, ms_account_user, ms_account_pw, process_list, autoarm_list, asset_list):
    folder_id = orchHelper.create_folder()

    (robot_id, user_id) = orchHelper.create_and_connect_robot(password)
    environment_id = orchHelper.create_environment("Demo")
    orchHelper.add_robot_to_environment(robot_id, environment_id)
    role_id = orchHelper.get_role_id("DSF_Robot")
    orchHelper.assign_user_role(user_id, role_id)
    
    release_keys = []
    autoarm_release_keys = []

    for process_cfg in process_list:
        process_name = process_cfg["Name"]
        process_args = process_cfg["Args"]
        version = process_cfg["Version"] if "Version" in process_cfg else orchHelper.get_latest_process_version_by_package_name(
            process_name)
        release_key = orchHelper.publish_release(process_name, version)
        if process_cfg["Autostart"] == True:
            release_keys.append((release_key, process_args, process_cfg["Autostart"]))
        if process_name in autoarm_list:
            autoarm_release_keys.append(release_key)

    for asset_data in asset_list:
        orchHelper.create_asset(asset_data)

    # ms office account
    orchHelper.create_asset({
        "Name": "DSF_MS-Account",
        "ValueScope": "Global",
        "ValueType": "Credential",
        "CredentialUsername": ms_account_user,
        "CredentialPassword": ms_account_pw
    })


    # autostart by default
    for (release_key, process_args) in release_keys:
        orchHelper.start_process(release_key, robot_id, process_args.format(orchHelper=orchHelper))

    # auto-arm based on arguments
    for release_key in autoarm_release_keys:
        orchHelper.start_process(release_key, robot_id, "{'Mode': 'arm'}")


def setup_dsf_folder_dev(orchHelper, password, ms_account_user, ms_account_pw, process_list, autoarm_list, asset_list):
    print(autoarm_list)
