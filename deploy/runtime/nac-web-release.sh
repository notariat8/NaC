#!/usr/bin/env bash
set -euo pipefail

: "${NAC_RELEASE_ARCHIVE:?set NAC_RELEASE_ARCHIVE to the reviewed source archive}"
: "${NAC_RELEASE_SHA256:?set NAC_RELEASE_SHA256 to the expected archive SHA-256}"
: "${NAC_RELEASE_COMMIT:?set NAC_RELEASE_COMMIT to the reviewed Git commit}"

NAC_RELEASE_ROOT="${NAC_RELEASE_ROOT:-/opt/nac}"
NAC_RELEASE_SERVICE="${NAC_RELEASE_SERVICE:-nac-web}"
NAC_RELEASE_HEALTH_URL="${NAC_RELEASE_HEALTH_URL:-http://127.0.0.1:8768/healthz}"

# Default release store: /opt/nac/releases; active symlink: /opt/nac/current.

case "$NAC_RELEASE_COMMIT" in
  *[!0123456789abcdefABCDEF]*)
    echo "NAC_RELEASE_COMMIT must be a hexadecimal Git commit" >&2
    exit 2
    ;;
esac

case "${#NAC_RELEASE_COMMIT}" in
  40|64) ;;
  *)
    echo "NAC_RELEASE_COMMIT must be a 40 or 64 character identifier" >&2
    exit 2
    ;;
esac

if ! tar -tzf "$NAC_RELEASE_ARCHIVE" >/dev/null; then
  echo "Release archive cannot be read" >&2
  exit 2
fi

if tar -tzf "$NAC_RELEASE_ARCHIVE" | grep -Eq '(^/|(^|/)\.\.(/|$))'; then
  echo "Release archive contains unsafe paths" >&2
  exit 2
fi

printf '%s  %s\n' "$NAC_RELEASE_SHA256" "$NAC_RELEASE_ARCHIVE" | sha256sum -c

releases_dir="${NAC_RELEASE_ROOT}/releases"
release_dir="${releases_dir}/${NAC_RELEASE_COMMIT}"
tmp_dir="${releases_dir}/.${NAC_RELEASE_COMMIT}.tmp"
current_link="${NAC_RELEASE_ROOT}/current"

install -d -m 0755 "$releases_dir"
rm -rf "$tmp_dir"
install -d -m 0755 "$tmp_dir"

previous_target=""
if [ -L "$current_link" ]; then
  previous_target="$(readlink -f "$current_link")"
elif [ -d "$current_link" ]; then
  previous_target="${releases_dir}/bootstrap-before-${NAC_RELEASE_COMMIT}"
  if [ -e "$previous_target" ]; then
    echo "Bootstrap rollback target already exists: ${previous_target}" >&2
    exit 2
  fi
  mv "$current_link" "$previous_target"
fi

rollback() {
  status="$?"
  if [ "$status" -ne 0 ] && [ -n "$previous_target" ] && [ -e "$previous_target" ]; then
    ln -sfn "$previous_target" "$current_link"
    systemctl restart "$NAC_RELEASE_SERVICE" || true
  fi
  exit "$status"
}

trap rollback EXIT

if [ ! -d "$release_dir" ]; then
  tar -xzf "$NAC_RELEASE_ARCHIVE" -C "$tmp_dir" --strip-components=1
  test -f "$tmp_dir/pyproject.toml"
  test -d "$tmp_dir/src"
  chmod -R a+rX "$tmp_dir"
  mv "$tmp_dir" "$release_dir"
else
  rm -rf "$tmp_dir"
fi

ln -sfn "$release_dir" "$current_link"
systemctl restart "$NAC_RELEASE_SERVICE"
systemctl is-active --quiet "$NAC_RELEASE_SERVICE"
curl --fail --silent --show-error "$NAC_RELEASE_HEALTH_URL" | grep -F '"status": "ok"'

trap - EXIT
echo "NaC release ${NAC_RELEASE_COMMIT} is active"
