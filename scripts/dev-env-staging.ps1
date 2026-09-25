# Carga en esta terminal las variables del Supabase staging para correr la app contra él.
# Uso (con .env.staging en la raíz, fuera de git):   . .\scripts\dev-env-staging.ps1
# No escribe nada en disco: las claves salen de .env.staging una sola vez.

$path = "$(Split-Path $PSScriptRoot)\\.env.staging"
if (-not (Test-Path $path)) {
    Write-Error ".env.staging no existe. Copialo a mano desde la otra PC (está en .gitignore)."
    return
}

Get-Content $path | ForEach-Object {
    if ($_ -match '^\s*([A-Z_]+)\s*=\s*(.+)$') {
        [Environment]::SetEnvironmentVariable($matches[1], $matches[2].Trim())
    }
}

Write-Host "Supabase staging: $env:SUPABASE_URL  ·  Resend: onboarding@resend.dev"
