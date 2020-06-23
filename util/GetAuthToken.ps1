
param(
    [Parameter(Mandatory = $true)][string]$refreshToken,
    [string]$UiPathAuthURL = "https://id-preprod.uipath.com",
    [string]$UiPathCloudClientID = "rbF7fh7X36eE3GzSAKO2DTYsjkhi3HFn"
)

function getAccessTokens {
    $requestBody = @{grant_type = 'refresh_token'; refresh_token = $refreshToken; client_id = $UiPathCloudClientID } | ConvertTo-Json
    $Response = Invoke-WebRequest -Uri "$($UiPathAuthURL)/oauth/token" -Method POST -body $requestBody -ContentType "application/json" -UseBasicParsing
    $jsonResponse = $Response.Content | ConvertFrom-Json 

    return $jsonResponse
}

return getAccessTokens $refreshToken