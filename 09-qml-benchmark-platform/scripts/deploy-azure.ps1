[CmdletBinding()]
param(
    [switch]$Apply,
    [string]$Location = "centralus",
    [string]$ResourceGroupName = "rg-p9-qml-benchmark-demo",
    [string]$EnvironmentName = "p9qml-env",
    [string]$ExistingEnvironmentResourceId = "",
    [string]$SharedEnvironmentResourceGroupName = "rg-p7-rl-simulation-demo",
    [string]$SharedEnvironmentName = "p7rl-env",
    [switch]$AllowCreateEnvironment,
    [string]$AppName = "p9qml-platform",
    [string]$RegistryServer = "ghcr.io",
    [string]$RegistryNamespace = "path-software-engineer",
    [string]$ImageTag = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Assert-Command([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "$Name is required."
    }
}

function Invoke-Native([string]$Label, [scriptblock]$Command) {
    Write-Host "  -> $Label"
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed."
    }
}

function Get-SourceDigest {
    $Entries = git ls-files --cached --others --exclude-standard -- .
    if ($LASTEXITCODE -ne 0 -or -not $Entries) {
        throw "The project source inventory could not be resolved."
    }
    $Lines = foreach ($Relative in ($Entries | Sort-Object)) {
        $Target = Join-Path $Root $Relative
        if (Test-Path -LiteralPath $Target -PathType Leaf) {
            "$($Relative.Replace('\', '/'))`:$((Get-FileHash -LiteralPath $Target -Algorithm SHA256).Hash)"
        }
    }
    $Bytes = [Text.Encoding]::UTF8.GetBytes(($Lines -join "`n"))
    $Hasher = [Security.Cryptography.SHA256]::Create()
    try {
        return ([BitConverter]::ToString($Hasher.ComputeHash($Bytes))).Replace("-", "").ToLower()
    }
    finally {
        $Hasher.Dispose()
    }
}

function Write-DeploymentParameters(
    [string]$Path,
    [string]$Username,
    [string]$Password
) {
    @{
        '$schema' = "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#"
        contentVersion = "1.0.0.0"
        parameters = @{
            location = @{ value = $Location }
            resourceGroupName = @{ value = $ResourceGroupName }
            environmentName = @{ value = $EnvironmentName }
            existingEnvironmentResourceId = @{ value = $ExistingEnvironmentResourceId }
            appName = @{ value = $AppName }
            gatewayImage = @{ value = $GatewayImage }
            apiImage = @{ value = $ApiImage }
            dashboardImage = @{ value = $DashboardImage }
            registryServer = @{ value = $RegistryServer }
            registryUsername = @{ value = $Username }
            registryPassword = @{ value = $Password }
        }
    } | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $Path -Encoding UTF8
}

Assert-Command "az"
Assert-Command "git"

$SourceDigest = Get-SourceDigest
$GitCommit = git rev-parse HEAD
if ($LASTEXITCODE -ne 0 -or -not $GitCommit) {
    throw "Git commit identity could not be resolved."
}
if (-not $ImageTag) {
    $ImageTag = "s3-$($GitCommit.Substring(0, 12))"
}
$GatewayImage = "$RegistryServer/$RegistryNamespace/qml-benchmark-gateway:$ImageTag"
$ApiImage = "$RegistryServer/$RegistryNamespace/qml-benchmark-api:$ImageTag"
$DashboardImage = "$RegistryServer/$RegistryNamespace/qml-benchmark-dashboard:$ImageTag"
$Template = Join-Path $Root "infra\azure\main.bicep"

Write-Host "Azure release target: $ResourceGroupName / $Location"
Write-Host "Source digest: $SourceDigest"
Write-Host "Git commit: $GitCommit"
Write-Host "Gateway image: $GatewayImage"
Write-Host "API image: $ApiImage"
Write-Host "Dashboard image: $DashboardImage"
Write-Host "Cost boundary: Consumption min=0 max=1; shared environment; no ACR, Log Analytics, Azure Files or managed database"
Write-Warning "Cloud-created reports use replica memory and reset after scale-to-zero or replacement."

