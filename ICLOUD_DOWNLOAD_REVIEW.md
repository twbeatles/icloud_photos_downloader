# iCloud 사진 다운로드 구현 점검 리포트

검토 기준:
- [README.md](./README.md)
- [CLAUDE.md](./CLAUDE.md)
- 주요 코드: `app/core/*`, `app/ui/*`, `app/storage/*`

테스트 현황:
- 기준선(최초 리뷰 당시): `16 passed`
- 현재(개선 반영 후): `30 passed`

## 적용 현황 업데이트 (2026-03-04)

- 결론: 주요 Findings 8개와 추가 권장 A/B/C 항목이 코드/테스트에 반영됨.
- 반영 핵심:
  - 설정 즉시 저장 + 종료 시 재저장
  - 다운로드 경로 정규화 + preflight(자동 생성/쓰기 검사)
  - 완료 상태/사유 판정 `final_state` 단일화
  - override 경로 유효성 검사 + 경고 후 fallback
  - MFA URL 알림과 NEED_MFA 상태 전이 분리
  - 실행 커맨드 `--username` 마스킹
  - 로그 파서 case-insensitive + transient 오류 판정
  - 실행 이력 저장(cap 50), Run/Logs 검색·오류 필터, 자동 재시도 옵션

### Findings 처리 상태

| 항목 | 상태 |
|---|---|
| 1) 설정 저장 시점 문제 | 완료 |
| 2) `~` 경로 미확장 | 완료 |
| 3) reason/state 불일치 | 완료 |
| 4) 깨진 override fallback 부재 | 완료 |
| 5) override 검증 약함 | 완료 |
| 6) MFA 상태 조기 전환 | 완료 |
| 7) Apple ID 로그 노출 | 완료 |
| 8) 로그 파서 취약성 | 완료 |

## 주요 Findings (심각도 순)

### 1) High - 설정이 "실행 시작" 시점에만 저장됨 (문서 기대와 불일치)
- 근거:
  - `MainWindow._on_theme_selected()` / `_on_language_selected()`는 메모리 값만 변경: `app/ui/main_window.py:293-299`
  - 실제 `QSettings` 저장은 `_start_run()`에서만 호출: `app/ui/main_window.py:197-199`
  - README는 언어 선택이 저장/복원된다고 명시: `README.md:141`
- 영향:
  - 사용자가 언어/테마/설정을 바꾸고 실행(Start)하지 않은 채 종료하면 다음 실행에 반영되지 않음.
- 권장:
  - 언어/테마 변경 즉시 `self._store.save(self.settings_view.collect_settings())` 호출
  - 최소한 `closeEvent()`에서 마지막 설정 저장

### 2) High - 다운로드 경로 `~`(home) 미확장으로 잘못된 대상 폴더 가능
- 근거:
  - UI 수집 시 `download_dir`는 문자열 그대로 저장: `app/ui/settings_view.py:205`
  - CLI 인자 변환 시 `Path(settings.download_dir)`만 적용 (`expanduser()` 없음): `app/core/config.py:58`
- 영향:
  - `QProcess`는 쉘 확장을 하지 않으므로 `~` 입력 시 홈 경로가 아닌 리터럴 경로로 처리될 수 있음.
- 권장:
  - `collect_settings()` 또는 `to_icloudpd_args()`에서 `Path(...).expanduser().resolve()` 처리
  - 검증 단계에서 비정상 경로를 명시적으로 에러 처리

### 3) High - 완료 사유(reason)와 상태(state) 판정 기준이 달라 성공 오표시 가능
- 근거:
  - `reason`은 `exit_code == 0`이면 `"completed"`로 판정: `app/core/runner.py:181`
  - 최종 상태는 `error_count > 0`이면 `ERROR`: `app/core/log_parser.py:82-87`
  - UI는 reason 기준으로 성공 메시지 노출: `app/ui/main_window.py:238-246`
- 영향:
  - 로그에 `ERROR`가 있었는데도 "성공적으로 완료" 메시지가 뜰 수 있음.
- 권장:
  - `_on_finished()`에서 `final_state` 기반으로 reason을 일관되게 계산
  - 상태/토스트 메시지를 하나의 판정 함수로 통합

