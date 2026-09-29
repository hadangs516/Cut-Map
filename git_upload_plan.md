# GitHub 업로드 계획 (작업 20, 점검만)

- 작성: 2026-09-29 / make_git_upload_plan.py (audit_repo_files.py 결과 사용)
- git 작업(commit, push, 저장소 설정 변경)은 하지 않았음. 이 문서는 계획 초안
- 폴더 파일 154개, 합계 267.5 MB

## 1. 요약

| 구분 | 파일 수 | 합계 |
|---|---|---|
| 올릴 후보 | 99 | 13.5 MB |
| 판단 필요 | 11 | 114.9 MB |
| 올리지 않을 후보 | 44 | 139.1 MB |

## 2. 올릴 후보

| 경로 | 크기 | 분류 |
|---|---|---|
| .gitignore | 0.0 KB | git 설정 |
| 2027_IT대학_입시조사_초안.md | 134.6 KB | 보고·점검 문서 |
| 2027_경기인천영남_모집요강_URL.md | 44.8 KB | 보고·점검 문서 |
| 2027_정시모집요강_URL_누적.md | 16.1 KB | 현재 기준 조사 md |
| 4yr_list_gyeonggi_incheon_yeongnam.md | 11.9 KB | 현재 기준 조사 md |
| 4yr_list_seoul_chungcheong_gangwon_jeju_honam.md | 13.2 KB | 현재 기준 조사 md |
| CHANGELOG.md | 7.1 KB | 기획·명세 문서 |
| HANDOFF_컷맵_20260924.md | 3.6 KB | 보고·점검 문서 |
| HANDOFF_컷맵_20260924_v2.md | 6.6 KB | 보고·점검 문서 |
| PROGRESS.md | 12.8 KB | 기획·명세 문서 |
| PROJECT_BRIEF.md | 3.9 KB | 기획·명세 문서 |
| RELEASE_CHECKLIST.md | 6.7 KB | 기획·명세 문서 |
| SPEC_대학맵.md | 10.3 KB | 기획·명세 문서 |
| SPEC_성적관리시스템.md | 35.0 KB | 기획·명세 문서 |
| add_new_candidate_univs.py | 12.0 KB | 처리 스크립트 |
| api_csv_coverage_20260924.md | 39.8 KB | 보고·점검 문서 |
| api_csv_dept_diff_20260929.md | 54.4 KB | 보고·점검 문서 |
| app_meta.json | 0.5 KB | 마커·학과·목록 데이터 |
| apply_decisions_v3.py | 27.4 KB | 처리 스크립트 |
| apply_decisions_v4.py | 18.1 KB | 처리 스크립트 |
| apply_decisions_v5.py | 24.8 KB | 처리 스크립트 |
| apply_it_confirmation.py | 10.4 KB | 처리 스크립트 |
| audit_repo_files.py | 4.3 KB | 처리 스크립트 |
| build.py | 3.1 KB | 처리 스크립트 |
| build_university_master_list.py | 22.9 KB | 처리 스크립트 |
| catalog.json | 4.5 MB | 마커·학과·목록 데이터 |
| catalog_extra.json | 109.4 KB | 마커·학과·목록 데이터 |
| check_api_csv_coverage.py | 7.0 KB | 처리 스크립트 |
| check_api_csv_dept_diff.py | 4.0 KB | 처리 스크립트 |
| check_research_coverage.py | 15.4 KB | 처리 스크립트 |
| classify_it_dept_names.py | 3.4 KB | 처리 스크립트 |
| confirm_kedi_multi_address.py | 10.0 KB | 처리 스크립트 |
| coords22_report.txt | 17.3 KB | 보고·점검 문서 |
| coords_review_v2.json | 0.2 KB | 마커·학과·목록 데이터 |
| coords_unresolved_v2.json | 0.2 KB | 마커·학과·목록 데이터 |
| courses_master.json | 15.2 KB | 마커·학과·목록 데이터 |
| cowork_allowed_domains.md | 39.4 KB | 현재 기준 조사 md |
| cutmap_research_round2.md | 11.0 KB | 보고·점검 문서 |
| data.json | 24.9 KB | 마커·학과·목록 데이터 |
| data.py | 22.3 KB | 처리 스크립트 |
| decisions_v3_report.txt | 6.1 KB | 보고·점검 문서 |
| decisions_v4_report.txt | 6.4 KB | 보고·점검 문서 |
| decisions_v5_report.txt | 3.3 KB | 보고·점검 문서 |
| dedup_univ_major.py | 2.0 KB | 처리 스크립트 |
| draft_it_classification.py | 9.5 KB | 처리 스크립트 |
| dup_sample.txt | 5.3 KB | 보고·점검 문서 |
| exam_schedule.json | 4.5 KB | 마커·학과·목록 데이터 |
| extract_cowork_domains.py | 9.4 KB | 처리 스크립트 |
| fetch_univ_major_api.py | 4.8 KB | 처리 스크립트 |
| fill_coords_from_kedi.py | 10.0 KB | 처리 스크립트 |
| final_exclude_list.json | 11.6 KB | 마커·학과·목록 데이터 |
| final_include_list.json | 29.2 KB | 마커·학과·목록 데이터 |
| find_name_normalization_candidates.py | 10.4 KB | 처리 스크립트 |
| geo_prov.json | 171.3 KB | 지도·화면 파일 |
| geo_seoul.json | 31.0 KB | 지도·화면 파일 |
| geocode_failed.json | 3.7 KB | 마커·학과·목록 데이터 |
| geocode_gyeongnam_univ.py | 4.9 KB | 처리 스크립트 |
| geocode_retry_failed.py | 6.7 KB | 처리 스크립트 |
| grades/00_core.js | 17.2 KB | 지도·화면 파일 |
| grades/10_my.js | 22.5 KB | 지도·화면 파일 |
| grades/20_exams.js | 10.5 KB | 지도·화면 파일 |
| grades/30_score.js | 19.0 KB | 지도·화면 파일 |
| grades/40_analysis.js | 13.4 KB | 지도·화면 파일 |
| grades/45_scale.js | 3.8 KB | 지도·화면 파일 |
| grades/50_skin.js | 3.8 KB | 지도·화면 파일 |
| grades/60_targets.js | 11.1 KB | 지도·화면 파일 |
| grades/style.css | 15.6 KB | 지도·화면 파일 |
| grades/view.html | 1.8 KB | 지도·화면 파일 |
| it-major-map.html | 472.5 KB | 지도 화면 파일 (GitHub의 index.html과 내용 다름) |
| it_classification_draft_20260924.json | 5.4 MB | 마커·학과·목록 데이터 |
| it_classification_draft_20260924.md | 7.2 KB | 보고·점검 문서 |
| it_track_candidates.json | 150.7 KB | 마커·학과·목록 데이터 |
| kedi_multi_address_review.json | 3.3 KB | 마커·학과·목록 데이터 |
| leaflet.min.css | 14.3 KB | 지도·화면 파일 |
| link_coords_and_build_markers.py | 11.1 KB | 처리 스크립트 |
| make_catalog.py | 8.1 KB | 처리 스크립트 |
| make_git_upload_plan.py | 7.4 KB | 처리 스크립트 |
| make_mapping.py | 2.8 KB | 처리 스크립트 |
| map/50_basis.js | 8.1 KB | 지도·화면 파일 |
| map/60_list.js | 7.0 KB | 지도·화면 파일 |
| merged_schools.json | 21.4 KB | 마커·학과·목록 데이터 |
| name_normalization_candidates.json | 73.3 KB | 마커·학과·목록 데이터 |
| normalize_report.txt | 10.0 KB | 보고·점검 문서 |
| phase1_markers_v3.json | 270.3 KB | 마커·학과·목록 데이터 |
| recommended_courses_2028.json | 10.4 KB | 마커·학과·목록 데이터 |
| report_20260924_2.md | 6.9 KB | 보고·점검 문서 |
| report_20260924_3.md | 8.1 KB | 보고·점검 문서 |
| research_coverage_check_20260924.md | 8.7 KB | 보고·점검 문서 |
| resolve_coords22.py | 28.6 KB | 처리 스크립트 |
| skins.css | 10.4 KB | 지도·화면 파일 |
| synonyms.json | 3.9 KB | 마커·학과·목록 데이터 |
| template.html | 65.2 KB | 지도·화면 파일 |
| tidy_jeongsi_url_md.py | 4.1 KB | 처리 스크립트 |
| tidy_jeongsi_url_md_v2.py | 4.2 KB | 처리 스크립트 |
| undetermined_markers_check_20260924.md | 3.1 KB | 보고·점검 문서 |
| univ_coords.json | 42.0 KB | 마커·학과·목록 데이터 |
| univ_map.json | 4.6 KB | 마커·학과·목록 데이터 |
| university_master_list_v2.json | 1014.9 KB | 마커·학과·목록 데이터 |
| 컷맵_입결위치조사_20260924_v3.md | 88.5 KB | 현재 기준 조사 md |

