# cleanup-llm-only.ps1
param(
  [switch]$KeepMcp,
  [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Get-Location)

function Remove-Path {
  param([string]$relativePath)

  $fullPath = Join-Path $repoRoot $relativePath
  if (Test-Path $fullPath) {
    if ($DryRun) {
      Write-Host "[DRY] Remove: $relativePath"
    } else {
      Write-Host "Remove: $relativePath"
      Remove-Item -LiteralPath $fullPath -Recurse -Force
    }
  } else {
    Write-Host "Skip (not found): $relativePath"
  }
}

# LLM-only에서 불필요한 항목들
$pathsToRemove = @(
  "frontend",
  "web_tool",
  "assets",
  "live2d-models",
  "avatars",
  "backgrounds",
  "model_dict.json",
  "src/open_llm_vtuber/asr",
  "src/open_llm_vtuber/tts",
  "src/open_llm_vtuber/vad",
  "src/open_llm_vtuber/conversations",
  "src/open_llm_vtuber/utils/stream_audio.py",
  "src/open_llm_vtuber/live",
  "doc",
  "LOCAL_GUIDE.md",
  "LOCAL_GUIDE_DESKTOP_PET.md",
  "OLLAMA_GUIDE.md"
)

# MCP는 옵션 유지/삭제
if (-not $KeepMcp) {
  $pathsToRemove += @(
    "src/open_llm_vtuber/mcpp",
    "mcp_servers.json",
    "prompts/utils/mcp_prompt.txt"
  )
}

foreach ($p in $pathsToRemove) {
  Remove-Path $p
}

Write-Host "Done."