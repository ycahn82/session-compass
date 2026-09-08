# cli-sessions 서비스별 CLI 호환성 및 주간 모니터링 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Claude, Codex, Antigravity, Copilot CLI의 session 수집과 resume command를 서비스별 모듈로 분리하고, `resume_min_version`과 `storage_min_version`을 기준으로 최신 CLI 호환성을 주간 검사해 GitHub Issue로 보고한다.

**Architecture:** 각 서비스는 `src/cli_sessions/agents/<service>.py`에서 collector, storage contract, resume command, compatibility 규칙을 함께 소유한다. `base.py`는 공통 타입만 제공하고 `registry.py`는 adapter 등록만 담당한다. 사용자의 runtime에서는 `--help` probe를 실행하지 않으며, GitHub Actions가 최신 CLI를 주 1회 설치해 version/help contract를 검사한다.

**Tech Stack:** Python 3.9 표준 library, `unittest`, SQLite read-only connection, JSONL fixtures, GitHub Actions, Node/npm, `actions/github-script`.

**Spec:** `docs/superpowers/specs/2026-09-08-cli-compatibility-monitoring-design.md`

## Global Constraints

- 지원 버전은 agent별 `resume_min_version`과 `storage_min_version`으로 분리한다.
- 최신 agent CLI에 `max_version` allowlist를 두지 않는다.
- 사용자의 session database는 read-only로 열고 migration하거나 수정하지 않는다.
- runtime resume 과정에서 agent CLI의 `--help`를 네트워크로 조회하지 않는다.
- dangerous permission argument는 모든 agent에 같은 문자열을 전달하지 않고 native argument로 매핑한다.
- dangerous argument 변경은 자동 수정하지 않고 GitHub Issue로 보고한다.
- 기존 collector 결과와 resume argument는 모듈 이동 전후에 보존한다.
- Python 3.9 표준 library 외 runtime dependency를 추가하지 않는다.
- GitHub Actions 권한은 `contents: read`, `issues: write`만 사용한다.
- Issue와 workflow artifact에 API key, session ID, 사용자 prompt, 전체 경로를 기록하지 않는다.

## 개발 브랜치와 실행 workspace

- 기준 checkout은 `/home/ycahn/tools/cli-sessions`이다.
- 현재 기준 branch는 `main`이며, 구현 기준 commit은 `84d98ba`이다.
- `main`에서 직접 구현하지 않고 `feat/cli-compatibility-monitoring` branch를 만든다.
- 구현 worktree는 `/home/ycahn/tools/cli-sessions-compatibility`로 만든다.
- 모든 source, fixture, unit test, package build는 구현 worktree에서 실행한다.
- `/home/ycahn/codes/Quote`와 `/home/ycahn/codes/PPLL`은 이 작업의 대상이 아니며 읽거나 수정하지 않는다.
- 구현 시작 전 다음 명령으로 branch/worktree를 확인한다.

```bash
git -C /home/ycahn/tools/cli-sessions status --short --branch
git -C /home/ycahn/tools/cli-sessions worktree add -b feat/cli-compatibility-monitoring /home/ycahn/tools/cli-sessions-compatibility main
git -C /home/ycahn/tools/cli-sessions-compatibility status --short --branch
```

- 실제 사용자 `~/.claude`, `~/.codex`, `~/.gemini`, `~/.copilot` storage는 unit test 입력으로 사용하지 않는다.
- local test는 temporary directory와 repository fixture만 사용한다.
- 실제 설치된 service CLI는 local에서 `--version`/`--help` 확인이 필요한 경우에만 읽기 방식으로 호출하며, `--resume`, model request, login, session creation은 실행하지 않는다.
- 최신 service CLI 설치와 version/help integration check는 GitHub Actions Ubuntu runner에서만 수행한다.

## 테스트 실행 위치와 검증 경계

| 검증 종류 | 실행 위치 | 입력 | 금지 사항 |
|---|---|---|---|
| characterization/unit test | `/home/ycahn/tools/cli-sessions-compatibility` | temporary directory, committed fixture | 사용자 home storage 사용 금지 |
| storage contract test | 구현 worktree | synthetic JSONL/SQLite fixture | 실제 DB migration/write 금지 |
| command builder test | 구현 worktree | fake executable 또는 mocked subprocess | 실제 agent 실행 금지 |
| package build | 구현 worktree | local source tree | 다른 workspace 파일 참조 금지 |
| latest CLI compatibility | GitHub Actions runner | 최신 공개 CLI의 `--version`/`--help` | login, model 호출, 실제 resume 금지 |

