$ErrorActionPreference = 'Stop'
$gaiaProject = Split-Path -Parent $PSScriptRoot

function Read-PrivateValue([string]$Name) {
    do {
        $gaiaSecure = Read-Host "$Name - pega la clave y pulsa Enter (entrada oculta)" -AsSecureString
        $gaiaPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($gaiaSecure)
        try { $gaiaValue = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($gaiaPointer).Trim() }
        finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($gaiaPointer) }
    } while ([string]::IsNullOrWhiteSpace($gaiaValue) -or $gaiaValue.Contains("`n") -or $gaiaValue.Contains("`r"))
    return $gaiaValue
}

function Save-PrivateValues([string]$Path, [System.Collections.IDictionary]$Values) {
    # Preserve unrelated settings locally. Never output existing settings or credentials.
    $gaiaLines = @()
    if (Test-Path -LiteralPath $Path) { $gaiaLines = [IO.File]::ReadAllLines($Path) }
    foreach ($gaiaKey in $Values.Keys) {
        $gaiaPattern = '^\s*(?:export\s+)?' + [regex]::Escape($gaiaKey) + '\s*='
        $gaiaLines = @($gaiaLines | Where-Object { $_ -notmatch $gaiaPattern })
        $gaiaLines += $gaiaKey + '=' + $Values[$gaiaKey]
    }
    [IO.File]::WriteAllLines($Path, [string[]]$gaiaLines, [Text.UTF8Encoding]::new($false))
}

try {
    Write-Host 'GAIA - Configuracion local de credenciales' -ForegroundColor Cyan
    Write-Host 'Pega cada clave en esta ventana. Los caracteres permanecen ocultos.'
    Write-Host ''
    $gaiaEarthdata = Read-PrivateValue '1/3 EARTHDATA_TOKEN'
    $gaiaFirms = Read-PrivateValue '2/3 FIRMS_MAP_KEY'
    $gaiaCesium = Read-PrivateValue '3/3 VITE_CESIUM_ION_TOKEN'
    Save-PrivateValues (Join-Path $gaiaProject '.env') ([ordered]@{ EARTHDATA_TOKEN = $gaiaEarthdata; FIRMS_MAP_KEY = $gaiaFirms })
    Save-PrivateValues (Join-Path $gaiaProject 'apps/web/.env') ([ordered]@{ VITE_CESIUM_ION_TOKEN = $gaiaCesium })
    $gaiaEarthdata = $null; $gaiaFirms = $null; $gaiaCesium = $null
    Write-Host ''
    Write-Host 'Credenciales guardadas. Vuelve a Codex y escribe GUARDADO.' -ForegroundColor Green
} catch {
    Write-Host 'No se pudo completar el guardado. Revisa que los archivos permitan escritura.' -ForegroundColor Red
}
