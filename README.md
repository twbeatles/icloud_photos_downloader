# iCloudPD GUI 백업 도구 (PySide6)

`icloudpd`를 외부 실행 파일로 래핑하여 사용하는 크로스플랫폼 데스크톱 백업 앱입니다.  
대상 플랫폼은 Windows/macOS/Linux이며, 인증은 `webui` 흐름을 우선 사용합니다.

## 1. 프로젝트 개요

### 핵심 목표
- `icloudpd` 본체를 직접 수정하지 않고 GUI에서 안정적으로 호출
- 설정/실행/로그/상태/요약/중지 흐름을 하나의 UI에서 제공
- EN/KO 다국어(i18n)와 라이트/다크 테마 지원

### 현재 구현 상태(MVP)
- 설정 화면: Apple ID, 다운로드 폴더, 증분/삭제동기화/라이브포토/RAW/최근 N일/watch, 고급 옵션
- 실행 화면: Start/Stop, 상태 배지, 실시간 로그, 요약 카운터, MFA URL 열기
- 로그 화면: 전체 프로세스 출력 확인/초기화
- 정보 화면: 제한사항/보안/요구조건 안내
- 안전장치: auto-delete 2단계 확인, 위험 경로 경고, 종료 시 실행 중 확인 모달

## 2. 아키텍처

### 디렉터리 구조
```text
app/
  main.py
  core/
    config.py
    runner.py
    log_parser.py
    i18n.py
  storage/
    settings_store.py
  ui/
    main_window.py
    settings_view.py
    run_view.py
    logs_view.py
    info_view.py
  i18n/
    messages_en.ts / messages_en.qm
    messages_ko.ts / messages_ko.qm
scripts/
  build.py
icloudpd-gui.spec
```

### 실행 흐름
1. UI에서 설정 수집
2. `app/core/config.py`가 `icloudpd` CLI 인자 목록 생성
3. `app/core/runner.py`가 `QProcess`로 `icloudpd` 실행
4. stdout/stderr 라인을 `app/core/log_parser.py`가 파싱
5. 상태/요약/로그를 UI에 실시간 반영

## 3. 사전 요구사항

1. Python `>=3.10,<3.14`
2. `icloudpd` 외부 설치 완료
3. 로컬 브라우저 접근 가능 (`http://127.0.0.1:8080/`)

## 4. 설치 및 실행

### 의존성 설치
```bash
pip install -e .
```

개발 의존성 포함:
```bash
pip install -e .[dev]
```

### 앱 실행
```bash
icloudpd-gui
```

또는:
```bash
python -m app.main
```

## 5. 빌드 (PyInstaller onefile)

### 빌드 스크립트 사용
```bash
python scripts/build.py
```

빌드 단계:
1. `app/i18n/*.ts` -> `*.qm` 컴파일
2. `icloudpd-gui.spec` 기반 onefile 빌드

결과물:
- `dist/icloudpd-gui` (OS별 확장자/형태 상이)

## 6. 설정값과 `icloudpd` 매핑

| GUI 항목 | `icloudpd` 인자 |
|---|---|
| Apple ID | `--username` |
| 다운로드 폴더 | `--directory` |
| 인증 방식(고정) | `--password-provider webui --mfa-provider webui` |
| 증분 다운로드 ON | `--until-found 200` |
| 삭제 동기화 ON | `--auto-delete` |
| 라이브 포토 처리 OFF | `--skip-live-photos` |
| RAW 포함 ON/OFF | `--align-raw original` / `--align-raw alternative` |
| 최근 N일 | `--skip-created-before Nd` |
| watch 모드 ON | `--watch-with-interval <분*60>` |
| 파일 매칭 정책 | `--file-match-policy ...` |
| 폴더 구조 프리셋 | `--folder-structure {:%Y/%m/%d} / {:%Y/%m} / none` |
| XMP Sidecar | `--xmp-sidecar` |
| EXIF DateTime | `--set-exif-datetime` |

## 7. 보안/안전 정책

- 비밀번호/MFA 코드는 저장하지 않습니다.
- keyring 연동은 훅만 제공하며 현재 no-op입니다.
- `auto-delete`는 체크박스 + 경고 모달 확인이 모두 필요합니다.
- 루트/시스템 경로를 다운로드 경로로 선택하면 경고합니다.

## 8. 제한사항

`icloudpd` 자체 제한을 따릅니다.

- ADP(Advanced Data Protection) 계정 미지원
- FIDO/하드웨어 키 로그인 미지원

## 9. 테스트

```bash
python -m pytest -q
```

현재 테스트:
- `tests/test_config.py`
- `tests/test_log_parser.py`
- `tests/test_settings_store.py`

## 10. AI 세션 참조 문서

다음 세션에서 AI가 빠르게 맥락을 복원할 수 있도록 아래 문서를 제공합니다.

- `CLAUDE.md`: 구현/운영 관점의 작업 가이드
- `cladue.md`: 오타 호환용 포인터 문서
- `GEMINI.md`: 제약/검증 기준 중심 가이드

## 11. 트러블슈팅

### `icloudpd` 실행 파일을 찾을 수 없음
- 시스템 PATH에 `icloudpd`가 있는지 확인
- 또는 설정 화면의 `icloudpd Executable`에 절대 경로 지정

### MFA URL이 열리지 않음
- 로컬 보안 정책/방화벽에서 `127.0.0.1:8080` 차단 여부 확인
- 외부 브라우저 버튼으로 먼저 확인

### 앱 종료 시 멈춤
- 실행 중 프로세스 종료 대기 중일 수 있음
- 앱은 `terminate -> kill` 순서로 중지합니다