Invoke-Native "Azure account check" { az account show --output none }
Invoke-Native "Bicep compilation" { az bicep build --file $Template --stdout | Out-Null }

if (-not $ExistingEnvironmentResourceId) {
    $SubscriptionId = az account show --query id --output tsv
    if ($LASTEXITCODE -ne 0 -or -not $SubscriptionId) {
        throw "Azure subscription identity could not be resolved."
    }
    $InventoryJson = az rest `
        --method get `
        --url (
            "https://management.azure.com/subscriptions/$SubscriptionId" +
            "/providers/Microsoft.App/managedEnvironments?api-version=2025-07-01"
        ) `
        --output json
    if ($LASTEXITCODE -ne 0 -or -not $InventoryJson) {
        throw "Container Apps environment inventory failed."
    }
    $Inventory = ($InventoryJson | ConvertFrom-Json).value
    $LocationKey = ($Location -replace "[^a-zA-Z0-9]", "").ToLowerInvariant()
    $Regional = @($Inventory) | Where-Object {
        ($_.location -replace "[^a-zA-Z0-9]", "").ToLowerInvariant() -eq $LocationKey
    }
    if ($Regional.Count -eq 1) {
        $ExistingEnvironmentResourceId = $Regional[0].id
    }
    elseif ($Regional.Count -gt 1) {
        $Names = $Regional | ForEach-Object { $_.id.Split("/")[-1] }
        throw (
            "Multiple Container Apps environments exist in ${Location}: " +
            "$($Names -join ', '). Select one with -ExistingEnvironmentResourceId."
        )
    }
    else {
        $SharedPath = (
            "/subscriptions/$SubscriptionId/resourceGroups/" +
            "$SharedEnvironmentResourceGroupName/providers/Microsoft.App/managedEnvironments/" +
            $SharedEnvironmentName
        )
        $SharedJson = az rest `
            --method get `
            --url "https://management.azure.com${SharedPath}?api-version=2025-07-01" `
            --output json 2>$null
        if ($LASTEXITCODE -eq 0 -and $SharedJson) {
            $Shared = $SharedJson | ConvertFrom-Json
            $SharedLocationKey = `
                ($Shared.location -replace "[^a-zA-Z0-9]", "").ToLowerInvariant()
            if ($SharedLocationKey -eq $LocationKey) {
                $ExistingEnvironmentResourceId = $Shared.id
            }
        }
    }
}

if ($ExistingEnvironmentResourceId) {
    Write-Host "Container Apps environment: reuse $($ExistingEnvironmentResourceId.Split('/')[-1])"
}
elseif ($AllowCreateEnvironment) {
    Write-Host "Container Apps environment: create $EnvironmentName"
}
else {
    throw (
        "No reusable Container Apps environment was resolved. " +
        "Pass -ExistingEnvironmentResourceId or explicitly allow creation with " +
        "-AllowCreateEnvironment."
    )
}

$PreflightParameters = New-TemporaryFile
try {
    $PreflightUsername = if ($env:GHCR_USERNAME) { $env:GHCR_USERNAME } else { "preflight-user" }
    $PreflightPassword = if ($env:GHCR_TOKEN) { $env:GHCR_TOKEN } else { "preflight-token" }
    Write-DeploymentParameters $PreflightParameters $PreflightUsername $PreflightPassword
    Invoke-Native "Azure deployment validation before image publication" {
        az deployment sub validate `
            --name "p9qml-s3-validate" `
            --location $Location `
            --template-file $Template `
            --parameters "@$PreflightParameters" `
            --output none
    }
    Invoke-Native "Azure deployment what-if before image publication" {
        az deployment sub what-if `
            --name "p9qml-s3-what-if" `
            --location $Location `
            --template-file $Template `
            --parameters "@$PreflightParameters" `
            --result-format ResourceIdOnly
    }
}
finally {
    Remove-Item -LiteralPath $PreflightParameters -Force -ErrorAction SilentlyContinue
}

if (-not $Apply) {
    Write-Host "OK - Azure release preflight passed without publishing images or creating resources"
    Write-Host "After the Sprint 3 gate, commit and tag v1.0.0-qml-benchmark-platform, then rerun with -Apply."
    exit 0
}

Assert-Command "docker"
$Dirty = git status --porcelain -- .
if ($LASTEXITCODE -ne 0 -or $Dirty) {
    throw "-Apply requires a clean Project 09 Git worktree. Commit the verified Sprint 3 release first."
}
$ReleaseTag = git describe --exact-match --tags HEAD 2>$null
if ($LASTEXITCODE -ne 0 -or $ReleaseTag -ne "v1.0.0-qml-benchmark-platform") {
    throw "-Apply requires HEAD to carry tag v1.0.0-qml-benchmark-platform."
}
$RegistryUsername = $env:GHCR_USERNAME
$RegistryPassword = $env:GHCR_TOKEN
if (-not $RegistryUsername -or -not $RegistryPassword) {
    throw "GHCR_USERNAME and GHCR_TOKEN must be set in this PowerShell process. Do not paste them into chat."
}

Write-Host "Running the strict Sprint 3 quality gate before publication"
& .\scripts\run-quality-gate.ps1
if ($LASTEXITCODE -ne 0) {
    throw "Sprint 3 quality gate failed; no images were published."
}

Invoke-Native "Microsoft.App provider registration" {
    az provider register --namespace Microsoft.App --wait --output none
}

$DockerConfigDirectory = Join-Path `
    ([IO.Path]::GetTempPath()) `
    "p9qml-docker-$([guid]::NewGuid().ToString('N'))"
$PreviousDockerConfig = $env:DOCKER_CONFIG
New-Item -ItemType Directory -Path $DockerConfigDirectory | Out-Null
try {
    $env:DOCKER_CONFIG = $DockerConfigDirectory
    Invoke-Native "Temporary GHCR login" {
        $RegistryPassword |
            docker login $RegistryServer --username $RegistryUsername --password-stdin
    }
    Invoke-Native "Gateway image build" {
        docker build --file deployment/gateway.Dockerfile --tag $GatewayImage .
    }
    Invoke-Native "API image build" {
        docker build --file deployment/api.Dockerfile --tag $ApiImage .
    }
    Invoke-Native "Dashboard image build" {
        docker build --file deployment/dashboard.Dockerfile --tag $DashboardImage .
    }
    Invoke-Native "Gateway image publication" { docker push $GatewayImage }
    Invoke-Native "API image publication" { docker push $ApiImage }
    Invoke-Native "Dashboard image publication" { docker push $DashboardImage }
    $GatewayDigest = docker image inspect $GatewayImage --format '{{join .RepoDigests ","}}'
    $ApiDigest = docker image inspect $ApiImage --format '{{join .RepoDigests ","}}'
    $DashboardDigest = docker image inspect $DashboardImage --format '{{join .RepoDigests ","}}'
}
finally {
    $env:DOCKER_CONFIG = $PreviousDockerConfig
    Remove-Item -LiteralPath $DockerConfigDirectory -Recurse -Force -ErrorAction SilentlyContinue
}

$Parameters = New-TemporaryFile
try {
    Write-DeploymentParameters $Parameters $RegistryUsername $RegistryPassword
    Invoke-Native "Azure scale-to-zero deployment" {
        az deployment sub create `
            --name "p9qml-s3" `
            --location $Location `
            --template-file $Template `
            --parameters "@$Parameters" `
            --output none
    }
}
finally {
    Remove-Item -LiteralPath $Parameters -Force -ErrorAction SilentlyContinue
}

