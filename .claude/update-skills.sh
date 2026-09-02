#!/usr/bin/env bash
# Sync the vendored third-party skill libraries into .claude/skills/.
#
#   superpowers    https://github.com/obra/superpowers          MIT
#   agent-browser  https://github.com/vercel-labs/agent-browser Apache-2.0
#
# The skills are vendored rather than installed as Claude Code plugins because a
# plugin has to be installed into the machine's own ~/.claude, which does not
# survive the ephemeral containers Claude Code on the web runs in. Project skills
# under .claude/skills/ are read straight from the repository, so every session
# gets them with no install step.
#
# Usage: .claude/update-skills.sh [superpowers|agent-browser]
#        (no argument syncs everything)
#
# The skills land in <root>/.claude/skills/, where <root> defaults to this
# repository. Set CLAUDE_SKILLS_ROOT to install them elsewhere, e.g.
#
#   CLAUDE_SKILLS_ROOT="$HOME" .claude/update-skills.sh
#
# which puts them in ~/.claude/skills/ and makes them available in every local
# project. Cloud sessions do not read ~/.claude/skills/ — see the README.

set -euo pipefail

if [ -n "${CLAUDE_SKILLS_ROOT:-}" ]; then
    REPO_ROOT="$(cd "${CLAUDE_SKILLS_ROOT}" && pwd)"
elif [ -f "${BASH_SOURCE[0]}" ]; then
    REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
else
    REPO_ROOT="${PWD}"
fi
DEST="${REPO_ROOT}/.claude/skills"
VENDOR="${REPO_ROOT}/.claude/vendor"
MANIFEST="${VENDOR}/manifest.tsv"

TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT

mkdir -p "${DEST}" "${VENDOR}"
touch "${MANIFEST}"

# Remove the skills a previous run vendored from this source, so a skill that
# disappears upstream disappears here too. Never touches skills we don't own.
prune_source() {
    local source="$1"
    awk -F'\t' -v s="${source}" '$1==s {print $2}' "${MANIFEST}" | while read -r skill; do
        [ -n "${skill}" ] && rm -rf "${DEST:?}/${skill}"
    done
    grep -v -P "^${source}\t" "${MANIFEST}" > "${MANIFEST}.new" 2>/dev/null || : > "${MANIFEST}.new"
    mv "${MANIFEST}.new" "${MANIFEST}"
}

record() { printf '%s\t%s\t%s\n' "$1" "$2" "$3" >> "${MANIFEST}"; }

sync_superpowers() {
    local ref="${SUPERPOWERS_REF:-main}" src commit
    echo "Cloning obra/superpowers @ ${ref}..."
    git clone --quiet --depth 1 --branch "${ref}" \
        https://github.com/obra/superpowers.git "${TMP}/superpowers"
    src="${TMP}/superpowers/skills"
    [ -d "${src}" ] || { echo "error: obra/superpowers has no skills/ directory" >&2; exit 1; }
    commit="$(git -C "${TMP}/superpowers" rev-parse HEAD)"

    prune_source superpowers
    local names=()
    for dir in "${src}"/*/; do
        local name; name="$(basename "${dir}")"
        rm -rf "${DEST:?}/${name}"
        cp -a "${dir}" "${DEST}/${name}"
        record superpowers "${name}" "${commit}"
        names+=("${DEST}/${name}")
    done
    # Project skills are not namespaced the way plugin skills are, so rewrite the
    # "superpowers:<skill>" cross references to the names they load under here.
    grep -rl 'superpowers:' "${names[@]}" 2>/dev/null | xargs -r sed -i 's/superpowers://g' || true
    cp "${TMP}/superpowers/LICENSE" "${VENDOR}/LICENSE-superpowers"
    echo "  superpowers: $(ls -1 "${src}" | wc -l) skills @ ${commit}"
}

sync_agent_browser() {
    local ref="${AGENT_BROWSER_REF:-main}" src commit
    echo "Cloning vercel-labs/agent-browser @ ${ref}..."
    git clone --quiet --depth 1 --branch "${ref}" \
        https://github.com/vercel-labs/agent-browser.git "${TMP}/agent-browser"
    src="${TMP}/agent-browser/skills"
    [ -d "${src}" ] || { echo "error: vercel-labs/agent-browser has no skills/ directory" >&2; exit 1; }
    commit="$(git -C "${TMP}/agent-browser" rev-parse HEAD)"

    prune_source agent-browser
    for dir in "${src}"/*/; do
        local name; name="$(basename "${dir}")"
        rm -rf "${DEST:?}/${name}"
        cp -a "${dir}" "${DEST}/${name}"
        record agent-browser "${name}" "${commit}"
    done
    cp "${TMP}/agent-browser/LICENSE" "${VENDOR}/LICENSE-agent-browser"
    echo "  agent-browser: $(ls -1 "${src}" | wc -l) skills @ ${commit}"
}

case "${1:-all}" in
    superpowers)   sync_superpowers ;;
    agent-browser) sync_agent_browser ;;
    all)           sync_superpowers; sync_agent_browser ;;
    *) echo "usage: $0 [superpowers|agent-browser]" >&2; exit 2 ;;
esac

sort -o "${MANIFEST}" "${MANIFEST}"
echo "Manifest: ${MANIFEST}"
