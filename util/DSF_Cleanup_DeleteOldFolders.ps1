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
$folders = .\GetFoldersOlderThan.ps1 -refreshToken $refreshToken -cloudAccount $cloudAccount -cloudServiceInstance $cloudServiceInstance -cloudServiceInstanceLogicalName $cloudServiceInstanceLogicalName -lastJobOlderThanDays $lastJobOlderThanDays -UiPathCloudAddress $UiPathCloudAddress -UiPathAuthURL $UiPathAuthURL -UiPathCloudClientID $UiPathCloudClientID


if ($folders.Count -gt 0) {
    $folders | % { Write-Host $_ }
    $answer = Read-Host "Really delete all of these $($folders.Count) folders? (y/n)"

    if ($answer.StartsWith("y")) {
        .\DeleteFolder.ps1 -folderName $_.DisplayName -refreshToken $refreshToken -cloudAccount $cloudAccount -cloudServiceInstance $cloudServiceInstance -cloudServiceInstanceLogicalName $cloudServiceInstanceLogicalName -UiPathCloudAddress $UiPathCloudAddress -UiPathAuthURL $UiPathAuthURL -UiPathCloudClientID $UiPathCloudClientID
    } else {
        Write-Host "aborted"
    }

} else {
    Write-Host "Squeaky clean. Nothing to delete."
}