$AppUrl = az deployment sub show `
    --name "p9qml-s3" `
    --query "properties.outputs.appUrl.value" `
    --output tsv
$AppResourceId = az deployment sub show `
    --name "p9qml-s3" `
    --query "properties.outputs.appResourceId.value" `
    --output tsv
if ($LASTEXITCODE -ne 0 -or -not $AppUrl -or -not $AppResourceId) {
    throw "The deployed Container App identity could not be resolved."
}

$Ready = $false
for ($Attempt = 1; $Attempt -le 36; $Attempt++) {
    try {
        $Response = Invoke-RestMethod -Uri "$AppUrl/health/ready" -TimeoutSec 10
        if ($Response.status -eq "ready") {
            $Ready = $true
            break
        }
    }
    catch {
        Write-Host "Cold-start acceptance: attempt $Attempt/36"
    }
    Start-Sleep -Seconds 5
}
if (-not $Ready) {
    throw "Azure did not expose a ready API within 180 seconds."
}

$Web = Invoke-WebRequest -Uri $AppUrl -UseBasicParsing -TimeoutSec 30
$Layout = Invoke-WebRequest -Uri "$AppUrl/_dash-layout" -UseBasicParsing -TimeoutSec 30
$Swagger = Invoke-WebRequest -Uri "$AppUrl/docs" -UseBasicParsing -TimeoutSec 30
$OpenApi = Invoke-RestMethod -Uri "$AppUrl/openapi.json" -TimeoutSec 30
$Capabilities = Invoke-RestMethod -Uri "$AppUrl/api/v1/capabilities" -TimeoutSec 30
$Datasets = Invoke-RestMethod -Uri "$AppUrl/api/v1/datasets" -TimeoutSec 30
$NoiseBody = @{
    snapshot_id = $Datasets[0].snapshot_id
    seeds = @(3501)
    shots = 64
    noise_strength = 0.08
    readout_error = 0.04
    max_depth = 1
} | ConvertTo-Json
$Noise = Invoke-RestMethod `
    -Method Post `
    -Uri "$AppUrl/api/v1/noise/reports" `
    -ContentType "application/json" `
    -Body $NoiseBody `
    -TimeoutSec 120
$Persisted = Invoke-RestMethod `
    -Uri "$AppUrl/api/v1/noise/reports/$($Noise.report_id)" `
    -TimeoutSec 30
$Csv = Invoke-WebRequest `
    -Uri "$AppUrl/api/v1/noise/reports/$($Noise.report_id)/report.csv" `
    -UseBasicParsing `
    -TimeoutSec 30
