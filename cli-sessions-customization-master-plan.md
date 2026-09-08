# Session Compass 커스텀 마스터 플랜

## 1. 목적

본 문서는 upstream `cli-sessions`에서 출발한 `Session Compass` 프로젝트를 다음 도구 중심의 실용적이고 복잡도가 낮은 워크플로우에 맞게 커스텀하기 위한 마스터 플랜을 정의합니다:

- Antigravity
- Codex
- Claude Code

주요 목표는 대규모 오케스트레이션 플랫폼을 구축하지 않고도, 여러 서버와 디바이스 전반에서 AI 코딩 세션을 쉽게 **발견(discover), 식별(identify), 재개(resume) 및 관리(manage)**할 수 있도록 하는 것입니다.

시스템은 다음 원칙을 유지해야 합니다:

- 로컬 우선 (local-first)
- 가능한 한 파일 기반 유지
- 이해하기 쉬운 구조
- 디버깅 용이성
- Linux 서버에 간편한 설치
- 데스크톱 IDE 터미널, 일반 SSH, 모바일 SSH 어디서든 사용 가능
- 외부 서비스 의존성 최소화
- 실용적인 수준에서 업스트림 `cli-sessions`와의 호환성 유지

이 도구는 다음과 같은 반복적이고 구체적인 문제를 해결하기 위한 것입니다:

> "어떤 대화에서 어떤 에이전트나 머신을 사용했는지 자주 잊어버리고, 서버 CLI에서 생성된 세션은 IDE에서 항상 보이지는 않는다."

---

# 2. 핵심 제품 원칙

본 프로젝트는 에이전트 오케스트레이션이 아니라 **세션 발견 가능성(discoverability)과 연속성(continuity)**을 최우선으로 해야 합니다.

이 도구는 다음 질문에 신속하게 답할 수 있어야 합니다:

1. 내가 가지고 있는 AI 세션은 무엇인가?
2. 각 세션을 생성한 에이전트는 누구인가?
3. 어떤 프로젝트에 속해 있는가?
4. 어떤 호스트(머신)를 사용했는가?
5. 그 세션의 내용은 무엇이었는가?
6. 마지막으로 사용한 시간은 언제인가?
7. 연관된 Git 브랜치는 무엇인가?
8. 즉시 해당 세션을 재개할 수 있는가?
9. 노트북, 회사 PC, 스마트폰에서도 동일한 정보를 확인할 수 있는가?
10. 중앙 데이터베이스 없이도 나중에 여러 서버의 세션을 모아서 볼 수 있는가?

---

# 3. 지원 대상 에이전트

오직 다음 3가지 에이전트 제품군만 지원 범위에 포함됩니다:

- Claude Code
- Codex
- Antigravity CLI

이 3가지 도구를 지원하는 데 필요한 경우가 아니라면, 범용적인 멀티 에이전트 추상화 계층을 추가하지 마십시오.

그럼에도 불구하고 향후 시스템의 다른 부분을 수정하지 않고 새 지원을 추가할 수 있도록, 에이전트별 파싱 로직은 작은 어댑터 경계 뒤에 유지해야 합니다.

개념적 권장 인터페이스:

```python
class SessionProvider:
    name: str

    def discover_sessions(self) -> list[Session]:
        ...

    def resume(self, session: Session) -> None:
        ...
```

기존 코드를 검토하기 전에 이 인터페이스를 과도하게 엔지니어링하지 마십시오.

---

# 4. 표준 사용 모델

## 4.1 서버 우선 모델

기본 배포 모델은 다음과 같습니다:

```text
노트북 / 회사 PC / 스마트폰
            |
            | SSH / 원격 SSH
            v
        AI 서버
            |
     +------+------+------+
     |             |      |
 Claude Code     Codex   Antigravity
     |             |      |
     +-------------+------+
                   |
           Session Compass
```

해당 서버에서 생성된 세션의 표준 소스(canonical source)는 서버 자체입니다.

예시 세션 저장소 위치:

```text
~/.claude/
~/.codex/
~/.gemini/
```

정확한 경로는 실제 업스트림 구현과 설치된 에이전트 버전을 확인하여 결정해야 합니다.

본 문서의 추측만으로 경로를 하드코딩하지 마십시오.

---

## 4.2 모바일 환경 활용

예상되는 모바일 워크플로우는 다음과 같습니다:

```text
Android
  |
FortiClient VPN
  |
SSH 클라이언트
  |
AI 서버
  |
Session Compass
```

스마트폰에 별도의 세션 데이터베이스나 동기화 로직이 필요하지 않아야 합니다.

사용자는 서버 셸에서 다음과 같이 실행하여:

```bash
scompass
```

또는 이후:

```bash
scompass
```

데스크톱 SSH에서 볼 때와 동일한 세션 정보를 확인할 수 있어야 합니다.

---

# 5. 비목표 (Non-Goals)

다음 항목들은 실제 사용 과정에서 필요성이 입증되기 전까지는 명시적으로 범위에서 제외합니다.

초기 단계에서는 다음을 구축하지 **마십시오**:

- 자율 에이전트 오케스트레이션
- 공유 LLM 메모리
- 시맨틱 장기 기억 (semantic long-term memory)
- LLM 생성 요약
- 중앙 웹 백엔드
- 클라우드 데이터베이스
- Redis
- 메시지 큐
- MCP 서버
- Docker 기반 배포 필수화
- 인증 서버
- 다중 사용자 권한 시스템
- 에이전트 간 자동 작업 라우팅
- 에이전트 간 자동 핸드오프
- 토큰 쿼터 모니터링
- 과금 대시보드
- 복잡한 웹 UI
- 벤더 간 전체 대화 동기화
- IDE 플러그인을 기본 원천(source of truth)으로 삼는 것

프로젝트는 우선 작은 CLI/TUI 도구로 유지되어야 합니다.

---

# 6. 포크 및 업스트림 전략

저장소는 업스트림 `cli-sessions`의 포크로 유지 관리됩니다.

권장 원격 저장소(remotes):

```text
origin   -> 개인 포크 저장소
upstream -> 원본 cli-sessions 저장소
```

예시:

```bash
git remote -v
```

예상 구조:

```text
origin    git@github.com:<USER>/cli-sessions.git
upstream  https://github.com/<UPSTREAM>/cli-sessions.git
```

## 규칙

1. 업스트림 커밋 히스토리를 온전히 유지할 것.
2. 절대적으로 필요한 경우가 아니라면 대규모 재작성을 피할 것.
3. 작고 격리된 확장을 선호할 것.
4. 프로바이더 파싱 변경 사항과 화면 표시(presentation) 변경 사항을 분리할 것.
5. 업스트림과의 모든 의도적 차이점을 문서화할 것.
6. 업스트림에서 유사한 기능을 이미 구현했는지 정기적으로 확인할 것.
7. 테스트가 통과된 후에만 업스트림을 리베이스하거나 병합할 것.
8. 로컬 세션 파일에서 필요한 정보를 이미 제공하는 경우, 커스텀 동작을 문서화되지 않은 벤더 비공개 API에 의존하게 만들지 말 것.

---

# 7. 개발 철학

모든 단계는 항상 도구가 즉시 사용 가능한 상태를 유지해야 합니다.

진행 순서는 다음과 같아야 합니다:

```text
사용 가능한 기준선
    ->
작은 사용성 개선
    ->
실제 작업에 사용
    ->
필요한 경우에만 다음 개선 진행
```

피해야 할 패턴:

```text
대규모 재설계
    ->
수많은 추측성 기능 추가
    ->
실제 사용까지 수개월 소요
```

제품은 일상 업무에서 실제로 관찰된 마찰(friction)로부터 발전해야 합니다.

---

# 8. Phase 0 — 저장소 분석 및 기준선 검증

## 목표

안전하게 확장할 수 있을 만큼 업스트림을 완벽히 이해합니다.

이 단계가 완료되기 전에는 어떤 기능 구현도 시작해서는 안 됩니다.

## 작업 항목

- [ ] 전체 저장소 구조 분석.
- [ ] CLI 진입점 파악.
- [ ] 세션 모델 및 데이터 구조 파악.
- [ ] 프로바이더별 파싱 로직 파악.
- [ ] Claude Code 세션 감지 로직 파악.
- [ ] Codex 세션 감지 로직 파악.
- [ ] Antigravity 세션 감지 로직 파악.
- [ ] 각 프로바이더의 재개(resume) 명령어 파악.
- [ ] SQLite/JSONL 파싱 의존성 확인.
- [ ] 기존 정렬/필터링 로직 파악.
- [ ] 테스트 구조 파악.
- [ ] 패키징 및 설치 메커니즘 파악.
- [ ] 현재 테스트 실행.
- [ ] 수정되지 않은 포크 설치.
- [ ] 커스텀 전에 CLI가 정상 작동하는지 확인.
- [ ] 각 프로바이더에서 실제 세션을 하나 이상 검증.
- [ ] 각 프로바이더의 resume 기능 검증.
- [ ] tmux 내에서의 동작 검증.
- [ ] 일반 SSH 환경에서의 동작 검증.
- [ ] FortiClient VPN을 통한 모바일 SSH 환경에서의 동작 검증.

## 필수 수집 근거

다음 정보를 기록합니다:

- Python 버전
- OS 버전
- cli-sessions 버전
- Claude Code 버전
- Codex 버전
- Antigravity CLI 버전
- 확인된 세션 저장소 위치
- 동작하는 resume 명령어
- 미지원 또는 불안정한 동작 사항

권장 파일:

```text
docs/assessment/BASELINE.md
```

## 완료 조건

다음 조건이 충족되어야 Phase 0이 완료됩니다:

- 세 프로바이더 모두 세션 감지가 가능하거나, 미지원 케이스가 명시적으로 문서화됨
- 지원되는 각 프로바이더에 대해 최소 1개 이상의 세션을 재개할 수 있음
- 현재 업스트림 테스트 통과
- 커스텀 수정 없이 포크 저장소가 정상 작동함

---

# 9. Phase 1 — 최소 일상 사용 기준선

## 목표

기존 도구를 즉시 일상 업무에 편안하게 사용할 수 있는 수준으로 만듭니다.

이 단계는 가능한 한 가장 작은 변경 사항만 포함해야 합니다.

## 필수 기능

### 9.1 통합 목록

Claude Code, Codex, Antigravity 세션을 하나의 목록으로 표시합니다.

필수 필드:

```text
Agent
Project
Last Used
Session
```

예시:

```text
#  Agent        Project        Last Used        Session
1  Claude       DO-KO-TR       09/08 09:31      validate sessions
2  Codex        DO-KO-TR       09/08 08:12      workflow state fix
3  Antigravity  BoT            09/07 22:43      oracle experiment
```

