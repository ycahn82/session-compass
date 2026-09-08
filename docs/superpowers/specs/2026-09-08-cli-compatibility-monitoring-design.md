# cli-sessions 다중 Agent CLI 호환성 모니터링 설계

## 상태

- 설계 승인 상태: 사용자 승인 완료
- 작성일: 2026-09-08
- 대상 저장소: `cli-sessions`
- 구현 범위: Agent별 resume command adapter, capability contract 검사, 주간 GitHub Actions 검사, 호환성 Issue 자동 생성·갱신, README 운영 문서

## 목표

`cli-sessions` 사용자가 Claude, Codex, Antigravity, Copilot CLI를 독립적으로 업데이트하더라도, CLI argument 변경으로 인한 resume 장애를 빠르게 발견하고 안전하게 대응한다.

이 설계는 다음을 목표로 한다.

1. 최신 agent CLI 버전에 대해 고정된 버전 allowlist 없이 호환성을 검사한다.
2. 일반 resume과 dangerous permission resume을 분리해 검증한다.
3. dangerous 옵션 변경을 발견하면 잘못된 옵션을 자동 추측하지 않고 Issue로 보고한다.
4. 주 1회 최신 agent CLI를 검사하고, 문제가 발생하면 agent별 고정 GitHub Issue에 결과를 누적한다.
5. 문제 해결은 자동 코드 수정이 아니라 사람이 검토하고 `cli-sessions`를 업데이트하는 흐름으로 유지한다.

## 비목표

- 실제 사용자 세션을 자동으로 resume하거나 실행하지 않는다.
- 사용자 환경의 설치된 CLI를 runtime마다 네트워크로 조회하지 않는다.
- agent CLI의 내부 permission 의미를 완전히 보증한다고 주장하지 않는다.
- 최신 agent CLI의 breaking change를 자동으로 수정하지 않는다.
- 서비스별 모든 과거 버전을 실제로 설치해 테스트하지 않는다.

## 사용자 운영 정책

README에는 다음 정책을 명시한다.

- `cli-sessions`는 지원 agent CLI의 최소 버전을 명시한다.
- 최소 버전보다 최신인 agent CLI는 고정된 최대 버전 제한 없이 지원을 시도한다.
- 사용자가 agent CLI를 업데이트할 때 `cli-sessions`도 최신 버전인지 확인한다.
- agent CLI 업데이트 후 resume 또는 permission argument가 변경되면 `cli-sessions` 업데이트가 필요할 수 있다.
- dangerous resume은 현재 배포된 `cli-sessions` adapter가 해당 native option을 지원하는 경우에만 허용된다.
- 최신 agent CLI의 변경 여부는 runtime이 아니라 주간 maintainer 호환성 검사에서 확인한다.
- 사용자는 `sessions doctor` 또는 호환성 검사 결과를 통해 현재 agent CLI 상태를 확인할 수 있다.

## 지원 대상과 native command

공통 사용자 옵션은 `sessions --dangerously-skip-permissions`로 제공하되, 내부에서는 agent별 native 옵션으로 변환한다.

| Agent | 일반 resume | dangerous permission 옵션 |
|---|---|---|
| Claude | `claude --resume <ID>` | `--dangerously-skip-permissions` |
| Codex | `codex resume <ID>` | `--dangerously-bypass-approvals-and-sandbox` |
| Antigravity | `agy --conversation <ID>` | `--dangerously-skip-permissions` |
| Copilot | `copilot --resume=<ID>` | `--allow-all` |

이 표는 현재 배포된 adapter의 command contract 기준이며, 주간 최신 버전 검사의 대상이다. 동일한 문자열을 모든 agent에 전달해서는 안 된다.

## 아키텍처

### Agent adapter

각 agent는 독립 adapter를 갖는다. Adapter는 다음 책임만 가진다.

- 실행 파일 이름과 최소 지원 버전
- version 검사 command
- resume 관련 help 검사 command
- help 출력에서 capability를 탐지하는 규칙(주간 검사 전용)
- 일반/dangerous resume command 생성

개념적 인터페이스는 다음과 같다.

```python
class AgentAdapter(Protocol):
    name: str
    executable: str
    minimum_version: str

    def version_command(self) -> list[str]: ...
    def help_commands(self) -> list[list[str]]: ...
    def detect_capabilities(self, outputs: ProbeOutputs) -> CapabilityReport: ...
    def build_resume_command(self, session_id: str, dangerous: bool) -> list[str]: ...
```

실제 구현에서는 현재 저장소의 작은 구조를 존중하되, command 생성과 주간 capability 검사를 `cli.py`의 resume 흐름에서 분리한다. 사용자의 runtime resume 과정에서는 help probe를 수행하지 않는다. agent별 차이를 공통 함수의 조건문에 계속 추가하지 않는다.

