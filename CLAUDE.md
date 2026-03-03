# CLAUDE.md

이 문서는 다음 세션의 AI/엔지니어가 빠르게 프로젝트 맥락을 복원하고 안전하게 작업하도록 돕기 위한 운영 가이드입니다.

## 1) 프로젝트 정체성

- 프로젝트명: `icloudpd-gui`
- 목적: `icloudpd`를 직접 수정하지 않고 GUI로 래핑
- 핵심 스택:
  - Python
  - PySide6
  - qdarktheme
  - PyInstaller(onefile)

## 2) 절대 원칙

1. `icloudpd` 코어 로직을 이 레포에 재구현하지 않는다.
2. 인증은 `webui` 우선이며 GUI는 URL 안내 및 열기 역할에 집중한다.
3. 비밀번호/MFA 코드는 저장하지 않는다.
4. 설정-실행-로그 파이프라인을 깨는 변경을 피한다.

## 3) 주요 파일과 책임

- `app/core/config.py`
  - `BackupSettings` 도메인 모델
  - GUI 설정 -> `icloudpd` 인자 변환
  - 유효성 검사 + 위험 경로 판정
- `app/core/runner.py`
  - `QProcess` 실행 래퍼
  - 시작/중지/종료 시그널 처리
  - stdout/stderr 라인 스트리밍
- `app/core/log_parser.py`
  - 진행/오류/MFA/완료 상태 감지
  - 최소 통계(`downloaded_count`, `error_count`)
- `app/storage/settings_store.py`
  - `QSettings` 저장/복원
  - 민감정보 미저장
- `app/ui/*.py`
  - 페이지와 메인 윈도우, 사용자 인터랙션
- `scripts/build.py`
  - 번역 컴파일 + PyInstaller 빌드
- `icloudpd-gui.spec`
  - PyInstaller 공식 빌드 설정(재현성 확보)

## 4) 로컬 개발 커맨드

설치:
```bash
pip install -e .[dev]
```

실행:
```bash
icloudpd-gui
```

테스트:
```bash
python -m pytest -q
```

빌드:
```bash
python scripts/build.py
```

## 5) 변경 시 체크리스트

1. `README.md`가 실제 동작과 일치하는가
2. `config.py` 매핑 규칙이 깨지지 않았는가
3. `runner.py` 중지 시 `terminate -> kill` 흐름이 유지되는가
4. i18n 문자열 변경 시 `messages_en.ts/messages_ko.ts`가 같이 갱신되었는가
5. 테스트 3종이 통과하는가

## 6) 자주 발생하는 실수

- `--recent`를 날짜 의미로 오해하는 것
  - 이 프로젝트는 날짜 필터로 `--skip-created-before Nd`를 사용한다.
- `*.spec`를 `.gitignore`로 누락시키는 것
  - `icloudpd-gui.spec`는 버전 관리 대상이다.
- UI 문자열 추가 후 번역 누락
  - 최소한 EN/KO 둘 다 반영한다.

## 7) 다음 세션 권장 시작 순서

1. `README.md`
2. `app/core/config.py`
3. `app/core/runner.py`
4. `app/ui/main_window.py`
5. `scripts/build.py` + `icloudpd-gui.spec`

