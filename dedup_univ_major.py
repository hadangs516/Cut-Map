# -*- coding: utf-8 -*-
"""univ_major_full.json의 완전 중복행(모든 필드 값이 동일한 행) 제거.

원본은 그대로 두고 univ_major_dedup.json으로 새로 저장한다.
완전 중복은 첫 번째 것만 남긴다. schlNm+scsbjtNm 조합만 겹치고
나머지 필드가 다른 행은 별개 행으로 보고 그대로 둔다.
"""
import io
import json
import os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "univ_major_full.json")
OUT = os.path.join(HERE, "univ_major_dedup.json")


def row_key(item):
    return json.dumps(item, sort_keys=True, ensure_ascii=False)


def main():
    with io.open(SRC, encoding="utf-8") as f:
        data = json.load(f)

    items = data["items"]
    before = len(items)

    seen = set()
    kept = []
    for it in items:
        k = row_key(it)
        if k in seen:
            continue
        seen.add(k)
        kept.append(it)

    after = len(kept)
    removed = before - after

    combo_counts = Counter((it.get("schlNm", ""), it.get("scsbjtNm", "")) for it in kept)
    remaining_multi = {k: v for k, v in combo_counts.items() if v > 1}

    out = dict(data)
    out["items"] = kept
    out["dedup"] = {
        "beforeRows": before,
        "afterRows": after,
        "removedRows": removed,
        "remainingMultiComboCount": len(remaining_multi),
    }

    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

    lines = []
    lines.append("제거 전 행 수: %d" % before)
    lines.append("제거 후 행 수: %d" % after)
    lines.append("제거된 행 수: %d" % removed)
    lines.append("완전 중복은 아니지만 schlNm+scsbjtNm 조합이 2회 이상 남은 조합 수: %d" % len(remaining_multi))
    with io.open(os.path.join(HERE, "dedup_report.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
