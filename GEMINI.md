# GEMINI.md

이 문서는 기능 추가/수정 시 요구사항 정합성을 확인하기 위한 기준 문서입니다.

## A. 제품 요구 정합성

### A-1. 인증
- 인증 방식은 WebUI 우선이어야 한다.
- GUI는 MFA 필요 시 URL 표시 + 외부 브라우저 열기를 제공해야 한다.
- QtWebEngine이 있을 때만 앱 내 WebView 기능을 선택적으로 활성화한다.

### A-2. 설정/실행 흐름
- 필수 입력: Apple ID, 다운로드 경로.
- 실행 동선: 설정 -> 실행 -> 로그/상태 -> 결과 요약.
- watch 모드 interval은 분 입력, 내부 변환은 초 단위.
- 설정 변경은 실행과 무관하게 즉시 저장되어야 하며, 종료 시점에도 재저장해야 한다.
- 스핀/콤보 입력은 휠 스크롤로 값이 의도치 않게 변경되지 않아야 한다.

### A-3. 안전장치
- auto-delete는 2단계 확인(체크 + 경고 모달).
- 위험 경로(루트/시스템 폴더) 경고.
- 실행 직전 다운로드 경로 preflight(자동 생성 시도 + 쓰기 가능성 검사).
- 실행 중 종료 시 확인 모달 및 안전 중지.

### A-4. 보안
- 비밀번호/MFA 저장 금지.
- keyring은 인터페이스 훅만 허용(no-op).

## B. 기술 요구 정합성

### B-1. `icloudpd` 실행 전략
- `QProcess` subprocess 실행 유지.
- 실행 해석 우선순위:
  1. 설정된 외부 실행 파일 경로
  2. PyInstaller 배포본: `sys.executable --_run_icloudpd`
  3. 소스/개발 모드: `python -m icloudpd.cli`
  4. PATH의 `icloudpd`
- 외부 실행 파일 경로가 유효하지 않으면 경고 후 fallback해야 한다(즉시 실패 금지).
- 실행 커맨드 로그는 `--username` 값을 마스킹해야 한다.
- 앱 시작 시 `icloudpd.cli` 엔트리포인트 self-check를 수행해야 한다.
- 개발 모드에서 `--bootstrap-icloudpd` 옵션으로 누락 의존성 자동 설치를 지원할 수 있다.
- 런타임 누락 시 앱은 시작을 유지하고 경고 메시지로 안내해야 한다(하드 블로킹 지양).

### B-2. 상태/로그 모델
- 상태: `idle`, `running`, `need_mfa`, `done`, `error`.
- 로그 파서 키워드 기반 감지:
  - MFA 문구
  - WebUI 시작 문구 -> `http://127.0.0.1:8080/`
  - 완료 문구
  - ERROR 라인
- 완료 reason/상태 표시는 `final_state` 단일 기준으로 일치해야 한다.
- 로그 파서는 case-insensitive + 일시 네트워크 오류(transient) 판정을 제공해야 한다.
- MFA URL 알림과 NEED_MFA 상태 전이는 분리되어야 한다.

### B-3. 운영 기능
- Run/Logs 화면은 로그 검색 + 오류만 보기 필터를 지원해야 한다.
- 최근 실행 이력(시간/결과/카운트/재시도)을 `QSettings` JSON 배열로 저장하고 최신순 cap(기본 50)을 유지한다.
- 자동 재시도는 기본 OFF, watch 모드에서는 비활성이며 transient 오류에서만 지수 백오프로 동작한다.

### B-4. i18n
- `QTranslator` + `messages_en/ko.ts(.qm)`.
- 기본 언어는 시스템 로캘(ko면 한국어).
- 사용자 선택 전에는 시스템 로캘을 사용하고, 명시 선택 이후에는 선택 언어를 `QSettings`에서 복원한다.

### B-5. 빌드/배포
- `scripts/build.py`에서 `.ts -> .qm` 후 PyInstaller onefile.
- `icloudpd-gui.spec`는 번들 리소스/hidden import를 포함해야 한다.
- 빌드 후 실행 파일의 내부 워커 smoke test(`--_run_icloudpd --help`)를 수행해야 한다.
- 산출물은 `dist/` 기준.

## C. 변경 검증 프로토콜

1. 정적 검토
- 임포트/경로/타입 오류 여부
- 문서와 코드 동작 일치 여부

2. 자동 테스트
```bash
python -m pytest -q
```

3. 수동 QA
- 설정 저장/복원
- Start/Stop + 종료 안전 처리
- MFA URL 노출/열기
- invalid override 경고 + fallback 확인
- preflight 실패(권한/경로) 메시지 확인
- 자동 재시도 조건(transient only, watch 제외) 확인
- Run/Logs 검색 및 오류 필터 확인
- 최근 실행 이력 누적/최대 보관량 확인
- EN/KO 즉시 반영
- 라이트/다크 전환 반영
- 번들/외부 실행 파일 해석 우선순위 확인

## D. 금지 패턴

- `icloudpd` upstream 코드 직접 수정
- 민감정보 저장 구현
- 공식 spec 우회 임시 빌드 파이프라인 추가
- 동작 변경 후 문서/번역 미갱신

## E. 우선순위

1. 데이터 손실 방지(auto-delete/경로 안전성)
2. 실행 신뢰성(start/stop/process 상태)
3. 사용자 피드백 품질(로그/상태/오류 메시지)
4. 번들 빌드 재현성(spec + build.py)
5. 문서 및 i18n 정합성