### 9.2 세션 재개

세션을 선택하면 해당 프로바이더에 맞는 올바른 재개 명령어가 실행되어야 합니다.

### 9.3 검색

사용 가능한 메타데이터 전반에 대해 간단한 텍스트 검색을 지원합니다.

가능한 문법:

```bash
scompass do-ko-tr
scompass validate
```

또는 이미 지원되는 경우 대화형(interactive) 검색 활용.

### 9.4 프로바이더 필터

다음과 같은 필터를 유지하거나 지원합니다:

```bash
scompass --claude
scompass --codex
scompass --agy
```

## Phase 1 비요구사항

아직 다음 기능을 추가하지 마십시오:

- 원격 호스트
- IDE 확장
- LLM 요약
- 고급 그룹화 UI
- 새로운 영구 데이터베이스

## 완료 조건

사용자가 이전 세션을 찾기 위해 다른 도구를 쓸 필요 없이 며칠 동안 실제 작업에 이 도구를 계속 사용할 수 있음.

---

# 10. Phase 2 — 프로젝트 식별

## 목표

각 세션이 어떤 프로젝트에 속해 있는지 명확히 알 수 있도록 합니다.

## 문제 상황

저장소가 많고 오래 실행되는 작업이 많을 때는 에이전트 세션 제목만으로는 부족합니다.

## 프로젝트 감지 우선순위

가능한 경우 다음 순서대로 가장 신뢰할 수 있고 단순한 신호를 사용합니다:

1. 프로바이더가 이미 저장해 둔 명시적 프로젝트/세션 메타데이터
2. 세션에 기록된 작업 디렉토리 (working directory)
3. 작업 디렉토리로부터 파생된 Git 저장소 루트
4. 저장소 디렉토리 이름
5. 순수 작업 디렉토리의 기본 이름(basename)으로 대체 (fallback)
6. `unknown`

실제 사용에서 필수적임이 증명되기 전까지는 외부 프로젝트 레지스트리를 추가하지 마십시오.

## 필수 표시 형식

예시:

```text
DO-KO-TR
  Claude        validate sessions
  Codex         workflow state fix
  Antigravity   integration testing

BoT
  Codex         oracle experiment
  Claude        RL design
```

그룹화 표시는 선택 사항이거나 설정 가능하도록 할 수 있습니다.

## 인수 기준

- Git 저장소의 대부분 세션에 올바른 프로젝트 이름이 부여됨
- Git 저장소 외부의 세션도 여전히 정상 표시됨
- 프로젝트 감지 실패가 세션 목록 표시를 방해하지 않음

---

# 11. Phase 3 — 호스트 인지

## 목표

다음 질문에 답합니다:

> "이 대화를 어떤 머신/서버에서 진행했는가?"

## 필수 메타데이터

각 세션 결과는 다음 필드를 지원해야 합니다:

```text
host
```

예시:

```text
HOST          AGENT         PROJECT       SESSION

aiengine1     Claude        DO-KO-TR      validate sessions
aiengine1     Codex         DO-KO-TR      workflow fix
aiengine2     Antigravity   BoT           oracle test
Laptop-ss     Codex         BoT           dataset analysis
```

## 초기 구현

로컬에서 발견된 세션의 경우:

```python
socket.gethostname()
```

또는 이와 동등한 방식이면 충분합니다.

호스트명 충돌이 실제 문제가 되기 전까지는 전역 고유 머신 식별자(UUID 등)를 만들지 마십시오.

## 완료 조건

도구에서 출력되는 모든 세션에 host 필드가 포함됨.

---

# 12. Phase 4 — Git 컨텍스트

## 목표

Git 정보를 활용하여 세션을 더 쉽게 식별할 수 있도록 합니다.

## 목표 메타데이터

복구 가능한 경우:

```text
repository
branch
commit
```

최소 요구사항:

```text
branch
```

## 주요 제약 사항

과거 브랜치를 항상 재구성할 수 있는 것은 아닙니다.

현재 브랜치를 세션 당시의 브랜치인 것처럼 임의로 보고하지 마십시오.

권장 신뢰도 모델:

```text
branch: feature/foo
branch_source: session_metadata
```

또는:

```text
branch: main
branch_source: current_repo_state
```

과거 브랜치를 신뢰성 있게 확인할 수 없는 경우, 없는 역사를 지어내지 말고 다음과 같이 표시하십시오:

```text
branch: unknown
```

---

# 13. Phase 5 — 세션 미리보기

## 목표

세션을 직접 열지 않고도 내용을 식별할 수 있도록 합니다.

## 필수 미리보기 정보

세션 로그에 이미 존재하는 결정론적(deterministic) 데이터를 사용합니다.

권장 필드:

```text
Agent
Project
Host
Last active
Git branch
First user message
Last user message
```

예시:

```text
Agent: Claude Code
Project: DO-KO-TR
Host: aiengine1
Last active: Sep 8 09:31
Branch: feature/validate-sessions

Started with:
"Implement per-session validation stage..."

Last user message:
"Run the failing integration tests again."
```

## 중요 규칙

이 단계에서는 요약 생성을 위해 LLM을 사용하지 마십시오.

이유:

- 추가 지연 시간 (latency)
- 비용 발생
- 외부 의존성 추가
- 프라이버시 복잡성
- 캐시 무효화 문제
- 불필요한 아키텍처 복잡화