로컬 unit test의 표준 실행 명령은 다음과 같다.

```bash
cd /home/ycahn/tools/cli-sessions-compatibility
PYTHONPATH=src python -m unittest discover -s tests -v
python3 -m pip wheel --no-deps --no-build-isolation . -w /tmp/cli-sessions-wheel
```

각 task의 commit은 `feat/cli-compatibility-monitoring` branch에 생성하고, `main`에는 직접 commit하지 않는다.

---

## 파일 구조

구현 전후의 책임 경계는 다음과 같다.

```text
src/cli_sessions/
├── cli.py                         # argparse, 수집 통합, 출력, 선택, subprocess 실행
└── agents/
    ├── __init__.py
    ├── base.py                    # 공통 protocol, dataclass/TypedDict, report 타입
    ├── claude.py                  # Claude JSONL collector와 command contract
    ├── codex.py                   # Codex SQLite/JSONL collector와 command contract
    ├── antigravity.py             # Antigravity SQLite/JSONL collector와 command contract
    ├── copilot.py                 # Copilot SQLite collector와 command contract
    └── registry.py                # agent 이름과 adapter 연결

tests/
├── test_characterization.py       # 모듈 이동 전후의 기존 동작 보호
├── agents/
│   ├── test_claude.py
│   ├── test_codex.py
│   ├── test_antigravity.py
│   ├── test_copilot.py
│   ├── test_registry.py
│   └── test_compatibility.py
└── fixtures/
    ├── cli_help/
    └── storage/

scripts/
├── probe_cli_compatibility.py     # 최신 CLI version/help 검사
└── build_compatibility_report.py  # Issue/comment용 민감정보 제거 report

.github/workflows/cli-compatibility.yml
.github/scripts/update_compatibility_issue.js
README.md
```

---

### Task 1: 현재 동작 characterization test 고정

**Files:**
- Create: `tests/test_characterization.py`
- Create: `tests/__init__.py`
- Test: `src/cli_sessions/cli.py`

**Interfaces:**
- Consumes: 현재 `collect_*_sessions()`와 `resume_session()` 함수
- Produces: 모듈 이동 전후 비교에 사용할 session record와 command argument 기대값

- [x] **Step 1: 현재 데이터 형식을 재현하는 최소 fixture 테스트 작성**

Claude JSONL, Codex SQLite, Antigravity SQLite/history JSONL, Copilot SQLite를 `tempfile.TemporaryDirectory()` 안에 만들고 현재 collector가 반환하는 다음 필드를 검증한다.

```python
expected_keys = {"tool", "id", "cwd", "summary", "last_active"}
assert expected_keys <= set(session)
```

테스트는 실제 `$HOME`을 읽지 않도록 `cli.CLAUDE_PROJECTS_DIR`, `cli.CODEX_SESSIONS_DIR`, `cli.CODEX_INDEX_FILE`, `cli.AGY_CONVERSATIONS_DIR`, `cli.AGY_HISTORY_FILE`, `cli.AGY_METADATA_FILE`, `cli.COPILOT_DB_FILE`을 임시 경로로 patch한다.

- [x] **Step 2: 현재 resume command argument characterization test 작성**

`shutil.which`와 `subprocess.run`을 patch하고 네 agent에 대해 현재 command를 기록한다.

```python
assert captured["claude"] == ["claude", "--resume", "claude-id"]
assert captured["codex"] == ["codex", "resume", "codex-id"]
assert captured["agy"] == ["agy", "--conversation", "agy-id"]
assert captured["copilot"] == ["copilot", "--resume=copilot-id"]
```

- [x] **Step 3: 테스트를 실행해 baseline을 확인**

Run: `PYTHONPATH=src python -m unittest discover -s tests -v`

Expected: 새 characterization test와 기존 테스트가 모두 PASS한다. 실패하면 모듈 이동 전에 현재 동작을 정확히 기록하도록 fixture를 수정한다.

- [x] **Step 4: characterization baseline을 커밋**

```bash
git add tests/test_characterization.py tests/__init__.py
git commit -m "test: capture current session and resume behavior"
```

---

### Task 2: 공통 adapter 타입과 서비스별 모듈로 behavior-preserving 이동

