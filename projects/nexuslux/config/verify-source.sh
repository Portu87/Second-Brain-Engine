#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
package_dir="$project_dir/sources/raw/SRC-NEXUSLUX-CONSTITUTION-V1-2"
output="$(mktemp)"
trap 'rm -f "$output"' EXIT

expected_part_hashes=(
  d59c7b74ef1ed3636bd6c421e45fc225e62e755e3e4d8e7858f0ab324b84b06d
  3e1dfc8a9bb3e8624c56a1e77a9520b64c478456a8c2079138174f0cd7b540b4
  b4f6958390ebf9bb8aa9d782e2d290cb0bd0dc611f7ad4c36b47e741b2451874
  a0742be556dc232a6bcfb21e75ed1e38b5c580175a021c4b743d29f109140d95
  2611a57ca4b23fadfda5a5258e8e9e001d41c621b4e6a8bb4f020649b1e0ffef
  e58c543aacbb8b703f75d684860b239a0d8347212c5579956450729174037c02
  cd79f70807e56f3c4dd6ed7fbbee508677e34ef19b2475011ae851d57b21fc50
  f97dcd998bb04219563ba4428e10cc123095439352b03b2287f2ff9a2cc50bf4
  a79a9f2236b3f773a366a4c504e3ea2965212847cee5b0d8ccb5f8066859a6a2
  0866afd16cbaa6f6c7273425de95e483ed9450d475c96bd42bc21f1920d403fb
  a7a5ebccb5811a5056fefc6bfcc283a6999894b96799ea3570b310ee7d0e2bf8
  21e56a375914db01e4aaeb2e31056501dae9ca65d715ac87bf165c031ae8dae4
  a4dea396eaa9ef1ac2ce943377abd73cd7e24b1950efe7cb3a55dfbf9758994c
  8656fe557e61e98e78a7136f7f82c2352bc42224b1a15c255c920b8cbf439027
  0b7ed4e9662e3c560cac8419a8ee83c65f9066d272dd57a83ceba465257a8683
  9cd88c812df8f301a118fad37b8a0ff6bb5b95efe5e8ca7bb65254a212a7c15a
  588252502f1b90f69f3859ec5c4a5970d04642782f85c7775d17e61d7d8c39e1
  e3e4d8418cfc2f5fb968eac3d223b2fcf99a9d17c420d6605402e50503a46138
  965f3cb910f146f697f98810ad9bec8090f3d77a3e0bc4d6dd4927607985db13
)

status=0
for index in $(seq 1 19); do
  part="$(printf '%s/parts/canon(4).odt.b64.part-%03d' "$package_dir" "$index")"
  actual_part_hash="$(sha256sum "$part" | awk '{print $1}')"
  expected_part_hash="${expected_part_hashes[$((index - 1))]}"
  if [[ "$actual_part_hash" != "$expected_part_hash" ]]; then
    echo "Part $(printf '%03d' "$index") hash mismatch: expected $expected_part_hash, got $actual_part_hash" >&2
    status=1
  fi
done

if [[ "$status" -ne 0 ]]; then
  exit "$status"
fi

cat "$package_dir"/parts/canon\(4\).odt.b64.part-* | base64 --decode > "$output"

actual_size="$(wc -c < "$output" | tr -d ' ')"
expected_size="113825"
if [[ "$actual_size" != "$expected_size" ]]; then
  echo "Size mismatch: expected $expected_size bytes, got $actual_size" >&2
  exit 1
fi

actual_hash="$(sha256sum "$output" | awk '{print $1}')"
expected_hash="adc2dd18e9a5cf2f3b9fd63dac32e6859d878185b29506b420c3fcdccd25936d"
if [[ "$actual_hash" != "$expected_hash" ]]; then
  echo "ODT hash mismatch: expected $expected_hash, got $actual_hash" >&2
  exit 1
fi

echo "Verified canon(4).odt: $actual_size bytes; SHA-256 $actual_hash"
