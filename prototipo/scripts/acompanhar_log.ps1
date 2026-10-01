# Acompanha o log de proveniência (Camada 8) em tempo real, mostrando um
# resumo legível de cada interação registrada por main.py.
#
# O log grava o horário em UTC; aqui ele é exibido no fuso local.
#
# Uso (de dentro de prototipo/, em PowerShell ou cmd):
#     powershell -ExecutionPolicy Bypass -File scripts\acompanhar_log.ps1
# Ctrl+C para encerrar.

$log = Join-Path $PSScriptRoot "..\logs\interacoes.jsonl"
if (-not (Test-Path $log)) { New-Item -ItemType File -Path $log -Force | Out-Null }

Write-Host "Aguardando interações em logs\interacoes.jsonl (Ctrl+C para sair)...`n"

Get-Content $log -Encoding UTF8 -Wait -Tail 0 | ForEach-Object {
    $e = $_ | ConvertFrom-Json
    $p = $e.parametros_llm
    $v = $e.validacao
    $hora = ([DateTimeOffset]::Parse($e.timestamp)).ToLocalTime().ToString('HH:mm:ss')
    "{0}  [{1}] -> {2}" -f $hora, $e.tipo_classificacao, $e.desfecho
    "  pergunta: $($e.pergunta)"
    "  fontes:   $(($e.fontes_normativas | ForEach-Object titulo) -join '; ')"
    "  ausentes: $($v.normas_declaradas_ausentes -join ', ')   aviso: $($v.possui_aviso)"
    "  modelo:   $($p.modelo) $($p.id_modelo)  temp $($p.temperatura_classificacao)/$($p.temperatura_sintese)  seed $($p.seed)"
    ""
}
