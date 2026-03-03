# GEMINI.md

이 문서는 다음 세션 AI가 기능 추가/수정 시 판단 기준을 일관되게 유지하기 위한 규격 문서입니다.

## A. 제품 요구 정합성 기준

### A-1. 인증
- 기본 인증 입력 흐름은 `webui`.
- GUI는 인증 URL을 노출하고 외부 브라우저 열기를 제공해야 함.
- QtWebEngine이 있으면 앱 내 WebView는 선택 기능으로만 제공.

### A-2. 설정
- 필수: Apple ID, 다운로드 경로.
- 고급: file-match-policy, folder-structure, XMP, EXIF.
- watch interval은 분 단위 입력, 내부는 초로 변환.

### A-3. 안전장치
- auto-delete는 위험 경고 + 확인 절차 필요.
- 루트/시스템 폴더 경고 필요.
- 실행 중 앱 종료 시 확인 모달 필요.

### A-4. 보안
- 비밀번호/MFA 저장 금지.
- keyring 훅은 인터페이스만 허용(no-op).

## B. 기술 요구 정합성 기준

### B-1. `icloudpd` 호출 방식
- `QProcess` 기반 subprocess 실행.
- 우선순위:
  1. 설정된 실행 파일 경로
  2. PATH 탐색(`shutil.which("icloudpd")`)

### B-2. 상태 모델
- 상태: `idle`, `running`, `need_mfa`, `done`, `error`.
- 로그 파싱으로 MFA/에러/완료를 갱신.

### B-3. i18n
- `QTranslator` + `messages_en/ko.ts(.qm)` 사용.
- UI 문자열 변경 시 번역 파일 동시 업데이트.

### B-4. 빌드
- 번역 컴파일 후 `icloudpd-gui.spec`로 PyInstaller onefile 빌드.
- 빌드 경로/산출물은 `dist/` 기준.

## C. 변경 검증 프로토콜

1. 정적 점검
- 타입/임포트/경로 오류 없는지 확인

2. 단위 테스트
```bash
python -m pytest -q
```

3. 수동 시나리오
- 설정 저장/복원
- Start/Stop 동작
- MFA URL 노출/열기
- 언어 전환(EN/KO)
- 테마 전환(라이트/다크)

## D. 금지 패턴

- `icloudpd` 내부 소스 종속을 강화하는 직접 import 실행
- 민감 정보 저장
- `spec` 파일 없이 임시 옵션만으로 배포 빌드 수행
- 문서 미갱신 상태로 동작 변경 반영

## E. 우선순위

1. 데이터 손실 방지(auto-delete/경로 안정성)
2. 실행 신뢰성(start/stop/process 상태)
3. 사용자 피드백 품질(로그/상태/오류 메시지)
4. 빌드 재현성(spec + 스크립트)
5. 문서 정합성