## 3. 판단 필요

| 경로 | 크기 | 분류 |
|---|---|---|
| 2026년 고등 학교별 학과수 입학정원 지원 입학 학생 외국학생 졸업 교직원_260826H.xlsx | 1.6 MB | 내려받은 공공 원본 자료(입결 아님) |
| coords_review.json | 31.5 KB | 이전 버전 (현재 기준: coords_review_v2.json) |
| coords_unresolved.json | 11.5 KB | 이전 버전 (현재 기준: coords_unresolved_v2.json) |
| marker_missing_coords.json | 13.3 KB | 이전 버전 (현재 기준: phase1_markers_v3.json 등) |
| phase1_markers.json | 197.7 KB | 이전 버전 (현재 기준: phase1_markers_v3.json) |
| phase1_markers_v2.json | 204.3 KB | 이전 버전 (현재 기준: phase1_markers_v3.json) |
| univ_major_dedup.json | 78.0 MB | 50MB 초과 (GitHub 경고 크기, 100MB 미만) |
| university_master_list.json | 970.0 KB | 이전 버전 (현재 기준: university_master_list_v2.json) |
| 경상남도교육청_대학정보_20250918.csv | 41.6 KB | 내려받은 공공 원본 자료(입결 아님) |
| 전국대학별학과정보표준데이터.csv | 33.9 MB | 내려받은 공공 원본 자료(입결 아님) |
| 컷맵_입결위치조사_20260924.md | 35.9 KB | 이전 버전 (현재 기준: 컷맵_입결위치조사_20260924_v3.md) |