**Files:**
- Create: `src/cli_sessions/agents/__init__.py`
- Create: `src/cli_sessions/agents/base.py`
- Create: `src/cli_sessions/agents/claude.py`
- Create: `src/cli_sessions/agents/codex.py`
- Create: `src/cli_sessions/agents/antigravity.py`
- Create: `src/cli_sessions/agents/copilot.py`
- Create: `tests/agents/__init__.py`
- Modify: `src/cli_sessions/cli.py`
- Test: `tests/test_characterization.py`

**Interfaces:**
- Consumes: Task 1의 baseline
- Produces: 각 모듈의 `collect_sessions() -> list[dict[str, Any]]`, `build_resume_command(session_id: str, dangerous: bool = False) -> list[str]`

- [x] **Step 1: 공통 타입과 protocol의 failing import test 작성**

`tests/agents/test_registry.py`에 다음 import와 기본 속성 검사를 먼저 작성한다.

```python
from cli_sessions.agents.base import AgentAdapter
from cli_sessions.agents.registry import get_adapters

assert {adapter.name for adapter in get_adapters()} == {
    "claude", "codex", "agy", "copilot"
}
```

Run: `PYTHONPATH=src python -m unittest tests.agents.test_registry -v`

Expected: FAIL because the `agents` package and registry do not yet exist.

- [x] **Step 2: `base.py`에 공통 타입을 구현**

Python 3.9 표준 library만 사용해 `AgentAdapter` protocol, `AgentCompatibility`, `ProbeResult`, `CapabilityReport`를 정의한다. `AgentCompatibility`는 다음 필드를 가진다.

```python
@dataclass(frozen=True)
class AgentCompatibility:
    agent: str
    resume_min_version: str
    storage_min_version: str
    tested_latest_version: str | None = None
```

Python 3.9에서는 `str | None` 대신 `Optional[str]`을 사용한다.

- [x] **Step 3: 네 서비스 collector를 서비스별 파일로 이동**

기존 함수의 parsing 순서, fallback 값, timestamp 변환, read-only SQLite connection을 그대로 유지한다. 각 모듈은 현재 `cli.py`의 서비스별 상수도 함께 소유한다. 모듈 이동 과정에서 SQLite connection은 명시적으로 close해 현재 baseline에서 관찰된 `ResourceWarning`을 제거한다.

```python
class ClaudeAdapter:
    name = "claude"

    def collect_sessions(self) -> list[dict[str, Any]]:
        ...

    def build_resume_command(self, session_id: str, dangerous: bool = False) -> list[str]:
        ...
```

이 단계에서는 `dangerous=True`도 기존 command와 동일하게 반환해 behavior-preserving 이동을 유지한다. 실제 dangerous flag는 Task 6에서 추가한다.

- [x] **Step 4: registry와 `cli.py` 연결 구현**

`registry.py`에 `get_adapters() -> list[AgentAdapter]`와 `get_adapter(name: str) -> AgentAdapter`를 구현한다. `cli.py`는 registry를 순회해 session을 수집하고 선택된 adapter의 `build_resume_command()`를 호출한다.

- [x] **Step 5: 모듈 이동 후 characterization test 실행**

Run: `PYTHONPATH=src python -m unittest discover -s tests -v`

Expected: Task 1에서 고정한 session record 필드, sorting, fallback, 네 resume command가 모두 동일하다.

- [ ] **Step 6: 구조 이동을 커밋**

```bash
git add src/cli_sessions/agents src/cli_sessions/cli.py tests
git commit -m "refactor: split agent session integrations by service"
```

---

### Task 3: resume 후보 판정과 기본 목록 필터

**Files:**
- Modify: `src/cli_sessions/agents/base.py`
- Modify: `src/cli_sessions/agents/claude.py`
- Modify: `src/cli_sessions/agents/codex.py`
- Modify: `src/cli_sessions/agents/antigravity.py`
- Modify: `src/cli_sessions/agents/copilot.py`
- Modify: `src/cli_sessions/agents/registry.py`
- Modify: `src/cli_sessions/cli.py`
- Create: `tests/agents/test_resumability.py`

**Interfaces:**
- Consumes: Task 2의 서비스별 adapter와 `list[dict[str, Any]]` session record
- Produces: `ResumeStatus`, `classify_resumability(session) -> ResumeStatus`, `filter_resume_candidates(sessions, include_unverified) -> list[dict[str, Any]]`