실제 사용 후 미리보기가 부족하다고 판단되면 시맨틱 요약 도입을 나중에 재검토할 수 있습니다.

---

# 14. Phase 6 — 향상된 검색 및 필터링

## 목표

수백 개의 세션이 있어도 원하는 세션을 빠르게 찾을 수 있도록 합니다.

## 검색 가능 필드

최소 지원 대상:

- agent
- project
- host
- session title
- first user message
- last user message
- working directory
- branch

## 권장 CLI 사용법

예시:

```bash
scompass --project do-ko-tr
scompass --host aiengine1
scompass --agent codex
scompass --branch feature/validate-sessions
scompass --search synthesize
```

실용적인 경우 여러 필터가 조합(compose)될 수 있어야 합니다.

예시:

```bash
scompass --host aiengine1 --project do-ko-tr --agent claude
```

파싱 구조는 단순하게 유지하십시오.

---

# 15. Phase 7 — 상태 점검 / Doctor 명령어

## 목표

새 서버에서 설치 및 디버깅을 쉽게 할 수 있도록 합니다.

권장 명령어:

```bash
scompass doctor
```

또는 이후:

```bash
scompass doctor
```

출력 예시:

```text
Claude Code
  ✓ ~/.claude found
  ✓ 184 sessions
  ✓ claude command available

Codex
  ✓ ~/.codex found
  ✓ 92 sessions
  ✓ codex command available

Antigravity
  ✓ session store found
  ✓ 37 sessions
  ✓ agy command available

Git
  ✓ available

SSH
  ✓ available

Status: ready
```

## Doctor 점검 항목

- 프로바이더 CLI 사용 가능 여부
- 예상 세션 저장소 존재 여부
- 파서가 저장소를 읽을 수 있는지 여부
- 세션 개수
- Git 사용 가능 여부
- 호스트명 확인
- Python 버전 호환성
- 권한 오류 검사
- 손상되었거나 지원되지 않는 세션 파일 감지
- 선택적 tmux 사용 가능 여부

doctor 명령어는 사용자 데이터를 절대 수정해서는 안 됩니다.

---

# 16. Phase 8 — 설치 및 업데이트 워크플로우

## 목표

어떤 AI 서버에서도 이 도구를 쉽게 설치할 수 있도록 합니다.

## 선호 도구

실용적인 경우 다음 도구를 사용합니다:

```text
uv
```

권장 설치 방식:

```bash
uv tool install .
```

또는 포크 저장소에서 직접 설치:

```bash
uv tool install git+ssh://git@github.com/<USER>/cli-sessions.git
```

정확한 명령어는 실제 패키지 메타데이터와 일치해야 합니다.

## 요구사항

- Docker 필수화 금지
- 데몬 불필요
- root 권한 불필요
- 시스템 Python 수정 금지
- 간편한 삭제 (uninstall)
- 간편한 업데이트
- 간편한 롤백

## 권장 스크립트

유용한 경우에만 생성:

```text
scripts/install.sh
scripts/update.sh
```

이 스크립트들은 표준 패키지 도구를 감싸는 얇은 래퍼로 유지되어야 합니다.

---

# 17. Phase 9 — 안정적인 JSON 출력

## 목표

UI를 구축하기 전에 기계가 읽을 수 있는(machine-readable) 인터페이스를 먼저 만듭니다.

권장 명령어:

```bash
scompass --json
```

개념적 스키마 예시:

```json
{
  "sessions": [
    {
      "id": "...",
      "provider": "claude",
      "project": "DO-KO-TR",
      "host": "aiengine1",
      "title": "validate sessions",
      "last_used": "...",
      "working_directory": "...",
      "git_branch": "...",
      "first_user_message": "...",
      "last_user_message": "...",
      "resume": {
        "provider": "claude",
        "session_id": "..."
      }
    }
  ]
}
```

## 설계 규칙

- 안정적인 필드명 유지
- 필요한 경우 스키마 버전 명시
- 불필요한 원시 비공개 로그 내용을 노출하지 말 것
- 텍스트 출력과 JSON 출력은 동일한 정규화된 세션 모델에서 파생되어야 함

이 JSON 인터페이스는 원격 집계와 선택적 UI 구축의 기반이 됩니다.

---

# 18. Phase 10 — 원격 호스트 집계

## 목표

중앙 서비스를 배포하지 않고도 여러 서버의 세션을 확인합니다.

## 아키텍처

로컬 머신:

```text
scompass
   |
   +-- ssh aiengine1 scompass --json
   |
   +-- ssh aiengine2 scompass --json
   |
   +-- local scompass --json
```

결과는 로컬에서 병합됩니다.

## 권장 사용법

```bash
scompass --host aiengine1
```

이 명령은 로컬 메타데이터를 필터링하거나 설정된 원격 머신에 질의할 수 있습니다.

멀티 호스트 집계의 경우 다음과 같은 방식을 고려합니다:

```bash
scompass --remote aiengine1
scompass --remote aiengine2
scompass --all-hosts
```

정확한 UX는 기존 CLI와의 충돌 여부를 검토한 후에 결정합니다.

## 설정

소형 설정 파일을 선호합니다 (예시):

```toml
[hosts.aiengine1]
ssh = "aiengine1"

[hosts.aiengine2]
ssh = "aiengine2"
```

인벤토리 데이터베이스는 피하십시오.

