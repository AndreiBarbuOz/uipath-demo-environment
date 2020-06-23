
param(
    [Parameter(Mandatory = $true)][string]$refreshToken,
    [Parameter(Mandatory = $true)][string]$cloudAccount,
    [Parameter(Mandatory = $true)][string]$cloudServiceInstance,
    [Parameter(Mandatory = $true)][string]$cloudServiceInstanceLogicalName,
    [Int32]$lastJobOlderThanDays = 7,
    [string]$UiPathCloudAddress = "https://staging.uipath.com",
    [string]$UiPathAuthURL = "https://id-preprod.uipath.com",
    [string]$UiPathCloudClientID = "rbF7fh7X36eE3GzSAKO2DTYsjkhi3HFn"
)



$accessToken = (.\GetAuthToken.ps1 $refreshToken -UiPathAuthURL $UiPathAuthURL -UiPathCloudClientID $UiPathCloudClientID).access_token

$headers = (.\GetDefaultHeaders.ps1 -accessToken $accessToken -cloudServiceInstanceLogicalName $cloudServiceInstanceLogicalName)
$endpoint = (.\GetRequestBaseURL.ps1 $UiPathCloudAddress $cloudAccount $cloudServiceInstance) + 'odata/Folders?$filter' + "=startswith(DisplayName, 'DSF_')"
$folders = (.\GetEntities.ps1 $endpoint $headers)

$folderNames = @()
if ($folders.'@odata.count' -gt 0) {
    
    $endpoint = (.\GetRequestBaseURL.ps1 $UiPathCloudAddress $cloudAccount $cloudServiceInstance) + 'odata/Jobs?$filter' + "=StartTime gt " + (Get-Date).AddDays(-1 * $lastJobOlderThanDays).ToUniversalTime().ToString("o")
    $folders.value | ForEach-Object {
        $id = $_.Id
        $displayName = $_.DisplayName
        $headers = (.\GetDefaultHeaders.ps1 -accessToken $accessToken -cloudServiceInstanceLogicalName $cloudServiceInstanceLogicalName -folderID $id)
        try {
            $jobs = .\GetEntities.ps1 $endpoint $headers
            if ($jobs.'@odata.count' -eq 0) {
                $folderNames = $folderNames + $displayName
            }
        } catch {
            Write-Host "$displayName($id): " + $_
        }
    }
}

return $folderNames
