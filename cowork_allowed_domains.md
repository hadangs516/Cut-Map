# Cowork 허용 도메인 목록

- 작성: 2026-09-28 / extract_cowork_domains.py (읽기 전용 추출)
- 출처: `2026년 고등 학교별 학과수 입학정원 지원 입학 학생 외국학생 졸업 교직원_260826H.xlsx` 학교별 교육통계 시트의 '홈페이지' 열 (KEDI 2026 고등교육통계)
- 대상: `university_master_list_v2.json` 학부 조사 대상 301행
- KEDI 행 연결: 연결캠퍼스명(학교명+본분교) 우선, 없으면 학교명 일치. 대학원 학제 행은 쓰지 않음. 운영 중 행이 있으면 폐교 행은 뺌
- 허용 도메인: 홈페이지 주소의 호스트에서 등록 도메인만 남김 (ac.kr·or.kr 등은 끝 3단계, 그 외는 끝 2단계). SPEC 13번에 따라 이 도메인과 그 하위 도메인을 허용
- 학교명으로만 연결돼 KEDI 행이 여러 개면 KEDI 시도가 같은 권역인 행으로 좁힘. 그래도 여러 개면 홈페이지를 모두 적음

## 1. 행별 목록 (301행)

| # | 권역 | 대학명 | 캠퍼스 | KEDI 홈페이지 URL | 허용 도메인 |
|---|---|---|---|---|---|
| 1 | 서울 | 강서대학교 | 강서대학교 (본교(제1캠퍼스)) | www.gangseo.ac.kr | gangseo.ac.kr |
| 2 | 서울 | 건국대학교 | 건국대학교(서울) | www.konkuk.ac.kr | konkuk.ac.kr |
| 3 | 서울 | 경기대학교 | 경기대학교 (본교(제2캠퍼스)) | www.kyonggi.ac.kr | kyonggi.ac.kr |
| 4 | 서울 | 경희대학교 | 경희대학교 (본교(제1캠퍼스)) | www.khu.ac.kr | khu.ac.kr |
| 5 | 서울 | 고려대학교 | 고려대학교(서울) | www.korea.ac.kr | korea.ac.kr |
| 6 | 서울 | 광운대학교 | 광운대학교(서울) | www.kw.ac.kr | kw.ac.kr |
| 7 | 서울 | 국민대학교 | 국민대학교(서울) | www.kookmin.ac.kr | kookmin.ac.kr |
| 8 | 서울 | 덕성여자대학교 | 덕성여자대학교(서울) | www.duksung.ac.kr | duksung.ac.kr |
| 9 | 서울 | 동국대학교 | 동국대학교(서울) | http://www.dongguk.edu | dongguk.edu |
| 10 | 서울 | 동덕여자대학교 | 동덕여자대학교(서울) | www.dongduk.ac.kr | dongduk.ac.kr |
| 11 | 서울 | 동양미래대학교 | 동양미래대학교 (본교(제1캠퍼스)) | www.dongyang.ac.kr/ | dongyang.ac.kr |
| 12 | 서울 | 명지대학교 | 명지대학교 (본교(제2캠퍼스)) | https://www.mju.ac.kr/ | mju.ac.kr |
| 13 | 서울 | 명지전문대학 | 명지전문대학 (본교(제1캠퍼스)) | www.mjc.ac.kr | mjc.ac.kr |
| 14 | 서울 | 배화여자대학교 | 배화여자대학교 (본교(제1캠퍼스)) | www.baewha.ac.kr | baewha.ac.kr |
| 15 | 서울 | 삼육대학교 | 삼육대학교(서울) | http://www.syu.ac.kr | syu.ac.kr |
| 16 | 서울 | 상명대학교 | 상명대학교(서울) | www.smu.ac.kr | smu.ac.kr |
| 17 | 서울 | 서강대학교 | 서강대학교(서울) | www.sogang.ac.kr | sogang.ac.kr |
| 18 | 서울 | 서경대학교 | 서경대학교(서울) | https://www.skuniv.ac.kr | skuniv.ac.kr |
| 19 | 서울 | 서울과학기술대학교 | 서울과학기술대학교(서울) | www.seoultech.ac.kr | seoultech.ac.kr |
| 20 | 서울 | 서울교육대학교 | 서울교육대학교 (본교(제1캠퍼스)) | www.snue.ac.kr | snue.ac.kr |
| 21 | 서울 | 서울기독대학교 | 서울기독대학교(서울) | https://www.scu.ac.kr/main | scu.ac.kr |
| 22 | 서울 | 서울대학교 | 서울대학교(서울) | www.snu.ac.kr | snu.ac.kr |
| 23 | 서울 | 서울시립대학교 | 서울시립대학교(서울) | www.uos.ac.kr | uos.ac.kr |
| 24 | 서울 | 서울여자대학교 | 서울여자대학교(서울) | www.swu.ac.kr | swu.ac.kr |
| 25 | 서울 | 서일대학교 | 서일대학교 (본교(제1캠퍼스)) | www.seoil.ac.kr | seoil.ac.kr |
| 26 | 서울 | 성공회대학교 | 성공회대학교(서울) | www.skhu.ac.kr | skhu.ac.kr |
| 27 | 서울 | 성균관대학교 | 성균관대학교(서울) | http://www.skku.edu | skku.edu |
| 28 | 서울 | 성신여자대학교 | 성신여자대학교(서울) | www.sungshin.ac.kr | sungshin.ac.kr |
| 29 | 서울 | 세종대학교 | 세종대학교(서울) | www.sejong.ac.kr | sejong.ac.kr |
| 30 | 서울 | 숙명여자대학교 | 숙명여자대학교(서울) | www.sookmyung.ac.kr | sookmyung.ac.kr |
| 31 | 서울 | 숭실대학교 | 숭실대학교(서울) | https://ssu.ac.kr/ | ssu.ac.kr |
| 32 | 서울 | 숭의여자대학교 | 숭의여자대학교 (본교(제1캠퍼스)) | www.sewu.ac.kr | sewu.ac.kr |
| 33 | 서울 | 연세대학교 | 연세대학교(서울) | www.yonsei.ac.kr | yonsei.ac.kr |
| 34 | 서울 | 이화여자대학교 | 이화여자대학교(서울) | https://www.ewhamed.ac.kr/<br>www.ewha.ac.kr | ewha.ac.kr, ewhamed.ac.kr |
| 35 | 서울 | 인덕대학교 | 인덕대학교 (본교(제1캠퍼스)) | www.induk.ac.kr | induk.ac.kr |
| 36 | 서울 | 정석대학 | 정석대학 (본교(제1캠퍼스)) | (비어 있음, 보류) | - |
| 37 | 서울 | 중앙대학교 | 중앙대학교(서울) | www.cau.ac.kr | cau.ac.kr |
| 38 | 서울 | 한국성서대학교 | 한국성서대학교(서울) | www.bible.ac.kr | bible.ac.kr |
| 39 | 서울 | 한국외국어대학교 | 한국외국어대학교(서울) | www.hufs.ac.kr | hufs.ac.kr |
| 40 | 서울 | 한국폴리텍 I 대학 서울정수캠퍼스 | 한국폴리텍대학 서울정수캠퍼스 (본교(제1캠퍼스)) | jungsu.kopo.ac.kr | kopo.ac.kr |
| 41 | 서울 | 한성대학교 | 한성대학교(서울) | www.hansung.ac.kr | hansung.ac.kr |
| 42 | 서울 | 한양대학교 | 한양대학교(서울) | www.hanyang.ac.kr | hanyang.ac.kr |
| 43 | 서울 | 한양여자대학교 | 한양여자대학교 (본교(제1캠퍼스)) | www.hywoman.ac.kr | hywoman.ac.kr |
| 44 | 서울 | 홍익대학교 | 홍익대학교 (본교(제1캠퍼스)) | www.hongik.ac.kr/kr/index.do | hongik.ac.kr |
| 45 | 경기 | 가천대학교 | 가천대학교 (본교(제1캠퍼스)) | www.gachon.ac.kr | gachon.ac.kr |
| 46 | 경기 | 가톨릭대학교 | 가톨릭대학교 (본교(제1캠퍼스)) | www.catholic.ac.kr | catholic.ac.kr |
| 47 | 경기 | 강남대학교 | 강남대학교(용인) | www.kangnam.ac.kr | kangnam.ac.kr |
| 48 | 경기 | 경기과학기술대학교 | 경기과학기술대학교 (본교(제1캠퍼스)) | gtec.ac.kr | gtec.ac.kr |
| 49 | 경기 | 경기대학교 | 경기대학교 (본교(제1캠퍼스)) | www.kyonggi.ac.kr | kyonggi.ac.kr |
| 50 | 경기 | 경동대학교 | 경동대학교 (본교(제4캠퍼스)) | www.kduniv.ac.kr | kduniv.ac.kr |
| 51 | 경기 | 경민대학교 | 경민대학교 (본교(제1캠퍼스)) | www.kyungmin.ac.kr | kyungmin.ac.kr |
| 52 | 경기 | 경복대학교 | 경복대학교 (본교(제1캠퍼스)) | www.kbu.ac.kr | kbu.ac.kr |
| 53 | 경기 | 경인교육대학교 | 경인교육대학교 (본교(제2캠퍼스)) | www.ginue.ac.kr | ginue.ac.kr |
| 54 | 경기 | 경희대학교 | 경희대학교 (본교(제2캠퍼스)) | www.khu.ac.kr | khu.ac.kr |
| 55 | 경기 | 계원예술대학교 | 계원예술대학교 (본교(제1캠퍼스)) | www.kaywon.ac.kr | kaywon.ac.kr |
| 56 | 경기 | 국립한국교통대학교 | 국립한국교통대학교 (본교(제3캠퍼스)) | www.ut.ac.kr | ut.ac.kr |
| 57 | 경기 | 국제대학교 | 국제대학교 (본교(제1캠퍼스)) | www.kookje.ac.kr | kookje.ac.kr |
| 58 | 경기 | 김포대학교 | 김포대학교 (본교(제1캠퍼스)) | https://ukp.ac.kr | ukp.ac.kr |
| 59 | 경기 | 단국대학교 | 단국대학교 (본교(제1캠퍼스)) | www.dankook.ac.kr | dankook.ac.kr |
| 60 | 경기 | 대림대학교 | 대림대학교 (본교(제1캠퍼스)) | www.daelim.ac.kr | daelim.ac.kr |
| 61 | 경기 | 대진대학교 | 대진대학교(포천) | www.daejin.ac.kr | daejin.ac.kr |
| 62 | 경기 | 동남보건대학교 | 동남보건대학교 (본교(제1캠퍼스)) | www.dongnam.ac.kr | dongnam.ac.kr |
| 63 | 경기 | 동서울대학교 | 동서울대학교 (본교(제1캠퍼스)) | www.du.ac.kr | du.ac.kr |
| 64 | 경기 | 동양대학교 | 동양대학교 (본교(제2캠퍼스)) | http://bsc.dyu.ac.kr/ | dyu.ac.kr |
| 65 | 경기 | 동원대학교 | 동원대학교 (본교(제1캠퍼스)) | www.tw.ac.kr | tw.ac.kr |
| 66 | 경기 | 두원공과대학교 | 두원공과대학교 (본교(제1캠퍼스)) | doowon.ac.kr | doowon.ac.kr |
| 67 | 경기 | 명지대학교 | 명지대학교 (본교(제1캠퍼스)) | https://www.mju.ac.kr/ | mju.ac.kr |
| 68 | 경기 | 부천대학교 | 부천대학교 (본교(제1캠퍼스)) | www.bc.ac.kr | bc.ac.kr |
| 69 | 경기 | 서영대학교 | 서영대학교 (본교(제2캠퍼스)) | www.seoyeong.ac.kr | seoyeong.ac.kr |
| 70 | 경기 | 서울신학대학교 | 서울신학대학교(부천) | www.stu.ac.kr | stu.ac.kr |
| 71 | 경기 | 서정대학교 | 서정대학교 (본교(제1캠퍼스)) | www.seojeong.ac.kr | seojeong.ac.kr |
| 72 | 경기 | 성결대학교 | 성결대학교(안양) | www.sungkyul.ac.kr | sungkyul.ac.kr |
| 73 | 경기 | 성균관대학교 | 성균관대학교 (본교(제2캠퍼스)) | http://www.skku.edu | skku.edu |
| 74 | 경기 | 수원과학대학교 | 수원과학대학교 (본교(제1캠퍼스)) | www.ssc.ac.kr | ssc.ac.kr |
| 75 | 경기 | 수원대학교 | 수원대학교(수원) | suwon.ac.kr | suwon.ac.kr |
| 76 | 경기 | 수원여자대학교 | 수원여자대학교 (본교(제1캠퍼스)) | https://www.swwu.ac.kr/swwu.do | swwu.ac.kr |
| 77 | 경기 | 신구대학교 | 신구대학교 (본교(제1캠퍼스)) | www.shingu.ac.kr | shingu.ac.kr |
| 78 | 경기 | 신안산대학교 | 신안산대학교 (본교(제1캠퍼스)) | www.sau.ac.kr | sau.ac.kr |
| 79 | 경기 | 신한대학교 | 신한대학교(의정부) | http://www.shinhan.ac.kr | shinhan.ac.kr |
| 80 | 경기 | 아주대학교 | 아주대학교(수원) | www.ajou.ac.kr | ajou.ac.kr |
| 81 | 경기 | 안산대학교 | 안산대학교 (본교(제1캠퍼스)) | www.ansan.ac.kr | ansan.ac.kr |
| 82 | 경기 | 안양대학교 | 안양대학교(안양) | www.anyang.ac.kr/main.do | anyang.ac.kr |
| 83 | 경기 | 여주대학교 | 여주대학교 (본교(제1캠퍼스)) | www.yit.ac.kr | yit.ac.kr |
| 84 | 경기 | 연성대학교 | 연성대학교 (본교(제1캠퍼스)) | www.yeonsung.ac.kr | yeonsung.ac.kr |
| 85 | 경기 | 예원예술대학교 | 예원예술대학교 (본교(제2캠퍼스)) | www.yewon.ac.kr | yewon.ac.kr |
| 86 | 경기 | 오산대학교 | 오산대학교 (본교(제1캠퍼스)) | www.osan.ac.kr | osan.ac.kr |
| 87 | 경기 | 용인대학교 | 용인대학교(용인) | www.yongin.ac.kr | yongin.ac.kr |
| 88 | 경기 | 용인예술과학대학교 | 용인예술과학대학교 (본교(제1캠퍼스)) | https://www.ysc.ac.kr | ysc.ac.kr |
| 89 | 경기 | 유한대학교 | 유한대학교 (본교(제1캠퍼스)) | www.yuhan.ac.kr | yuhan.ac.kr |
| 90 | 경기 | 을지대학교 | 을지대학교(성남) | www.eulji.ac.kr | eulji.ac.kr |
| 91 | 경기 | 장안대학교 | 장안대학교 (본교(제1캠퍼스)) | www.jangan.ac.kr | jangan.ac.kr |
| 92 | 경기 | 중부대학교 | 중부대학교 (본교(제2캠퍼스)) | https://www.joongbu.ac.kr/ | joongbu.ac.kr |
| 93 | 경기 | 중앙대학교 | 중앙대학교(안성) | www.cau.ac.kr | cau.ac.kr |
| 94 | 경기 | 차의과학대학교 | 차의과학대학교(포천) | www.cha.ac.kr | cha.ac.kr |
| 95 | 경기 | 청강문화산업대학교 | 청강문화산업대학교 (본교(제1캠퍼스)) | www.ck.ac.kr | ck.ac.kr |
| 96 | 경기 | 평택대학교 | 평택대학교(평택) | www.ptu.ac.kr | ptu.ac.kr |
| 97 | 경기 | 한경국립대학교 | 한경국립대학교 (본교(제1캠퍼스)) | www.hknu.ac.kr | hknu.ac.kr |
| 98 | 경기 | 한경국립대학교(평택) | 한경국립대학교 (본교(제2캠퍼스)) | https://pt-hknu.ac.kr | pt-hknu.ac.kr |
| 99 | 경기 | 한국공학대학교 | 한국공학대학교 (본교(제1캠퍼스)) | www.tukorea.ac.kr | tukorea.ac.kr |
| 100 | 경기 | 한국외국어대학교 | 한국외국어대학교 (본교(제2캠퍼스)) | www.hufs.ac.kr/ | hufs.ac.kr |
| 101 | 경기 | 한국폴리텍 II 대학 화성캠퍼스 | 한국폴리텍 II 대학 화성캠퍼스 (본교(제1캠퍼스)) | https://www.kopo.ac.kr/hwaseong/ | kopo.ac.kr |
| 102 | 경기 | 한국항공대학교 | 한국항공대학교(고양) | www.kau.ac.kr | kau.ac.kr |
| 103 | 경기 | 한세대학교 | 한세대학교(군포) | www.hansei.ac.kr | hansei.ac.kr |
| 104 | 경기 | 한신대학교 | 한신대학교(오산) | www.hs.ac.kr | hs.ac.kr |
| 105 | 경기 | 한양대학교(ERICA) | 한양대학교(에리카) | http://www.hanyang.ac.kr/ | hanyang.ac.kr |
| 106 | 경기 | 협성대학교 | 협성대학교(화성) | www.uhs.ac.kr | uhs.ac.kr |
| 107 | 경기 | 화성의과학대학교 | 화성의과학대학교 (본교(제1캠퍼스)) | https://www.hsmu.ac.kr/sgu_main/index.do | hsmu.ac.kr |
| 108 | 인천 | 경인교육대학교 | 경인교육대학교(인천) | www.ginue.ac.kr | ginue.ac.kr |
| 109 | 인천 | 경인여자대학교 | 경인여자대학교 (본교(제1캠퍼스)) | www.kiwu.ac.kr | kiwu.ac.kr |
| 110 | 인천 | 안양대학교 | 안양대학교 (본교(제2캠퍼스)) | www.anyang.ac.kr/main.do | anyang.ac.kr |
| 111 | 인천 | 연세대학교 | 연세대학교 (본교(제2캠퍼스)) | (비어 있음, 보충: www.yonsei.ac.kr) | yonsei.ac.kr |
| 112 | 인천 | 인천대학교 | 인천대학교(인천) | www.inu.ac.kr | inu.ac.kr |
| 113 | 인천 | 인하공업전문대학 | 인하공업전문대학 (본교(제1캠퍼스)) | www.inhatc.ac.kr | inhatc.ac.kr |
| 114 | 인천 | 인하대학교 | 인하대학교 (본교(제1캠퍼스)) | www.inha.ac.kr | inha.ac.kr |
| 115 | 인천 | 재능대학교 | 재능대학교 (본교(제1캠퍼스)) | www.jeiu.ac.kr | jeiu.ac.kr |
| 116 | 인천 | 청운대학교 | 청운대학교 (본교(제2캠퍼스)) | www.chungwoon.ac.kr | chungwoon.ac.kr |
| 117 | 인천 | 한국폴리텍 II 대학 인천캠퍼스 | 한국폴리텍대학 인천캠퍼스 (본교(제1캠퍼스)) | www.kopo.ac.kr/incheon/index.do | kopo.ac.kr |
| 118 | 강원 | 가톨릭관동대학교 | 가톨릭관동대학교 (본교(제1캠퍼스)) | https://www.cku.ac.kr/sites/cku_kr/index.do | cku.ac.kr |
| 119 | 강원 | 강릉영동대학교 | 강릉영동대학교 (본교(제1캠퍼스)) | www.gyu.ac.kr | gyu.ac.kr |
| 120 | 강원 | 강원대학교 | 강원대학교(춘천) | www.kangwon.ac.kr/ | kangwon.ac.kr |
| 121 | 강원 | 강원도립대학교 | 강원도립대학교 (본교(제1캠퍼스)) | https://www.gw.ac.kr/po/portal | gw.ac.kr |
| 122 | 강원 | 경동대학교 | 경동대학교 (본교(제1캠퍼스)) | www.kduniv.ac.kr | kduniv.ac.kr |
| 123 | 강원 | 상지대학교 | 상지대학교(원주) | www.sangji.ac.kr | sangji.ac.kr |
| 124 | 강원 | 세경대학교 | 세경대학교 (본교(제1캠퍼스)) | www.saekyung.ac.kr | saekyung.ac.kr |
| 125 | 강원 | 송곡대학교 | 송곡대학교 (본교(제1캠퍼스)) | www.songgok.ac.kr | songgok.ac.kr |
| 126 | 강원 | 송호대학교 | 송호대학교 (본교(제1캠퍼스)) | www.songho.ac.kr | songho.ac.kr |
| 127 | 강원 | 연세대학교(미래) | 연세대학교(원주) | www.yonsei.ac.kr | yonsei.ac.kr |
| 128 | 강원 | 춘천교육대학교 | 춘천교육대학교(춘천) | www.cnue.ac.kr | cnue.ac.kr |
| 129 | 강원 | 한국골프과학기술대학교 | 한국골프과학기술대학교 (본교(제1캠퍼스)) | http://www.kg.ac.kr/ | kg.ac.kr |
| 130 | 강원 | 한국폴리텍 III 대학 원주캠퍼스 | 한국폴리텍 III 대학 원주캠퍼스 (본교(제1캠퍼스)) | www.kopo.ac.kr/wonju | kopo.ac.kr |
| 131 | 강원 | 한라대학교 | 한라대학교(원주) | www.halla.ac.kr | halla.ac.kr |
| 132 | 강원 | 한림대학교 | 한림대학교(춘천) | www.hallym.ac.kr | hallym.ac.kr |
| 133 | 강원 | 한림성심대학교 | 한림성심대학교 (본교(제1캠퍼스)) | http://www.hsc.ac.kr | hsc.ac.kr |
| 134 | 충청 | 강동대학교 | 강동대학교 (본교(제1캠퍼스)) | www.gangdong.ac.kr | gangdong.ac.kr |
| 135 | 충청 | 건국대학교(글로컬) | 건국대학교(글로컬) | www.kku.ac.kr | kku.ac.kr |
| 136 | 충청 | 건양대학교 | 건양대학교(논산) | www.konyang.ac.kr | konyang.ac.kr |
| 137 | 충청 | 고려대학교(세종) | 고려대학교(세종) | www.korea.ac.kr | korea.ac.kr |
| 138 | 충청 | 공주교육대학교 | 공주교육대학교(공주) | www.gjue.ac.kr | gjue.ac.kr |
| 139 | 충청 | 국립공주대학교 | 국립공주대학교 (본교(제2캠퍼스)) | https://brain.kongju.ac.kr/sites/ZD0000/index.do | kongju.ac.kr |
| 140 | 충청 | 국립한국교통대학교 | 국립한국교통대학교 (본교(제1캠퍼스)) | http://www.ut.ac.kr | ut.ac.kr |
| 141 | 충청 | 국립한밭대학교 | 국립한밭대학교 (본교(제1캠퍼스)) | www.hanbat.ac.kr | hanbat.ac.kr |
| 142 | 충청 | 극동대학교 | 극동대학교(음성) | www.kdu.ac.kr | kdu.ac.kr |
| 143 | 충청 | 금강대학교 | 금강대학교(논산) | www.ggu.ac.kr | ggu.ac.kr |
| 144 | 충청 | 나사렛대학교 | 나사렛대학교 (본교(제1캠퍼스)) | www.kornu.ac.kr | kornu.ac.kr |
| 145 | 충청 | 남서울대학교 | 남서울대학교(천안) | http://www.nsu.ac.kr | nsu.ac.kr |
| 146 | 충청 | 단국대학교 | 단국대학교 (본교(제2캠퍼스)) | www.dankook.ac.kr | dankook.ac.kr |
| 147 | 충청 | 대덕대학교 | 대덕대학교 (본교(제1캠퍼스)) | https://www.ddu.ac.kr | ddu.ac.kr |
| 148 | 충청 | 대원대학교 | 대원대학교 (본교(제1캠퍼스)) | www.daewon.ac.kr | daewon.ac.kr |
| 149 | 충청 | 대전과학기술대학교 | 대전과학기술대학교 (본교(제1캠퍼스)) | www.dst.ac.kr | dst.ac.kr |
| 150 | 충청 | 대전대학교 | 대전대학교(대전) | www.dju.ac.kr | dju.ac.kr |
| 151 | 충청 | 대전보건대학교 | 대전보건대학교 (본교(제1캠퍼스)) | www.hit.ac.kr | hit.ac.kr |
| 152 | 충청 | 목원대학교 | 목원대학교 (본교(제1캠퍼스)) | www.mokwon.ac.kr | mokwon.ac.kr |
| 153 | 충청 | 배재대학교 | 배재대학교(대전) | www.pcu.ac.kr | pcu.ac.kr |
| 154 | 충청 | 백석대학교 | 백석대학교(천안) | https://www.bu.ac.kr | bu.ac.kr |
| 155 | 충청 | 백석문화대학교 | 백석문화대학교 (본교(제1캠퍼스)) | www.bscu.ac.kr | bscu.ac.kr |
| 156 | 충청 | 상명대학교 | 상명대학교(천안) | www.smuc.ac.kr | smuc.ac.kr |
| 157 | 충청 | 서원대학교 | 서원대학교(청주) | www.seowon.ac.kr | seowon.ac.kr |
| 158 | 충청 | 선문대학교 | 선문대학교(아산) | www.sunmoon.ac.kr | sunmoon.ac.kr |
| 159 | 충청 | 세명대학교 | 세명대학교(제천) | http://www.semyung.ac.kr | semyung.ac.kr |
| 160 | 충청 | 세한대학교 | 세한대학교 (본교(제2캠퍼스)) | www.sehan.ac.kr | sehan.ac.kr |
| 161 | 충청 | 순천향대학교 | 순천향대학교(아산) | https://med.sch.ac.kr/<br>www.sch.ac.kr | sch.ac.kr |
| 162 | 충청 | 신성대학교 | 신성대학교 (본교(제1캠퍼스)) | www.shinsung.ac.kr | shinsung.ac.kr |
| 163 | 충청 | 아주자동차대학교 | 아주자동차대학교 (본교(제1캠퍼스)) | https://www.motor.ac.kr | motor.ac.kr |
| 164 | 충청 | 우석대학교 | 우석대학교 (본교(제2캠퍼스)) | https://jc.woosuk.ac.kr/ | woosuk.ac.kr |
| 165 | 충청 | 우송대학교 | 우송대학교(대전) | www.wsu.ac.kr | wsu.ac.kr |
| 166 | 충청 | 우송정보대학 | 우송정보대학 (본교(제1캠퍼스)) | http://www.wsi.ac.kr | wsi.ac.kr |
| 167 | 충청 | 유원대학교 | 유원대학교 (본교(제2캠퍼스)) | www.u1.ac.kr | u1.ac.kr |
| 168 | 충청 | 중부대학교 | 중부대학교 (본교(제1캠퍼스)) | www.joongbu.ac.kr | joongbu.ac.kr |
| 169 | 충청 | 중원대학교 | 중원대학교(괴산) | www.jwu.ac.kr | jwu.ac.kr |
| 170 | 충청 | 청운대학교 | 청운대학교(홍성) | www.chungwoon.ac.kr | chungwoon.ac.kr |
| 171 | 충청 | 청주교육대학교 | 청주교육대학교(청주) | www.cje.ac.kr | cje.ac.kr |
| 172 | 충청 | 청주대학교 | 청주대학교(청주) | www.cju.ac.kr | cju.ac.kr |
| 173 | 충청 | 충남대학교 | 충남대학교(대전) | http://www.cnu.ac.kr | cnu.ac.kr |
| 174 | 충청 | 충남도립대학교 | 충남도립대학교 (본교(제1캠퍼스)) | www.cnsu.ac.kr | cnsu.ac.kr |
| 175 | 충청 | 충북대학교 | 충북대학교(청주) | www.chungbuk.ac.kr | chungbuk.ac.kr |
| 176 | 충청 | 충북보건과학대학교 | 충북보건과학대학교 (본교(제1캠퍼스)) | www.chsu.ac.kr | chsu.ac.kr |
| 177 | 충청 | 충청대학교 | 충청대학교 (본교(제1캠퍼스)) | www.ok.ac.kr | ok.ac.kr |
| 178 | 충청 | 한국과학기술원 | 한국과학기술원 (본교(제1캠퍼스)) | www.kaist.ac.kr | kaist.ac.kr |
| 179 | 충청 | 한국교원대학교 | 한국교원대학교(청원) | https://www.knue.ac.kr/ | knue.ac.kr |
| 180 | 충청 | 한국기술교육대학교 | 한국기술교육대학교(천안) | www.koreatech.ac.kr | koreatech.ac.kr |
| 181 | 충청 | 한국영상대학교 | 한국영상대학교 (본교(제1캠퍼스)) | www.pro.ac.kr | pro.ac.kr |
| 182 | 충청 | 한국폴리텍 IV 대학 아산캠퍼스 | 한국폴리텍 IV 대학 아산캠퍼스 (본교(제1캠퍼스)) | http://www.kopo.ac.kr/asan | kopo.ac.kr |
| 183 | 충청 | 한남대학교 | 한남대학교(대전) | www.hannam.ac.kr | hannam.ac.kr |
| 184 | 충청 | 한서대학교 | 한서대학교(서산) | www.hanseo.ac.kr | hanseo.ac.kr |
| 185 | 충청 | 혜전대학교 | 혜전대학교 (본교(제1캠퍼스)) | www.hj.ac.kr | hj.ac.kr |
| 186 | 충청 | 호서대학교 | 호서대학교(아산) | www.hoseo.ac.kr<br>www.hoseo.ac.rk | hoseo.ac.kr (제외: ac.rk — KEDI 표기 오타 의심) |
| 187 | 충청 | 홍익대학교 | 홍익대학교 세종캠퍼스 (본교(제2캠퍼스)) | http://sejong.hongik.ac.kr/index.do | hongik.ac.kr |
| 188 | 호남 | 광양보건대학교 | 광양보건대학교 (본교(제1캠퍼스)) | www.gy.ac.kr | gy.ac.kr |
| 189 | 호남 | 광주과학기술원 | 광주과학기술원(GIST) | www.gist.ac.kr | gist.ac.kr |
| 190 | 호남 | 광주교육대학교 | 광주교육대학교(광주) | www.gnue.ac.kr | gnue.ac.kr |
| 191 | 호남 | 광주대학교 | 광주대학교(광주) | http://www.gwangju.ac.kr | gwangju.ac.kr |
| 192 | 호남 | 광주여자대학교 | 광주여자대학교 (본교(제1캠퍼스)) | www.kwu.ac.kr | kwu.ac.kr |
| 193 | 호남 | 국립군산대학교 | 국립군산대학교 (본교(제1캠퍼스)) | www.kunsan.ac.kr/index.kunsan | kunsan.ac.kr |
| 194 | 호남 | 국립목포대학교 | 국립목포대학교 (본교(제1캠퍼스)) | www.mokpo.ac.kr | mokpo.ac.kr |
| 195 | 호남 | 국립목포해양대학교 | 국립목포해양대학교 (본교(제1캠퍼스)) | (비어 있음, 보충: http://www.mmu.ac.kr/) | mmu.ac.kr |
| 196 | 호남 | 국립순천대학교 | 국립순천대학교 (본교(제1캠퍼스)) | www.sunchon.ac.kr | sunchon.ac.kr |
| 197 | 호남 | 군장대학교 | 군장대학교 (본교(제1캠퍼스)) | www.kunjang.ac.kr | kunjang.ac.kr |
| 198 | 호남 | 남부대학교 | 남부대학교(광주) | www.nambu.ac.kr | nambu.ac.kr |
| 199 | 호남 | 동강대학교 | 동강대학교 (본교(제1캠퍼스)) | www.dkc.ac.kr | dkc.ac.kr |
| 200 | 호남 | 동신대학교 | 동신대학교 (본교(제1캠퍼스)) | www.dsu.ac.kr | dsu.ac.kr |
| 201 | 호남 | 목포과학대학교 | 목포과학대학교 (본교(제1캠퍼스)) | http://www.msu.ac.kr | msu.ac.kr |
| 202 | 호남 | 서영대학교 | 서영대학교 (본교(제1캠퍼스)) | www.seoyeong.ac.kr | seoyeong.ac.kr |
| 203 | 호남 | 세한대학교 | 세한대학교(영암) | www.sehan.ac.kr | sehan.ac.kr |
| 204 | 호남 | 송원대학교 | 송원대학교(광주) | www.songwon.ac.kr | songwon.ac.kr |
| 205 | 호남 | 순천제일대학교 | 순천제일대학교 (본교(제1캠퍼스)) | www.suncheon.ac.kr | suncheon.ac.kr |
| 206 | 호남 | 예원예술대학교 | 예원예술대학교(임실) | www.yewon.ac.kr | yewon.ac.kr |
| 207 | 호남 | 우석대학교 | 우석대학교(완주) | www.woosuk.ac.kr | woosuk.ac.kr |
| 208 | 호남 | 원광대학교 | 원광대학교(익산) | www.wku.ac.kr | wku.ac.kr |
| 209 | 호남 | 전남과학대학교 | 전남과학대학교 (본교(제1캠퍼스)) | www.cntu.ac.kr | cntu.ac.kr |
| 210 | 호남 | 전남대학교 | 전남대학교 (본교(제1캠퍼스)) | http://www.jnu.ac.kr | jnu.ac.kr |
| 211 | 호남 | 전북과학대학교 | 전북과학대학교 (본교(제1캠퍼스)) | www.jbsc.ac.kr | jbsc.ac.kr |
| 212 | 호남 | 전북대학교 | 전북대학교(전주) | www.jbnu.ac.kr | jbnu.ac.kr |
| 213 | 호남 | 전주교육대학교 | 전주교육대학교(전주) | WWW.JNUE.KR | jnue.kr |
| 214 | 호남 | 전주기전대학 | 전주기전대학 (본교(제1캠퍼스)) | www.kijeon.ac.kr | kijeon.ac.kr |
| 215 | 호남 | 전주대학교 | 전주대학교(전주) | www.jj.ac.kr | jj.ac.kr |
| 216 | 호남 | 전주비전대학교 | 전주비전대학교 (본교(제1캠퍼스)) | www.jvision.ac.kr | jvision.ac.kr |
| 217 | 호남 | 조선대학교 | 조선대학교 (본교(제1캠퍼스)) | https://www.chosun.ac.kr | chosun.ac.kr |
| 218 | 호남 | 조선이공대학교 | 조선이공대학교 (본교(제1캠퍼스)) | www.cst.ac.kr | cst.ac.kr |
| 219 | 호남 | 청암대학교 | 청암대학교 (본교(제1캠퍼스)) | http://ca.ac.kr | ca.ac.kr |
| 220 | 호남 | 한일장신대학교 | 한일장신대학교(완주) | www.hanil.ac.kr | hanil.ac.kr |
| 221 | 호남 | 호남대학교 | 호남대학교 (본교(제1캠퍼스)) | www.honam.ac.kr | honam.ac.kr |
| 222 | 호남 | 호원대학교 | 호원대학교(군산) | www.howon.ac.kr | howon.ac.kr |
| 223 | 영남 | 가톨릭상지대학교 | 가톨릭상지대학교 (본교(제1캠퍼스)) | www.csj.ac.kr | csj.ac.kr |
| 224 | 영남 | 거제대학교 | 거제대학교 (본교(제1캠퍼스)) | www.koje.ac.kr | koje.ac.kr |
| 225 | 영남 | 경남대학교 | 경남대학교(마산) | www.kyungnam.ac.kr | kyungnam.ac.kr |
| 226 | 영남 | 경남정보대학교 | 경남정보대학교 (본교(제1캠퍼스)) | www.kit.ac.kr | kit.ac.kr |
| 227 | 영남 | 경북대학교 | 경북대학교(대구) | www.knu.ac.kr | knu.ac.kr |
| 228 | 영남 | 경북보건대학교 | 경북보건대학교 (본교(제1캠퍼스)) | www.gch.ac.kr | gch.ac.kr |
| 229 | 영남 | 경북전문대학교 | 경북전문대학교 (본교(제1캠퍼스)) | https://www.kbc.ac.kr/ | kbc.ac.kr |
| 230 | 영남 | 경상국립대학교 | 경상국립대학교 (본교(제1캠퍼스)) | https://www.gnu.ac.kr/main/main.do | gnu.ac.kr |
| 231 | 영남 | 경성대학교 | 경성대학교 (본교(제1캠퍼스)) | https://kscms.ks.ac.kr/kor/Main.do | ks.ac.kr |
| 232 | 영남 | 경운대학교 | 경운대학교 (본교(제1캠퍼스)) | www.ikw.ac.kr | ikw.ac.kr |
| 233 | 영남 | 경일대학교 | 경일대학교(경산) | www.kiu.ac.kr | kiu.ac.kr |
| 234 | 영남 | 계명대학교 | 계명대학교(대구) | www.kmu.ac.kr | kmu.ac.kr |
| 235 | 영남 | 계명문화대학교 | 계명문화대학교 (본교(제1캠퍼스)) | www.kmcu.ac.kr | kmcu.ac.kr |
| 236 | 영남 | 고신대학교 | 고신대학교(부산) | https://www.kucm.ac.kr/<br>www.kosin.ac.kr | kosin.ac.kr, kucm.ac.kr |
| 237 | 영남 | 구미대학교 | 구미대학교 (본교(제1캠퍼스)) | www.gumi.ac.kr | gumi.ac.kr |
| 238 | 영남 | 국립경국대학교 | 국립경국대학교 (본교(제1캠퍼스)) | https://www.gknu.ac.kr/main/index.do | gknu.ac.kr |
| 239 | 영남 | 국립금오공과대학교 | 국립금오공과대학교 (본교(제1캠퍼스)) | www.kumoh.ac.kr | kumoh.ac.kr |
| 240 | 영남 | 국립부경대학교 | 국립부경대학교 (본교(제1캠퍼스)) | www.pknu.ac.kr | pknu.ac.kr |
| 241 | 영남 | 국립창원대학교 | 국립창원대학교 (본교(제1캠퍼스)) | www.changwon.ac.kr | changwon.ac.kr |
| 242 | 영남 | 국립한국해양대학교 | 국립한국해양대학교 (본교(제1캠퍼스)) | www.kmou.ac.kr/kmou/main.do | kmou.ac.kr |
| 243 | 영남 | 김천대학교 | 김천대학교(김천) | www.gimcheon.ac.kr | gimcheon.ac.kr |
| 244 | 영남 | 김해대학교 | 김해대학교 (본교(제1캠퍼스)) | www.gimhae.ac.kr | gimhae.ac.kr |
| 245 | 영남 | 대경대학교 | 대경대학교 (본교(제1캠퍼스)) | www.tk.ac.kr | tk.ac.kr |
| 246 | 영남 | 대구가톨릭대학교 | 대구가톨릭대학교(경산) | http://www.cu.ac.kr/ | cu.ac.kr |
| 247 | 영남 | 대구과학대학교 | 대구과학대학교 (본교(제1캠퍼스)) | www.tsu.ac.kr | tsu.ac.kr |
| 248 | 영남 | 대구교육대학교 | 대구교육대학교(대구) | http://www.dnue.ac.kr | dnue.ac.kr |
| 249 | 영남 | 대구대학교 | 대구대학교(경산) | www.daegu.ac.kr | daegu.ac.kr |
| 250 | 영남 | 대구보건대학교 | 대구보건대학교 (본교(제1캠퍼스)) | www.dhc.ac.kr | dhc.ac.kr |
| 251 | 영남 | 대구예술대학교 | 대구예술대학교(칠곡) | www.dgau.ac.kr | dgau.ac.kr |
| 252 | 영남 | 대구한의대학교 | 대구한의대학교(경산) | www.dhu.ac.kr | dhu.ac.kr |
| 253 | 영남 | 동국대학교(WISE) | 동국대학교(경주) | web.dongguk.ac.kr | dongguk.ac.kr |
| 254 | 영남 | 동명대학교 | 동명대학교(부산) | www.tu.ac.kr | tu.ac.kr |
| 255 | 영남 | 동서대학교 | 동서대학교(부산) | https://www.dongseo.ac.kr<br>https://www.dongseo.ac.kr/ | dongseo.ac.kr |
| 256 | 영남 | 동아대학교 | 동아대학교(부산) | www.donga.ac.kr | donga.ac.kr |
| 257 | 영남 | 동양대학교 | 동양대학교(영주) | www.dyu.ac.kr | dyu.ac.kr |
| 258 | 영남 | 동원과학기술대학교 | 동원과학기술대학교 (본교(제1캠퍼스)) | www.dist.ac.kr | dist.ac.kr |
| 259 | 영남 | 동의과학대학교 | 동의과학대학교 (본교(제1캠퍼스)) | www.dit.ac.kr | dit.ac.kr |
| 260 | 영남 | 동의대학교 | 동의대학교(부산) | www.deu.ac.kr | deu.ac.kr |
| 261 | 영남 | 마산대학교 | 마산대학교 (본교(제1캠퍼스)) | www.masan.ac.kr | masan.ac.kr |
| 262 | 영남 | 부산가톨릭대학교 | 부산가톨릭대학교 (본교(제1캠퍼스)) | www.cup.ac.kr | cup.ac.kr |
| 263 | 영남 | 부산경상대학교 | 부산경상대학교 (본교(제1캠퍼스)) | www.bsks.ac.kr | bsks.ac.kr |
| 264 | 영남 | 부산과학기술대학교 | 부산과학기술대학교 (본교(제1캠퍼스)) | bist.ac.kr | bist.ac.kr |
| 265 | 영남 | 부산교육대학교 | 부산교육대학교(부산) | www.bnue.ac.kr | bnue.ac.kr |
| 266 | 영남 | 부산대학교 | 부산대학교(부산) | www.pusan.ac.kr | pusan.ac.kr |
| 267 | 영남 | 부산보건대학교 | 부산보건대학교 (본교(제1캠퍼스)) | www.bhu.ac.kr | bhu.ac.kr |
| 268 | 영남 | 부산외국어대학교 | 부산외국어대학교(부산) | www.bufs.ac.kr | bufs.ac.kr |
| 269 | 영남 | 선린대학교 | 선린대학교 (본교(제1캠퍼스)) | https://www.sunlin.ac.kr | sunlin.ac.kr |
| 270 | 영남 | 성운대학교 | 성운대학교 (본교(제1캠퍼스)) | www.sw.ac.kr | sw.ac.kr |
| 271 | 영남 | 수성대학교 | 수성대학교 (본교(제1캠퍼스)) | www.sc.ac.kr | sc.ac.kr |
| 272 | 영남 | 신경주대학교 | 신경주대학교 (본교(제1캠퍼스)) | www.gu.ac.kr | gu.ac.kr |
| 273 | 영남 | 신라대학교 | 신라대학교(부산) | www.silla.ac.kr | silla.ac.kr |
| 274 | 영남 | 안동과학대학교 | 안동과학대학교 (본교(제1캠퍼스)) | www.asc.ac.kr | asc.ac.kr |
| 275 | 영남 | 연암공과대학교 | 연암공과대학교 (본교(제1캠퍼스)) | http://www.yc.ac.kr | yc.ac.kr |
| 276 | 영남 | 영남대학교 | 영남대학교(경산) | www.yu.ac.kr | yu.ac.kr |
| 277 | 영남 | 영남이공대학교 | 영남이공대학교 (본교(제1캠퍼스)) | www.ync.ac.kr | ync.ac.kr |
| 278 | 영남 | 영산대학교(양산) | 영산대학교(양산) | www.ysu.ac.kr | ysu.ac.kr |
| 279 | 영남 | 영산대학교(해운대) | 영산대학교 (본교(제1캠퍼스)) | www.ysu.ac.kr | ysu.ac.kr |
| 280 | 영남 | 영진전문대학교 | 영진전문대학교 (본교(제1캠퍼스)) | www.yju.ac.kr | yju.ac.kr |
| 281 | 영남 | 울산과학기술원 | 울산과학기술원(UNIST) | www.unist.ac.kr | unist.ac.kr |
| 282 | 영남 | 울산과학대학교 | 울산과학대학교 (본교(제1캠퍼스)) | www.uc.ac.kr | uc.ac.kr |
| 283 | 영남 | 울산대학교 | 울산대학교(울산) | www.ulsan.ac.kr | ulsan.ac.kr |
| 284 | 영남 | 위덕대학교 | 위덕대학교(경주) | www.uu.ac.kr | uu.ac.kr |
| 285 | 영남 | 인제대학교 | 인제대학교(김해) | www.inje.ac.kr | inje.ac.kr |
| 286 | 영남 | 진주교육대학교 | 진주교육대학교 (본교(제1캠퍼스)) | www.cue.ac.kr | cue.ac.kr |
| 287 | 영남 | 창신대학교 | 창신대학교(창원) | www.cs.ac.kr | cs.ac.kr |
| 288 | 영남 | 창원문성대학교 | 창원문성대학교 (본교(제1캠퍼스)) | http://www.cmu.ac.kr | cmu.ac.kr |
| 289 | 영남 | 포항공과대학교 | 포항공과대학교 (본교(제1캠퍼스)) | www.postech.ac.kr | postech.ac.kr |
| 290 | 영남 | 포항대학교 | 포항대학교 (본교(제1캠퍼스)) | www.pohang.ac.kr | pohang.ac.kr |
| 291 | 영남 | 한국폴리텍 VI 대학 영주캠퍼스 | 한국폴리텍 Ⅵ 대학 영주캠퍼스 (본교(제1캠퍼스)) | www.kopo.ac.kr/yeongju/index.do | kopo.ac.kr |
| 292 | 영남 | 한국폴리텍 VII 대학 부산캠퍼스 | 한국폴리텍Ⅶ대학 부산캠퍼스 (본교(제1캠퍼스)) | http://www.kopo.ac.kr/busan | kopo.ac.kr |
| 293 | 영남 | 한국폴리텍 VII 대학 창원캠퍼스 | 한국폴리텍VII대학 창원캠퍼스 (본교(제1캠퍼스)) | http://www.kopo.ac.kr/changwon/index.do | kopo.ac.kr |
| 294 | 영남 | 한국폴리텍 특성화대학 로봇캠퍼스 | 한국폴리텍 특성화대학 로봇캠퍼스 (본교(제1캠퍼스)) | https://www.kopo.ac.kr/robot/index.do | kopo.ac.kr |
| 295 | 영남 | 한동대학교 | 한동대학교(포항) | www.handong.edu | handong.edu |
| 296 | 영남 | 호산대학교 | 호산대학교 (본교(제1캠퍼스)) | www.hosan.ac.kr | hosan.ac.kr |
| 297 | 제주 | 제주관광대학교 | 제주관광대학교 (본교(제1캠퍼스)) | www.jtu.ac.kr | jtu.ac.kr |
| 298 | 제주 | 제주국제대학교 | 제주국제대학교(제주) | www.jeju.ac.kr | jeju.ac.kr |
| 299 | 제주 | 제주대학교 | 제주대학교(제주) | www.jejunu.ac.kr | jejunu.ac.kr |
| 300 | 제주 | 제주한라대학교 | 제주한라대학교 (본교(제1캠퍼스)) | www.chu.ac.kr | chu.ac.kr |
| 301 | 제주 | 한국폴리텍 I 대학 제주캠퍼스 | 한국폴리텍 I 대학 제주캠퍼스 (본교(제1캠퍼스)) | www.kopo.ac.kr/jeju/index.do | kopo.ac.kr |

## 2. KEDI 홈페이지 주소가 비어 있는 행 (3)

KEDI 값이 없어 다른 자료로 보충한 행과 보류한 행. 보충 도메인은 5장 전체 목록에 포함됨.

- 서울 / 정석대학 / 정석대학 (본교(제1캠퍼스)): 보류(허용 도메인 없음) — 출처: KEDI·경남교육청 CSV·API 수집본(홈페이지 필드 없음)·univ_coords.json 어디에도 값 없음 / 보류 (사용자 결정 #0929-01-A: 없으면 비워 두고 보류)
- 인천 / 연세대학교 / 연세대학교 (본교(제2캠퍼스)): 보충 도메인 yonsei.ac.kr — 출처: KEDI 같은 학교 행(연세대학교 본교(제1캠퍼스), 서울)의 홈페이지 값 / 사용자 결정 #0929-01-A: 같은 학교의 KEDI 도메인 yonsei.ac.kr 사용
- 호남 / 국립목포해양대학교 / 국립목포해양대학교 (본교(제1캠퍼스)): 보충 도메인 mmu.ac.kr — 출처: 경상남도교육청_대학정보_20250918.csv '목포해양대학교(목포)' 행 홈페이지 열 (학교명에 '국립' 없음) / 사용자 결정 #0929-01-A: 폴더 안 다른 공식 자료 값 사용

## 3. 한 행에 도메인이 둘 이상인 행 (2)

- 서울 / 이화여자대학교: https://www.ewhamed.ac.kr/, www.ewha.ac.kr
- 영남 / 고신대학교: https://www.kucm.ac.kr/, www.kosin.ac.kr

## 4. 같은 대학인데 캠퍼스(행)별 도메인이 다른 경우 (6)

- 건국대학교: kku.ac.kr, konkuk.ac.kr
- 고신대학교: kosin.ac.kr, kucm.ac.kr
- 동국대학교: dongguk.ac.kr, dongguk.edu
- 상명대학교: smu.ac.kr, smuc.ac.kr
- 이화여자대학교: ewha.ac.kr, ewhamed.ac.kr
- 한경국립대학교: hknu.ac.kr, pt-hknu.ac.kr

## 4-1. 허용 목록에서 뺀 도메인 (1행)

최상위 도메인이 kr·com·net·org·edu가 아닌 값. KEDI 원본 표기 그대로 두고 허용 목록에만 넣지 않음.

- 충청 / 호서대학교: www.hoseo.ac.kr, www.hoseo.ac.rk -> ac.rk

## 5. 허용 도메인 전체 (중복 제거, 272개)

- ajou.ac.kr
- ansan.ac.kr
- anyang.ac.kr
- asc.ac.kr
- baewha.ac.kr
- bc.ac.kr
- bhu.ac.kr
- bible.ac.kr
- bist.ac.kr
- bnue.ac.kr
- bscu.ac.kr
- bsks.ac.kr
- bu.ac.kr
- bufs.ac.kr
- ca.ac.kr
- catholic.ac.kr
- cau.ac.kr
- cha.ac.kr
- changwon.ac.kr
- chosun.ac.kr
- chsu.ac.kr
- chu.ac.kr
- chungbuk.ac.kr
- chungwoon.ac.kr
- cje.ac.kr
- cju.ac.kr
- ck.ac.kr
- cku.ac.kr
- cmu.ac.kr
- cnsu.ac.kr
- cntu.ac.kr
- cnu.ac.kr
- cnue.ac.kr
- cs.ac.kr
- csj.ac.kr
- cst.ac.kr
- cu.ac.kr
- cue.ac.kr
- cup.ac.kr
- daegu.ac.kr
- daejin.ac.kr
- daelim.ac.kr
- daewon.ac.kr
- dankook.ac.kr
- ddu.ac.kr
- deu.ac.kr
- dgau.ac.kr
- dhc.ac.kr
- dhu.ac.kr
- dist.ac.kr
- dit.ac.kr
- dju.ac.kr
- dkc.ac.kr
- dnue.ac.kr
- donga.ac.kr
- dongduk.ac.kr
- dongguk.ac.kr
- dongguk.edu
- dongnam.ac.kr
- dongseo.ac.kr
- dongyang.ac.kr
- doowon.ac.kr
- dst.ac.kr
- dsu.ac.kr
- du.ac.kr
- duksung.ac.kr
- dyu.ac.kr
- eulji.ac.kr
- ewha.ac.kr
- ewhamed.ac.kr
- gachon.ac.kr
- gangdong.ac.kr
- gangseo.ac.kr
- gch.ac.kr
- ggu.ac.kr
- gimcheon.ac.kr
- gimhae.ac.kr
- ginue.ac.kr
- gist.ac.kr
- gjue.ac.kr
- gknu.ac.kr
- gnu.ac.kr
- gnue.ac.kr
- gokmu.ac.kr
- gtec.ac.kr
- gu.ac.kr
- gumi.ac.kr
- gw.ac.kr
- gwangju.ac.kr
- gy.ac.kr
- gyu.ac.kr
- halla.ac.kr
- hallym.ac.kr
- hanbat.ac.kr
- handong.edu
- hanil.ac.kr
- hannam.ac.kr
- hansei.ac.kr
- hanseo.ac.kr
- hansung.ac.kr
- hanyang.ac.kr
- hit.ac.kr
- hj.ac.kr
- hknu.ac.kr
- honam.ac.kr
- hongik.ac.kr
- hosan.ac.kr
- hoseo.ac.kr
- howon.ac.kr
- hs.ac.kr
- hsc.ac.kr
- hsmu.ac.kr
- hufs.ac.kr
- hywoman.ac.kr
- iajou.ac.kr
- ikw.ac.kr
- induk.ac.kr
- inha.ac.kr
- inhatc.ac.kr
- inje.ac.kr
- inu.ac.kr
- jangan.ac.kr
- jbnu.ac.kr
- jbsc.ac.kr
- jeiu.ac.kr
- jeju.ac.kr
- jejunu.ac.kr
- jj.ac.kr
- jnu.ac.kr
- jnue.kr
- joongbu.ac.kr
- jtu.ac.kr
- jvision.ac.kr
- jwu.ac.kr
- kaist.ac.kr
- kangnam.ac.kr
- kangwon.ac.kr
- kau.ac.kr
- kaywon.ac.kr
- kbc.ac.kr
- kbu.ac.kr
- kdu.ac.kr
- kduniv.ac.kr
- kg.ac.kr
- khu.ac.kr
- kijeon.ac.kr
- kit.ac.kr
- kiu.ac.kr
- kiwu.ac.kr
- kku.ac.kr
- kmcu.ac.kr
- kmou.ac.kr
- kmu.ac.kr
- knu.ac.kr
- knue.ac.kr
- koje.ac.kr
- kongju.ac.kr
- konkuk.ac.kr
- konyang.ac.kr
- kookje.ac.kr
- kookmin.ac.kr
- kopo.ac.kr
- korea.ac.kr
- koreatech.ac.kr
- kornu.ac.kr
- kosin.ac.kr
- ks.ac.kr
- kucm.ac.kr
- kumoh.ac.kr
- kunjang.ac.kr
- kunsan.ac.kr
- kw.ac.kr
- kwu.ac.kr
- kyonggi.ac.kr
- kyungmin.ac.kr
- kyungnam.ac.kr
- masan.ac.kr
- mjc.ac.kr
- mju.ac.kr
- mmu.ac.kr
- mokpo.ac.kr
- mokwon.ac.kr
- motor.ac.kr
- msu.ac.kr
- nambu.ac.kr
- namseoul.net
- nsu.ac.kr
- ok.ac.kr
- osan.ac.kr
- pcu.ac.kr
- pknu.ac.kr
- pohang.ac.kr
- postech.ac.kr
- pro.ac.kr
- pt-hknu.ac.kr
- ptu.ac.kr
- pusan.ac.kr
- saekyung.ac.kr
- sangji.ac.kr
- sau.ac.kr
- sc.ac.kr
- sch.ac.kr
- scu.ac.kr
- sehan.ac.kr
- sejong.ac.kr
- semyung.ac.kr
- seoil.ac.kr
- seojeong.ac.kr
- seoultech.ac.kr
- seowon.ac.kr
- seoyeong.ac.kr
- sewu.ac.kr
- shingu.ac.kr
- shinhan.ac.kr
- shinsung.ac.kr
- silla.ac.kr
- skhu.ac.kr
- skku.edu
- skuniv.ac.kr
- smu.ac.kr
- smuc.ac.kr
- snu.ac.kr
- snue.ac.kr
- sogang.ac.kr
- songgok.ac.kr
- songho.ac.kr
- songwon.ac.kr
- sookmyung.ac.kr
- ssc.ac.kr
- ssu.ac.kr
- stu.ac.kr
- suncheon.ac.kr
- sunchon.ac.kr
- sungkyul.ac.kr
- sungshin.ac.kr
- sunlin.ac.kr
- sunmoon.ac.kr
- suwon.ac.kr
- sw.ac.kr
- swu.ac.kr
- swwu.ac.kr
- syu.ac.kr
- tk.ac.kr
- tsu.ac.kr
- tu.ac.kr
- tukorea.ac.kr
- tw.ac.kr
- u1.ac.kr
- uc.ac.kr
- uhs.ac.kr
- ukp.ac.kr
- ulsan.ac.kr
- unist.ac.kr
- uos.ac.kr
- ut.ac.kr
- uu.ac.kr
- wku.ac.kr
- woosuk.ac.kr
- wsi.ac.kr
- wsu.ac.kr
- yc.ac.kr
- yeonsung.ac.kr
- yewon.ac.kr
- yit.ac.kr
- yju.ac.kr
- ync.ac.kr
- yongin.ac.kr
- yonsei.ac.kr
- ysc.ac.kr
- ysu.ac.kr
- yu.ac.kr
- yuhan.ac.kr

## 6. 추가 허용 도메인 (작업 22, #0929-20, 2026-09-29)

KEDI 홈페이지 도메인에는 없던 입학처 도메인을 추가함. 5장 전체 목록(272개)에 포함됨.

| 대학 | 추가 도메인 | 근거 |
|---|---|---|
| 아주대학교 | iajou.ac.kr | 공식 홈페이지 입학처 메뉴에서 직접 연결(Cowork 확인, 2026-09-29) |
| 계명대학교 | gokmu.ac.kr | 공식 홈페이지 입학처 메뉴에서 직접 연결(Cowork 확인, 2026-09-29) |
| 남서울대학교 | namseoul.net | cowork_results 31번에 www.nsu.ac.kr에서 namseoul.net으로 이동한 기록 있음, SPEC 13번 직접 연결 입학처 도메인 조항 적용 (#1005-04 작업 50, 2026-10-05) |

## 7. 보류 (작업 22, #0929-20)

- 신경주대학교 sgu.ac.kr: **보류(추가하지 않음)**. 폴더 안 공식 자료에서 신경주대의 도메인으로 확인되지 않음.
  - KEDI 2026: 신경주대학교 홈페이지 www.gu.ac.kr (허용 목록에 이미 gu.ac.kr).
  - 경상남도교육청 CSV: sgu.ac.kr은 "신경대학교(화성)"(경기 화성시 남양중앙로 400-5)의 홈페이지이고, 신경주대가 아님. 같은 CSV에서 gu.ac.kr은 "경주대학교(경주)".
  - API 수집본(json 파일들)에는 홈페이지 필드에 sgu.ac.kr 값이 없음.
  - sgu.ac.kr이 신경주대 입시자료실 주소로 적힌 곳은 컷맵_입결위치조사 v3·v4 문서와 cowork_20260929_06.md뿐이며 공식 자료가 아님. 사용자·Cowork의 공식 페이지 직접 연결 확인이 필요함.

## 8. 보류 (작업 44, #0929-58, 2026-10-05)

- 남서울대학교 namseoul.net: **(2026-10-05 #1005-04 작업 50으로 허용 목록에 추가됨. 아래는 #0929-58 당시 보류 기록)** 보류(추가하지 않음). Cowork(cowork_20260930_31.md)가 허용 도메인 nsu.ac.kr 접속 시 https://www.namseoul.net/ 으로 자동 이동한다고 기록했으나, 폴더 안 공식 자료에서 namseoul.net이 확인되지 않음.
  - KEDI 2026 xlsx: 남서울대학교 홈페이지 http://www.nsu.ac.kr (대학원·특수대학원 행은 gr.nsu.ac.kr, www.nsu.ac.kr). 파일 안에 namseoul 문자열 없음.
  - 경상남도교육청 CSV: 남서울대학교(천안) 홈페이지 https://www.nsu.ac.kr/.
  - API 수집본(json 파일들), univ_coords.json, 폴더 안 다른 자료: namseoul.net 값 없음.
  - namseoul.net이 적힌 곳은 컷맵_입결위치조사 문서(조사 문서, 공식 자료 아님)와 Cowork 결과 31번뿐임.
  - 조건: 허용 도메인(nsu.ac.kr)의 공식 페이지에서 namseoul.net으로 직접 연결되는 것을 폴더 안 공식 자료나 이후 Cowork 재확인으로 확인하면 SPEC 13번에 따라 추가할 수 있음.
