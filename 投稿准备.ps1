[CmdletBinding()]
param(
    [string]$ReleaseId,
    [ValidateSet('抖音', '小红书', '哔哩哔哩')]
    [string]$Platform,
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

$variantNames = @()
if ($release.platform_posts) {
    $variantNames = @($release.platform_posts.PSObject.Properties.Name)
}
if (-not $Platform) {
    if ($variantNames.Count -gt 0) {
        Write-Host "`n选择投稿平台：" -ForegroundColor Cyan
        for ($index = 0; $index -lt $variantNames.Count; $index++) {
            Write-Host ("[{0}] {1}" -f ($index + 1), $variantNames[$index])
        }
        $platformSelection = Read-Host '输入编号'
        if ($platformSelection -notmatch '^\d+$' -or [int]$platformSelection -lt 1 -or [int]$platformSelection -gt $variantNames.Count) {
            throw '无效平台编号。'
        }
        $Platform = $variantNames[[int]$platformSelection - 1]
    }
    else {
        $Platform = $release.platform
    }
}
elseif ($variantNames.Count -gt 0 -and $Platform -notin $variantNames) {
    throw "作品 $($release.id) 没有 $Platform 投稿版本。"
}

$post = $release.posting
if ($variantNames.Count -gt 0) {
    $post = $release.platform_posts.PSObject.Properties[$Platform].Value
}
$tags = @($post.tags | ForEach-Object { "#$_" }) -join ' '
$clipboardText = @"
【标题】
$($post.title)

【正文】
$($post.description)

【标签】
$tags

【AI标识】
AI生成 / AI辅助制作
"@

$folder = Join-Path $root "publishing\ready\$($release.folder)"
$video = Join-Path $folder "$($release.file_title).mp4"
Set-Clipboard -Value $clipboardText
Start-Process explorer.exe -ArgumentList "/select,`"$video`""
if ($OpenUploadPage) {
    $uploadUrl = $release.upload_url
    if ($release.upload_urls -and $release.upload_urls.PSObject.Properties.Name -contains $Platform) {
        $uploadUrl = $release.upload_urls.PSObject.Properties[$Platform].Value
    }
    Start-Process $uploadUrl
}

Write-Host "`n已复制 $Platform 投稿文案并定位成片：" -ForegroundColor Green
Write-Host $post.title
Write-Host "活动处理：$($release.posting.campaign_note)" -ForegroundColor Yellow
