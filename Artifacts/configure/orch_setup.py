import requests
import os
import time
import getpass

class CloudOrchHelper:
    def __init__(self, username, auth_url, client_id, refresh_token, orch_url, service_logical_name, account_name):
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.auth_url = auth_url.rstrip("/")
        self.service_logical_name = service_logical_name
        self.account_name = account_name
        self.orch_url = orch_url.rstrip("/")

        # filled in later
        self.access_token = None
        self.id_token = None
        self.organization_unit_id = None
        self.environment_id = None
        self.environment_name = None
        self.user_id = None
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
        r = r.json()
        self.access_token = r['access_token']
        self.id_token = r['id_token']
        return r['access_token']

    def _get_default_headers(self):
        return {"X-UIPATH-TenantName": self.service_logical_name,
                "Authorization": "Bearer " + self.access_token,
                "X-UIPATH-OrganizationUnitId": self.organization_unit_id
                }

    def post(self, relative_endpoint, body):
        headers = self._get_default_headers()
        return requests.post(self._getAbsoluteEndpoint(relative_endpoint),
                          headers=headers, json=body)

    def patch(self, relative_endpoint, body):
        headers = self._get_default_headers()
        return requests.patch(self._getAbsoluteEndpoint(relative_endpoint),
                             headers=headers, json=body)

    def get(self, relative_endpoint):
        headers = self._get_default_headers()
        return requests.get(self._getAbsoluteEndpoint(relative_endpoint), headers=headers)

    def login(self):
        self._get_access_token()

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

    def _get_my_account_user_id(self):
        headers = {"Authorization": "Bearer " + self.id_token}
        body = {'guid': None}
        r = requests.post(self._getAbsoluteEndpoint(
            '/portal_/api/profile/getLoggedInUser'), json=body, headers=headers)
        r = r.json()
        my_account = [acc for acc in r if acc['accountUserDto']['accountLogicalName'] == self.account_name][0]
        return my_account['accountUserDto']['id']

    def _get_all_services(self, account_user_id):
        headers = {"Authorization": "Bearer " + self.id_token}
        body = {'accountUserId': account_user_id}
        r = requests.post(self._getAbsoluteEndpoint(
            f'/{self.account_name}/portal_/api/serviceInstance/services'), json=body, headers=headers)
        r = r.json()
        return r
    
    def _get_all_users(self, account_user_id):
        headers = {"Authorization": "Bearer " + self.id_token}
        body = {'accountUserId': account_user_id}
        r = requests.post(self._getAbsoluteEndpoint(
            f'/{self.account_name}/portal_/api/users'), json=body, headers=headers)
        r = r.json()
        return r
    
    def _get_user_id_account(self, account_user_id, user_email):
        all_users = self._get_all_users(account_user_id)
        my_users = [usr for usr in all_users if usr['emailId'] == user_email]
        if len(my_users) > 0:
            return my_users[0]['id']
        else:
            return None

    def _get_my_service_id(self, account_user_id):
        all_services = self._get_all_services(account_user_id)
        my_service = [serv for serv in all_services if serv['logicalName'] == self.service_logical_name][0]
        return my_service['id']
    
    def _add_user_to_service(self, service_id, user_id, roles):
        headers = {"Authorization": "Bearer " + self.id_token}
        body = {
            "tenantId": service_id,
            "tenantData": [
                {
                    "user": {
                        "id": user_id
                    },
                    "serviceRoles": roles
                }
            ]
        }
        r = requests.post(self._getAbsoluteEndpoint(
            f"/portal_/api/serviceInstance/addUsersInService"), headers=headers, json=body)


    def _invite_user(self, account_user_id, service_id, user_email, roles):
        headers = {"Authorization": "Bearer " + self.id_token}
        body = {
            "accountUserId": account_user_id,
            "inviteUsersData": {
                "userCreateRequestDtoList": [
                    {
                        "emailId": user_email,
                        "redirectUrl": self._getAbsoluteEndpoint(f"/{self.account_name}/portal_/loginwithguid")
                    }
                ],
                "tenantRoleListMap": {
                    str(service_id): roles
                },
                "accountAdmin": False
            }
        }
        r = requests.post(self._getAbsoluteEndpoint(
            f"/{self.account_name}/portal_/api/users/inviteUsers"), headers=headers, json=body)

    def _get_user_id_tenant(self, user_email):
        r = self.get(f"/odata/Users/?$filter=EmailAddress eq '{user_email}'")
        return r.json()["value"][0]["Id"]
    
    def _add_user_to_folder(self, user_id, folder_id):
        print('Adding user to folder')
        body = {
            "assignments": {
                "UserIds": [user_id],
                "RolesPerFolder": [
                    {
                        "FolderId": int(folder_id)
                    }
                ]
            }
        }
        r = self.post(
            "/odata/Folders/UiPath.Server.Configuration.OData.AssignUsers", body)

    def _remove_user_from_folder(self, user_id, folder_id):
        print('Removing user from folder')
        body = {
            "userId": user_id
        }
        r = self.post(
            f"/odata/Folders({folder_id})/UiPath.Server.Configuration.OData.RemoveUserFromFolder", body)

    def _get_folder_id(self, folder_name):
        r = self.get(f"/odata/Folders?$filter=DisplayName eq '{folder_name}'")
        print(r.json())
        return r.json()['value'][0]['Id']

    def _adjust_user_folders(self, user_email):
        user_id = self._get_user_id_tenant(user_email)
        self._add_user_to_folder(user_id, self.organization_unit_id)
        default_folder_id = self._get_folder_id("Default")
        self._remove_user_from_folder(user_id, default_folder_id)

    def invite_user(self, user_email, roles):
        print('Inviting user to service: ' + user_email)
        account_user_id = self._get_my_account_user_id()
        service_id = self._get_my_service_id(account_user_id)
        user_id = self._get_user_id_account(account_user_id, user_email)
        if user_id is not None:
            self._add_user_to_service(service_id, user_id, roles)
        else:
            self._invite_user(account_user_id, service_id, user_email, roles)
        time.sleep(3)
        self._adjust_user_folders(user_email)
    
            
    def create_folder(self):
        return self._create_folder(self.folder_name)

    def create_and_connect_robot(self, password):
        print("Creating robot")
        body = {"Name": self.robot_name,
                "MachineName": self.machine_name,
                "Username": self.full_username,
                "Password": password,
                "Type": "Unattended",
                "ExecutionSettings": {
                    "LoginToConsole": False,
                    "ResolutionWidth": "1920", 
                    "ResolutionHeight": "1080"
                }
            }
        r = self.post("/odata/Robots", body)
        r = r.json()
        print(r)
        print("Connecting robot")
        license_key = r["LicenseKey"]
        os.system(
            f"\"C:\\Program Files (x86)\\UiPath\\Studio\\UiRobot.exe\" --connect -url {self.orch_url} -key {license_key}")
        return (r["Id"], r["UserId"])

    def patch_robot_development(self, robotId):
        print("Changing robot into Development type")
        body = {"Type": "Development"}
        r = self.patch(f"/odata/Robots({robotId})",body)

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
        # print(body) removed due to security concerns
        r = self.post("/odata/Assets", body=body)
        # print(r.json()) removed due to security concerns
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
        r = self.post("/odata/Jobs/UiPath.Server.Configuration.OData.StartJobs", body)
        r = r.json()
        print(r)
        return r["value"][0]["Id"]


    def wait_for_processes(self, process_id_set):
        print("Waiting for processes")

        any_job_running = True
        set_copy = process_id_set.copy() # use buffering as sets cannot be changed while being iterated over
        while any_job_running:
            any_job_running = False
            any_process_removed = False
            for pid in set_copy:
                if self.is_job_still_running(pid):
                    any_job_running = True
                else:
                    process_id_set.remove(pid)
                    any_process_removed = True
            
            if any_job_running: 
                print("Still have jobs running. Sleeping")
                time.sleep(30)

                # update copy for next poll
                if any_process_removed:
                    set_copy = process_id_set.copy()


    def get_job(self, job_id):
        r = self.get(f"/odata/Jobs({job_id})")
        r = r.json()
        return r

    def is_job_still_running(self, job_id):
        return self.get_job(job_id)["State"] not in ("Successful", "Stopped", "Faulted")


