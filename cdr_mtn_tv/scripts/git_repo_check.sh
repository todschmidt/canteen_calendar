#!/usr/bin/env bash
# Shared git repo health checks for install_pi.sh and app_user_setup.sh.
# Source this file; do not execute directly.

# Detect clones whose metadata still references /root (common after root ran git in ~cdr_mtn_tv).
git_repo_poisoned() {
  local repo_dir="$1"
  [[ -L "${repo_dir}" ]] && return 0
  if [[ -f "${repo_dir}/.git" ]]; then
    grep -q '/root/' "${repo_dir}/.git" 2>/dev/null && return 0
  fi
  if [[ -f "${repo_dir}/.git/config" ]]; then
    grep -qE '(^|\s)/root/' "${repo_dir}/.git/config" 2>/dev/null && return 0
  fi
  return 1
}

# rev-parse alone is not enough — it may pass while pull/status stat an unreadable worktree.
git_repo_healthy() {
  local repo_dir="$1"
  local install_dir="${repo_dir}/cdr_mtn_tv"
  git_repo_poisoned "${repo_dir}" && return 1
  [[ -r "${install_dir}/scripts/install_pi.sh" ]] || return 1
  git -C "${repo_dir}" status >/dev/null 2>&1 || return 1
  local top
  top="$(git -C "${repo_dir}" rev-parse --show-toplevel 2>/dev/null)" || return 1
  [[ "$(readlink -f "${top}" 2>/dev/null || echo "${top}")" == "$(readlink -f "${repo_dir}" 2>/dev/null || echo "${repo_dir}")" ]] || return 1
  return 0
}