### 4) Medium - 사용자 override 경로가 깨지면 내부 번들 fallback까지 막힘
- 근거:
  - override 값이 존재하지만 파일이 없으면 즉시 `None` 반환: `app/core/runner.py:24-29`
  - 이후 frozen/internal/module/PATH fallback 로직 미진입
- 영향:
  - 설정에 오래된 경로가 남아 있으면, 내부 번들이 있어도 실행 불가.
- 권장:
  - override 실패 시 경고 후 fallback 진행
  - 또는 UI에서 "경로가 유효하지 않으면 자동 fallback" 정책 명확화

### 5) Medium - override 실행 파일 검증이 약함 (`exists`만 체크)
- 근거:
  - `candidate.exists()`만 확인: `app/core/runner.py:25-27`
- 영향:
  - 디렉토리/비실행 파일/권한 없는 파일도 통과 -> 런타임 시작 실패로 사용자 경험 저하.
- 권장:
  - `is_file()` + 실행 가능 여부(`os.access(..., X_OK)` 또는 플랫폼별 점검) 추가

### 6) Medium - MFA 상태 UI가 실제 상태보다 먼저 `Need MFA`로 바뀔 수 있음
- 근거:
  - Runner는 WebUI 서버 시작 라인만 받아도 `mfa_required` 시그널 발생: `app/core/runner.py:157-158`
  - MainWindow는 해당 시그널 수신 시 상태가 `NEED_MFA`가 아니면 강제로 배지 변경: `app/ui/main_window.py:233-237`
- 영향:
  - 실제로는 단순 WebUI 준비 단계인데 사용자에게 MFA 필요 상태로 보일 수 있음.
- 권장:
  - `event.mfa_required`일 때만 `mfa_required` 시그널 송출
  - UI에서 상태 변경은 `state_changed`만 신뢰하도록 단일화

### 7) Medium - 실행 커맨드 로그에 Apple ID가 그대로 남음
- 근거:
  - 시작 시 전체 커맨드 라인 로그 출력: `app/core/runner.py:102`
  - `--username <apple_id>`가 포함됨: `app/core/config.py:55-56`
- 영향:
  - 로그 공유/스크린샷 시 개인정보(Apple ID) 노출 위험.
- 권장:
  - 로그 출력 시 민감 파라미터 마스킹 (`--username ***`)

### 8) Medium - 로그 파서가 문자열 패턴에 과도 의존 (업스트림 로그 변화에 취약)
- 근거:
  - MFA/완료/에러 판단이 고정 영문 패턴: `app/core/log_parser.py:9-15`, `52-77`
  - 테스트도 동일 패턴 중심: `tests/test_log_parser.py:14-29`
- 영향:
  - `icloudpd` 로그 문구가 바뀌면 상태/카운트가 무음 오작동 가능.
- 권장:
  - 패턴 테이블화 + 버전별 회귀 테스트 케이스 추가
  - 가능하면 exit code/구조화 출력 기반 판정 비중 확대

## 추가 권장 항목 (기능/안정성)

### A) 시작 전 사전 점검(Preflight) 강화
- 다운로드 디렉토리 쓰기 가능 여부
- 경로 자동 생성 실패 시 명확한 오류 안내
- Watch 모드에서 최소 권장 interval 안내(예: 너무 짧은 간격 경고)

### B) 운영 관점 가시성 개선
- 최근 실행 이력(시작/종료 시각, 결과, 다운로드 개수) 저장
- 오류 로그 필터/검색 기능(현재는 누적 텍스트 중심)

### C) 실패 복원력
- 네트워크 일시 실패 시 재시도 정책(지수 백오프) 옵션
- 중단 후 재실행 시 마지막 실패 원인 요약 제공

## 테스트 보강 권장

- `tests/test_main_window_*`:
  - 설정 변경 후 실행 없이 종료/재시작 시 영속성 검증
  - `reason`/`state` 불일치 재현 및 방지 테스트
- `tests/test_config.py`:
  - `download_dir="~/<path>"` 확장 처리 테스트
- `tests/test_runner_resolution.py`:
  - override 경로 실패 시 fallback 동작 테스트
- `tests/test_log_parser.py`:
  - 문구 변형/대소문자/추가 접미사에 대한 회귀 케이스 확대
