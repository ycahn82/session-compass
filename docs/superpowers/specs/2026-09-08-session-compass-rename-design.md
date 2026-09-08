# Session Compass 이름 변경 설계

## 1. 목표

현재 `cli-sessions` 포크를 공개적으로 배포 가능한 별도 프로젝트인 `session-compass`로 정리한다.

최종 공개 이름은 다음과 같다.

| 구분 | 최종 이름 |
| --- | --- |
| PyPI distribution | `session-compass` |
| Python import package | `session_compass` |
| CLI command | `scompass` |
| GitHub repository | `ycahn82/session-compass` |

기존 upstream `cli-sessions` 사용자와 충돌하지 않도록 `sessions` 명령은 제공하지 않는다. 기존 프로젝트의 fork에서 출발했다는 사실은 README에 명시하되, 새 패키지는 독립적인 distribution과 실행 파일을 사용한다.

## 2. 배경과 제품 설명

Session Compass는 Claude Code, Codex, Antigravity CLI, Copilot CLI가 로컬에 저장한 session을 한곳에서 발견하고 식별하며 재개하기 위한 local-first CLI다.

해결하려는 문제는 사용자가 여러 coding agent와 서버에서 작업한 뒤 다음 정보를 다시 찾기 어렵다는 것이다.

- 어떤 agent가 만든 session인지
- 어느 workspace/project에서 작업했는지
- 마지막으로 언제 사용했는지
- 어떤 제목 또는 사용자 메시지로 시작했는지
- 해당 session을 안전하게 resume할 수 있는지

초기 제품은 중앙 서버, telemetry, cloud database, LLM 요약, agent orchestration을 사용하지 않는다. 각 agent가 이미 기록한 로컬 JSONL/SQLite 데이터를 읽고, agent별 adapter가 session metadata와 resume command를 제공한다.

## 3. 변경 범위

### 3.0 공개 문서 언어

사용자와 PyPI가 직접 읽는 공개 문서는 모두 영어로 작성한다.

- `README.md`: 전체 영어
- `pyproject.toml`의 `description`, `keywords`, metadata 문구: 영어
- PyPI에 표시되는 project description: README 기반의 영어 내용
- CLI help와 사용자-facing error/message: 영어

한국어는 내부 설계 문서, 구현 계획, 개발 메모에만 사용한다.

### 3.1 패키징과 실행 파일

- `pyproject.toml`의 project name을 `session-compass`로 변경한다.
- `[project.scripts]` entry point를 `scompass = "session_compass.cli:main"`으로 변경한다.
- 소스 패키지 디렉터리를 `src/cli_sessions`에서 `src/session_compass`로 변경한다.
- Python 모듈의 내부 import와 모듈 docstring을 `session_compass`에 맞춘다.
- `sessions`라는 entry point나 shell wrapper는 추가하지 않는다.
- 기존 `cli-sessions` 설치와 동일한 Python package name을 공유하지 않도록 한다.

### 3.2 GitHub repository

GitHub repository 이름을 `ycahn82/cli-sessions`에서 `ycahn82/session-compass`로 변경한다.

repository rename 이후에는 로컬 `origin` URL을 새 주소로 갱신하고, `upstream`은 원본 `pavbyte/cli-sessions`를 유지한다.

```text
origin   -> git@github.com:ycahn82/session-compass.git
upstream -> https://github.com/pavbyte/cli-sessions.git
```

GitHub의 기존 URL redirect와 commit history는 유지되는 것으로 기대하지만, rename 후 실제 clone/fetch URL과 repository 페이지를 확인한다.

### 3.3 README

README는 단순 fork 안내가 아니라 현재 제품의 목적과 운영 원칙을 설명하는 문서로 갱신한다.

반드시 포함할 내용:

