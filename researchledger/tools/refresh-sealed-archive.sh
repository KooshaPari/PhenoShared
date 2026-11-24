#!/bin/bash
# Keep the sealed corpus archive current.
#
#   --check    read-only: is the sealed copy older than the live corpus?
#   --refresh  re-seal, verify, compress, push off-host, verify the push.
#
# The live corpus is written by the ingest pipeline in
# KooshaPari/PhenoShared/researchledger/ingest/. A sealed copy is only a backup
# if it postdates the last write to the corpus, so the whole point of this
# script is that comparison rather than a calendar.
set -uo pipefail

CORPUS="${ARCHIVE_CORPUS:-${HOME}/CodeProjects/docs/reports/Exports/analysis/research_ledger.sqlite}"
SEAL_DIR="${ARCHIVE_SEAL_DIR:-${HOME}/CodeProjects/backups/analysis}"
DESK_DIR="E:/analysis-transfer"
MODE="${1:---check}"

mkdir -p "${SEAL_DIR}"

corpus_stat() { stat -f '%m %z' "$1" 2>/dev/null; }

# The newest sealed copy, if any. Archives only: the .sha256 sidecars sit
# alongside them and would otherwise be mistaken for the archive itself.
LATEST_SEAL=""
for candidate in "${SEAL_DIR}"/research_ledger.sqlite.sealed-*; do
	[[ -e ${candidate} ]] || continue
	[[ ${candidate} == *.sha256 ]] && continue
	if [[ -z ${LATEST_SEAL} || ${candidate} -nt ${LATEST_SEAL} ]]; then
		LATEST_SEAL=${candidate}
	fi
done

if [[ ! -f ${CORPUS} ]]; then
	echo "FAIL: no live corpus at ${CORPUS}"
	exit 2
fi

CORPUS_STAT=$(corpus_stat "${CORPUS}")
read -r CORPUS_MTIME CORPUS_SIZE <<<"${CORPUS_STAT}"

SEAL_MTIME=0
SEAL_SIZE=0
if [[ -n ${LATEST_SEAL} ]]; then
	SEAL_STAT=$(corpus_stat "${LATEST_SEAL}")
	read -r SEAL_MTIME SEAL_SIZE <<<"${SEAL_STAT}"
fi

# Decide on freshness first. A seal is stale when the live corpus has been
# written since it was taken; that comparison is the whole point, and it must
# not be pre-empted by filename bookkeeping.
if [[ -n ${LATEST_SEAL} && ${SEAL_MTIME} -ge ${CORPUS_MTIME} ]]; then
	echo "UP_TO_DATE: the sealed copy postdates the live corpus"
	echo "  sealed ${LATEST_SEAL}"
	echo "  live   mtime ${CORPUS_MTIME} size ${CORPUS_SIZE}"
	exit 0
fi

if [[ -z ${LATEST_SEAL} ]]; then
	echo "REFRESH_NEEDED: no sealed copy exists (live corpus ${CORPUS_SIZE} bytes, mtime ${CORPUS_MTIME})"
else
	echo "REFRESH_NEEDED: the live corpus was written after the sealed copy"
	echo "  live   mtime ${CORPUS_MTIME} size ${CORPUS_SIZE}"
	echo "  sealed mtime ${SEAL_MTIME} size ${SEAL_SIZE} (${LATEST_SEAL})"
fi

# A stamp names a day, not a seal: a second refresh on the same day needs a
# distinct name so the earlier file is never overwritten.
STAMP=$(date -u +%Y%m%d)
DEST="${SEAL_DIR}/research_ledger.sqlite.sealed-${STAMP}"
N=2
while [[ -e ${DEST} ]]; do
	DEST="${SEAL_DIR}/research_ledger.sqlite.sealed-${STAMP}-${N}"
	N=$((N + 1))
done

if [[ ${MODE} != "--refresh" ]]; then
	echo "  would write ${DEST}"
	exit 1
fi

