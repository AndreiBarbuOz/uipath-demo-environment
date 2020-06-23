param(
    [Parameter(Mandatory = $true)][string]$accessToken,
    [Parameter(Mandatory = $true)][string]$cloudServiceInstanceLogicalName,
    [string]$folderID
)

$requestHeaders = @{Authorization = "Bearer $($accessToken)" } 
$requestHeaders["X-UIPATH-TenantName"] = $cloudServiceInstanceLogicalName
if ($folderID) {
    $requestHeaders["X-UIPATH-OrganizationUnitId"] = "$($folderID)"
}
return $requestHeaders