- [x] **Step 1: 서비스별 resumability 실패 테스트 작성**

다음 record를 기본 목록에서 제외하는 테스트를 먼저 작성한다.

```python
assert classify_resumability({"tool": "claude", "record_kind": "bridge_session"}) == ResumeStatus.METADATA_ONLY
assert classify_resumability({"tool": "claude", "id": "id", "has_conversation_content": False}) == ResumeStatus.METADATA_ONLY
assert classify_resumability({"tool": "codex", "id": "id", "has_rollout": False}) == ResumeStatus.INVALID
```

AGY의 summary가 비어 있어도 DB와 유효한 activity record가 있는 session은 숨기지 않는다.

- [x] **Step 2: resumability 상태와 provenance 타입 구현**

`base.py`에 다음 enum과 내부 필드를 추가한다.

```python
class ResumeStatus(Enum):
    RESUMABLE = "resumable"
    LIKELY_RESUMABLE = "likely_resumable"
    METADATA_ONLY = "metadata_only"
    INVALID = "invalid"
```

session record에는 `resume_status`, `record_kind`, `summary_source`를 추가하되 기존 표시용 필드는 유지한다.

- [x] **Step 3: Claude bridge-session 판정 구현**

`type == "bridge-session"`이고 user/assistant conversation record가 없는 JSONL은 `METADATA_ONLY`로 분류한다. 실제 conversation record가 있거나 검증된 Remote Control session 정보가 있으면 `RESUMABLE` 또는 `LIKELY_RESUMABLE`로 분류한다.

- [x] **Step 4: Codex, AGY, Copilot evidence 판정 구현**

Codex는 `threads` row와 연결된 rollout artifact를 확인한다. AGY는 conversation DB와 유효한 `steps` row를 확인하되, `steps` count를 summary로 사용하지 않는다. Copilot은 `sessions` row와 ID를 확인한다.

- [x] **Step 5: 기본 filter와 진단 option 구현**

`cli.py`에 `--include-unverified`를 추가한다. 기본값은 `False`이며 `RESUMABLE`, `LIKELY_RESUMABLE`만 목록에 남긴다. 옵션이 켜지면 `METADATA_ONLY`, `INVALID`도 표시하고 각 row에 상태를 표시한다.

숨겨진 개수가 있으면 다음과 같이 안내한다.

```text
2 unverified sessions hidden. Use --include-unverified to inspect them.
```

- [x] **Step 6: resumability test 실행**

Run: `PYTHONPATH=src python -m unittest tests.agents.test_resumability -v`

Expected: 서비스별 상태 판정, 기본 filter, `--include-unverified`, summary가 없어도 resume evidence가 있는 session을 유지하는 동작이 PASS한다.

- [ ] **Step 7: resumability 구현을 커밋**

```bash
git add src/cli_sessions/agents src/cli_sessions/cli.py tests/agents/test_resumability.py
git commit -m "feat: show only resumable session candidates by default"
```

---

### Task 4: 서비스별 storage contract fixture와 read-only schema 검증

**Files:**
- Create: `tests/fixtures/storage/claude/legacy.jsonl`
- Create: `tests/fixtures/storage/claude/current.jsonl`
- Create: `tests/fixtures/storage/codex/legacy.sqlite`
- Create: `tests/fixtures/storage/codex/current.sqlite`
- Create: `tests/fixtures/storage/antigravity/current.db`
- Create: `tests/fixtures/storage/antigravity/history.jsonl`
- Create: `tests/fixtures/storage/copilot/current.db`
- Modify: `src/cli_sessions/agents/claude.py`
- Modify: `src/cli_sessions/agents/codex.py`
- Modify: `src/cli_sessions/agents/antigravity.py`
- Modify: `src/cli_sessions/agents/copilot.py`
- Create: `tests/agents/test_storage_contracts.py`

**Interfaces:**
- Consumes: Task 2의 서비스별 `collect_sessions()`와 Task 3의 resumability 상태
- Produces: 서비스별 필수 storage contract를 확인하는 `check_storage_contract(path) -> ContractReport`

- [x] **Step 1: fixture 기반 contract 실패 테스트 작성**

각 서비스 fixture에서 필수 table/field를 하나씩 제거한 변형을 만들고, missing required field가 `ContractReport(ok=False, missing=...)`를 반환하는지 검증한다. 테스트는 실제 사용자 DB를 절대 변경하지 않는다.

