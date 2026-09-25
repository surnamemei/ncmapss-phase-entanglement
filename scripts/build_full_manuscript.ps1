param(
    [string]$RepositoryRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
$paper = Join-Path $RepositoryRoot 'paper'

function Read-Section([string]$name) {
    $path = Join-Path $paper $name
    if (-not (Test-Path -LiteralPath $path)) { throw "Missing section: $path" }
    return [IO.File]::ReadAllText($path, [Text.Encoding]::UTF8).Trim()
}

function Replace-Once([string]$text, [string]$old, [string]$new) {
    $count = ([regex]::Matches($text, [regex]::Escape($old))).Count
    if ($count -ne 1) { throw "Expected one occurrence, found $count`: $old" }
    return $text.Replace($old, $new)
}

$abstract = Read-Section 'abstract.md'
$abstract = Replace-Once $abstract 'healthy row false-positive rates (FPRs)' 'healthy row-level false-positive rates (FPRs)'
$abstract = Replace-Once $abstract 'the independent DS03 confirmatory subset' 'the DS03 independent confirmatory subset'
$abstract = Replace-Once $abstract 'The tested static, derivative-based, and finite-history corrections did not eliminate DS02 phase dependence.' 'In exploratory DS02 PCA sensitivity analysis, the tested static, derivative-based, and finite-history correction schemes did not eliminate the observed dependence.'
$abstract = Replace-Once $abstract 'the pre-specified pooled directional pattern reproduced.' 'the pre-specified pooled directional pattern was reproduced.'
$abstract = Replace-Once $abstract 'Pooled healthy calibration can therefore conceal flight-phase-dependent false-alarm behaviour; phase-stability auditing should accompany aggregate anomaly-detection evaluation under nonstationary operating conditions.' 'These results motivate explicit phase-stability auditing alongside aggregate anomaly-detection evaluation under nonstationary operating conditions.'
$abstract += ' <!-- evidence: M0018, E000107, E000108, E000109, E002627, E002628, E002629, E002987, E002988, E002989, E021498, E021511, E021524, E010947, E010948, E010949, E012858, E012859, E012860, E013131, E013132, E013133, E010950, E010951, E012861, E012862, E013134, E013135, E012043, E012316, E012589 -->'

$introduction = Read-Section 'introduction.md'
$introduction = Replace-Once $introduction 'healthy false-positive rates (FPRs).' 'healthy false-positive rates (FPRs), interpreted here as healthy false-alarm rates.'
$introduction = Replace-Once $introduction 'The question here is narrower than improving a detector: whether a nominal pooled healthy-alarm calibration remains stable across normal flight phases under full-flight operation.' 'The question here is narrower than improving a detector: whether nominal pooled healthy FPR calibration remains stable across normal flight phases under full-flight operation.'
$introduction = Replace-Once $introduction 'DS02 supplied exploratory discovery' 'The DS02 discovery dataset supplied exploratory development'
$introduction = Replace-Once $introduction 'the independent DS03 confirmatory subset' 'the DS03 independent confirmatory subset'
$introduction = Replace-Once $introduction 'Healthy-state labels restrict retrospective healthy evaluation and are not detector inputs; the study consequently makes no claim about fault sensitivity or real-aircraft deployment.' 'Oracle health-state labels select healthy rows for model fitting, threshold calibration, and retrospective FPR evaluation; they are never numerical detector inputs. The study consequently makes no claim about fault sensitivity or real-aircraft deployment.'
$introduction = Replace-Once $introduction 'A falsification-oriented robustness analysis showing that the observed DS02 dependence is not eliminated by the tested static, derivative-based, or finite-history correction schemes and is observed across three tested detector implementations.' 'An exploratory PCA correction challenge in which the tested static, derivative-based, and finite-history schemes did not eliminate the observed DS02 dependence; separately, the pattern was observed across three tested detector implementations under the common history correction.'
$introduction = Replace-Once $introduction 'do healthy anomaly scores and false-alarm rates vary systematically across flight phases?' 'do healthy anomaly scores and healthy row-level FPRs vary systematically across flight phases?'

$related = Read-Section 'related_work.md'
$related = Replace-Once $related 'Reconstruction and one-class approaches have long supplied anomaly scores for monitoring; PCA and autoencoders are discussed explicitly in prior N-CMAPSS anomaly-detection work [7](https://doi.org/10.36001/IJPHM.2024.v15i1.3589). Ulmer *et al.* used N-CMAPSS DS02 in a study of training-data contamination and unsupervised refinement, emphasizing anomaly-detection performance rather than phase-conditional healthy calibration [7](https://doi.org/10.36001/IJPHM.2024.v15i1.3589).' 'Reconstruction and one-class approaches have long supplied anomaly scores for monitoring. Ulmer *et al.* used N-CMAPSS DS02 to study training-data contamination and unsupervised refinement with residual-based models, emphasizing anomaly-detection performance rather than phase-conditional healthy calibration [7](https://doi.org/10.36001/IJPHM.2024.v15i1.3589).'
$related = Replace-Once $related 'More recent N-CMAPSS work compares LSTM autoencoders, transformer autoencoders, and a physics-guided spatiotemporal graph model primarily through detection metrics such as ROC-AUC, PR-AUC, and F1 [9](https://doi.org/10.3390/math14183413).' 'More recent N-CMAPSS work evaluates a physics-guided spatiotemporal graph model primarily through detection metrics such as ROC-AUC and F1 [9](https://doi.org/10.3390/math14183413).'
$related = Replace-Once $related 'the stability of a nominal healthy false-alarm calibration' 'the stability of nominal pooled healthy FPR calibration'

$methods = Read-Section 'methods.md'
$methods = Replace-Once $methods '# Methods' '## III. Methodology'
$methods = Replace-Once $methods 'The analysis used the N-CMAPSS DS02 subset for exploratory development and the separate DS03 subset for a frozen external confirmation.' 'The analysis used the N-CMAPSS DS02 discovery dataset for exploratory development and the DS03 independent confirmatory subset for frozen confirmation.'
for ($i = 1; $i -le 6; $i++) {
    $letter = [char](64 + $i)
    $methods = [regex]::Replace($methods, "(?m)^## $i\. ", "### $letter. ")
}
$methods = Replace-Once $methods 'The LSTM detector was a causal sequence-reconstruction network.' 'The LSTM detector was a causal LSTM sequence-reconstruction network.'
$methods = Replace-Once $methods 'nominal row-level false-positive-rate targets' 'nominal pooled healthy row-level FPR targets'
$methods = Replace-Once $methods 'Overall and phase-specific false-positive rates were calculated' 'Overall and phase-specific healthy row-level FPRs were calculated'

$results = Read-Section 'results.md'
$results = Replace-Once $results 'At the primary 1% pooled-calibration target' 'At the primary nominal 1% pooled calibration target'
$results = Replace-Once $results 'The descent elevation was observed across three tested detector implementations under this shared preprocessing and calibration protocol.' 'The descent elevation was observed across three tested detector implementations under a shared preprocessing and calibration protocol.'
$results = Replace-Once $results 'DS02 served as the discovery dataset.' 'DS02 served as the exploratory discovery dataset.'
$results = Replace-Once $results 'DS02 overall healthy row-FPRs' 'DS02 overall healthy row-level FPRs'
$results = Replace-Once $results 'worst off-diagonal healthy row-FPR after phase-specific calibration' 'worst off-diagonal healthy row-level FPR after phase-specific calibration'

$discussion = Read-Section 'discussion.md'
$discussion = Replace-Once $discussion 'on the independent DS03 confirmatory subset' 'on the DS03 independent confirmatory subset'
$discussion = Replace-Once $discussion 'Health-state labels are oracle annotations used to restrict retrospective healthy FPR evaluation and are never detector inputs.' 'Oracle health-state labels select healthy rows for fitting, calibration, and retrospective FPR evaluation; they are never numerical detector inputs.'
$discussion = Replace-Once $discussion 'Thus, the tested specifications were insufficient to make the resulting healthy scores phase-stable at the evaluated pooled threshold.' 'Thus, the tested specifications were insufficient to make healthy row-level FPR phase-stable at the evaluated pooled threshold.'
$discussion = Replace-Once $discussion 'cross-context threshold transfer' 'cross-phase threshold transfer'

$conclusion = Read-Section 'conclusion.md'
$conclusion = Replace-Once $conclusion 'a nominal healthy false-alarm calibration' 'nominal pooled healthy FPR calibration'
$conclusion = Replace-Once $conclusion 'the causal LSTM sequence-reconstruction implementation' 'the causal LSTM sequence-reconstruction network'
$conclusion = Replace-Once $conclusion 'The tested static, derivative-based, and finite-history operating-condition corrections did not eliminate the DS02 dependence.' 'In the exploratory DS02 PCA comparison, the tested static, derivative-based, and finite-history operating-condition correction schemes did not eliminate the observed dependence.'
$conclusion = Replace-Once $conclusion 'the pre-specified pooled directional pattern reproduced on an independent confirmatory subset.' 'the pre-specified pooled directional pattern was reproduced on the independent confirmatory subset.'
$conclusion = Replace-Once $conclusion 'Future work should test the same calibration-audit question on real or independently sourced full-flight data and examine whether context-aware calibration can reduce phase dependence without degrading fault sensitivity.' 'Future work should test the calibration-audit question on real or independently sourced full-flight data and evaluate whether context-aware calibration can reduce phase dependence without compromising fault sensitivity.'

$register = Read-Section 'literature_positioning.md'
$references = [regex]::Matches($register, '(?m)^- (\[\d+\] .+)$') | ForEach-Object { $_.Groups[1].Value }
if ($references.Count -ne 12) { throw "Expected 12 registered references; found $($references.Count)" }

if ($introduction -notmatch '^# Auditing Flight-Phase') { throw 'Working title missing' }
$title = ($introduction -split "`n", 2)[0].TrimEnd("`r")
$introduction = $introduction.Substring($title.Length).Trim()
$internal = (@($title, $abstract, $introduction, $related, $methods, $results, $discussion, $conclusion, "## References`n`n$($references -join "`n")") -join "`n`n") + "`n"
$internal = [regex]::Replace($internal, '\[((?:[EM]\d{4,6})(?:,\s*[EM]\d{4,6})*)\]', '<!-- evidence: $1 -->')
$clean = [regex]::Replace($internal, '[ \t]*<!-- evidence:[^\r\n]*?-->', '')

$utf8 = [Text.UTF8Encoding]::new($false)
[IO.File]::WriteAllText((Join-Path $paper 'manuscript_full_internal.md'), $internal, $utf8)
[IO.File]::WriteAllText((Join-Path $paper 'manuscript_full.md'), $clean, $utf8)
Write-Output "Built manuscript_full_internal.md and manuscript_full.md from authoritative section files."
