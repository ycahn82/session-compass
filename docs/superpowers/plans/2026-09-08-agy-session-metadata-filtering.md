# AGY 사용자 세션 metadata 및 resume 후보 정리 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Antigravity의 UI 사용자 채팅 metadata를 기준으로 일반 session만 resume 목록에 표시하고, internal/subagent session과 metadata 누락을 자동 테스트로 검출한다.

**Architecture:** `antigravity.py`가 `conversation_summaries.db`와 `cache/conversation_metadata.json`을 read-only로 읽는다. `title`을 summary 최우선 source로 사용하고, 비어 있으면 `preview`를 사용한다. `is_internal=true` 또는 summary catalog가 없는 conversation은 기본 resume 후보에서 제외한다. 두 GitHub Actions workflow는 공통 unittest suite를 실행한다.

**Tech Stack:** Python 3.9 표준 library, `sqlite3` read-only URI, JSON, `unittest`, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-08-cli-compatibility-monitoring-design.md`

## Global Constraints

- 사용자 AGY storage는 `mode=ro`로 열고 쓰기, migration, vacuum을 하지 않는다.
- `conversation_summaries.db`의 `title`을 summary 최우선 source로 사용한다.
- `title`이 비어 있으면 같은 row의 `preview`를 사용한다.
- `is_internal=true`인 internal/subagent session은 기본 resume 목록에서 제외한다.
- summary catalog row가 없는 session은 기본 resume 후보에서 제외한다.
- internal/unknown session은 진단 경로에서만 표시하고 resumable로 분류하지 않는다.
- GitHub Actions는 기존 표준 library unittest만 실행한다.

## 개발 workspace와 검증 경계

- Branch: `feat/cli-compatibility-monitoring`
- Workspace: `/home/ycahn/tools/cli-sessions-compatibility`
- 실제 `~/.gemini/antigravity-cli`는 read-only smoke 확인에만 사용한다.
- unit test는 temporary directory의 synthetic SQLite/JSON fixture만 사용한다.

---

### Task 1: AGY catalog contract와 regression test 추가

**Files:**
- Create: `tests/agents/test_antigravity_metadata.py`
- Modify: `tests/agents/test_storage_contracts.py`

- [ ] **Step 1:** Temporary directory에 `cache/conversation_metadata.json`, `conversation_summaries.db`, `conversations/<id>.db`, `history.jsonl`을 만들고 title이 있는 user session, preview만 있는 user session, internal session, uncatalogued session을 준비한다.
- [ ] **Step 2:** 현재 구현에서 실패하는 title/preview 우선순위 테스트를 작성한다. `title`이 있으면 title, 비어 있으면 preview가 summary가 되어야 한다.
- [ ] **Step 3:** internal 및 uncatalogued session이 기본 `collect_sessions()` 결과에서 제외되는 테스트를 작성한다.
- [ ] **Step 4:** 표시되는 AGY record의 `summary`와 `cwd`가 비어 있지 않은지 검증하는 테스트를 작성한다.
- [ ] **Step 5:** `PYTHONPATH=src python -m unittest tests.agents.test_antigravity_metadata -v`를 실행해 현재 구현의 실패를 확인한다.
- [ ] **Step 6:** `git commit -m "test: define AGY user session metadata contract"`로 테스트를 커밋한다.

### Task 2: AGY catalog reader와 user-session collector 구현

**Files:**
- Modify: `src/cli_sessions/agents/antigravity.py`
- Modify: `tests/agents/test_antigravity_metadata.py`

- [ ] **Step 1:** `conversation_summaries` table을 read-only로 읽어 `title`, `preview`, `workspace_uris`를 conversation ID별로 반환하는 helper를 구현한다. malformed JSON/없는 DB는 빈 catalog로 처리하고 connection은 닫는다.
- [ ] **Step 2:** `conversation_metadata.json`의 `is_internal` 값을 읽는다. catalog row가 없거나 internal이면 기본 collector에서 제외한다.
- [ ] **Step 3:** summary는 `title -> preview`, cwd는 `workspace_uris[0] -> history workspace` 순으로 선택한다. summary 또는 cwd가 없는 catalog row는 기본 resume 후보에서 제외한다.
- [ ] **Step 4:** 정상 record에 `summary_source`, `workspace_source`, `has_conversation_content=True` provenance를 기록한다.
- [ ] **Step 5:** 대상 테스트와 `PYTHONPATH=src python -m unittest discover -s tests -v`를 실행한다.
- [ ] **Step 6:** `git commit -m "fix: use AGY user conversation catalog for resume"`으로 구현을 커밋한다.

### Task 3: 진단 경로와 resume 차단 보강

**Files:**
- Modify: `src/cli_sessions/agents/base.py`
- Modify: `src/cli_sessions/cli.py`
- Modify: `tests/agents/test_resumability.py`

- [ ] **Step 1:** internal/uncatalogued record가 진단 목록에 나타나더라도 `ResumeStatus.METADATA_ONLY` 또는 동등한 non-resumable 상태인지 검증하는 테스트를 작성한다.
- [ ] **Step 2:** `--include-unverified`에서 선택된 record가 resumable이 아니면 외부 AGY CLI를 실행하지 않고 상태만 출력하도록 구현한다.
- [ ] **Step 3:** resumability 대상 테스트와 전체 unittest를 실행한다.
- [ ] **Step 4:** `git commit -m "fix: prevent internal AGY sessions from resume"`으로 커밋한다.

### Task 4: GitHub Actions regression suite 연결

**Files:**
- Modify: `.github/workflows/cli-compatibility.yml`
- Modify: `.github/workflows/cli-compatibility-pr.yml`
- Modify: `docs/superpowers/progress/2026-09-08-cli-compatibility-monitoring-progress.md`

- [ ] **Step 1:** 두 workflow의 CLI 설치 전에 `PYTHONPATH=src python -m unittest discover -s tests -v` step을 추가한다.
- [ ] **Step 2:** 전체 unittest와 `git diff --check`를 실행한다.
- [ ] **Step 3:** workflow 및 progress 문서를 `git commit -m "ci: run AGY metadata regression tests"`로 커밋한다.

### Task 5: 실제 서버 read-only 검증

**Files:**
- Modify: `docs/superpowers/progress/2026-09-08-cli-compatibility-monitoring-progress.md`

- [ ] **Step 1:** 전체 unittest와 `python3 -m pip wheel --no-deps --no-build-isolation . -w /tmp/cli-sessions-wheel`을 실행한다.
- [ ] **Step 2:** `printf 'q\\n' | sessions --agy`로 현재 서버 목록을 확인한다. internal/subagent는 숨고 catalog user session의 title/preview와 workspace가 표시되어야 한다.
- [ ] **Step 3:** `git diff --check`와 `git status --short --branch`를 확인한다.
- [ ] **Step 4:** progress 문서에 테스트 수와 실제 AGY resume을 수행하지 않은 범위를 기록한다.