## 중요 제약 사항

- SSH를 전송 계층으로 유지
- 서버에 데몬 상주 금지
- HTTP 포트 개방 금지
- 중앙 동기화 데이터베이스 금지
- 기존 VPN/네트워크 제한 존중
- 한 호스트의 장애가 다른 호스트의 결과 조회를 차단해서는 안 됨

## 원격 재개 (Remote Resume)

초기부터 이를 과도하게 구현하지 마십시오.

향후 가능한 동작:

```bash
ssh -t aiengine1 "scompass --resume <id>"
```

신뢰할 수 있고 안전한 경우에만 구현하십시오.

---

# 19. Phase 11 — Session Compass 이름과 명령어

초기 포크에서는 가능한 한 업스트림 명령어를 유지해야 합니다:

```bash
scompass
```

커스텀이 안정화된 후 선택적 래퍼를 도입할 수 있습니다:

```bash
scompass
```

가능한 명령어:

```bash
scompass
scompass recent
scompass doctor
scompass --project do-ko-tr
scompass --host aiengine1
scompass --json
```

패키지 전체의 이름을 조기에 변경하지 마십시오.

초기에 업스트림 명칭을 유지하는 것이 디버깅 혼선을 줄여줍니다.

---

# 20. Phase 12 — 선택적 Antigravity 사이드바

## 계기 / 발동 조건

실제 CLI 사용 중에 터미널을 여는 것이 실질적으로 불편하다고 느껴질 때만 구축하십시오.

CLI가 언제나 신뢰할 수 있는 단일 원천(source of truth)이어야 합니다.

## 아키텍처

```text
Antigravity 확장
        |
        v
scompass --json
        |
        v
세션 트리 (Session tree)
```

확장은 다음 항목들을 재구현해서는 안 됩니다:

- 프로바이더 파서
- 세션 감지 로직
- Git 프로젝트 감지
- 원격 집계 로직

확장은 오직 다음 역할만 수행해야 합니다:

- CLI 호출
- 결과 렌더링
- 필터링/검색
- resume 트리거

## UI 예시

```text
AI SESSIONS

▼ DO-KO-TR
   Claude
      validate sessions
   Codex
      workflow state
   Antigravity
      audit implementation

▼ BoT
   Codex
      oracle experiment
```

## 비목표

확장이 세션 영속화(persistence)를 담당하도록 만들지 마십시오.

---

# 21. tmux 통합

tmux는 cli-sessions와 다른 문제를 해결합니다.

명확한 구분을 유지하십시오:

```text
tmux
  -> 현재 실행 중인 터미널 프로세스

cli-sessions
  -> 저장된 대화/세션 기록
```

권장 모바일 워크플로우:

현재 실행 중인 세션 확인:

```bash
tmux ls
```

과거 기록 조회 및 재개 가능한 AI 대화 확인:

```bash
scompass
```

향후 편의 명령어 후보:

```bash
scompass --running
```

사용자들의 반복적인 요구가 있을 때만 고려하십시오.

애플리케이션 아키텍처를 tmux와 강하게 결합하지 마십시오.

---

# 22. 데이터 모델

하나의 정규화된 내부 세션 모델을 만들거나 그 방향으로 발전시킵니다.

개념적 필드:

```python
Session(
    id,
    provider,
    title,
    created_at,
    last_used_at,
    working_directory,
    project,
    host,
    git_repository,
    git_branch,
    git_commit,
    first_user_message,
    last_user_message,
    provider_metadata,
)
```

모든 프로바이더가 모든 필드를 채울 필요는 없습니다.

필요한 곳에서는 필드가 선택 사항(optional)이어야 합니다.

프로바이더 고유의 특화 필드가 UI 로직으로 새어 나가지 않도록 하십시오.

---

# 23. 프로바이더 어댑터 규칙

각 프로바이더 어댑터는 독립적으로 테스트 가능해야 합니다.

담당 책임:

- 세션 저장소 위치 탐색
- 세션 목록 열거
- 안전한 메타데이터 파싱
- 미리보기 메시지 읽기
- 타임스탬프 도출
- 프로바이더 세션 ID 제공
- resume 명령어 생성 및 호출

프로바이더 어댑터가 하지 **말아야** 할 것:

- TUI 출력 포맷팅
- 전역 검색 구현
- 원격 SSH 수행
- Git 프로젝트 그룹화 관리
- 프로바이더 간 중복 제거

---

# 24. 파싱 견고성

에이전트 벤더는 로컬 포맷을 언제든지 변경할 수 있습니다.

따라서 파서는 다음 조건을 만족해야 합니다:

- 누락된 선택적 필드 허용
- 가능한 경우 형식이 잘못된 개별 세션만 건너뛰기
- 전체 목록 조회를 중단하지 않고 경고만 표시
- 파괴적인 쓰기 방지
- 가능한 경우 읽기 전용(read-only) SQLite 연결 사용
- 에이전트 소유의 데이터베이스를 절대 수정하지 말 것
- 알려진 프로바이더 포맷 변형에 대한 픽스처 포함

포맷이 크게 달라질 경우 파서 버전 감지 로직을 고려하십시오.

---

# 25. 테스트 전략

## 25.1 단위 테스트

테스트 대상:

- Claude 파서
- Codex 파서
- Antigravity 파서
- 정규화된 세션 매핑
- 프로젝트 감지
- 호스트 감지
- Git 메타데이터 로직
- 정렬
- 필터링
- 검색
- JSON 직렬화
- resume 명령어 구성