RECEIPT_NAME=$(basename "${DEST}")
RECEIPT_NAME=${RECEIPT_NAME#research_ledger.sqlite.sealed-}
RECEIPT="${HOME}/CodeProjects/temp/corpus-verify/refresh-${RECEIPT_NAME}.txt"
# Transcript to console and receipt. Bash gives no way to observe the exit
# status of a process substitution, so there is nothing here to check.
# shellcheck disable=SC2312
exec > >(tee "${RECEIPT}") 2>&1

NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "=== REFRESH ${STAMP} ${NOW} ==="

echo "--- sealing with the SQLite online backup API (WAL-safe, not cp)"
sqlite3 "file:${CORPUS}?mode=ro" ".backup '${DEST}'" || {
	echo "FAIL: backup failed"
	exit 1
}
chmod 444 "${DEST}"
ls -l "${DEST}"

echo "--- hashing"
shasum -a 256 "${DEST}" | tee "${DEST}.sha256"

echo "--- structural check: page count and page size"
PAGES_LIVE=$(sqlite3 "file:${CORPUS}?mode=ro&immutable=1" "PRAGMA page_count;")
PAGES_SEAL=$(sqlite3 "file:${DEST}?mode=ro&immutable=1" "PRAGMA page_count;")
SIZE_SEAL=$(stat -f%z "${DEST}")
echo "live page_count=${PAGES_LIVE}  sealed page_count=${PAGES_SEAL}  sealed size=${SIZE_SEAL}"
if [[ ${PAGES_LIVE} != "${PAGES_SEAL}" ]]; then
	echo "FAIL: page count differs between the live corpus and the sealed copy"
	exit 1
fi

echo "--- compressing for the off-host copy"
GZ="${HOME}/CodeProjects/temp/corpus-xfer/corpus-${STAMP}.sqlite.gz"
gzip -1 -c "${DEST}" >"${GZ}" || {
	echo "FAIL: compression failed"
	exit 1
}
GZ_SHA=$(shasum -a 256 "${GZ}" | awk '{print $1}')
GZ_SIZE=$(stat -f%z "${GZ}")
echo "compressed ${GZ_SIZE} bytes, sha256 ${GZ_SHA}"

echo "--- pushing to the desk node"
ssh -o ConnectTimeout=15 -o ServerAliveInterval=30 -o ServerAliveCountMax=60 desk-lan \
	"mkdir ${DESK_DIR}" >/dev/null 2>&1
scp -o ConnectTimeout=15 -o ServerAliveInterval=30 "${GZ}" "desk-lan:${DESK_DIR}/corpus-${STAMP}.sqlite.gz" || {
	echo "FAIL: the transfer to the desk failed"
	exit 1
}

echo "--- verifying the off-host copy"
REMOTE_SHA=$(ssh -o ConnectTimeout=15 -o ServerAliveInterval=30 desk-lan \
	"sha256sum ${DESK_DIR}/corpus-${STAMP}.sqlite.gz" | awk '{print $1}')
echo "remote sha256 ${REMOTE_SHA}"
if [[ ${REMOTE_SHA} != "${GZ_SHA}" ]]; then
	echo "FAIL: the off-host copy does not match the local compressed archive"
	exit 1
fi

echo "--- verifying the off-host archive decompresses to the sealed archive's hash"
LOCAL_RAW=$(gzip -dc "${GZ}" | shasum -a 256 | awk '{print $1}')
DEST_SHA=$(awk '{print $1}' "${DEST}.sha256")
echo "decompressed sha256 ${LOCAL_RAW}"
if [[ ${LOCAL_RAW} != "${DEST_SHA}" ]]; then
	echo "FAIL: the archive does not decompress to the sealed copy"
	exit 1
fi

rm -f "${GZ}"
echo "REFRESH_OK: sealed ${DEST}, off-host copy verified"
COMPLETED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "=== REFRESH COMPLETE ${COMPLETED_AT} ==="