def setup_dsf_folder(orchHelper, password, ms_account_user, ms_account_pw, process_list, autoarm_list, asset_list, roles):
    folder_id = orchHelper.create_folder()

    (robot_id, user_id) = orchHelper.create_and_connect_robot(password)
    environment_id = orchHelper.create_environment("Demo")
    orchHelper.add_robot_to_environment(robot_id, environment_id)
    role_id = orchHelper.get_role_id("DSF_Robot")
    orchHelper.assign_user_role(user_id, role_id)

    orchHelper.invite_user(ms_account_user, roles)
    
    release_keys = []
    autoarm_release_keys = []

    for process_cfg in process_list:
        process_name = process_cfg["Name"]
        process_args = process_cfg["Args"]
        version = process_cfg["Version"] if "Version" in process_cfg else orchHelper.get_latest_process_version_by_package_name(
            process_name)
        release_key = orchHelper.publish_release(process_name, version)
        if process_cfg["Autostart"] == True:
            release_keys.append((release_key, process_args))
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

    # unique username
    orchHelper.create_asset({
        "Name": "DSF_UniqueUser",
        "ValueScope": "Global",
        "ValueType": "Text",
        "StringValue": orchHelper.sap_user_name
    })

    # orchestrator URL
    orchHelper.create_asset({
        "Name": "DSF_OrchURL",
        "ValueScope": "Global",
        "ValueType": "Text",
        "StringValue": orchHelper.orch_url
    })



    # autostart by default
    process_ids_to_merge = set()
    for (release_key, process_args) in release_keys:
        process_ids_to_merge.add(orchHelper.start_process(release_key, robot_id, process_args))

    # auto-arm based on arguments
    for release_key in autoarm_release_keys:
        process_ids_to_merge.add(orchHelper.start_process(release_key, robot_id, "{'Mode': 'arm'}"))

    orchHelper.wait_for_processes(process_ids_to_merge)
    orchHelper.patch_robot_development(robot_id)


def setup_dsf_folder_dev(orchHelper, password, ms_account_user, ms_account_pw, process_list, autoarm_list, asset_list, roles):
    orchHelper.organization_unit_id = "3060"
    process_ids_to_merge = set()
    #process_ids_to_merge.add(orchHelper.start_process("04a4ad4c-1b4b-4d10-a4ca-e5b9664738dd", 4201, ""))
    #orchHelper.wait_for_processes(process_ids_to_merge)
    orchHelper.patch_robot_development(4201)
