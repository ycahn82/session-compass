"use strict";

const UUID_RE = /\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b/g;
const SECRET_RE = /\b(?:sk|ghp|github_pat)[_-][A-Za-z0-9_-]+\b/g;
const PATH_RE = /(?<!\w)(?:\/Users|\/home|\/tmp|[A-Z]:\\)[^\s,;]+/g;

function sanitizeText(value) {
  return String(value)
    .replace(PATH_RE, "<path>")
    .replace(UUID_RE, "<uuid>")
    .replace(SECRET_RE, "<secret>")
    .slice(0, 200);
}

function issueTitle(agent, problemType) {
  return `[compat] ${agent} ${problemType}`;
}

function issueLabels(agent) {
  return ["compatibility", "automated-detection", `agent:${agent}`];
}

function problemType(result) {
  if (result.failure === "executable_not_found" || result.failure === "execution_error") {
    return "CLI installation failure";
  }
  if (Array.isArray(result.missing_flags) && result.missing_flags.length > 0) {
    return "resume capability mismatch";
  }
  if (result.failure && String(result.failure).includes("storage")) {
    return "storage contract mismatch";
  }
  return "CLI compatibility failure";
}

function failureBody(result, artifactUrl, runUrl) {
  const safe = {
    agent: result.agent,
    version: result.version || "unknown",
    status: result.status,
    failure: result.failure ? sanitizeText(result.failure) : undefined,
    detected_flags: result.detected_flags || [],
    missing_flags: result.missing_flags || [],
  };
  return [
    "## CLI compatibility failure",
    "",
    "```json",
    JSON.stringify(safe, null, 2),
    "```",
    "",
    `Artifact: ${artifactUrl}`,
    `Workflow run: ${runUrl}`,
  ].join("\n");
}

function recoveryComment(agent, runUrl) {
  return `Compatibility check recovered for ${agent}. The issue remains open for maintainer review. Workflow run: ${runUrl}`;
}

async function updateCompatibilityIssues({ github, context, results, artifactUrl, runUrl }) {
  const repo = { owner: context.repo.owner, repo: context.repo.repo };
  for (const result of results) {
    if (result.status === "pass") {
      const open = await github.rest.search.issuesAndPullRequests({
        q: `repo:${repo.owner}/${repo.repo} is:issue is:open [compat] ${result.agent}`,
      });
      for (const issue of open.data.items.filter((item) => item.title.startsWith(`[compat] ${result.agent} `))) {
        await github.rest.issues.createComment({
          ...repo,
          issue_number: issue.number,
          body: recoveryComment(result.agent, runUrl),
        });
      }
      continue;
    }

    const title = issueTitle(result.agent, problemType(result));
    const all = await github.rest.search.issuesAndPullRequests({
      q: `repo:${repo.owner}/${repo.repo} is:issue "${title}"`,
    });
    const exact = all.data.items.find((item) => item.title === title);
    const body = failureBody(result, artifactUrl, runUrl);
    if (exact && exact.state === "open") {
      await github.rest.issues.createComment({ ...repo, issue_number: exact.number, body });
    } else {
      const previous = exact ? `\n\nPrevious issue: #${exact.number}` : "";
      await github.rest.issues.create({
        ...repo,
        title,
        labels: issueLabels(result.agent),
        body: body + previous,
      });
    }
  }
}

module.exports = {
  sanitizeText,
  issueTitle,
  issueLabels,
  problemType,
  failureBody,
  recoveryComment,
  updateCompatibilityIssues,
};