## 4. 올리지 않을 후보

| 경로 | 크기 | 사유 |
|---|---|---|
| __pycache__/ (파일 7개) | 157.0 KB | 파이썬 캐시 |
| archive/ (파일 2개) | 123.8 KB | archive 폴더 |
| backup_20260924_coords22/ (파일 4개) | 1.2 MB | 백업 폴더 |
| backup_20260924_decisions_v3/ (파일 6개) | 1.2 MB | 백업 폴더 |
| backup_20260924_decisions_v4/ (파일 8개) | 1.2 MB | 백업 폴더 |
| backup_20260924_decisions_v5/ (파일 8개) | 1.2 MB | 백업 폴더 |
| backup_20260924_decisions_v6/ (파일 4개) | 1.3 MB | 백업 폴더 |
| backup_20260929_v1/ (파일 2개) | 55.3 KB | 백업 폴더 |
| .env | 0.1 KB | API 키가 든 파일 |
| audit_repo_files.json | 2.7 MB | 이번 점검 산출물(파일 목록·검사 결과). 저장소에 둘 필요 없음 |
| univ_major_full.json | 130.0 MB | 100MB 초과 (GitHub 한도) |

## 5. .gitignore 초안

현재 `.gitignore`에는 `.env`, `__pycache__/`, `*.pyc` 세 줄이 있음. 아래는 추가안(아직 파일에 쓰지 않음).

