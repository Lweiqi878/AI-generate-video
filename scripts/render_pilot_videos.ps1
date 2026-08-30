[CmdletBinding()]
param(
    [string]$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
)

$ErrorActionPreference = 'Stop'
$ffmpeg = (Get-Command ffmpeg -ErrorAction Stop).Source

$works = @(
    @{
        Id = 'V2-191'
        Slug = 'walking-opera'
        Title = '歌剧院下班后开始散步'
    },
    @{
        Id = 'V2-193'
        Slug = 'tape-escape'
        Title = '午夜录像带从货架集体越狱'
    }
)

Push-Location $RepositoryRoot
try {
    foreach ($work in $works) {
        $production = Join-Path $RepositoryRoot "production\$($work.Id)-$($work.Slug)"
        $input = Join-Path $production "raw\$($work.Id)_h3_raw.mp4"
        $deliverable = Join-Path $RepositoryRoot "deliverables\$($work.Id)-$($work.Slug)"
        $output = Join-Path $deliverable "$($work.Id)_final.mp4"
        $cover = Join-Path $deliverable "$($work.Id)_cover.jpg"
        $captionRelative = "deliverables/$($work.Id)-$($work.Slug)/captions.ass"
        if (-not (Test-Path -LiteralPath $input -PathType Leaf)) {
            throw "Missing raw H3 clip: $input"
        }
        New-Item -ItemType Directory -Path $deliverable -Force | Out-Null

        $videoFilter = "scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920,setsar=1,eq=contrast=1.03:saturation=1.05:brightness=0.005,unsharp=5:5:0.35:3:3:0,subtitles='$captionRelative',format=yuv420p"
        $analysisText = (& $ffmpeg -hide_banner -nostats -i $input -map 0:a:0 `
            -af 'loudnorm=I=-16:LRA=11:TP=-2.0:print_format=json' -f null NUL 2>&1 | Out-String)
        $jsonMatch = [regex]::Match($analysisText, '(?s)\{\s*"input_i".*?\}')
        if (-not $jsonMatch.Success) { throw "Could not parse loudness analysis for $($work.Id)" }
        $loudness = $jsonMatch.Value | ConvertFrom-Json
        $audioFilter = "aresample=48000,loudnorm=I=-16:LRA=11:TP=-2.0:measured_I=$($loudness.input_i):measured_LRA=$($loudness.input_lra):measured_TP=$($loudness.input_tp):measured_thresh=$($loudness.input_thresh):offset=$($loudness.target_offset):linear=true:print_format=summary"
        & $ffmpeg -hide_banner -loglevel warning -y -i $input `
            -map 0:v:0 -map 0:a:0 `
            -vf $videoFilter `
            -af $audioFilter `
            -c:v libx264 -preset slow -crf 18 -profile:v high -level 4.1 `
            -c:a aac -b:a 192k -ar 48000 -ac 2 `
            -movflags +faststart `
            -metadata "title=$($work.Title)" `
            -metadata 'comment=AI-generated / AI-assisted; MiniMax H3 local generation; deterministic FFmpeg finishing' `
            $output
        if ($LASTEXITCODE -ne 0) { throw "FFmpeg render failed for $($work.Id)" }

        & $ffmpeg -hide_banner -loglevel warning -y -ss 1.10 -i $output -frames:v 1 -update 1 -q:v 2 $cover
        if ($LASTEXITCODE -ne 0) { throw "Cover extraction failed for $($work.Id)" }
        Write-Host "Rendered $output" -ForegroundColor Green
    }
}
finally {
    Pop-Location
}