### Capability report

각 probe는 최소한 다음 정보를 반환한다.

```json
{
  "agent": "codex",
  "executable": "codex",
  "version": "0.153.4",
  "minimum_version": "0.153.0",
  "resume": true,
  "dangerous_resume": true,
  "detected_flags": [
    "resume",
    "--dangerously-bypass-approvals-and-sandbox"
  ]
}
```

버전은 최소 버전 검증과 진단 정보에 사용한다. 최신 버전에 대한 허용 여부는 `max_version` 목록이 아니라 실제 capability 탐지 결과로 판단한다.

## Capability 검사 정책

Capability 검사는 maintainer의 주간 workflow에서 수행한다. `cli-sessions` runtime은 매 실행마다 agent CLI의 `--help`를 조회하지 않는다.

### 일반 resume

- adapter에 정의된 resume command와 식별자 위치를 사용한다.
- maintainer가 최소 버전 fixture와 최신 CLI help contract를 주기적으로 검증한다.
- help 형식이 약간 바뀌어도 실제 필요한 native option이 유지되면 최신 검사에 통과한다.

### Dangerous resume

- adapter가 정의한 agent의 native dangerous option을 사용한다.
- 해당 option을 어떤 resume command에 붙이는지는 adapter가 명시적으로 결정한다.
- 주간 검사에서 option이 사라지거나 의미가 변경된 것으로 보이면 Issue를 생성하고 maintainer가 adapter를 수정한다.
- 이름이 비슷한 다른 option으로 자동 대체하지 않는다.

정책은 다음과 같다.

| 상태 | 일반 resume | dangerous resume |
|---|---:|---:|
| 현재 adapter가 해당 native command를 지원 | 허용 | 허용 |
| 최신 CLI가 기존 contract를 유지 | 허용 | 허용 |
| 최신 CLI의 contract 변경이 주간 검사에서 발견됨 | 기존 adapter로 시도 | adapter 업데이트 전 기존 dangerous command 유지 여부를 maintainer가 판단 |
| 최소 버전 미만 | 경고 또는 차단 | 차단 |
| 주간 help 검사 실패 | runtime에는 영향 없음 | Issue 생성 후 maintainer 판단 |

## 주간 GitHub Actions workflow

### 실행 시점

```yaml
on:
  schedule:
    - cron: "0 0 * * 1"
  workflow_dispatch:
```

실제 저장소 workflow의 timezone 해석에 의존하지 않으며, 주 1회 실행이면 충분하다. `workflow_dispatch`는 서비스 CLI 업데이트 직후 수동 확인에 사용한다.

### 검사 단계

1. 저장소 checkout
2. 지원되는 Python 환경 구성
3. 최신 Claude, Codex, Antigravity, Copilot CLI 설치
4. 각 executable의 `--version` 실행
5. 각 agent의 resume 관련 `--help` 실행
6. capability contract 검사
7. adapter command builder의 fixture/fake executable 검사
8. 모든 결과를 구조화된 artifact와 workflow summary에 기록
9. 실패한 agent마다 고정 Issue를 생성하거나 갱신

workflow는 실제 session ID, API key, 사용자 prompt, 작업 디렉터리를 사용하지 않는다. 설치와 help 실행에 필요한 공개 패키지/배포 채널만 사용한다.

### 최신 버전과 최소 버전

- 주간 workflow는 각 agent의 최신 버전을 실제로 설치해 검사한다.
- 최소 지원 버전은 실제 설치 matrix가 아니라 저장소의 고정 help fixture와 unit test로 검증한다.
- 최신 버전에 대한 `max_version` 제한은 두지 않는다.
- 최신 버전에서 contract가 깨지면 Issue를 생성하고, maintainer가 adapter를 수정해 새 버전을 배포한다.
- workflow가 runtime 사용자의 동작을 직접 변경하지 않는다.

## GitHub Issue 자동화

### Issue 식별

agent와 문제 유형을 조합해 고정 식별자를 만든다.

예:

```text
[compat] codex resume capability mismatch
[compat] claude dangerous permission flag mismatch
```

Issue에는 `compatibility`, `agent:<name>`, `automated-detection` label을 사용한다.

### 생성·갱신 규칙

- 같은 agent와 같은 문제 유형의 open Issue가 있으면 새 Issue를 만들지 않는다.
- 기존 Issue에 최신 검사 결과를 comment로 추가한다.
- open Issue가 없으면 새 Issue를 생성한다.
- 이미 닫힌 Issue와 동일한 문제가 다시 발생하면 새 Issue를 생성하고 이전 Issue를 링크한다.
- workflow가 정상으로 돌아온 경우 기존 Issue에 recovery comment를 추가할 수 있으나, 자동으로 close하지 않는다.

