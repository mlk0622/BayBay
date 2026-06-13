param(
    [string]$Version,
    [string]$SetupFile
)

# Calculer le SHA512 du fichier
$hash = Get-FileHash -Path $SetupFile -Algorithm SHA512
$sha512 = $hash.Hash.ToLower()

# Taille du fichier
$fileSize = (Get-Item $SetupFile).Length

# Nom du fichier
$fileName = [System.IO.Path]::GetFileName($SetupFile)

# Date actuelle au format ISO
$releaseDate = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")

# Contenu du fichier latest.yml
$yamlContent = @"
version: $Version
files:
  - url: $fileName
    sha512: $sha512
    size: $fileSize
path: $fileName
sha512: $sha512
releaseDate: $releaseDate
"@

# Écrire le fichier
$yamlContent | Out-File -FilePath "latest.yml" -Encoding utf8 -NoNewline

Write-Host "latest.yml genere avec succes"
Write-Host "  Version: $Version"
Write-Host "  Fichier: $fileName"
Write-Host "  Taille: $fileSize bytes"
Write-Host "  SHA512: $($sha512.Substring(0, 32))..."
