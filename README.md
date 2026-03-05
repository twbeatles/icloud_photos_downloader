# iCloudPD GUI 백업 도구 (PySide6)

`icloudpd`를 **수정하지 않고** GUI로 래핑해 사용하는 크로스플랫폼(Windows/macOS/Linux) 백업 앱입니다.
MVP는 `QProcess` 기반 subprocess 실행 방식을 사용하며, 인증은 `webui`(`--password-provider webui`, `--mfa-provider webui`)를 우선 사용합니다.

## 1. 핵심 목표

- upstream(`icloudpd`)과 결합도를 낮춰 유지보수성 확보
- 설정 -> 실행 -> 로그/상태 -> 결과 요약 -> 중지/종료 안전처리 동선 제공
- EN/KO i18n 및 라이트/다크 테마 지원
- 배포(onefile) 시 `icloudpd` 파이썬 패키지를 앱에 번들

## 2. 현재 구현 범위(MVP)

- 설정 화면
  - Apple ID, 다운로드 폴더
  - 증분 다운로드, 삭제 동기화(auto-delete), 라이브포토, RAW, 최근 N일
  - watch 모드 + interval(분)
  - 고급 옵션(file-match-policy, folder-structure, XMP/EXIF, 외부 실행 파일 경로)
  - 네트워크 일시 오류용 자동 재시도(기본 OFF, watch 모드 ON 시 UI 비활성 + 안내 문구)
  - 설정 변경 즉시 저장 + 종료 시 재저장
  - 스핀/콤보 입력은 휠 스크롤로 값이 바뀌지 않도록 보호
- 실행 화면
  - Start/Stop
  - 상태 배지(`Idle/Running/Need MFA/Done/Error`)
  - 실시간 로그
  - 다운로드/오류 카운트 + 최근 로그
  - 자동 재시도 대기 상태(`Retry pending`) 표시 + `Cancel Retry`
  - MFA 필요 시 URL 노출 + 외부 브라우저 열기 + (가능 시) 앱 내 WebView
  - 로그 검색 + 오류만 보기 필터
- 로그/정보 화면
  - 전체 로그 확인/지우기
  - 최근 실행 이력(시작/종료/결과/다운로드/오류/재시도/실행 소스)
  - 로그 검색 + 오류만 보기 필터
  - 요구사항/제한사항/보안 안내
- 안전장치
  - auto-delete 2단계 확인(옵션 + 경고 모달)
  - 루트/시스템 폴더 경고
  - 실행 직전 다운로드 폴더 preflight(자동 생성 시도 + 쓰기 가능성 점검)
  - 실행 중 종료 확인 모달 + `terminate -> kill` fallback

## 3. 프로젝트 구조

```text
app/
  main.py
  core/
    config.py
    runner.py
    log_parser.py
    i18n.py
    icloudpd_runtime.py
  storage/
    settings_store.py
  ui/
    main_window.py
    settings_view.py
    run_view.py
    logs_view.py
    info_view.py
    no_wheel_input.py
  i18n/
    messages_en.ts / messages_en.qm
    messages_ko.ts / messages_ko.qm
scripts/
  build.py
tests/
  test_config.py
  test_i18n.py
  test_icloudpd_runtime.py
  test_log_parser.py
  test_runner_lifecycle.py
  test_settings_store.py
  test_runner_resolution.py
  test_ui_views.py
icloudpd-gui.spec
```

## 4. 실행 방식(번들 전략)

`app/core/runner.py`의 실행 파일 해석 우선순위는 다음과 같습니다.

1. 설정의 `icloudpd_executable` (존재할 때)
2. PyInstaller 배포본(`sys.frozen=True`)이면 현재 실행 파일 + 내부 워커 플래그
   - `sys.executable --_run_icloudpd ...`
3. 소스/개발 환경이면 `python -m icloudpd.cli`
4. 시스템 PATH의 `icloudpd`

즉, **배포본은 내부 번들된 `icloudpd`를 기본 사용**하고, 필요 시 외부 실행 파일로 override할 수 있습니다.
설정된 외부 경로가 유효하지 않으면 경고를 남기고 내부/다음 후보로 자동 fallback합니다.
앱 시작 시 내부 `icloudpd.cli` 엔트리포인트를 self-check하며, 누락 시 앱은 계속 실행되고 경고 로그/상태 메시지로 안내합니다.
시작 경고는 실행 차단 팝업 대신 상태바/로그로 표시됩니다.

## 5. 요구사항

- Python: `>=3.10,<3.14`
- 권장: 가상환경 사용
- 소스 실행 시 의존성 설치 필요

주의:
- Python 3.14는 현재 지원 범위 밖입니다. 3.10~3.13 사용을 권장합니다.
- 3.14+에서도 앱은 시작되지만, 시작 시 경고가 표시되며 일부 기능이 불안정할 수 있습니다.

## 6. 설치 및 실행

### 6.1 개발 환경 설치

```bash
pip install -e .
```

개발/테스트/빌드 도구 포함:

```bash
pip install -e .[dev]
```

### 6.2 앱 실행

```bash
icloudpd-gui
```

또는:

```bash
python -m app.main
```

개발 환경에서 `icloudpd`가 누락된 경우 자동 설치 모드:

