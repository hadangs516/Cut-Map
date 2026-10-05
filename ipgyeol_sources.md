# 입결 자료 내려받기 현황 (ipgyeol_sources.md)

작업 112·113(#1005-45). target_univ.md의 그룹 A~D 대상 학교(지도 마커 없는 대구경북과학기술원 포함)에서 학생부종합전형(학종) 결과가 들어 있는 최근 학년도 수시 입결 자료를 찾아 sources/ipgyeol/ 에 받았다.
원본 주소와 파일 위치는 v8의 입결 위치에서 시작해, 그 게시글 화면의 첨부 링크를 따라갔다. 허용 도메인 밖이거나 robots.txt가 그 경로를 막으면 받지 않았다. 50MB를 넘는 파일은 받지 않는다(이번에는 해당 없음).
같은 내용을 data/ipgyeol_sources.json에도 저장했다.

## 학교별 상태 개수

| 상태 | 학교 수 | 학교 |
|---|---|---|
| 받음 | 18 | 강원대학교, 부산대학교, 충북대학교, 한동대학교, 대구대학교, 대구가톨릭대학교, 연세대학교(서울), 서강대학교, 성균관대학교(수원), 한양대학교(서울), 한양대학교(ERICA), 경희대학교(국제캠퍼스), 건국대학교(서울), 동국대학교(서울), 홍익대학교(서울), 숭실대학교, 세종대학교, 광운대학교 |
| robots 차단 | 12 | 경북대학교, 경상국립대학교, 전남대학교, 전북대학교, 제주대학교, 충남대학교, 계명대학교, 영남대학교, 서울시립대학교, 중앙대학교(서울), 국민대학교, 서울과학기술대학교 |
| 허용 도메인 밖 | 0 | - |
| 입결 위치 미확인 | 4 | 포항공과대학교, 대구경북과학기술원, 고려대학교(서울), 가톨릭대학교(성심) |
| 학종 자료 없음 | 1 | 서울대학교 |
| 내려받기 실패 | 0 | - |

## 목록

| 그룹 | 학교명 | 마커 이름 | 파일명 | 원본 주소 | 학년도 | 형식 | 상태 | 비고 |
|---|---|---|---|---|---|---|---|---|
| A | 강원대학교 | 강원대학교(춘천) | 강원대학교_2026_수시입결_1.xlsx | https://admission.kangwon.ac.kr/admission/cmmn/download.do?dn=20260511102957280fYK.xlsx&path=/DATA/bbs/376&fn=2026%ED%95%99%EB%85%84%EB%8F%84%20%EC%88%98%EC%8B%9C%20%EC%9E%85%EC%8B%9C%EA%B2%B0%EA%B3%BC%EF%BC%88%ED%99%88%ED%8E%98%EC%9D%B4%EC%A7%80%20%EA%B2%8C%EC%8B%9C%EC%9A%A9%EF%BC%89.xlsx | 2026 | xlsx | 받음 | 2026학년도 수시 입시결과（홈페이지 게시용）.xlsx / 학종 문구 확인(미래인재, 서류, 학생부종합) |
| A | 강원대학교 | 강원대학교(춘천) | 강원대학교_2026_수시입결_2.xlsx | https://admission.kangwon.ac.kr/admission/cmmn/download.do?dn=20260528084749540B03.xlsx&path=/DATA/bbs/376&fn=2026%ED%95%99%EB%85%84%EB%8F%84%20%ED%95%99%EC%83%9D%EB%B6%80%EC%A2%85%ED%95%A9%EC%A0%84%ED%98%95%20%EC%82%B0%ED%8F%AC%EB%8F%84.xlsx | 2026 | xlsx | 받음 | 2026학년도 학생부종합전형 산포도.xlsx / 학종 문구 확인(미래인재, 서류) |
| A·C(겹침) | 경북대학교 | 경북대학교(대구) | - | https://ipsi1.knu.ac.kr/data/view.php?r=FxlcTxxJV0FHAHIbHAY6WQ9CEEogPWAvMyE1S0M4CAMAEEc | 2026 | - | robots 차단 | 2026 수시/정시 전형결과 게시글(통합자료실) / robots.txt 있음: 차단 / User-agent: * Disallow: / |
| A | 경상국립대학교 | 경상국립대학교 (본교(제1캠퍼스)) | - | https://www.gnu.ac.kr/common/fileDownload.do?fileKey=65036 | 2026 | - | robots 차단 | 2026학년도 수시모집 결과(다운로드) — 게시글은 열렸으나 파일 경로가 robots 차단 / robots.txt 있음: 차단 / User-agent: * Disallow: /editor/ Disallow: /excel/ Disallow: / 게시글은 열렸으나 파일 경로(/common/fileDownload.do)가 robots.txt로 막힘 |
| A | 부산대학교 | 부산대학교(부산) | 부산대학교_2026_수시입결.pdf | https://go.pusan.ac.kr/_common/new_download_file.asp?menu=boardfile&file_no=4250 | 2026 | pdf | 받음 | 2026학년도 부산대학교 대입전형결과_공개용.pdf / 학종 문구 확인(학생부종합) / 수시·정시 통합 파일 |
| A | 전남대학교 | 전남대학교 (본교(제1캠퍼스)) | - | https://admission.jnu.ac.kr/WebApp/web/HOM/COM/Board/board.aspx?boardID=423&bbsMode=view&page=1&key=26 | 2026 | - | robots 차단 | 2026학년도 대입전형 입시 결과분석 자료 공고(수시_공개.xlsx) / robots.txt 있음: 차단 / ﻿# 전체 차단 User-agent: * Disallow: /  User-agent: Googlebo |
| A | 전북대학교 | 전북대학교(전주) | - | https://enter.jbnu.ac.kr/detail.do?search_key=title&searchNo=&searchtext=&menuurl=vQ5Um0%2FKclp6EAegmwbvhQ%3D%3D&board_seq=43573&pageNo=1&categoryid=8&value= | 2026 | - | robots 차단 | v8에 있는 전북대 입결 위치는 2026 정시 게시글 하나뿐 / robots.txt 있음: 차단 / User-agent: * Disallow: / |
| A | 제주대학교 | 제주대학교(제주) | - | https://ibsi.jejunu.ac.kr/10000048?mode=view&bbs_seq=45701&categorycode=57 | 2026 | - | robots 차단 | (게시용)최근 3개 학년도 입시 결과자료.xlsx / robots.txt 있음: 차단 / User-agent: * Disallow: /  User-agent:Yeti User-agent:Google |
| A | 충남대학교 | 충남대학교(대전) | - | https://ipsi.cnu.ac.kr/html/uadm/ | 2026 | - | robots 차단 | 2026 수시모집 결과 안내 공지(입학정보 메인) / robots.txt 있음: 차단 / User-agent: * Disallow : / Disallow : /_hamTool/ |
| A | 충북대학교 | 충북대학교(청주) | 충북대학교_2026_수시입결_1.pdf | https://ipsi.chungbuk.ac.kr/cmm/fms/FileDown.do?atchFileId=FILE_000000000003237SxAbe&fileSn=0 | 2026 | pdf | 받음 | 01. 2026학년도 충북대학교 대학입학전형결과 현황표(수시 학생부종합I 전형).pdf / 학종 문구 확인(서류, 학생부종합) |
| A | 충북대학교 | 충북대학교(청주) | 충북대학교_2026_수시입결_2.pdf | https://ipsi.chungbuk.ac.kr/cmm/fms/FileDown.do?atchFileId=FILE_000000000003237SxAbe&fileSn=1 | 2026 | pdf | 받음 | 02. …(수시 학생부종합II 전형).pdf / 학종 문구 확인(서류, 학생부종합) |
| A | 충북대학교 | 충북대학교(청주) | 충북대학교_2026_수시입결_3.pdf | https://ipsi.chungbuk.ac.kr/cmm/fms/FileDown.do?atchFileId=FILE_000000000003237SxAbe&fileSn=2 | 2026 | pdf | 받음 | 03. …(수시 sw우수인재 전형).pdf / 학종 문구 확인(서류, 학생부종합) |
| B | 포항공과대학교 | 포항공과대학교 (본교(제1캠퍼스)) | - |  | - | - | 입결 위치 미확인 | v8 1장·3장에 행 없음 |
| B | 한동대학교 | 한동대학교(포항) | 한동대학교_2026_수시입결.pdf | https://admissions.handong.edu/dcp/editor/files/2026%ED%95%99%EB%85%84%EB%8F%84%20%EC%9E%85%EC%8B%9C%EA%B2%B0%EA%B3%BC.pdf | 2026 | pdf | 받음 | 2026학년도 입시결과.pdf (PDF 다운) / 학종 문구 확인(G-IMPACT, 학생부종합, 한동인재) / 지원·입학 현황 표(학생부종합 행 있음, 컷 점수 없음) |
| C | 계명대학교 | 계명대학교(대구) | - | https://www.gokmu.ac.kr/service/board.htm?bbsid=result&mode=view&bltn_seq=85112 | 2026 | - | robots 차단 | 2026학년도 신입생 수시모집 성적현황.pdf / robots.txt 있음: 차단 / User-agent: * Disallow: / |
| C | 대구경북과학기술원 | (지도 마커 없음) | - |  | - | - | 입결 위치 미확인 | v8에 행 없음, 지도 마커 없음 |
| C | 영남대학교 | 영남대학교(경산) | - | https://enter.yu.ac.kr/10000011?mode=view&bbs_seq=1223 | 2026 | - | robots 차단 | 2026학년도 수시모집 입학자 성적_게시용.xlsx / robots.txt 있음: 차단 / User-agent: * Disallow: / |
| C | 대구대학교 | 대구대학교(경산) | 대구대학교_2026_수시입결_1.pdf | https://ipsi.daegu.ac.kr/attach/4f07f1bc883c5ed3a5f2810a1615e214/9a9db098b587ee18b321c826f3707a49 | 2026 | pdf | 받음 | 대구대학교 2026학년도 수시모집 학생부위주 주요 전형 결과 ….pdf / 학종 문구 확인(서류, 학생부종합) |
| C | 대구대학교 | 대구대학교(경산) | 대구대학교_2026_수시입결_2.xlsx | https://ipsi.daegu.ac.kr/attach/4f07f1bc883c5ed3a5f2810a1615e214/778bdbf5db9ced7c8fd52756c00bf0cd | 2026 | xlsx | 받음 | 같은 제목 .xlsx / 학종 문구 확인(서류, 학생부종합) |
| C | 대구가톨릭대학교 | 대구가톨릭대학교(경산) | 대구가톨릭대학교_2026_수시입결_1.pdf | https://ibsi.cu.ac.kr/cmm/fms/FileDown.do?atchFileId=FILE_000000000004342&fileSn=0 | 2026 | pdf | 받음 | 2026학년도 신입생 수시모집 입시결과(성적자료)_홈페이지공개용.pdf / 학종 문구 확인(종합전형, 학생부종합) |
| C | 대구가톨릭대학교 | 대구가톨릭대학교(경산) | 대구가톨릭대학교_2026_수시입결_2.xlsx | https://ibsi.cu.ac.kr/cmm/fms/FileDown.do?atchFileId=FILE_000000000004342&fileSn=1 | 2026 | xlsx | 받음 | 같은 제목 .xlsx / 학종 문구 확인(종합전형, 학생부종합) |
| D | 서울대학교 | 서울대학교(서울) | - | https://admission.snu.ac.kr/materials/stats/result | - | - | 학종 자료 없음 | v8: 성적 입결 자료 없음(입학본부 공개 범위는 선발현황·보도자료). 보도자료는 선발 결과 요약이라 받지 않음 |
| D | 연세대학교(서울) | 연세대학교(서울) | 연세대학교(서울)_2026_수시입결.pdf | https://admission.yonsei.ac.kr/seoul/download.asp?furl=bbs/202604201055398D4W8V.PDF&fname=2026%C7%D0%B3%E2%B5%B5+%BC%F6%BD%C3%B8%F0%C1%FD+%BC%B1%B9%DF%B0%E1%B0%FA%2Epdf | 2026 | pdf | 받음 | 2026학년도 수시모집 선발결과.pdf / 학종 문구 확인(학생부종합) |
| D | 고려대학교(서울) | 고려대학교(서울) | - | https://oku.korea.ac.kr/oku/cms/FR_CON/index.do?MENU_ID=710 | - | - | 입결 위치 미확인 | v8: 지원율통계(경쟁률만) 확인, 입결 파일 위치 미확인(입학자료실 비어 있음) |
| D | 서강대학교 | 서강대학교(서울) | 서강대학교_2026_수시입결.pdf | https://admission.sogang.ac.kr/upload/GUIDES/20260602150120JNQJPH.pdf | 2026 | pdf | 받음 | 2026학년도 서강대학교 입시결과.pdf (PDF 확대보기 링크, 수시·정시 통합) / 학종 문구 확인(학생부종합) / 수시·정시 통합 파일 |
| D | 성균관대학교(수원) | 성균관대학교 (본교(제2캠퍼스)) | 성균관대학교(수원)_2026_수시입결.pdf | https://admission.skku.edu/common/download.php?fpath=board/2026041019340236ADBE.pdf&fname=%5B%EC%84%B1%EA%B7%A0%EA%B4%80%EB%8C%80%5D+2026%ED%95%99%EB%85%84%EB%8F%84+%EB%8C%80%EC%9E%85%EC%A0%84%ED%98%95+%EA%B2%B0%EA%B3%BC.pdf | 2026 | pdf | 받음 | [성균관대] 2026학년도 대입전형 결과.pdf / 텍스트에서 학종 문구를 찾지 못함 / 텍스트 층이 없는 PDF(이미지)라 학종 포함 여부 미확인 |
| D | 한양대학교(서울) | 한양대학교(서울) | 한양대학교(서울)_2024-2026_수시입결.pdf | https://go.hanyang.ac.kr/file/download.do?menu=board&file_no=20773&type=B_1_8 | 2024-2026 | pdf | 받음 | 수시 2024 - 2026 전형별 입시결과 (게시 2026.05.11) / 학종 문구 확인(면접형, 서류, 학생부종합) / 2024~2026 전형별 입시결과 한 파일(41MB) |
| D | 한양대학교(ERICA) | 한양대학교(에리카) | 한양대학교(ERICA)_2024-2026_수시입결.pdf | https://goerica.hanyang.ac.kr/upload/BBS0062/20260423200430A2SV89.PDF | 2024-2026 | pdf | 받음 | 2024-2026학년도 입시결과 (수시모집 > 입시결과 메뉴, PDF 확대보기 링크) / 학종 문구 확인(면접형, 서류, 학생부종합) / 수시모집 > 입시결과 메뉴의 PDF(2024~2026) |
| D | 서울시립대학교 | 서울시립대학교(서울) | - | https://admission.uos.ac.kr/common/board-download.do?listId=K7&seq=35&fSeq=3 | 2026 | - | robots 차단 | 붙임3. 2026학년도 수시모집 최종등록자 성적 현황(학생부종합위주) — 파일 경로가 robots 차단(붙임4도 같음) / robots.txt 있음: 차단 / User-agent: * Disallow: /exsignon/ Disallow: /search/  Disal / 게시글은 열렸으나 파일 경로(/common/board-download.do)가 robots.txt로 막힘. 학종 파일은 붙임3·붙임4 |
| D | 서울시립대학교 | 서울시립대학교(서울) | - | https://admission.uos.ac.kr/common/board-download.do?listId=K7&seq=35&fSeq=4 | 2026 | - | robots 차단 | 붙임4. 2026학년도 수시모집 최종등록자 고교유형별 성적 현황(학생부종합위주).pdf / robots.txt 있음: 차단 / User-agent: * Disallow: /exsignon/ Disallow: /search/  Disal / 게시글은 열렸으나 파일 경로(/common/board-download.do)가 robots.txt로 막힘. 학종 파일은 붙임3·붙임4 |
| D | 중앙대학교(서울) | 중앙대학교(서울) | - | https://admission.cau.ac.kr/files/2027/becaus_news_s_2027.pdf | 2026 | - | robots 차단 | BECAUS NEWS 수시 입시결과 뉴스레터 / robots.txt 있음: 차단 / User-agent: * Disallow: /  User-agent: Googlebot Allow: / Di |
| D | 경희대학교(국제캠퍼스) | 경희대학교 (본교(제2캠퍼스)) | 경희대학교(국제캠퍼스)_2026_수시입결.pdf | https://iphak.khu.ac.kr/file/download.do?sfn=20260513054241529_2026%ed%95%99%eb%85%84%eb%8f%84+%ec%9e%85%ed%95%99%ec%a0%84%ed%98%95+%ed%86%b5%ea%b3%84%ec%9e%90%eb%a3%8c_%ed%99%88%ed%8e%98%ec%9d%b4%ec%a7%80%ea%b3%b5%ec%a7%80%ec%9a%a9.pdf&ofn=2026%ed%95%99%eb%85%84%eb%8f%84+%ec%9e%85%ed%95%99%ec%a0%84%ed%98%95+%ed%86%b5%ea%b3%84%ec%9e%90%eb%a3%8c_%ed%99%88%ed%8e%98%ec%9d%b4%ec%a7%80%ea%b3%b5%ec%a7%80%ec%9a%a9.pdf | 2026 | pdf | 받음 | 2026학년도 입학전형 통계자료_홈페이지공지용.pdf / 학종 문구 확인(서류, 학생부종합) / 수시·정시 통합 통계자료(서울·국제 공통 파일) |
| D | 건국대학교(서울) | 건국대학교(서울) | 건국대학교(서울)_2026_수시입결.pdf | https://admission.konkuk.ac.kr/bbs/admission/6290/1216634/download.do | 2026 | pdf | 받음 | 2026학년도 입시결과_통합(게시용).pdf / 학종 문구 확인(학생부종합) / 수시·정시 통합 파일 |
| D | 동국대학교(서울) | 동국대학교(서울) | 동국대학교(서울)_2026_수시입결.pdf | https://ipsi.dongguk.edu/common/downLoad.asp?strFileName=2026%B5%BF%B1%B9%5F%C0%D4%C7%D0%C0%FC%C7%FC%B0%E1%B0%FA%5F%B4%DC%B8%E9%5F260918%BC%F6%C1%A4%2Epdf&strRealFileName=/upload/file/202609181646284P926C.PDF | 2026 | pdf | 받음 | 2026동국_입학전형결과_단면_260918수정.pdf (PDF다운로드; 같은 문서의 HWP는 받지 않음) / 학종 문구 확인(면접형, 서류, 학생부종합) / 수시·정시 통합 파일, 같은 문서의 HWP는 받지 않음 |
| D | 홍익대학교(서울) | 홍익대학교 (본교(제1캠퍼스)) | 홍익대학교(서울)_2026_수시입결_1.zip | https://www.hongik.ac.kr/kr/admission/entrance-point.do?mode=download&articleNo=152834&attachNo=89149 | 2026 | zip | 받음 | [홍익대학교] 2026학년도 수시모집 입학전형 결과_홈페이지공지.zip / zip 안: [홍익대학교] 2026학년도 수시모집 입학전형 결과_홈페이지공지(홈페이지_공지).pdf / zip 안 PDF가 텍스트 층이 없는 이미지라 학종 포함 여부 미확인 |
| D | 홍익대학교(서울) | 홍익대학교 (본교(제1캠퍼스)) | 홍익대학교(서울)_2026_수시입결_2.zip | https://www.hongik.ac.kr/kr/admission/entrance-point.do?mode=download&articleNo=152832&attachNo=89148 | 2026 | zip | 받음 | [홍익대학교] 2026학년도 수시모집_정시모집_일반전형 학생부_수능표준점수평균.zip / zip 안: [홍익대학교] 2026학년도 수시모집_정시모집_일반전형 학생부_수능표준점수평균(홈페이지_공지).pdf / zip 안 PDF가 텍스트 층이 없는 이미지라 학종 포함 여부 미확인 |
| D | 국민대학교 | 국민대학교(서울) | - | https://admission.kookmin.ac.kr/main.php?kw=047359 | 2026 | - | robots 차단 | 입학처 메인(2026 학생부교과·학생부종합 입시결과 안내 배너) / robots.txt 있음: 차단 / # 기본: 모든 User-agent 차단 User-agent: * Disallow: /  # 허용: 주요 검 |
| D | 숭실대학교 | 숭실대학교(서울) | 숭실대학교_2026_수시입결.pdf | https://iphak.ssu.ac.kr/upload/SSU(1)_26051116627.pdf | 2026 | pdf | 받음 | 입시통계(게시글 number=241의 첨부, 파일명 SSU(1)_26051116627.pdf) / 학종 문구 확인(SW우수, 면접형, 미래인재, 서류) / 게시글 number=241의 첨부(파일명 안의 학년도는 게시글보다 1년 뒤) |
| D | 세종대학교 | 세종대학교(서울) | 세종대학교_2026_수시입결.pdf | https://ipsi.sejong.ac.kr/ipsi/assistant/entrance.do?mode=download&articleNo=2742&attachNo=2850 | 2026 | pdf | 받음 | 공지용_2027학년도수시모집입시상담자료.pdf (v8: 입결 학년도는 게시글 제목 기준 2026) / 학종 문구 확인(면접형, 서류, 학생부종합) / 파일명은 2027학년도 수시모집 입시상담자료, v8은 입결 학년도를 게시글 제목 기준 2026으로 기록 |
| D | 광운대학교 | 광운대학교(서울) | 광운대학교_2026_수시입결.pdf | https://iphak.kw.ac.kr/_common/new_download_file.php?menu=board&b_code=B_1_8&b_no=44580&field=file_nm | 2026 | pdf | 받음 | 2026학년도 수시모집 최종등록자 평균성적 및 충원합격 비율 / 학종 문구 확인(면접형, 서류, 학생부종합) |
| D | 서울과학기술대학교 | 서울과학기술대학교(서울) | - | https://admission.seoultech.ac.kr/cms/FR_BBS_CON/BoardView.do?MENU_ID=810&SITE_NO=2&BOARD_SEQ=22&BBS_SEQ=48 | 2026 | - | robots 차단 | 서울과학기술대학교 2026학년도 입시결과.pdf / robots.txt 있음: 차단 / User-agent: * Disallow: / |
| D | 가톨릭대학교(성심) | 가톨릭대학교 (본교(제1캠퍼스)) | - |  | - | - | 입결 위치 미확인 | v8 3-1장 보류 표에만 있음(IT 학과 소재지 좌표 미확보), 입결 행 없음 |