### Issue 내용

자동 comment에는 다음을 포함한다.

- agent 이름
- 탐지된 version
- workflow 실행 시각
- repository commit SHA
- 기대한 capability
- 실제 탐지된 capability
- 관련 help 출력의 제한된 부분
- workflow run URL
- 재현용 `workflow_dispatch` 안내

출력에는 API key, session ID, 사용자 경로, prompt, 전체 환경변수를 포함하지 않는다.

### 권한

workflow는 최소 권한으로 실행한다.

```yaml
permissions:
  contents: read
  issues: write
```

pull request 생성, 코드 push, 자동 merge 권한은 부여하지 않는다. 자동화의 결과는 Issue 보고까지로 제한한다.

## 테스트 전략

### 로컬 unit test

실제 agent CLI 설치에 의존하지 않는 테스트를 추가한다.

- fixture help 출력에서 capability 탐지
- 최소 버전 fixture 처리
- 알 수 없는 최신 version의 동일 capability 허용
- dangerous flag가 사라진 help 출력에서 compatibility 검사 실패
- agent별 command argument 순서와 session ID 위치
- 다른 agent의 dangerous flag가 섞이지 않음
- 일반 resume은 dangerous capability 실패와 독립적으로 동작

### Fake executable test

실제 agent를 실행하지 않고 fake executable이 전달받은 argv를 기록하게 한다.

검증 예:

```text
Claude + dangerous  -> claude --dangerously-skip-permissions --resume ID
Codex + dangerous   -> codex --dangerously-bypass-approvals-and-sandbox resume ID
agy + dangerous     -> agy --dangerously-skip-permissions --conversation ID
Copilot + dangerous -> copilot --allow-all --resume=ID
```

### 주간 integration test

GitHub Actions에서만 다음을 확인한다.

- 최신 CLI 설치 성공 여부
- version command 성공 여부
- help command 성공 여부
- capability report 생성 여부
- contract 실패 시 Issue client가 올바른 Issue를 생성·갱신하는지

실제 session resume은 integration test에서도 수행하지 않는다.

## 실패 처리와 안전성

- CLI 설치 실패는 agent별 실패로 분리하고 나머지 agent 검사는 계속한다.
- version parsing 실패는 해당 agent의 compatibility 검사를 실패시킨다.
- help command timeout/non-zero exit는 해당 agent의 compatibility Issue를 생성한다.
- 예상하지 못한 help 형식은 자동 수정하지 않고 Issue에 보고한다.
- 자동화가 실패해도 사용자 로컬의 resume 경로를 자동으로 변경하거나 차단하지 않는다.
- dangerous option은 항상 명시적 사용자 요청이 있을 때만 추가한다.

## 구현 파일 계획

구현 시 다음 경계를 사용한다.

- `src/cli_sessions/agents.py`: agent adapter, capability 모델, native command builder
- `src/cli_sessions/cli.py`: argparse 옵션, session 선택, adapter 호출, 사용자 출력
- `tests/`: adapter와 command builder unit/fake executable 테스트
- `tests/fixtures/cli_help/`: 최소 버전 및 변경 시나리오 help fixture
- `.github/workflows/cli-compatibility.yml`: 최신 CLI 주간 검사와 수동 실행
- `.github/scripts/`: capability 결과 정규화 및 Issue 생성·갱신 보조 코드
- `README.md`: 사용자 업데이트 정책과 지원 범위 문서

구현 전까지 위 파일은 계획된 경계이며, 실제 plan 작성 시 현재 저장소의 Python 3.9 호환성과 의존성 최소화 원칙을 반영해 확정한다.

## 완료 기준

- `sessions --dangerously-skip-permissions`가 네 agent에 대해 native flag로 변환된다.
- agent별 일반/dangerous resume command unit test가 통과한다.
- 최소 버전 fixture 테스트가 통과한다.
- 등록되지 않은 최신 버전도 capability가 확인되면 검사에 통과한다.
- dangerous capability 변경이 발견되면 Issue가 생성되고 adapter 수정 전 자동 변경을 하지 않는다.
- 주간 및 수동 GitHub Actions workflow가 존재한다.
- 검사 실패 시 agent별 고정 Issue를 재사용한다.
- Issue와 workflow 로그에 민감 정보가 기록되지 않는다.
- README에 사용자 업데이트 정책이 명시된다.
- workflow에는 `contents: read`, `issues: write` 외 권한이 없다.