테스트 픽스처(fixture)를 활용하십시오.

단위 테스트에서 실제 사용자의 세션 디렉토리를 요구해서는 안 됩니다.

---

## 25.2 통합 테스트

현실적인 샘플 세션 데이터가 포함된 임시 디렉토리를 사용합니다.

검증 흐름:

```text
프로바이더 파일
   ->
파서
   ->
정규화된 세션
   ->
CLI 출력
```

---

## 25.3 라이브 검증

벤더 포맷이 계속 변경되므로 자동화된 픽스처만으로는 충분하지 않습니다.

문서화된 라이브 검증 체크리스트를 유지하십시오.

권장 파일:

```text
docs/verification/LIVE_CHECKLIST.md
```

설치된 실제 버전을 대상으로 수동 검증 수행:

- Claude Code
- Codex
- Antigravity CLI

필수 점검 항목:

- 세션 생성
- 세션 감지
- 미리보기 정확성
- 세션 재개 (resume)
- 새 메시지 추가 후 정상 동작
- 세션 재감지
- SSH를 통한 동작
- tmux 내에서의 동작
- 모바일 SSH에서의 동작

---

# 26. 회귀 방지 규칙

어떤 기능을 병합하기 전에도:

- 기존 프로바이더 감지가 계속 작동해야 함
- resume 기능이 계속 작동해야 함
- 손상된 데이터로 인해 전체 목록 조회가 비정상 종료(crash)되지 않아야 함
- 문서화된 스키마 버전 내에서 JSON 출력이 하위 호환성을 유지해야 함
- 업스트림 테스트가 통과해야 함
- 커스텀 테스트가 통과해야 함
- 파서 변경 시 최소 1개 이상의 실제 프로바이더 라이브 검증을 수행해야 함

---

# 27. 성능 목표

이 도구는 대화형(interactive) 인터페이스입니다.

성능 목표는 지나치게 엄격하기보다는 실용적이어야 합니다.

지향점:

- 수백 개의 세션을 눈에 띄는 지연 없이 나열
- 메타데이터만 필요한 경우 거대한 전체 대화 파일 읽기를 피할 것
- 유용한 경우 첫/마지막 메시지 미리보기를 지연 로딩(lazy-load)
- 세션들이 동일한 저장소를 공유하는 경우 각 세션마다 Git 명령어를 반복 실행하지 말 것
- 프로파일링을 통해 필요성이 입증된 경우에만 캐싱 적용

초기 단계에는 영구 인덱싱 데이터베이스를 도입하지 마십시오.

---

# 28. 프라이버시 및 보안

애플리케이션은 민감할 수 있는 대화 기록을 다룹니다.

규칙:

- 기본 로컬 전용 (default local-only)
- 포크에서 원격 측정(telemetry) 추가 금지
- 외부 LLM 호출 금지
- 자동 업로드 금지
- 클라우드 동기화 금지
- 디버그 모드가 명시적으로 활성화되지 않는 한 로그에 원시 대화 내용 출력 금지
- JSON 출력에는 문서화된 필드만 포함
- 에이전트 메타데이터에 나타날 수 있는 비밀값(secret) 출력 방지
- 프로바이더 데이터베이스는 가능한 모든 곳에서 읽기 전용으로 열 것

원격 집계는 기존 SSH 인프라를 통해서만 이루어져야 합니다.

---

# 29. 장애 대응 동작

도구는 점진적으로 성능 저하(graceful degradation)를 처리해야 합니다.

예시:

```text
Claude 파서 실패
Codex 사용 가능
Antigravity 사용 가능
```

이 경우에도 사용자는 Codex 및 Antigravity 결과를 정상적으로 확인할 수 있어야 합니다.

하나의 손상된 세션 때문에 애플리케이션 전체를 사용할 수 없게 되어서는 안 됩니다.

권장 사용자 메시지:

```text
Warning: 2 Claude sessions could not be parsed.
Run `scompass doctor --verbose` for details.
```

---

# 30. 로깅 및 진단

기본 출력은 간결하게 유지하십시오.

선택적 플래그:

```bash
scompass --verbose
```

또는:

```bash
scompass doctor --verbose
```

진단 출력에 포함될 수 있는 항목:

- 스캔된 파일 목록
- 선택된 프로바이더
- 파서 버전
- 무시된 파일의 사유
- SSH 실패 내역
- Git 메타데이터 실패 내역

토큰이나 자격 증명을 절대 출력하지 마십시오.

---

# 31. 문서 구조

저장소 권장 문서 구조:

```text
docs/
├── MASTER_PLAN.md
├── assessment/
│   └── BASELINE.md
├── architecture/
│   └── SESSION_MODEL.md
├── development/
│   └── CONTRIBUTING_CUSTOM.md
├── verification/
│   └── LIVE_CHECKLIST.md
└── decisions/
    └── ADR-*.md
```

모든 문서를 한 번에 만들지 마십시오.

해당 단계에서 필요할 때만 작성하십시오.

장기적인 방향성에 대해서는 `MASTER_PLAN.md`가 최종 기준입니다.

---

# 32. 아키텍처 결정 기록 (ADR)

나중에 중요해질 가능성이 높은 결정에만 소형 ADR을 작성하십시오.

예시:

- 원격 집계에 데몬 대신 SSH 사용
- 영구 인덱스 데이터베이스 미사용
- 서버 우선 표준 세션 모델
- 향후 Antigravity UI를 위한 단일 원천으로 CLI 유지

사소한 구현 세부 사항까지 기록하느라 시간을 낭비하지 마십시오.

---

# 33. 마스터 플랜 실행 프로토콜

구현은 한 번에 한 단계씩 진행되어야 합니다.

각 단계별 진행 절차:

1. 현재 코드 점검
2. 현재 프로바이더 버전을 기준으로 가정 확인
3. 테스트 작성 또는 업데이트
4. 가장 작은 단위로 변경 사항 구현
5. 자동화된 검증 실행
6. 관련 라이브 검증 수행
7. 결과 문서화
8. 커밋
9. 실제 업무에 도구 사용
10. 그 후에만 다음 단계가 여전히 필요한지 판단

---

# 34. 권장 초기 커밋 전략

처음부터 거대한 "커스텀 플랫폼" 단일 커밋으로 시작하지 마십시오.

권장 커밋 순서:

```text
docs: add customization master plan

docs: record upstream baseline assessment

test: add provider parsing fixtures

feat: add normalized project metadata

feat: add host metadata

feat: add session preview

feat: add advanced filtering

feat: add doctor command

feat: add stable json output

feat: add ssh remote aggregation
```

각 기능 커밋은 독립적으로 이해될 수 있어야 합니다.

---

# 35. 업스트림 동기화 프로토콜

주기적으로 실행:

```bash
git fetch upstream
```

통합하기 전에 변경 사항을 검토하십시오.

권장 절차:

1. 업스트림 커밋 점검
2. 중복되거나 충돌하는 프로바이더 파서 변경 사항 확인
3. 포맷이 변경된 경우 픽스처 업데이트 또는 재생성
4. 격리된 브랜치나 워크트리(worktree)에서 업스트림 병합/리베이스
5. 전체 테스트 실행
6. 영향받는 프로바이더에 대해 라이브 검증 수행
7. 검증 완료 후에만 최종 병합

업스트림을 운영 브랜치로 자동 병합하지 마십시오.

---

# 36. 브랜치 전략

단순함을 유지합니다.

권장 구성:

```text
main
  안정적이고 사용 가능한 포크 브랜치

feature/<name>
  개별 커스텀 기능 작업

upstream-sync/<date>
  업스트림 통합 작업
```

꼭 필요한 경우가 아니라면 수명이 긴 단계별 브랜치를 만들지 마십시오.

격리된 구현이나 업스트림 동기화에는 git worktree를 활용할 수 있습니다.

---

# 37. 릴리스 전략

이 프로젝트는 우선 개인 및 내부용 도구입니다.

PyPI 배포는 필요하지 않습니다.

선호 배포 방식:

```bash
uv tool install git+ssh://git@github.com/<USER>/cli-sessions.git
```

또는 체크아웃된 로컬 저장소에서 직접 설치합니다.

안정적인 마일스톤에 태그를 지정합니다:

```text
v0.1-custom-baseline
v0.2-project-host
v0.3-preview-search
v0.4-remote-hosts
```

유용한 경우에만 유의적 버전(Semantic Versioning)을 적용하십시오.

---

# 38. "최소 성공 제품"의 정의

다음 워크플로우가 안정적으로 작동하면 이 커스텀 프로젝트는 이미 성공한 것입니다:

```text
$ scompass

DO-KO-TR
  Claude        aiengine1   validate sessions       Sep 8 09:31
  Codex         aiengine1   workflow state fix      Sep 8 08:12
  Antigravity   aiengine1   integration testing     Sep 7 22:43

BoT
  Codex         aiengine2   oracle experiment       Sep 7 20:13
```

사용자가 원하는 대화를 식별하고 즉시 재개할 수 있습니다.

그 이상의 모든 것은 선택적 개선 사항입니다.

---

# 39. 장기 선택적 기능

충분한 실제 사용을 거친 후에만 다음 사항을 고려하십시오:

- 대화형 퍼지(fuzzy) TUI
- 즐겨찾기 / 핀 고정
- 태그
- 세션 별칭 (alias)
- 프로젝트 별칭
- 보관된(archived) 세션
- 최근 프로젝트 모아보기
- 현재 실행 중인 tmux 프로세스 연동
- 대화 본문 내용 검색
- 선택적 로컬 전문(full-text) 인덱스
- IDE 사이드바
- SSH 터널 기반 읽기 전용 웹 뷰
- 세션 내보내기 (export)
- 명시적 에이전트 간 핸드오프 기록
- 프로바이더별 쿼터 잔여량 표시

이 중 어느 것도 확정된 약속이 아닙니다.

---

# 40. 명시적 보류 개념

검토되었으나 계속 보류되어야 하는 항목들입니다:

## 공유 메모리 시스템

메모리 브릿지 같은 도구는 나중에 유용할 수 있으나 두 번째 상태 관리 시스템을 도입하게 됩니다.

현재 결정:

> 세션 메타데이터 + Git + 실제 프로바이더 세션 로그만으로도 초기 문제를 해결하기에 충분합니다.

## 에이전트 오케스트레이션

현재 결정:

> 사용할 에이전트는 사용자가 직접 선택합니다. 이 도구는 세션을 찾고 재개하는 것을 돕습니다.

## 중앙 세션 서버

현재 결정:

> 데몬이나 API 서버를 고려하기 전에 SSH 집계를 사용합니다.

## AI 생성 요약

현재 결정:

> 초기에는 첫/마지막 사용자 메시지와 프로젝트/호스트/브랜치 정보만으로 충분합니다.

---

# 41. 코딩 에이전트를 위한 핸드오프 / 인계 프로토콜

구현이 Codex, Claude Code, Antigravity 등 여러 에이전트에서 진행될 수 있으므로, 이 포크에서 작업하는 모든 코딩 세션은 경량 핸드오프 프로토콜을 따라야 합니다.

작업 전:

1. `docs/MASTER_PLAN.md` 읽기.
2. 가장 최근의 관련 계획/결정 파일 읽기.
3. 상태 확인:
   ```bash
   git status
   git branch --show-current
   git log --oneline -10
   ```
4. 코드를 수정하기 전에 관련 테스트 실행.
5. 현재 진행 단계와 범위를 확인.

작업 중:

- 후속 단계의 기능을 기회주의적으로 미리 구현하지 말 것
- 변경 범위를 활성 단계로만 제한할 것
- 동작 변경에 대한 테스트 작성
- 벤더 세션 저장소에 대한 포맷 가정 문서화

작업 종료 전:

1. 검증 실행
2. 관련 문서 업데이트
3. 일관성 있는 단위로 변경 사항 커밋
4. 다음 사항 기록:
   - 변경된 내용
   - 남아있는 작업
   - 실행한 테스트
   - 수행한 라이브 검증
   - 알려진 문제점
5. 저장소를 깨끗한 상태로 두거나, 커밋되지 않은 작업을 명시적으로 문서화

필요한 경우 나중에 간단한 인계 파일을 추가할 수 있습니다:

```text
HANDOFF.md
```

그러나 Git 히스토리와 단계별 문서가 기본적이고 지속 가능한 상태 저장소여야 합니다.

---

# 42. 초기 구현 순서

이 마스터 플랜이 승인된 후에는 정확히 다음 순서로 진행하십시오:

## 1단계 — 기준선 검증

아직 커스텀을 진행하지 마십시오.

세 프로바이더를 모두 검증하고 실제 현실을 기록하십시오.

## 2단계 — 수정되지 않은 포크 사용

일반적인 업무 중에 사용해 보십시오.

구체적인 불편 사항을 수집하십시오.

## 3단계 — 프로젝트 식별 구현

현재 목록 표시에서 프로젝트 구분이 어려운 경우에만 진행하십시오.

## 4단계 — 호스트 메타데이터 추가

멀티 서버 워크플로우에 중요합니다.

## 5단계 — 미리보기 추가

첫/마지막 사용자 메시지, 신뢰할 수 있는 경우 브랜치 정보 추가.

## 6단계 — 검색/필터 개선 추가

실제 관찰된 세션 규모에 기반하여 진행하십시오.

## 7단계 — doctor 명령어 추가

더 많은 머신으로 배포를 확장하기 전에 진행하십시오.

## 8단계 — JSON 인터페이스 추가

원격 집계나 UI를 구축할 준비가 되었을 때만 진행하십시오.

## 9단계 — 멀티 호스트 SSH 집계 추가

중앙화된 백엔드를 만들기 전에 이 방식을 사용하십시오.

## 10단계 — 재평가

이 시점에서 Antigravity 사이드바가 여전히 필요한지 여부를 결정하십시오.

---

# 43. 현재 권장 대상 아키텍처

```text
Claude Code ------------------+
                               |
Codex ------------------------+--> 프로바이더 어댑터
                               |          |
Antigravity ------------------+          v
                                  정규화된 Session
                                         |
                         +---------------+---------------+
                         |               |               |
                         v               v               v
                     CLI / TUI          JSON           Resume
                         |
                         |
                     로컬 서버
                         ^
                         |
         +----------------+----------------+
         |                                 |
    데스크톱 SSH                      모바일 SSH
                                       |
                                  FortiClient VPN
```

향후 확장:

```text
노트북
  |
scompass --all-hosts
  |
  +-- ssh aiengine1 scompass --json
  |
  +-- ssh aiengine2 scompass --json
```

선택적 최종 계층:

```text
Antigravity 사이드바
        |
   scompass --json
```

---

# 44. 전체 프로젝트 성공 기준

사용자가 더 이상 다음 사항을 기억할 필요가 없다면 프로젝트는 성공한 것입니다:

- 어떤 AI 에이전트를 사용했는지
- 어떤 서버를 사용했는지
- 과거 코딩 대화가 어디에 저장되어 있는지

세션은 다음 명령어를 통해 수초 내에 찾을 수 있어야 합니다:

```bash
scompass
```

또는 소수의 필터를 조합하여 찾을 수 있어야 합니다.

저장소를 한 번 훑어보는 것만으로도 아키텍처를 이해할 수 있어야 합니다.

새로운 문제를 해결하기 위해 서버, 데이터베이스, 에이전트 프레임워크 또는 동기화 하위 시스템 도입이 필요해 보인다면, 먼저 기존의 CLI + SSH 아키텍처로는 간단히 해결할 수 없는지부터 증명하십시오.

---

# 45. 핵심 지침

> 도구가 세션 발견과 연속성에 집중하도록 유지하십시오.  
> 실제 반복되는 불편함을 없애는 가장 작은 기능만을 만드십시오.
