#!/usr/bin/env bash

set -euo pipefail

BUILD_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "$BUILD_DIR/../.." && pwd)"
PARENT_DIR="$(dirname -- "$ROOT_DIR")"
VERSION="$(tr -d '[:space:]' < "$ROOT_DIR/VERSION")"
OUTPUT="$PARENT_DIR/解放单手-$VERSION.zip"
STAGING_DIR="$(mktemp -d)"
PACKAGE_DIR="$STAGING_DIR/解放单手"

cleanup() {
    rm -rf "$STAGING_DIR"
}
trap cleanup EXIT

rm -f "$OUTPUT"
cp -a "$ROOT_DIR" "$PACKAGE_DIR"
rm -rf "$PACKAGE_DIR/.git" "$PACKAGE_DIR/.venv" \
    "$PACKAGE_DIR/build" "$PACKAGE_DIR/dist"
find "$PACKAGE_DIR" -type d -name '__pycache__' -prune -exec rm -rf {} +
find "$PACKAGE_DIR" -type f \( -name '*.pyc' -o -name '*.spec' \) -delete

cd "$STAGING_DIR"
zip -r "$OUTPUT" 解放单手

printf '跨电脑安装包已生成：%s\n' "$OUTPUT"
