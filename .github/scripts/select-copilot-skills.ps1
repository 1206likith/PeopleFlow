param(
    [Parameter(Mandatory = $true)]
    [string]$PromptText,
    [string]$ManifestPath = ".github/copilot-skills/_manifest.md",
    [string]$RoutingMapPath = ".github/copilot-skills/skill-routing-map.json",
    [int]$Top = 6
)

$ErrorActionPreference = "Stop"

if ($Top -lt 1) {
    $Top = 1
}

if (-not (Test-Path -LiteralPath $ManifestPath)) {
    throw "Manifest not found at $ManifestPath. Run sync-copilot-skills.ps1 first."
}

if (-not (Test-Path -LiteralPath $RoutingMapPath)) {
    throw "Routing map not found at $RoutingMapPath."
}

$promptLower = $PromptText.ToLowerInvariant()

$manifestLines = Get-Content -LiteralPath $ManifestPath
$manifestSkills = @()
foreach ($line in $manifestLines) {
    if ($line -match "^\|\s*([^|]+?)\s*\|\s*\.github/copilot-skills/.+?\|$") {
        $skillName = $matches[1].Trim()
        if ($skillName -ne "Skill" -and $skillName -ne "---") {
            $manifestSkills += $skillName
        }
    }
}
$manifestSkills = $manifestSkills | Sort-Object -Unique

$routing = Get-Content -LiteralPath $RoutingMapPath -Raw | ConvertFrom-Json

$candidates = @()
foreach ($rule in $routing.routingRules) {
    if ($manifestSkills -notcontains $rule.skill) {
        continue
    }

    $score = 0
    $hits = @()

    foreach ($keyword in $rule.keywords) {
        if ($promptLower.Contains($keyword.ToLowerInvariant())) {
            $score += 1
            $hits += $keyword
        }
    }

    if ($score -gt 0) {
        $candidates += [PSCustomObject]@{
            skill = $rule.skill
            score = $score
            hits = @($hits | Sort-Object -Unique)
        }
    }
}

# Fallback if no keyword matches: include broadly useful workflow/security guardrails.
if ($candidates.Count -eq 0) {
    $fallback = @("context-engineering-kit", "owasp-security") | Where-Object { $manifestSkills -contains $_ }
    foreach ($skill in $fallback) {
        $candidates += [PSCustomObject]@{
            skill = $skill
            score = 1
            hits = @("fallback")
        }
    }
}

$selected = $candidates |
    Sort-Object -Property @{ Expression = "score"; Descending = $true }, @{ Expression = "skill"; Descending = $false } |
    Select-Object -First $Top

$result = [PSCustomObject]@{
    prompt = $PromptText
    selectedSkills = @($selected.skill)
    detail = @($selected)
}

$result | ConvertTo-Json -Depth 6
