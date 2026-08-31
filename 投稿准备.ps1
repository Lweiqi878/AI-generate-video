[CmdletBinding()]
param(
    [string]$ReleaseId,
    [switch]$OpenUploadPage,
    [switch]$ValidateOnly
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path $PSScriptRoot).Path
$config = Get-Content -LiteralPath (Join-Path $root 'data\releases.json') -Raw -Encoding utf8 | ConvertFrom-Json
$releases = @($config.releases)

if (-not $ReleaseId) {
    Write-Host "`n可投稿作品：" -ForegroundColor Cyan
    for ($index = 0; $index -lt $releases.Count; $index++) {
        $release = $releases[$index]
        $guard = if ($release.campaign_tag_allowed) { '可关联活动' } else { '暂不关联活动话题' }
        Write-Host ("[{0}] {1}｜{2}｜{3}" -f ($index + 1), $release.game, $release.display_title, $guard)
    }
    $selection = Read-Host '输入编号'
    if ($selection -notmatch '^\d+$' -or [int]$selection -lt 1 -or [int]$selection -gt $releases.Count) {
        throw '无效编号。'
    }
    $release = $releases[[int]$selection - 1]
}
else {
    $release = $releases | Where-Object id -eq $ReleaseId | Select-Object -First 1
    if (-not $release) { throw "未找到作品：$ReleaseId" }
}

& (Get-Command python -ErrorAction Stop).Source (Join-Path $root 'scripts\validate_releases.py')
if ($LASTEXITCODE -ne 0) { throw '发布校验未通过，已停止投稿准备。' }
if ($ValidateOnly) {
    Write-Host "发布校验通过：$($release.display_title)" -ForegroundColor Green
    return
}

$folder = Join-Path $root "publishing\ready\$($release.folder)"
$video = Join-Path $folder "$($release.file_title).mp4"
$card = Join-Path $folder "$($release.file_title)_投稿卡.txt"
Set-Clipboard -Value (Get-Content -LiteralPath $card -Raw -Encoding utf8)
Start-Process explorer.exe -ArgumentList "/select,`"$video`""
if ($OpenUploadPage) { Start-Process $release.upload_url }

Write-Host "`n已复制投稿卡并定位成片：" -ForegroundColor Green
Write-Host $release.posting.title
Write-Host "活动处理：$($release.posting.campaign_note)" -ForegroundColor Yellow
