#!/bin/bash
# WSL shim: run the Windows OAuth-authed wrangler. SQL goes through a --file (no shell quoting).
args=(); db=""; json=0; sql=""
while [ $# -gt 0 ]; do
  case "$1" in
    d1|execute) shift; continue;;
    --remote) shift; continue;;
    --json) json=1; shift; continue;;
    --command) sql="$2"; shift 2; continue;;
    *) db="$1"; shift;;
  esac
done
if [[ "$sql" =~ ^[[:space:]]*[Ss][Ee][Ll][Ee][Cc][Tt] ]] && [[ "$sql" != *'"'* ]] && [[ "$sql" != *'%'* ]]; then
  cd /mnt/c/Users/example && cmd.exe /c wrangler d1 execute "$db" --remote --json --command "$sql" 2>/dev/null | tr -d '\r' | sed -n '/^\[/,$p'
  exit ${PIPESTATUS[0]}
fi
f=/mnt/c/Users/example/intake-sql/q.$$.sql
printf '%s' "$sql" > "$f"
j=""; [ $json = 1 ] && j="--json"
cd /mnt/c/Users/example && cmd.exe /c wrangler d1 execute "$db" --remote $j --file "C:\Users\example\\intake-sql\\q.$$.sql" | tr -d '\r'
rc=${PIPESTATUS[0]}; rm -f "$f"; exit $rc
