# Pattern 27: starts VM1 on weekday mornings, from the TurnOn-VMs schedule (06:00).
# Plain REST with the Automation account's system identity: its only role is
# pathsol-vm1-ligar-v3 on VM1, and the Az cmdlets need a role on the whole
# subscription (troubleshoot/managed-identity, read 29/10/2026).
$ErrorActionPreference = 'Stop'

$vm1 = '/subscriptions/bd87a1ca-e4f5-460b-9f12-c89e114293f1/resourceGroups/rg-prod-brsouth-001/providers/Microsoft.Compute/virtualMachines/vm-appviewer-prod-001'

$identity = Invoke-RestMethod -Uri "$($env:IDENTITY_ENDPOINT)?resource=https://management.azure.com/" -Headers @{ 'X-IDENTITY-HEADER' = $env:IDENTITY_HEADER; 'Metadata' = 'True' }

# ARM answers 202 while VM1 starts and 200 if it is already running; any
# other answer throws, so the job fails instead of reporting success.
$response = Invoke-WebRequest -Method Post -Uri "https://management.azure.com$vm1/start?api-version=2024-07-01" -Headers @{ Authorization = "Bearer $($identity.access_token)" } -Body '{}' -ContentType 'application/json'
Write-Output "PowerShell $($PSVersionTable.PSVersion); VM1 start: HTTP $($response.StatusCode)"
