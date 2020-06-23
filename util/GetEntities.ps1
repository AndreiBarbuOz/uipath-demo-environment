
param(
    [Parameter(Mandatory = $true)][string]$endpoint,
    [Parameter(Mandatory = $true)][System.Collections.IDictionary]$headers
)

$Response = Invoke-WebRequest -Uri "$($endpoint)" -Method GET -Headers $headers -UseBasicParsing
$jsonResponse = $Response.Content | ConvertFrom-Json 
return $jsonResponse