1. 프로젝트 제목과 PyPI badge를 `session-compass`로 변경
2. `scompass` 설치 및 사용 예시
3. 기존 `cli-sessions`의 fork에서 출발했다는 설명과 upstream 링크
4. 여러 coding agent session의 discover, identify, resume 목적
5. local-first, read-only metadata discovery, no telemetry 원칙
6. 현재 지원 agent와 agent별 로컬 storage 개요
7. resumable session만 기본 목록에 표시하고 metadata-only/internal record는 resume 후보에서 제외한다는 설명
8. `-d`/`--dangerously-skip-permissions`가 각 agent의 native option으로 전달된다는 설명과 주의사항
9. 서비스 CLI가 독립적으로 업데이트될 수 있으므로 `session-compass`가 지원하는 compatibility floor와 weekly CI monitoring을 운영한다는 설명
10. master plan의 단계: metadata 품질, resumability, compatibility monitoring, 향후 검색/JSON/doctor/remote aggregation
11. 현재 구현 범위와 향후 계획을 구분한 roadmap
12. fork 유지 정책과 issue/reporting 안내

README의 모든 사용 예시는 `sessions`가 아니라 `scompass`를 사용한다.

### 3.4 Master plan과 문서

기존 `cli-sessions-customization-master-plan.md`의 제품명을 `Session Compass`로 갱신하고, 명령 예시는 현재 구현 범위에 맞게 `scompass`로 갱신한다. 원본 upstream을 가리키는 문맥에서는 `cli-sessions`를 유지한다.

기존 compatibility 설계/계획 문서는 역사적 구현 기록으로 보존하되, 새 README와 현재 master plan이 사용자에게 보이는 canonical 설명이 되도록 한다.

## 4. 호환성 및 마이그레이션 정책

이 변경은 기존 `cli-sessions` 설치를 자동으로 대체하지 않는다.

```text
기존 설치: pip install cli-sessions  -> sessions
새 설치:   pip install session-compass -> scompass
```

따라서 기존 사용자의 `sessions` 명령을 가로채거나 덮어쓰지 않는다. 새 프로젝트에서 `sessions` alias를 제공하지 않는 것은 의도적인 충돌 방지 정책이다.

새 package의 import namespace도 `session_compass`로 변경하여, 같은 Python environment에서 두 distribution을 설치할 때 `cli_sessions` 파일이 서로 덮어쓰이는 위험을 피한다. 다만 CLI 도구는 `pipx` 또는 `uv tool`처럼 별도 environment에 설치하는 것을 README에서 권장한다.

## 5. 구조와 책임 경계

이름 변경은 기능 동작을 바꾸지 않는 packaging/refactor 단계로 유지한다.

- `session_compass/cli.py`: argparse, 목록 출력, 선택, resume orchestration
- `session_compass/agents/`: Claude, Codex, Antigravity, Copilot별 storage/metadata/resume adapter
- `session_compass/compatibility.py`와 관련 workflow: 서비스 CLI compatibility contract
- `tests/`: import path와 public CLI 이름을 검증하고 기존 collector/resume 동작을 regression test로 보존

이번 단계에서는 agent adapter의 storage algorithm이나 resume argument를 변경하지 않는다. 이름 변경 때문에 발생하는 import/entry-point/path 변경만 수행한다.

## 6. 검증 기준

다음 조건을 모두 만족해야 한다.

1. 전체 unit test가 통과한다.
2. `python -m session_compass.cli --help`가 실행된다.
3. help 출력에 `scompass` 사용법과 `-d`/`--dangerously-skip-permissions`가 나타난다.
4. `python -m cli_sessions.cli`가 더 이상 프로젝트 내부의 정상적인 public module 경로가 아님을 확인한다.
5. wheel에 `session_compass/`가 포함되고 `cli_sessions/`가 포함되지 않는다.
6. 설치 후 `scompass --claude`와 provider filter가 동작한다.
7. `sessions` command는 새 package 설치만으로 생성되지 않는다.
8. README의 install, usage, source, PyPI 링크가 모두 새 이름을 가리킨다.
9. master plan의 사용자-facing 명령 예시가 `scompass`와 일치한다.
10. repository rename 후 `origin`은 `session-compass`, `upstream`은 원본 `cli-sessions`를 가리킨다.

## 7. 범위 밖

이번 rename 단계에서는 다음을 수행하지 않는다.

- 기존 사용자 환경의 `cli-sessions` uninstall 또는 자동 migration
- `sessions` compatibility alias 제공
- 새로운 agent 추가
- storage schema 변경
- runtime `--help` probe 추가
- 중앙 session synchronization
- GitHub repository archive
- PyPI publish 자체의 자동 실행
