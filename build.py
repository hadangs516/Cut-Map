# -*- coding: utf-8 -*-
# template.html + 데이터·자산 조각 -> it-major-map.html
#
# 조각:
#   data.json (data.py가 생성), leaflet.min.css, geo_prov.json, geo_seoul.json
#   grades/style.css, grades/view.html, grades/*.js (파일명 번호 순서대로 이어 붙임)
#   courses_master.json, app_meta.json
#
# app_meta의 buildDate(마지막 업데이트일)와 dataAsOf(데이터 기준일)는 여기서 채운다.
import datetime
import glob
import json
import os
import subprocess

subprocess.run(["python", "data.py"], check=True)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def read_json(path):
    return json.loads(read(path))


def compact(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def concat_js(pattern):
    parts = []
    for path in sorted(glob.glob(pattern)):
        parts.append("/* ===== " + path.replace(os.sep, "/") + " ===== */\n" + read(path).rstrip("\n"))
    if not parts:
        raise SystemExit("조각 파일을 찾지 못함: " + pattern)
    return "\n\n".join(parts)


meta = read_json("app_meta.json")
meta.pop("note", None)
meta["buildDate"] = datetime.date.today().isoformat()
meta["dataAsOf"] = read_json("data.json").get("asof", "")

html = read("template.html")
html = html.replace("/*__LEAFLET_CSS__*/", read("leaflet.min.css").rstrip("\n"), 1)
html = html.replace("/*__GRADES_CSS__*/", read("grades/style.css").rstrip("\n"), 1)
# 테마 규칙은 기존 다크 규칙보다 뒤에 와야 이긴다. 스타일 블록 맨 끝에 넣는다.
html = html.replace("/*__SKINS_CSS__*/", read("skins.css").rstrip("\n"), 1)
html = html.replace("<!--__GRADES_VIEW__-->", read("grades/view.html").rstrip("\n"), 1)
html = html.replace("/*__GRADES_JS__*/", concat_js("grades/*.js"), 1)
html = html.replace("/*__MAP_JS__*/", read("map/50_basis.js").rstrip("\n"), 1)
html = html.replace("/*__MAP_LIST_JS__*/", read("map/60_list.js").rstrip("\n"), 1)
html = html.replace("/*__SYNONYMS__*/null", compact(read_json("synonyms.json")), 1)
html = html.replace("/*__DATA__*/null", read("data.json"), 1)
html = html.replace("/*__GEO_PROV__*/null", read("geo_prov.json"), 1)
html = html.replace("/*__GEO_SEOUL__*/null", read("geo_seoul.json"), 1)
html = html.replace("/*__COURSES__*/null", compact(read_json("courses_master.json")), 1)
html = html.replace("/*__EXAM_SCHEDULE__*/null", compact(read_json("exam_schedule.json")), 1)
html = html.replace("/*__APP_META__*/null", compact(meta), 1)

left = [m for m in ("__LEAFLET_CSS__", "__GRADES_CSS__", "__SKINS_CSS__", "__GRADES_VIEW__", "__GRADES_JS__",
                    "__MAP_JS__", "__MAP_LIST_JS__", "__SYNONYMS__",
                    "__DATA__", "__GEO_PROV__", "__GEO_SEOUL__", "__COURSES__",
                    "__EXAM_SCHEDULE__", "__APP_META__")
        if m in html]
if left:
    raise SystemExit("치환되지 않은 자리가 있음: " + ", ".join(left))

with open("it-major-map.html", "w", encoding="utf-8") as f:
    f.write(html)

print("built it-major-map.html  v%s  build %s  data %s"
      % (meta["appVersion"], meta["buildDate"], meta["dataAsOf"]))
