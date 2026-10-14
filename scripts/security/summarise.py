"""Write reports/security/summary.md from the raw tool outputs of run_checks.sh; exit 1 if any check failed.

Secrets are never copied into the summary: gitleaks runs with --redact, and only the rule, file, line
and commit of a finding are listed.
"""
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path


def load(path):
    try:
        return json.loads(path.read_text() or "null")
    except (OSError, json.JSONDecodeError):
        return None


def pip_audit(raw):
    lines = []
    for path in sorted(raw.glob("pip-audit-*.json")):
        data = load(path) or {}
        deps = data.get("dependencies", data if isinstance(data, list) else [])
        for dep in deps:
            for vuln in dep.get("vulns", []):
                fixed = ", ".join(vuln.get("fix_versions") or []) or "no fix yet"
                lines.append(f"| {path.stem.removeprefix('pip-audit-')} | {dep['name']} {dep['version']} | "
                             f"{vuln['id']} | {fixed} |")
    if not lines:
        return ["No known vulnerabilities in any dependency set."]
    return ["| Set | Package | Advisory | Fixed in |", "|---|---|---|---|", *lines]


def bandit(raw):
    data = load(raw / "bandit.json") or {}
    results = data.get("results", [])
    skipped = sum(m.get("skipped_tests", 0) for m in [data.get("metrics", {}).get("_totals", {})])
    lines = [f"{len(results)} findings; {skipped} intended ones are marked in the code with `# nosec` and a reason."]
    if results:
        lines += ["", "| Severity | Check | Where |", "|---|---|---|"]
        lines += [f"| {r['issue_severity']} | {r['test_id']} {r['test_name']} | `{r['filename']}:{r['line_number']}` |"
                  for r in results]
    return lines


def trivy_findings(data):
    for result in (data or {}).get("Results", []) or []:
        target = result.get("Target", "")
        for v in result.get("Vulnerabilities") or []:
            yield "vulnerability", v.get("Severity"), f"{v.get('PkgName')} {v.get('InstalledVersion')}: {v.get('VulnerabilityID')}" \
                + (f" (fixed in {v['FixedVersion']})" if v.get("FixedVersion") else ""), target
        for m in result.get("Misconfigurations") or []:
            yield "misconfiguration", m.get("Severity"), f"{m.get('ID')}: {m.get('Title')}", target
        for s in result.get("Secrets") or []:
            yield "secret", s.get("Severity"), f"{s.get('RuleID')} at line {s.get('StartLine')}", target


def trivy(raw, name):
    data = load(raw / name)
    if data is None:
        return ["Not run."]
    rows = list(trivy_findings(data))
    if not rows:
        return ["Nothing found."]
    return ["| Kind | Severity | Finding | Where |", "|---|---|---|---|",
            *[f"| {k} | {s} | {f} | `{t}` |" for k, s, f, t in rows]]


def licences(raw, image):
    data = load(raw / f"trivy-{image}-licences.json")
    if data is None:
        return ["Not run."]
    groups = {}  # Trivy's groups: "OS Packages", "Python", "Loose File License(s)"
    for result in data.get("Results", []) or []:
        if result.get("Class") in ("license", "license-file"):
            groups.setdefault(result.get("Target"), []).extend(result.get("Licenses") or [])
    lines = ["Severity follows Trivy's licence categories: CRITICAL = forbidden (for example AGPL; fails the build), "
             "HIGH = restricted (GPL, LGPL), MEDIUM = reciprocal (MPL), LOW = notice or permissive.", "",
             "| Group | CRITICAL | HIGH | MEDIUM | LOW | UNKNOWN |", "|---|---|---|---|---|---|"]
    for target, found in groups.items():
        count = Counter(lic.get("Severity") for lic in found)
        lines.append(f"| {target} | " + " | ".join(str(count.get(s, 0)) for s in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN")) + " |")
    python = sorted({(lic.get("Severity"), lic.get("Category") or "unknown", lic.get("Name"), lic.get("PkgName"))
                     for lic in groups.get("Python", []) if lic.get("Severity") != "LOW"}, key=lambda x: (str(x[0]), str(x[3])))
    if python:
        lines += ["", "Python packages that aren't plainly permissive:", "",
                  "| Severity | Category | Licence | Package |", "|---|---|---|---|",
                  *[f"| {sev} | {cat} | {name} | {pkg} |" for sev, cat, name, pkg in python]]
    lines += ["", "OS packages come from the Debian base image (bash, openssl, apt and so on); GPL there is normal "
                  "for a base image and doesn't affect our code. LGPL Python libraries used unmodified, and MPL files "
                  "left unchanged, carry no obligation for a hosted service."]
    return lines


def gitleaks(raw):
    data = load(raw / "gitleaks.json")
    if data is None:
        return ["Not run."]
    if not data:
        return ["No secrets found in the Git history."]
    return [f"{len(data)} possible secrets (values redacted). Rotate any that are real, then remove them from history.", "",
            "| Rule | File | Line | Commit | Date |", "|---|---|---|---|---|",
            *[f"| {f.get('RuleID')} | `{f.get('File')}` | {f.get('StartLine')} | {str(f.get('Commit'))[:10]} | "
              f"{str(f.get('Date'))[:10]} |" for f in data]]


def main(out):
    out = Path(out)
    raw = out / "raw"
    checks = [line.split("|", 1) for line in (raw / "status.txt").read_text().splitlines() if line]
    failed = [name for name, code in checks if code not in ("0", "skipped")]
    images = [i for i in ("mcp-gateway", "document-graph") if (raw / f"trivy-{i}-licences.json").exists()]
    md = [f"# Security checks — {datetime.now().strftime('%Y-%m-%d %H:%M')}", "",
          "Replaced on every run of `scripts/security/run_checks.sh`. Raw tool output is in `raw/`.", "",
          f"**Result: {'FAILED — ' + ', '.join(failed) if failed else 'all checks passed'}**", "",
          "| Check | Result |", "|---|---|",
          *[f"| {name} | {'pass' if code == '0' else 'skipped' if code == 'skipped' else 'FAIL (exit ' + code + ')'} |"
            for name, code in checks],
          "", "## Dependency vulnerabilities (pip-audit)", "", *pip_audit(raw),
          "", "## Python security lint (Bandit)", "", *bandit(raw),
          "", "## Source: secrets and misconfigurations (Trivy)", "", *trivy(raw, "trivy-source.json")]
    for image in images:
        md += ["", f"## Image `{image}`: fixable HIGH/CRITICAL vulnerabilities (Trivy)", "",
               *trivy(raw, f"trivy-{image}-vulnerabilities.json"),
               "", f"## Image `{image}`: licences (Trivy)", "", *licences(raw, image)]
    md += ["", "## Git history: secrets (gitleaks)", "", *gitleaks(raw), ""]
    (out / "summary.md").write_text("\n".join(md))
    print(f"\nReport: {out / 'summary.md'}")
    print("Result:", "FAILED: " + ", ".join(failed) if failed else "all checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
