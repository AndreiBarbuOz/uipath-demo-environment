
param(
    [Parameter(Mandatory = $true)][string]$folderName,
    [Parameter(Mandatory = $true)][string]$refreshToken,
    [Parameter(Mandatory = $true)][string]$cloudAccount,
    [Parameter(Mandatory = $true)][string]$cloudServiceInstance,
    [Parameter(Mandatory = $true)][string]$cloudServiceInstanceLogicalName,
    [string]$UiPathCloudAddress = "https://staging.uipath.com",
    [string]$UiPathAuthURL = "https://id-preprod.uipath.com",
    [string]$UiPathCloudClientID = "rbF7fh7X36eE3GzSAKO2DTYsjkhi3HFn"
)

function getBaseUri {
    return "$($UiPathCloudAddress)/$($cloudAccount)/$($cloudServiceInstance)"
}

function getDefaultHeaders {
    param([bool]$withFolderID = $true)
    $requestHeaders = @{Authorization = "Bearer $($accessToken)" } 
    $requestHeaders["X-UIPATH-TenantName"] = $cloudServiceInstanceLogicalName
    if ($withFolderID -and $folderID) {
        $requestHeaders["X-UIPATH-OrganizationUnitId"] = "$($folderID)"
    }
    return $requestHeaders
}

function getAccessTokens {
    param([parameter(Mandatory)][string]$RefreshToken)
    $requestBody = @{grant_type = 'refresh_token'; refresh_token = $RefreshToken; client_id = $UiPathCloudClientID } | ConvertTo-Json
    $Response = Invoke-WebRequest -Uri "$($UiPathAuthURL)/oauth/token" -Method POST -body $requestBody -ContentType "application/json"
    $jsonResponse = $Response.Content | ConvertFrom-Json 

    return $jsonResponse
}

function getFolderIDByName {
    param(
        [parameter(Mandatory)][string]$folderName
    )  
    $requestHeaders = getDefaultHeaders
    $Response = Invoke-WebRequest -Uri "$(getBaseUri)/odata/Folders?`$filter=DisplayName eq '$($folderName)'" -Method GET -Headers $requestHeaders
    $jsonResponse = $Response.Content | ConvertFrom-Json 
    
    return $jsonResponse.value[0].Id
}


function getEntities {
    param(
        [parameter(Mandatory)][string]$endpoint,
        [bool]$withFolderID = $true
    )  
    $requestHeaders = getDefaultHeaders $withFolderID
    $Response = Invoke-WebRequest -Uri "$(getBaseUri)$($endpoint)" -Method GET -Headers $requestHeaders
    $jsonResponse = $Response.Content | ConvertFrom-Json 
    return $jsonResponse.value
}

function deleteEntity {
    param(
        [parameter(Mandatory)][string]$endpoint,
        [parameter(Mandatory)][string]$entityID,
        [bool]$withFolderID = $true
    ) 
    $requestHeaders = getDefaultHeaders $withFolderID
    Invoke-WebRequest -Uri "$(getBaseUri)$($endpoint)($($entityID))" -Method DELETE -Headers $requestHeaders
}

function deleteAllEntities {
    param(
        [parameter(Mandatory)][string]$endpoint,
        [bool]$withFolderID = $true
    )  

    getEntities $endpoint $withFolderID | ForEach-Object {
        deleteEntity $endpoint $_.Id $withFolderID
    }
}

function deleteAllRobotsAndMachines {
    getEntities "/odata/Robots" | ForEach-Object {
        deleteEntity "/odata/Robots" $_.Id
        deleteEntity "/odata/Machines" $_.MachineId
    }
}

function getUsersForFolder {
    return getEntities "/odata/Folders/UiPath.Server.Configuration.OData.GetUsersForFolder(key=$($folderID), includeInherited=true)"
}

function removeUserFromFolder {
    param(
        [parameter(Mandatory)][Int32]$userID
    ) 
    $requestHeaders = getDefaultHeaders $false
    $requestBody = @{userId = $userID } | ConvertTo-Json
    Invoke-WebRequest -Uri "$(getBaseUri)/odata/Folders($($folderID))/UiPath.Server.Configuration.OData.RemoveUserFromFolder" -Method POST -Headers $requestHeaders -Body $requestBody -ContentType "application/json"
}

function removeAllUsersFromFolder {
    getUsersForFolder | ForEach-Object {
        removeUserFromFolder $_.Id
    }
}



$accessTokens = getAccessTokens $refreshToken
$accessToken = $accessTokens.access_token
$folderID = getFolderIDByName $folderName

deleteAllEntities "/odata/Assets"
deleteAllEntities "/odata/Releases"
deleteAllRobotsAndMachines
deleteAllEntities "/odata/Environments"
deleteAllEntities "/odata/QueueDefinitions"

removeAllUsersFromFolder
deleteEntity "/odata/Folders" $folderID $false

# getEntities "/odata/Folders" | Write-Host
#getUsersForFolder | Write-Host