```bash
python -m app.main --bootstrap-icloudpd
```

직접 파일 실행도 가능:

```bash
python app/main.py
```

## 7. 설정 -> CLI 매핑

| GUI 설정 | `icloudpd` 인자 |
|---|---|
| Apple ID | `--username` |
| 다운로드 폴더 | `--directory` |
| 인증(고정) | `--password-provider webui --mfa-provider webui` |
| 증분 ON | `--until-found 200` |
| auto-delete ON | `--auto-delete` |
| 라이브포토 OFF | `--skip-live-photos` |
| RAW ON/OFF | `--align-raw original` / `--align-raw alternative` |
| 최근 N일 | `--skip-created-before Nd` |
| watch ON | `--watch-with-interval <minutes*60>` |
| file-match-policy | `--file-match-policy ...` |
| folder preset | `--folder-structure {:%Y/%m/%d} / {:%Y/%m} / none` |
| XMP sidecar | `--xmp-sidecar` |
| EXIF datetime | `--set-exif-datetime` |
| 자동 재시도 | 앱 레벨 동작(일시 네트워크 오류에서만, watch 모드 제외) |

## 8. i18n (EN/KO)

- Qt `QTranslator` + `.ts/.qm` 기반
- 지원 언어: `en`, `ko`
- 기본값: 시스템 로캘이 한국어면 `ko`, 그 외 `en`
- 사용자가 언어를 명시 선택하기 전까지 시스템 로캘을 따릅니다.
- 사용자 언어 선택 이후에는 `QSettings`에서 선택값을 복원합니다.

## 9. 보안 및 제한사항

### 9.1 보안

- Apple 비밀번호/MFA 코드를 저장하지 않습니다.
- keyring 연동은 향후 확장 훅만 있으며 현재는 no-op입니다.

### 9.2 `icloudpd` 제한

- ADP(Advanced Data Protection) 미지원
- FIDO/하드웨어 키 로그인 미지원
- WebUI 인증을 위해 로컬 웹 접근(`http://127.0.0.1:8080/`) 필요

## 10. 빌드(배포)

```bash
python scripts/build.py
```

smoke test를 건너뛰고 빌드만 하려면:

```bash
python scripts/build.py --skip-smoke-test
```

빌드 순서:

1. `app/i18n/*.ts -> *.qm` 컴파일
2. `icloudpd-gui.spec`로 PyInstaller onefile 빌드
3. 산출 실행 파일로 내부 워커 smoke test(`--_run_icloudpd --help`) 수행

결과물:

- `dist/icloudpd-gui` (OS별 확장자 차이)

## 11. 테스트

```bash
python -m pytest -q
```

현재 테스트 범위:

- 설정 -> CLI 매핑/검증
- 시스템 로캘 기반 기본 언어 판정 + 사용자 언어 고정 복원
- `icloudpd` 런타임 self-check/bootstrap 동작
- 로그 파싱/상태 판정 + 일시 네트워크 오류 판정
- `QSettings` 저장/복원 + 민감정보 미저장 + 실행 이력 저장(cap)
- runner 실행 해석 우선순위 + override fallback + preflight + 커맨드 마스킹
- runner 라이프사이클(start timeout, terminate->kill, finished 중복 방지, MFA 복귀)
- UI 경량 검증(자동 재시도 설정 수집/Watch 비활성, 로그 필터, retry pending 취소, 실행 이력 렌더링)

## 12. 트러블슈팅

### `ModuleNotFoundError: No module named 'app'`

- 프로젝트 루트에서 `python -m app.main`으로 실행하거나,
- `python app/main.py`를 사용합니다.

### `ModuleNotFoundError: No module named 'qdarktheme'`

- 의존성 설치가 필요합니다.
- `pip install -e .` 또는 `pip install -e .[dev]`

### `qdarktheme.setup_theme` 관련 오류

- 구버전 API 호환 처리(`setup_theme`/`load_stylesheet`)가 코드에 반영되어 있습니다.
- 여전히 발생하면 설치된 패키지 버전 충돌 여부를 확인하세요.

### Python 3.14+ 경고가 보임

- 지원 범위는 3.10~3.13입니다.
- 3.14+에서 앱은 실행되지만 상태바/로그에 경고가 표시되며 안정성이 보장되지 않습니다.
- 가능한 한 3.10~3.13 환경으로 전환하세요.

### `icloudpd`를 찾을 수 없음

- 소스 실행: `pip install -e .`로 `icloudpd` 포함 의존성 설치
- 또는 설정에서 외부 `icloudpd` 실행 파일 경로 지정
- 개발 실행에서 빠르게 복구하려면 `python -m app.main --bootstrap-icloudpd` 사용 가능

### 외부 `icloudpd` 경로를 지정했는데 실행이 안 되는 것 같음

- 유효하지 않은 경로면 경고 후 내부 번들/다음 후보로 자동 전환됩니다.
- 로그의 `[warning]` 라인과 상태바 메시지를 확인하세요.

## 13. AI 세션 인수인계 문서

- `CLAUDE.md`: 구현/운영 실무 가이드
- `GEMINI.md`: 요구 정합성/검증 기준
- `cladue.md`: 오타 호환 포인터
