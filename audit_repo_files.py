# -*- coding: utf-8 -*-
"""작업 20-4·5 (점검만): 프로젝트 폴더 전체 파일 목록과 키·토큰·비밀번호·개인정보 검사.
키 값은 출력하지 않고 파일명과 줄 번호만 기록한다. 결과는 audit_repo_files.json (git_upload_plan.md 작성용).
"""
import io
import json
import os
import re
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
TEXT_EXT = {".md", ".json", ".py", ".js", ".html", ".css", ".txt", ".csv", ".env", ".gitignore", ".yml", ".yaml", ""}
RAW_EXT = {".xlsx", ".xls", ".pdf", ".hwp", ".hwpx", ".zip", ".docx", ".doc"}
MB = 1024 * 1024

PATTERNS = {
    "키·토큰 대입문": re.compile(r"(?i)\b(api[_-]?key|service[_-]?key|servicekey|vworld_key|secret|token|passw(or)?d|pwd)\b\s*[:=]\s*['\"]?[A-Za-z0-9%+/_\-]{8,}"),
    "URL 쿼리의 key=": re.compile(r"(?i)[?&](key|servicekey|apikey|token)=[A-Za-z0-9%+/_\-]{8,}"),
    "GitHub 토큰": re.compile(r"\bgh[opsu]_[A-Za-z0-9]{20,}"),
    "이메일": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "휴대전화 번호": re.compile(r"(?<!\d)01[016789]-?\d{3,4}-?\d{4}(?!\d)"),
    "주민등록번호 형식": re.compile(r"(?<!\d)\d{6}-[1-4]\d{6}(?!\d)"),
}


def load_env_values():
    vals = {}
    p = os.path.join(HERE, ".env")
    if os.path.exists(p):
        for ln in io.open(p, encoding="utf-8"):
            if "=" in ln and not ln.strip().startswith("#"):
                k, v = ln.strip().split("=", 1)
                if len(v.strip()) >= 8:
                    vals[k.strip()] = v.strip().strip("'\"")
    return vals


def scan_text(path, env_vals, rel):
    hits = []
    try:
        with io.open(path, encoding="utf-8", errors="replace") as f:
            for no, ln in enumerate(f, 1):
                for k, v in env_vals.items():
                    if v in ln:
                        hits.append({"file": rel, "line": no, "kind": ".env 실제 값(%s)" % k})
                for kind, pat in PATTERNS.items():
                    for m in pat.finditer(ln):
                        hits.append({"file": rel, "line": no, "kind": kind,
                                     "sample": m.group(0)[:3] + "…" if kind != "이메일" else m.group(0).split("@")[-1]})
    except Exception as e:
        hits.append({"file": rel, "line": 0, "kind": "읽기 실패 %r" % e})
    return hits


def scan_xlsx(path, rel):
    hits = []
    try:
        z = zipfile.ZipFile(path)
        for n in z.namelist():
            if n.endswith("sharedStrings.xml") or n.startswith("xl/worksheets/"):
                s = z.read(n).decode("utf-8", "replace")
                for kind in ("이메일", "휴대전화 번호", "주민등록번호 형식"):
                    c = len(PATTERNS[kind].findall(s))
                    if c:
                        hits.append({"file": rel, "line": "(%s 내부 %d건)" % (n, c), "kind": kind})
    except Exception as e:
        hits.append({"file": rel, "line": 0, "kind": "읽기 실패 %r" % e})
    return hits


def main():
    env_vals = load_env_values()
    files, hits = [], []
    for root, dirs, fs in os.walk(HERE):
        dirs[:] = [d for d in dirs if d != ".git"]
        for fn in fs:
            p = os.path.join(root, fn)
            rel = os.path.relpath(p, HERE).replace("\\", "/")
            size = os.path.getsize(p)
            ext = os.path.splitext(fn)[1].lower() if not fn.startswith(".") else os.path.splitext(fn)[1].lower() or fn.lower()
            top = rel.split("/")[0] if "/" in rel else ""
            files.append({"path": rel, "size": size, "ext": ext, "top": top})
            if fn == ".env" or ext in TEXT_EXT or ext == ".env":
                hits += scan_text(p, env_vals, rel)
            elif ext in (".xlsx",):
                hits += scan_xlsx(p, rel)
    out = {"envKeys": sorted(env_vals), "files": sorted(files, key=lambda x: x["path"]), "hits": hits}
    with io.open(os.path.join(HERE, "audit_repo_files.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    big = [f for f in files if f["size"] > 100 * MB]
    print("files", len(files), "total MB %.1f" % (sum(f["size"] for f in files) / MB), "over100MB", [f["path"] for f in big])
    from collections import Counter
    print(Counter((h["file"].split("/")[0] if "/" in h["file"] else h["file"], h["kind"]) for h in hits).most_common(60))


if __name__ == "__main__":
    main()
