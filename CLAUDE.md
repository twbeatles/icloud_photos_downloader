# CLAUDE.md

이 문서는 다음 세션의 AI/엔지니어가 빠르게 맥락을 복원하고, 기존 아키텍처를 깨지 않도록 작업하기 위한 운영 가이드입니다.

## 1) 프로젝트 정체성

- 프로젝트명: `icloudpd-gui`
- 목표: `icloudpd` upstream을 수정하지 않고 GUI 래퍼로 제공
- UI: PySide6
- 프로세스 실행: `QProcess` subprocess
- 배포: PyInstaller onefile (`icloudpd` 번들 포함)

## 2) 절대 원칙

1. `icloudpd` 코어를 이 레포에서 재구현/패치하지 않는다.
2. 인증은 WebUI 우선(`--password-provider webui`, `--mfa-provider webui`)으로 유지한다.
3. 비밀번호/MFA 코드는 저장하지 않는다.
4. 데이터 손실 위험 옵션(auto-delete) 보호 장치를 제거하지 않는다.
5. UI 문자열 변경 시 EN/KO i18n 자산(`.ts/.qm`)을 함께 갱신한다.

## 3) 핵심 실행 우선순위 (`app/core/runner.py`)

`resolve_icloudpd_command()` 우선순위:

1. 사용자 지정 실행 파일 (`settings.icloudpd_executable`)
2. PyInstaller 배포본이면 내부 워커 호출
   - `sys.executable --_run_icloudpd`
3. 소스/개발 환경이면 모듈 실행
   - `sys.executable -m icloudpd.cli`
4. PATH의 `icloudpd`

주의:
- 배포본에서 내부 워커 플래그(`--_run_icloudpd`) 제거/변경 시 번들 실행이 깨진다.
- 사용자 지정 실행 파일이 유효하지 않으면 경고 후 다음 우선순위로 fallback한다.

## 4) 주요 파일 책임

- `app/core/config.py`
  - `BackupSettings`, `ValidationIssue`
  - GUI 설정 -> CLI args 변환
  - 경로 정규화(`expanduser + resolve(strict=False)`)
  - 위험 경로 판정/검증 + 자동 재시도 파라미터 검증
- `app/core/runner.py`
  - `QProcess` start/stop/kill fallback
  - 실행 직전 다운로드 폴더 preflight(생성/쓰기 점검)
  - stdout/stderr 라인 스트리밍 + signal 발행
  - 커맨드 로그 마스킹(`--username`)
  - final state 기준 완료 reason 일원화
- `app/core/log_parser.py`
  - MFA/에러/완료 키워드 파싱(case-insensitive)
  - 일시 네트워크 오류(transient) 판정
  - `RunSummary` 누적
- `app/core/i18n.py`
  - 기본 언어 결정(시스템 로캘)
  - `QTranslator` 로드/교체
- `app/storage/settings_store.py`
  - `QSettings` 기반 저장/복원
  - 민감정보 저장 금지, keyring 훅만 존재
  - 실행 이력(JSON 배열, 최신순 cap) 저장/로드
- `app/ui/*.py`
  - 설정 즉시 저장 + 종료 시 재저장
  - 자동 재시도 옵션 UI
  - Run/Logs 검색 + 오류 필터
  - Logs 최근 실행 이력 표시
- `icloudpd-gui.spec`
  - 번들 데이터/hidden import 포함
- `scripts/build.py`
  - 번역 컴파일 + onefile 빌드

## 5) 개발 표준 커맨드

설치:
```bash
pip install -e .[dev]
```

실행:
```bash
python -m app.main
```

테스트:
```bash
python -m pytest -q
```

빌드:
```bash
python scripts/build.py
```

## 6) 변경 체크리스트

1. `README.md`, `CLAUDE.md`, `GEMINI.md`가 코드 동작과 일치하는가
2. `config.py` 매핑 규칙이 요구사항과 동일한가
3. `runner.py` stop 로직(`terminate -> kill`)과 preflight/fallback가 유지되는가
4. final_state와 UI 완료 메시지 기준이 일치하는가
5. i18n 변경 시 `.ts`/`.qm` 동시 반영했는가
6. 테스트(`pytest -q`) 통과했는가
7. `icloudpd-gui.spec`가 번들 전략을 계속 반영하는가

## 7) 자주 발생하는 실수

- 한국어 시스템에서 사용자 언어 선택을 강제로 덮어쓰는 회귀
  - 기본값만 로캘 기반, 저장된 사용자 선택은 존중해야 함
- `*.spec` 전체를 ignore해서 공식 spec이 누락되는 문제
  - `icloudpd-gui.spec`는 반드시 버전 관리
- 문서 갱신 누락
  - 실행 우선순위/번들 여부가 코드와 어긋나기 쉬움

## 8) 세션 시작 추천 순서

1. `README.md`
2. `app/core/config.py`
3. `app/core/runner.py`
4. `app/ui/main_window.py`
5. `icloudpd-gui.spec` / `scripts/build.py`
