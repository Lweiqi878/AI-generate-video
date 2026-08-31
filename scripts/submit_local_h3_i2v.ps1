[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$FirstFrame,

    [Parameter(Mandatory = $true)]
    [string]$LastFrame,

    [Parameter(Mandatory = $true)]
    [string]$PromptFile,

    [Parameter(Mandatory = $true)]
    [string]$OutputFile,

    [Parameter(Mandatory = $true)]
    [string]$ResultJson,

    [ValidateRange(4.0, 15.0)]
    [double]$Seconds = 5.0,

    [ValidateSet('draft', 'balanced', 'high')]
    [string]$Quality = 'balanced',

    [ValidateSet('turbo', 'standard')]
    [string]$Speed = 'standard',

    [ValidateRange(1, 40)]
    [int]$Steps = 20,

    [int]$Seed = 2026090101,

    [string]$BaseUri = 'http://127.0.0.1:8180'
)

$ErrorActionPreference = 'Stop'
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

function ConvertTo-PortablePath {
    param([string]$Path)
    $relative = [IO.Path]::GetRelativePath($repositoryRoot, $Path)
    if ($relative -notmatch '^\.\.([\\/]|$)') {
        return ($relative -replace '\\', '/')
    }
    return $Path
}

function Resolve-InputFile {
    param([string]$Path, [string]$Label)
    $resolved = Resolve-Path -LiteralPath $Path -ErrorAction Stop
    if (-not (Test-Path -LiteralPath $resolved.Path -PathType Leaf)) {
        throw "$Label does not exist: $Path"
    }
    return $resolved.Path
}

function Upload-StudioAsset {
    param([string]$Path)
    $response = & curl.exe -sS -X POST -F "file=@$Path" "$BaseUri/api/assets" 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Studio upload failed for $Path`: $response"
    }
    $parsed = $response | ConvertFrom-Json
    if (-not $parsed.ok -or -not $parsed.asset.id) {
        throw "Studio rejected $Path`: $response"
    }
    return $parsed.asset
}

function Post-StudioJson {
    param([string]$Uri, [hashtable]$Payload)
    return Invoke-RestMethod -Uri $Uri -Method Post -ContentType 'application/json; charset=utf-8' `
        -Body ($Payload | ConvertTo-Json -Depth 12 -Compress)
}

$firstPath = Resolve-InputFile -Path $FirstFrame -Label 'First frame'
$lastPath = Resolve-InputFile -Path $LastFrame -Label 'Last frame'
$promptPath = Resolve-InputFile -Path $PromptFile -Label 'Prompt file'
$prompt = Get-Content -LiteralPath $promptPath -Raw -Encoding utf8
if (-not $prompt.Trim()) { throw "Prompt file is empty: $promptPath" }

$outputFullPath = [IO.Path]::GetFullPath($OutputFile)
$resultFullPath = [IO.Path]::GetFullPath($ResultJson)
if (Test-Path -LiteralPath $outputFullPath) { throw "Output already exists: $outputFullPath" }
if (Test-Path -LiteralPath $resultFullPath) { throw "Result JSON already exists: $resultFullPath" }
New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($outputFullPath)) -Force | Out-Null
New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($resultFullPath)) -Force | Out-Null

$status = Invoke-RestMethod -Uri "$BaseUri/api/status"
if (-not $status.ok) { throw "MiniMax H3 Studio is not ready at $BaseUri" }

Write-Host 'Uploading exact first and last frames to the local Studio...'
$firstAsset = Upload-StudioAsset -Path $firstPath
$lastAsset = Upload-StudioAsset -Path $lastPath

$effectiveSteps = if ($Speed -eq 'standard') { $Steps } else { $null }
$riskPayload = [ordered]@{
    mode = 'i2v'
    aspect_ratio = '9:16'
    quality = $Quality
    seconds = $Seconds
    speed = $Speed
    model_pack = 'stock'
    creative_lora = $null
    creative_lora_strength = $null
    steps = $effectiveSteps
    scheduler = 'simple'
    ref_image_size = 'match'
    custom_width = $null
    custom_height = $null
    prompt_length = $prompt.Length
    reference_count = 2
    reference_video_count = 0
    reference_sizes = @(
        @([int]$firstAsset.width, [int]$firstAsset.height),
        @([int]$lastAsset.width, [int]$lastAsset.height)
    )
}
$riskResponse = Post-StudioJson -Uri "$BaseUri/api/risk" -Payload $riskPayload
$risk = $riskResponse.risk
if ($risk.blocked) {
    throw "Local risk guard blocked the job: $($risk.blocked_reasons -join '; ')"
}

$jobPayload = [ordered]@{
    mode = 'i2v'
    prompt = $prompt
    assets = [ordered]@{
        first_frame = $firstAsset.id
        last_frame = $lastAsset.id
    }
    aspect_ratio = '9:16'
    quality = $Quality
    seconds = $Seconds
    speed = $Speed
    model_pack = 'stock'
    creative_lora = $null
    creative_lora_strength = $null
    steps = $effectiveSteps
    scheduler = 'simple'
    denoise = 1.0
    ref_image_size = 'match'
    custom_width = $null
    custom_height = $null
    seed = $Seed
    rights_confirmed = $true
    risk_acknowledged = [bool]$risk.confirmation_required
    risk_fingerprint = $risk.fingerprint
}

$submitted = Post-StudioJson -Uri "$BaseUri/api/jobs" -Payload $jobPayload
$jobId = $submitted.job.id
if (-not $jobId) { throw 'Studio did not return a job id.' }
Write-Host "Submitted local H3 job $jobId (risk $($risk.level), score $($risk.score))."

$lastProgress = -1
while ($true) {
    Start-Sleep -Seconds 5
    $snapshot = Invoke-RestMethod -Uri "$BaseUri/api/jobs/$jobId"
    $job = $snapshot.job
    if ([int]$job.progress -ne $lastProgress) {
        Write-Host ("[{0}%] {1}" -f $job.progress, $job.stage)
        $lastProgress = [int]$job.progress
    }
    if ($job.status -in @('completed', 'failed', 'cancelled')) { break }
}

if ($job.status -ne 'completed' -or -not $job.outputs -or $job.outputs.Count -lt 1) {
    throw "Local H3 job $jobId ended as $($job.status): $($job.error)"
}

Invoke-WebRequest -Uri "$BaseUri/api/jobs/$jobId/media/0" -OutFile $outputFullPath
$record = [ordered]@{
    studio_job_id = $jobId
    submitted_at = $submitted.job.created_at
    completed_at = $job.updated_at
    first_frame = ConvertTo-PortablePath -Path $firstPath
    last_frame = ConvertTo-PortablePath -Path $lastPath
    first_frame_asset_id = $firstAsset.id
    last_frame_asset_id = $lastAsset.id
    prompt_file = ConvertTo-PortablePath -Path $promptPath
    output_file = ConvertTo-PortablePath -Path $outputFullPath
    resolved = $job.resolved
    risk_assessment = $job.risk_assessment
    studio_output = $job.outputs[0]
}
[IO.File]::WriteAllText(
    $resultFullPath,
    ($record | ConvertTo-Json -Depth 16),
    [Text.UTF8Encoding]::new($false)
)

Write-Host "Completed $jobId -> $outputFullPath" -ForegroundColor Green
Write-Output $jobId
