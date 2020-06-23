param(
    [Parameter(Mandatory = $true)][string]$UiPathCloudAddress,
    [Parameter(Mandatory = $true)][string]$cloudAccount,
    [Parameter(Mandatory = $true)][string]$cloudServiceInstance
)


return "$($UiPathCloudAddress)/$($cloudAccount)/$($cloudServiceInstance)/"
