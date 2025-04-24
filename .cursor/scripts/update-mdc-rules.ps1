# Script to update MDC rules from the Elie222/inbox-zero GitHub repository
# Usage: Run this script from the root of your project
# Example: pwsh .cursor/scripts/update-mdc-rules.ps1

# Ensure the opensource directory exists
$mdcDir = ".cursor/rules/opensource"
if (-Not (Test-Path $mdcDir)) {
    Write-Host "Creating directory: $mdcDir"
    New-Item -ItemType Directory -Path $mdcDir -Force | Out-Null
}

# Get the list of MDC files from the repository
Write-Host "Fetching MDC rule files list from GitHub..."
$repoFiles = (Invoke-RestMethod -Uri "https://api.github.com/repos/elie222/inbox-zero/git/trees/main?recursive=1").tree | 
             Where-Object { $_.path -like ".cursor/rules/*.mdc" }

if ($repoFiles.Count -eq 0) {
    Write-Host "No MDC files found in the repository. Check the repository structure or your internet connection."
    exit 1
}

Write-Host "Found $($repoFiles.Count) MDC files. Downloading..."

# Download each file
foreach ($file in $repoFiles) {
    $fileName = Split-Path $file.path -Leaf
    $outputPath = Join-Path $mdcDir $fileName
    $url = "https://raw.githubusercontent.com/elie222/inbox-zero/main/$($file.path)"
    
    Write-Host "Downloading $fileName..."
    try {
        Invoke-RestMethod -Uri $url -OutFile $outputPath
        Write-Host "  ✓ Downloaded: $fileName"
    } catch {
        Write-Host "  ✗ Failed to download $fileName: Error occurred"
    }
}

Write-Host "`nMDC rules update completed."
Write-Host "Files are located in: $mdcDir"
Write-Host "To use these rules, reference them in your code or consult the 700-opensource-mdc.mdc file." 