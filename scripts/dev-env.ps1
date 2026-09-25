# Carga en esta terminal las variables del Supabase local para correr la app contra él.
# Uso (con `npx supabase start` ya corriendo):   . .\scripts\dev-env.ps1
# No escribe nada en disco: las claves salen de `supabase status` cada vez.

$status = npx --yes supabase@2.117.0 status -o env 2>$null
if ($LASTEXITCODE -ne 0 -or -not $status) {
    Write-Error "Supabase local no está corriendo. Arráncalo con: npx supabase start"
    return
}
$map = @{ "API_URL" = "SUPABASE_URL"; "PUBLISHABLE_KEY" = "SUPABASE_PUBLISHABLE_KEY"; "SECRET_KEY" = "SUPABASE_SECRET_KEY" }
foreach ($line in $status) {
    if ($line -match '^([A-Z_]+)="(.*)"$' -and $map.ContainsKey($Matches[1])) {
        Set-Item -Path "env:$($map[$Matches[1]])" -Value $Matches[2]
    }
}
Write-Host "Supabase local: $env:SUPABASE_URL  ·  correos de prueba en http://127.0.0.1:54324"