```python
report = adapter.check_storage_contract(incomplete_path)
assert report.ok is False
assert "threads.updated_at_ms" in report.missing
```

- [x] **Step 2: 정상 fixture contract 테스트 작성**

Claude는 JSONL 필드, Codex는 `threads`, Antigravity는 `steps`, Copilot은 `sessions`와 `turns`의 필수 column을 검증한다. optional field가 없는 fixture는 warning으로 처리하고 `ok=True`를 유지한다.

- [x] **Step 3: read-only schema probe 구현**

SQLite는 다음 형태로만 연다.

```python
sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
```

`PRAGMA` 또는 `SELECT`는 metadata 확인에만 사용하고 `CREATE`, `ALTER`, `INSERT`, `UPDATE`, `DELETE`를 호출하지 않는다. JSONL은 읽기만 수행한다.

- [x] **Step 4: collector의 optional/missing field 동작 검증**

optional field가 없는 legacy fixture에서 빈 summary 또는 file mtime fallback이 기존 contract대로 동작하는지 테스트한다. required table/field가 없는 경우에는 해당 adapter가 빈 session 목록과 진단 가능한 contract report를 반환하도록 한다.

- [x] **Step 5: storage contract test 실행**

Run: `PYTHONPATH=src python -m unittest tests.agents.test_storage_contracts -v`

Expected: 정상 fixture는 PASS하고 의도적으로 불완전한 fixture는 정확한 missing field를 보고한다.

- [ ] **Step 6: storage contract 구현을 커밋**

```bash
git add src/cli_sessions/agents tests/fixtures/storage tests/agents/test_storage_contracts.py
git commit -m "test: define per-agent session storage contracts"
```

---

### Task 5: 서비스별 최소 버전 조사와 compatibility manifest 확정