$Runtime = az rest `
    --method get `
    --url "https://management.azure.com${AppResourceId}?api-version=2024-03-01" `
    --output json | ConvertFrom-Json

if (
    $Web.StatusCode -ne 200 -or
    $Swagger.StatusCode -ne 200 -or
    $Layout.Content -notmatch "Quantum Noise Limitations Board" -or
    -not $OpenApi.paths."/api/v1/noise/reports" -or
    $Capabilities.release -ne "sprint-3" -or
    $Noise.runs.Count -ne 4 -or
    $Persisted.comparison_id -ne $Noise.comparison_id -or
    $Csv.Content -notmatch "run_id,mode,seed,shots" -or
    $Runtime.properties.template.scale.minReplicas -ne 0 -or
    $Runtime.properties.template.scale.maxReplicas -ne 1
) {
    throw "Azure cross-layer release acceptance failed."
}

Write-Host "OK - Project 09 deployed to Azure Container Apps Consumption"
Write-Host "Web:     $AppUrl"
Write-Host "API:     $AppUrl/api/v1"
Write-Host "Swagger: $AppUrl/docs"
Write-Host "OpenAPI: $AppUrl/openapi.json"
Write-Host "Revision: $($Runtime.properties.latestReadyRevisionName)"
Write-Host "Gateway digest: $GatewayDigest"
Write-Host "API digest: $ApiDigest"
Write-Host "Dashboard digest: $DashboardDigest"
Write-Host "Persistence: replica memory; resets after scale-to-zero or replacement."
Write-Host "Cost: zero fixed-cost design under Consumption grants; Azure usage is not an absolute zero-bill guarantee."
