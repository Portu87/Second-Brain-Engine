#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
package_dir="$project_dir/sources/raw/SRC-NEXUSLUX-CONSTITUTION-V1-2"
output="$(mktemp)"
trap 'rm -f "$output"' EXIT

cat "$package_dir"/parts/canon\(4\).odt.b64.part-* | base64 --decode > "$output"

actual_size="$(wc -c < "$output" | tr -d ' ')"
expected_size="113825"
if [[ "$actual_size" != "$expected_size" ]]; then
  echo "Size mismatch: expected $expected_size bytes, got $actual_size" >&2
  exit 1
fi

printf '%s  %s\n' \
  'adc2dd18e9a5cf2f3b9fd63dac32e6859d878185b29506b420c3fcdccd25936d' \
  "$output" | sha256sum --check --status

echo "Verified canon(4).odt: $actual_size bytes; SHA-256 adc2dd18e9a5cf2f3b9fd63dac32e6859d878185b29506b420c3fcdccd25936d"