**Files:**
- Create: `tests/fixtures/cli_help/claude-minimum.txt`
- Create: `tests/fixtures/cli_help/codex-minimum.txt`
- Create: `tests/fixtures/cli_help/agy-minimum.txt`
- Create: `tests/fixtures/cli_help/copilot-minimum.txt`
- Modify: `src/cli_sessions/agents/claude.py`
- Modify: `src/cli_sessions/agents/codex.py`
- Modify: `src/cli_sessions/agents/antigravity.py`
- Modify: `src/cli_sessions/agents/copilot.py`
- Create: `tests/agents/test_compatibility.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: Task 4의 storage contract와 공개 release artifact
- Produces: 각 adapter의 `AgentCompatibility`와 고정된 minimum help fixture

- [x] **Step 1: 공식 설치 채널과 release 목록을 조사**

다음 공식 배포 경로를 기준으로 version artifact를 수집한다.

```text
Claude:       npm install -g @anthropic-ai/claude-code
Codex:        npm install -g @openai/codex
Copilot:      npm install -g @github/copilot
Antigravity:  https://antigravity.google/cli/install.sh
```

조사 결과는 README에 링크로 기록한다. 인증이나 실제 model 호출 없이 `--version`과 `--help`를 실행할 수 있는 release만 대상으로 한다.

- [x] **Step 2: resume 최소 버전을 결정**

각 agent에서 과거 release 중 resume command, session ID 위치, dangerous native option이 동시에 검증되는 가장 오래된 버전을 선택한다. 과거 artifact를 재현할 수 없는 agent는 구현 시점에 재현 가능한 최초 release를 floor로 삼고, README에 “검증된 최초 버전”으로 명시한다. 현재 설치 버전은 `tested_latest_version`으로만 기록한다.

- [x] **Step 3: storage 최소 버전을 결정**

각 선택 release가 생성하는 session storage fixture가 Task 4의 required contract를 만족하는지 확인한다. resume command와 storage contract의 최초 통과 버전이 다르면 두 버전을 독립적으로 기록한다.

- [x] **Step 4: help fixture와 compatibility 테스트 작성**

다음 정책을 테스트한다.

```text
minimum version fixture + required flags       -> PASS
unknown newer version + unchanged flags        -> PASS
missing resume flag                             -> FAIL
missing dangerous flag                          -> FAIL only for dangerous capability
```

- [x] **Step 5: 최소 버전과 storage contract를 README에 기록**

README에 agent별 `resume_min_version`, `storage_min_version`, `tested_latest_version`의 의미와 업데이트 정책을 추가한다. 숫자는 Task 5에서 실제 release artifact와 fixture로 확인한 값만 기록한다.

- [ ] **Step 6: compatibility manifest와 테스트를 커밋**

```bash
git add src/cli_sessions/agents tests/fixtures/cli_help tests/agents/test_compatibility.py README.md
git commit -m "feat: record per-agent CLI and storage compatibility floors"
```

---

### Task 6: 공통 dangerous 옵션과 agent별 native resume command 구현

**Files:**
- Modify: `src/cli_sessions/cli.py`
- Modify: `src/cli_sessions/agents/claude.py`
- Modify: `src/cli_sessions/agents/codex.py`
- Modify: `src/cli_sessions/agents/antigravity.py`
- Modify: `src/cli_sessions/agents/copilot.py`
- Create: `tests/agents/test_resume_commands.py`

**Interfaces:**
- Consumes: Task 2의 `AgentAdapter.build_resume_command()`와 Task 5의 native contract
- Produces: `sessions --dangerously-skip-permissions`와 agent별 안전한 command mapping

- [x] **Step 1: dangerous command의 failing tests 작성**

```python
assert claude.build_resume_command("id", True) == [
    "claude", "--dangerously-skip-permissions", "--resume", "id"
]
assert codex.build_resume_command("id", True) == [
    "codex", "--dangerously-bypass-approvals-and-sandbox", "resume", "id"
]
assert agy.build_resume_command("id", True) == [
    "agy", "--dangerously-skip-permissions", "--conversation", "id"
]
assert copilot.build_resume_command("id", True) == [
    "copilot", "--allow-all", "--resume=id"
]
```

또한 `dangerous=False`에서는 Task 1의 baseline command가 그대로 유지되는지 검증한다.

- [x] **Step 2: argparse 옵션 추가**

`cli.py`에 `--dangerously-skip-permissions` boolean option을 추가하고, 선택된 session의 adapter에만 `dangerous=True`를 전달한다. 기본값은 `False`다.

- [x] **Step 3: agent별 native flag 구현**

네 adapter가 서로 다른 native flag를 직접 생성하게 한다. `cli.py`나 공통 base에 agent별 flag 문자열을 두지 않는다.

- [x] **Step 4: command test와 CLI parser test 실행**

Run: `PYTHONPATH=src python -m unittest tests.agents.test_resume_commands tests.agents.test_registry -v`

Expected: 모든 native mapping과 기본 비활성 동작이 PASS한다.

- [ ] **Step 5: dangerous resume 구현을 커밋**

```bash
git add src/cli_sessions/cli.py src/cli_sessions/agents tests/agents/test_resume_commands.py
git commit -m "feat: map dangerous resume flags per agent"
```

---

### Task 7: 최신 CLI 주간 compatibility probe 구현

**Files:**
- Create: `scripts/probe_cli_compatibility.py`
- Create: `scripts/build_compatibility_report.py`
- Create: `tests/test_compatibility_probe.py`

**Interfaces:**
- Consumes: 각 adapter의 `version_command()`, `help_commands()`, Task 5의 fixture/contract 규칙
- Produces: `compatibility-report.json` with agent/version/capability/status/failure fields

- [x] **Step 1: fake executable 기반 probe 실패 테스트 작성**

임시 executable이 `--version`과 help 명령에 정해진 stdout을 반환하도록 만들고, probe가 실제 model 호출 없이 결과를 생성하는지 검증한다.

```python
result = probe_agent(adapter, executable_dir)
assert result["version"] == "0.153.4"
assert result["resume"] is True
assert result["dangerous_resume"] is True
```

- [x] **Step 2: probe runner 구현**

각 subprocess 호출에 timeout을 적용하고 stdout/stderr에서 session ID, prompt, 경로처럼 민감할 수 있는 값을 report에 복사하지 않는다. non-zero exit와 timeout은 agent별 실패로 저장하고 다른 agent 검사를 계속한다.

- [x] **Step 3: 최신 version/help contract 연결**

최신 CLI의 version/help를 adapter 규칙으로 검사한다. `max_version` 비교는 하지 않고, required resume/native dangerous option 존재 여부와 storage contract fixture 검증 결과를 기록한다.

- [x] **Step 4: report sanitizer 구현**

`build_compatibility_report.py`는 version, detected flags, failure reason, bounded help excerpt, commit SHA만 출력한다. 사용자 home 절대 경로, API key 패턴, UUID session ID, prompt 내용은 제거한다.

- [x] **Step 5: probe unit test 실행**

Run: `PYTHONPATH=src python -m unittest tests.test_compatibility_probe -v`

Expected: 성공·실패·timeout·민감정보 제거 시나리오가 모두 PASS한다.

- [ ] **Step 6: probe 구현을 커밋**

```bash
git add scripts tests/test_compatibility_probe.py
git commit -m "feat: add sanitized CLI compatibility probe"
```

---

### Task 8: GitHub Actions 설치·주간 실행·artifact 수집

**Files:**
- Create: `.github/workflows/cli-compatibility.yml`
- Modify: `scripts/probe_cli_compatibility.py`
- Test: `tests/test_compatibility_probe.py`

**Interfaces:**
- Consumes: Task 7의 probe와 report
- Produces: 주간 최신 CLI compatibility artifact와 Issue reporter가 읽는 JSON

- [x] **Step 1: workflow trigger와 권한 정의**

다음 trigger와 권한만 사용한다.

```yaml
on:
  schedule:
    - cron: "0 0 * * 1"
  workflow_dispatch:

permissions:
  contents: read
  issues: write
```

- [x] **Step 2: 최신 CLI 설치 단계 작성**

Node를 설치한 뒤 다음 공개 배포 명령을 실행한다.

```bash
npm install --global @anthropic-ai/claude-code
npm install --global @openai/codex
npm install --global @github/copilot
curl -fsSL https://antigravity.google/cli/install.sh | bash
```

설치 직후 각 command의 `--version`을 기록한다. 실제 login, model request, session creation은 실행하지 않는다.

- [x] **Step 3: probe와 artifact upload 연결**

`PYTHONPATH=src python scripts/probe_cli_compatibility.py --output compatibility-report.json`을 실행하고, 성공/실패와 관계없이 `compatibility-report.json` 및 bounded log를 `actions/upload-artifact@v4`로 업로드한다.

- [x] **Step 4: agent별 실패 격리 확인**

한 agent 설치나 help가 실패해도 나머지 agent의 결과가 생성되도록 workflow exit status를 report 단계 이후까지 보존한다. 최종 job은 하나라도 contract failure가 있으면 실패 상태가 된다.

- [x] **Step 5: workflow YAML 정적 검증**

Run: `python3 - <<'PY'\nfrom pathlib import Path\ntext = Path('.github/workflows/cli-compatibility.yml').read_text()\nassert 'workflow_dispatch:' in text\nassert 'issues: write' in text\nassert 'contents: read' in text\nassert 'resume' in text\nPY`

Expected: 모든 assertion이 PASS하고 write 권한이 `issues` 외에 추가되지 않는다.

- [ ] **Step 6: workflow를 커밋**

```bash
git add .github/workflows/cli-compatibility.yml scripts
git commit -m "ci: check latest agent CLI compatibility weekly"
```

---

### Task 9: 고정 Issue 생성·갱신 자동화

**Files:**
- Create: `.github/scripts/update_compatibility_issue.js`
- Create: `tests/fixtures/compatibility/failure.json`
- Create: `tests/fixtures/compatibility/recovery.json`
- Create: `tests/test_issue_payload.py`
- Modify: `.github/workflows/cli-compatibility.yml`

**Interfaces:**
- Consumes: Task 7의 sanitized report
- Produces: agent와 문제 유형별 open Issue 재사용 및 comment payload

- [ ] **Step 1: Issue key와 중복 정책 test fixture 작성**

다음 title 규칙을 고정한다.

```text
[compat] codex resume capability mismatch
[compat] codex storage contract mismatch
[compat] codex CLI installation failure
```

실제 title은 report의 agent 값으로 다음 Python 형식으로 만든다: `f"[compat] {agent} {problem_type}"`. open Issue 검색은 생성된 exact title과 `is:issue is:open` 조건을 사용한다. 동일 title이 있으면 새 Issue를 생성하지 않는다.

- [ ] **Step 2: GitHub API script 구현**

`actions/github-script@v7`에서 report를 읽어 다음을 수행한다.

```text
open matching issue exists -> add sanitized result comment
no open matching issue    -> create issue with labels
closed matching issue     -> create a new issue and link previous issue
```

사용할 label은 `compatibility`, `automated-detection`, `agent:codex`와 같은 agent별 label이다. issue body/comment에는 artifact URL과 workflow run URL을 넣되 원본 전체 log는 넣지 않는다.

- [ ] **Step 3: recovery comment 구현**

이전 실행에서 실패했고 현재 실행에서 정상으로 돌아오면 기존 Issue에 recovery comment를 추가한다. Issue를 자동 close하지 않는다.

- [ ] **Step 4: workflow에 always-run report 단계 연결**

probe가 실패해도 `if: ${{ always() }}`인 reporter 단계가 실행되도록 한다. GitHub token은 Issue 단계에만 전달하고, CLI 설치/probe subprocess에는 전달하지 않는다.

- [ ] **Step 5: Issue payload sanitizer test 실행**

Run: `PYTHONPATH=src python -m unittest tests.test_issue_payload -v`

Expected: 동일 title 재사용, 민감정보 제거, recovery comment, agent별 label이 모두 PASS한다.

- [ ] **Step 6: Issue automation을 커밋**

```bash
git add .github/scripts tests/fixtures/compatibility tests/test_issue_payload.py .github/workflows/cli-compatibility.yml
git commit -m "ci: report compatibility failures in stable issues"
```

---

### Task 10: README와 전체 검증

**Files:**
- Modify: `README.md`
- Test: all files under `tests/`

**Interfaces:**
- Consumes: Task 5의 version floor와 Task 8-9의 workflow/Issue behavior
- Produces: 사용자 설치·업데이트·지원 버전 문서와 release-ready verification result

- [ ] **Step 1: README 사용 정책 작성**

다음 내용을 현재 Usage/How it works 섹션에 추가한다.

```text
서비스 CLI를 업데이트한 뒤 cli-sessions도 최신 버전인지 확인한다.
지원 버전은 resume_min_version과 storage_min_version으로 관리한다.
최신 서비스 CLI의 argument 또는 session storage 변경은 주간 compatibility 검사에서 발견된다.
dangerous resume 관련 변경은 자동 수정하지 않고 GitHub Issue로 보고된다.
```

agent별 실제 version floor, storage path, required schema를 표로 기록한다.

- [ ] **Step 2: 전체 unit test 실행**

Run: `PYTHONPATH=src python -m unittest discover -s tests -v`

Expected: characterization, service adapter, storage contract, compatibility probe, Issue payload 테스트가 모두 PASS한다.

- [ ] **Step 3: package build 검증**

Run: `python3 -m pip wheel --no-deps --no-build-isolation . -w /tmp/cli-sessions-wheel`

Expected: wheel build가 성공하고 `src/cli_sessions/agents/` 패키지가 wheel에 포함된다.

- [ ] **Step 4: CLI parser smoke 검증**

Run: `PYTHONPATH=src python -m cli_sessions.cli --help`

Expected: `--dangerously-skip-permissions`, `--claude`, `--codex`, `--agy`, `--copilot`가 help에 표시된다.

- [ ] **Step 5: diff와 민감정보 점검**

Run: `git diff --check` 그리고 `rg -n "API_KEY|TOKEN|session_id|prompt" README.md docs/superpowers .github scripts src tests`

Expected: 실제 secret 값이나 사용자 session 내용이 없고, 의도된 schema field/테스트 이름만 남는다.

- [ ] **Step 6: 최종 검증 결과를 커밋**

```bash
git add README.md tests src .github scripts
git commit -m "docs: document agent compatibility support policy"
```

---

## 최종 완료 기준

- 네 서비스의 collector와 resume 로직이 서비스별 모듈로 분리되어 있다.
- 모듈 이동 전후의 session record와 기본 resume argument가 동일하다.
- `sessions --dangerously-skip-permissions`가 agent별 native flag로 변환된다.
- `resume_min_version`과 `storage_min_version`이 서비스별로 기록되어 있다.
- JSONL/SQLite fixture와 read-only storage contract 테스트가 존재한다.
- 최신 CLI에 `max_version` 제한 없이 주간 version/help 검사가 실행된다.
- 실제 session resume 없이 compatibility report가 생성된다.
- 실패한 agent와 문제 유형별 open Issue가 재사용된다.
- GitHub Actions 권한이 `contents: read`, `issues: write`로 제한된다.
- README가 사용자 CLI 업데이트 정책과 서비스별 version/storage contract를 설명한다.
- 전체 unit test와 package build가 통과한다.
