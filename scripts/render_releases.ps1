[CmdletBinding()]
param(
    [string]$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path,
    [string[]]$ReleaseId
)

$ErrorActionPreference = 'Stop'
$ffmpeg = (Get-Command ffmpeg -ErrorAction Stop).Source
$python = (Get-Command python -ErrorAction Stop).Source
$configPath = Join-Path $RepositoryRoot 'data\releases.json'
$config = Get-Content -LiteralPath $configPath -Raw -Encoding utf8 | ConvertFrom-Json
$releases = @($config.releases)
if ($ReleaseId.Count -gt 0) {
    $releases = @($releases | Where-Object { $_.id -in $ReleaseId })
    $missing = @($ReleaseId | Where-Object { $_ -notin $releases.id })
    if ($missing.Count -gt 0) { throw "Unknown release id(s): $($missing -join ', ')" }
}

Push-Location $RepositoryRoot
try {
    foreach ($release in $releases) {
        $releaseDirectory = Join-Path $RepositoryRoot "publishing\ready\$($release.folder)"
        $provenance = Join-Path $releaseDirectory 'provenance'
        $production = Join-Path $RepositoryRoot "production\$($release.folder)"
        $editDirectory = Join-Path $production 'edit'
        New-Item -ItemType Directory -Path $releaseDirectory, $provenance, $editDirectory -Force | Out-Null

        $segments = @($release.source_segments | ForEach-Object { Join-Path $RepositoryRoot $_ })
        $missingSegments = @($segments | Where-Object { -not (Test-Path -LiteralPath $_ -PathType Leaf) })
        if ($missingSegments.Count -gt 0) {
            throw "$($release.id) missing source segment(s): $($missingSegments -join ', ')"
        }

        if ($segments.Count -eq 1) {
            $input = $segments[0]
        }
        else {
            $input = Join-Path $editDirectory 'story_master.mp4'
            & $python '.\scripts\concat_segments.py' @segments --output $input --width 1080 --height 1920 --crf 18 --audio
            if ($LASTEXITCODE -ne 0) { throw "Segment concat failed for $($release.id)" }
        }

        $output = Join-Path $releaseDirectory "$($release.file_title).mp4"
        $cover = Join-Path $releaseDirectory "$($release.file_title)_封面.jpg"
        $captionRelative = "publishing/ready/$($release.folder)/provenance/captions.ass"
        $captionPath = Join-Path $RepositoryRoot ($captionRelative -replace '/', '\')
        if (-not (Test-Path -LiteralPath $captionPath -PathType Leaf)) {
            throw "Missing captions: $captionPath"
        }

        $videoFilter = "setpts=PTS-STARTPTS,scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920,setsar=1,eq=contrast=1.035:saturation=1.06:brightness=0.004,unsharp=5:5:0.32:3:3:0,subtitles='$captionRelative',format=yuv420p"
        $analysisText = (& $ffmpeg -hide_banner -nostats -i $input -map 0:a:0 `
            -af 'loudnorm=I=-16:LRA=11:TP=-2.5:print_format=json' -f null NUL 2>&1 | Out-String)
        $jsonMatch = [regex]::Match($analysisText, '(?s)\{\s*"input_i".*?\}')
        if (-not $jsonMatch.Success) { throw "Could not parse loudness analysis for $($release.id)" }
        $loudness = $jsonMatch.Value | ConvertFrom-Json
        $audioFilter = "aresample=48000:async=1:first_pts=0,loudnorm=I=-16:LRA=11:TP=-2.5:measured_I=$($loudness.input_i):measured_LRA=$($loudness.input_lra):measured_TP=$($loudness.input_tp):measured_thresh=$($loudness.input_thresh):offset=$($loudness.target_offset):linear=true:print_format=summary,alimiter=limit=0.82:attack=5:release=50:level=0"

        & $ffmpeg -hide_banner -loglevel warning -y -fflags +genpts -i $input `
            -map 0:v:0 -map 0:a:0 -vf $videoFilter -af $audioFilter `
            -c:v libx264 -preset slow -crf 18 -profile:v high -level 4.1 `
            -c:a aac -b:a 192k -ar 48000 -ac 2 -avoid_negative_ts make_zero -movflags +faststart `
            -metadata "title=$($release.display_title)" `
            -metadata 'comment=AI-generated / AI-assisted; MiniMax H3 local generation; deterministic FFmpeg finishing' `
            $output
        if ($LASTEXITCODE -ne 0) { throw "FFmpeg render failed for $($release.id)" }

        & $ffmpeg -hide_banner -loglevel warning -y -ss $release.cover_time -i $output -frames:v 1 -update 1 -q:v 2 $cover
        if ($LASTEXITCODE -ne 0) { throw "Cover extraction failed for $($release.id)" }
        Write-Host "Rendered $($release.id): $output" -ForegroundColor Green
    }
}
finally {
    Pop-Location
}