```gitignore
# 비밀값 (API 키)
.env

# 파이썬 캐시
__pycache__/
*.pyc

# 백업·보관 폴더
backup_*/
archive/

# 로컬 도구 설정
.claude/

# 100MB 초과 파일
univ_major_full.json

# 내려받은 입결 원본 (Cowork 다운로드 포함)
*.pdf
*.hwp
*.hwpx
*.xls
*.zip
*.docx

# 점검용 임시 산출물
audit_repo_files.json

# 판단 필요 항목 (결정 후 주석 해제)
# *.xlsx
# 전국대학별학과정보표준데이터.csv
# 경상남도교육청_대학정보_20250918.csv
# univ_major_dedup.json
```

## 6. 전체 파일 목록 (크기 순)

표시: [100MB초과] [원본자료] [백업] [archive] [키]

| 경로 | 크기 | 표시 |
|---|---|---|
| univ_major_full.json | 130.0 MB | [100MB초과] |
| univ_major_dedup.json | 78.0 MB | - |
| 전국대학별학과정보표준데이터.csv | 33.9 MB | [원본자료] |
| it_classification_draft_20260924.json | 5.4 MB | - |
| catalog.json | 4.5 MB | - |
| audit_repo_files.json | 2.7 MB | - |
| 2026년 고등 학교별 학과수 입학정원 지원 입학 학생 외국학생 졸업 교직원_260826H.xlsx | 1.6 MB | [원본자료] |
| backup_20260924_decisions_v6/university_master_list_v2.json | 1014.9 KB | [백업] |
| university_master_list_v2.json | 1014.9 KB | - |
| backup_20260924_decisions_v5/university_master_list_v2.json | 976.9 KB | [백업] |
| backup_20260924_decisions_v4/university_master_list_v2.json | 974.6 KB | [백업] |
| backup_20260924_coords22/university_master_list.json | 970.0 KB | [백업] |
| backup_20260924_decisions_v3/university_master_list.json | 970.0 KB | [백업] |
| university_master_list.json | 970.0 KB | - |
| it-major-map.html | 472.5 KB | - |
| backup_20260924_decisions_v6/phase1_markers_v3.json | 270.3 KB | [백업] |
| phase1_markers_v3.json | 270.3 KB | - |
| backup_20260924_decisions_v5/phase1_markers_v3.json | 210.4 KB | [백업] |
| backup_20260924_decisions_v4/phase1_markers_v3.json | 207.7 KB | [백업] |
| backup_20260924_decisions_v3/phase1_markers_v2.json | 204.3 KB | [백업] |
| phase1_markers_v2.json | 204.3 KB | - |
| backup_20260924_coords22/phase1_markers.json | 197.7 KB | [백업] |
| phase1_markers.json | 197.7 KB | - |
| geo_prov.json | 171.3 KB | - |
| it_track_candidates.json | 150.7 KB | - |
| 2027_IT대학_입시조사_초안.md | 134.6 KB | - |
| catalog_extra.json | 109.4 KB | - |
| 컷맵_입결위치조사_20260924_v3.md | 88.5 KB | - |
| name_normalization_candidates.json | 73.3 KB | - |
| archive/컷맵_입결위치조사_20260924_v3_중간.md | 69.7 KB | [archive] |
| template.html | 65.2 KB | - |
| api_csv_dept_diff_20260929.md | 54.4 KB | - |
| archive/컷맵_입결위치조사_20260924_v2.md | 54.1 KB | [archive] |
| 2027_경기인천영남_모집요강_URL.md | 44.8 KB | - |
| __pycache__/resolve_coords22.cpython-314.pyc | 43.0 KB | - |
| univ_coords.json | 42.0 KB | - |
| 경상남도교육청_대학정보_20250918.csv | 41.6 KB | [원본자료] |
| api_csv_coverage_20260924.md | 39.8 KB | - |
| cowork_allowed_domains.md | 39.4 KB | - |
| backup_20260929_v1/cowork_allowed_domains.md | 38.7 KB | [백업] |
| 컷맵_입결위치조사_20260924.md | 35.9 KB | - |
| SPEC_성적관리시스템.md | 35.0 KB | - |
| backup_20260924_decisions_v3/coords_review.json | 31.5 KB | [백업] |
| coords_review.json | 31.5 KB | - |
| geo_seoul.json | 31.0 KB | - |
| __pycache__/build_university_master_list.cpython-314.pyc | 29.4 KB | - |
| final_include_list.json | 29.2 KB | - |
| resolve_coords22.py | 28.6 KB | - |
| apply_decisions_v3.py | 27.4 KB | - |
| __pycache__/data.cpython-314.pyc | 26.8 KB | - |
| data.json | 24.9 KB | - |
| apply_decisions_v5.py | 24.8 KB | - |
| build_university_master_list.py | 22.9 KB | - |
| grades/10_my.js | 22.5 KB | - |
| data.py | 22.3 KB | - |
| merged_schools.json | 21.4 KB | - |
| grades/30_score.js | 19.0 KB | - |
| __pycache__/fill_coords_from_kedi.cpython-314.pyc | 18.6 KB | - |
| apply_decisions_v4.py | 18.1 KB | - |
| coords22_report.txt | 17.3 KB | - |
| grades/00_core.js | 17.2 KB | - |
| backup_20260924_decisions_v5/merged_schools.json | 17.0 KB | [백업] |
| backup_20260929_v1/2027_정시모집요강_URL_누적.md | 16.6 KB | [백업] |
| __pycache__/link_coords_and_build_markers.cpython-314.pyc | 16.6 KB | - |
| backup_20260924_decisions_v6/2027_정시모집요강_URL_누적.md | 16.3 KB | [백업] |
| 2027_정시모집요강_URL_누적.md | 16.1 KB | - |
| grades/style.css | 15.6 KB | - |
| backup_20260924_decisions_v4/2027_정시모집요강_URL_누적.md | 15.6 KB | [백업] |
| check_research_coverage.py | 15.4 KB | - |
| courses_master.json | 15.2 KB | - |
| __pycache__/check_api_csv_coverage.cpython-314.pyc | 14.6 KB | - |
| backup_20260924_decisions_v4/merged_schools.json | 14.5 KB | [백업] |
| leaflet.min.css | 14.3 KB | - |
| grades/40_analysis.js | 13.4 KB | - |
| backup_20260924_coords22/marker_missing_coords.json | 13.3 KB | [백업] |
| marker_missing_coords.json | 13.3 KB | - |
| 4yr_list_seoul_chungcheong_gangwon_jeju_honam.md | 13.2 KB | - |
| PROGRESS.md | 12.8 KB | - |
| add_new_candidate_univs.py | 12.0 KB | - |
| backup_20260924_decisions_v5/4yr_list_seoul_chungcheong_gangwon_jeju_honam.md | 12.0 KB | [백업] |
| 4yr_list_gyeonggi_incheon_yeongnam.md | 11.9 KB | - |
| final_exclude_list.json | 11.6 KB | - |
| backup_20260924_decisions_v3/coords_unresolved.json | 11.5 KB | [백업] |
| coords_unresolved.json | 11.5 KB | - |
| link_coords_and_build_markers.py | 11.1 KB | - |
| grades/60_targets.js | 11.1 KB | - |
| cutmap_research_round2.md | 11.0 KB | - |
| backup_20260924_decisions_v4/4yr_list_gyeonggi_incheon_yeongnam.md | 10.8 KB | [백업] |
| backup_20260924_decisions_v5/4yr_list_gyeonggi_incheon_yeongnam.md | 10.8 KB | [백업] |
| grades/20_exams.js | 10.5 KB | - |
| skins.css | 10.4 KB | - |
| recommended_courses_2028.json | 10.4 KB | - |
| find_name_normalization_candidates.py | 10.4 KB | - |
| apply_it_confirmation.py | 10.4 KB | - |
| SPEC_대학맵.md | 10.3 KB | - |
| fill_coords_from_kedi.py | 10.0 KB | - |
| normalize_report.txt | 10.0 KB | - |
| confirm_kedi_multi_address.py | 10.0 KB | - |
| backup_20260924_decisions_v4/coords_review_v2.json | 9.6 KB | [백업] |
| backup_20260924_decisions_v6/SPEC_대학맵.md | 9.6 KB | [백업] |
| draft_it_classification.py | 9.5 KB | - |
| backup_20260924_decisions_v5/SPEC_대학맵.md | 9.4 KB | [백업] |
| extract_cowork_domains.py | 9.4 KB | - |
| research_coverage_check_20260924.md | 8.7 KB | - |
| backup_20260924_decisions_v4/SPEC_대학맵.md | 8.6 KB | [백업] |
| map/50_basis.js | 8.1 KB | - |
| report_20260924_3.md | 8.1 KB | - |
| make_catalog.py | 8.1 KB | - |
| __pycache__/geocode_gyeongnam_univ.cpython-314.pyc | 8.0 KB | - |
| backup_20260924_decisions_v3/SPEC_대학맵.md | 8.0 KB | [백업] |
| make_git_upload_plan.py | 7.4 KB | - |
| it_classification_draft_20260924.md | 7.2 KB | - |
| CHANGELOG.md | 7.1 KB | - |
| check_api_csv_coverage.py | 7.0 KB | - |
| map/60_list.js | 7.0 KB | - |
| report_20260924_2.md | 6.9 KB | - |
| RELEASE_CHECKLIST.md | 6.7 KB | - |
| geocode_retry_failed.py | 6.7 KB | - |
| HANDOFF_컷맵_20260924_v2.md | 6.6 KB | - |
| decisions_v4_report.txt | 6.4 KB | - |
| decisions_v3_report.txt | 6.1 KB | - |
| dup_sample.txt | 5.3 KB | - |
| geocode_gyeongnam_univ.py | 4.9 KB | - |
| fetch_univ_major_api.py | 4.8 KB | - |
| univ_map.json | 4.6 KB | - |
| exam_schedule.json | 4.5 KB | - |
| audit_repo_files.py | 4.3 KB | - |
| tidy_jeongsi_url_md_v2.py | 4.2 KB | - |
| tidy_jeongsi_url_md.py | 4.1 KB | - |
| check_api_csv_dept_diff.py | 4.0 KB | - |
| synonyms.json | 3.9 KB | - |
| PROJECT_BRIEF.md | 3.9 KB | - |
| grades/50_skin.js | 3.8 KB | - |
| grades/45_scale.js | 3.8 KB | - |
| geocode_failed.json | 3.7 KB | - |
| HANDOFF_컷맵_20260924.md | 3.6 KB | - |
| classify_it_dept_names.py | 3.4 KB | - |
| decisions_v5_report.txt | 3.3 KB | - |
| backup_20260924_coords22/kedi_multi_address_review.json | 3.3 KB | [백업] |
| backup_20260924_decisions_v3/kedi_multi_address_review.json | 3.3 KB | [백업] |
| kedi_multi_address_review.json | 3.3 KB | - |
| undetermined_markers_check_20260924.md | 3.1 KB | - |
| build.py | 3.1 KB | - |
| make_mapping.py | 2.8 KB | - |
| backup_20260924_decisions_v5/coords_review_v2.json | 2.6 KB | [백업] |
| dedup_univ_major.py | 2.0 KB | - |
| grades/view.html | 1.8 KB | - |
| app_meta.json | 0.5 KB | - |
| coords_review_v2.json | 0.2 KB | - |
| backup_20260924_decisions_v4/coords_unresolved_v2.json | 0.2 KB | [백업] |
| backup_20260924_decisions_v5/coords_unresolved_v2.json | 0.2 KB | [백업] |
| coords_unresolved_v2.json | 0.2 KB | - |
| .env | 0.1 KB | [키] |
| .gitignore | 0.0 KB | - |
