param([string]$Version)

if ([string]::IsNullOrWhiteSpace($Version)) {
    throw "Version vide."
}

$rawParts = $Version.Split('.')
if ($rawParts.Count -lt 1 -or $rawParts.Count -gt 4) {
    throw "Format de version invalide: '$Version' (attendu: 1 a 4 segments numeriques)."
}

foreach ($part in $rawParts) {
    if ($part -notmatch '^\d+$') {
        throw "Format de version invalide: '$Version' (segments numeriques uniquement)."
    }
}

$winParts = @($rawParts)
while ($winParts.Count -lt 4) {
    $winParts += '0'
}
$winVersion = ($winParts -join '.')

$file = "installer.nsi"
$content = Get-Content $file -Raw -Encoding UTF8
$content = $content -replace '!define APP_VERSION "[^"]+"', "!define APP_VERSION `"$Version`""

if ($content -match '!define APP_VERSION_WIN "[^"]+"') {
    $content = $content -replace '!define APP_VERSION_WIN "[^"]+"', "!define APP_VERSION_WIN `"$winVersion`""
} else {
    $content = $content -replace '(!define APP_VERSION "[^"]+")', "`$1`r`n!define APP_VERSION_WIN `"$winVersion`""
}

Set-Content $file $content -NoNewline -Encoding UTF8
