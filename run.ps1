# Inicia a interface com o ambiente virtual ou o runtime local de validação.
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$pythonCandidates = @('.venv/Scripts/python.exe', '.runtime_python/python.exe', 'python')
foreach ($candidate in $pythonCandidates) {
    if ($candidate -ne 'python' -and -not (Test-Path -LiteralPath $candidate)) { continue }
    try {
        & $candidate -c 'import streamlit, spacy, neo4j, sentence_transformers, networkx' 2>$null
        $ready = $LASTEXITCODE -eq 0
    } catch { $ready = $false }
    if ($ready) {
        & $candidate -m streamlit run app.py --browser.gatherUsageStats false
        exit $LASTEXITCODE
    }
}
throw 'Instale Python 3.12 e as dependências de requirements.txt antes de executar.'
