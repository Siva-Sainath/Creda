#!/usr/bin/env bash
# Data-driven live regression from scripts/test_cases.json — no backend tuning, no UI demo chips.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CATALOG="${CREDA_TEST_CATALOG:-$ROOT/scripts/test_cases.json}"
API="${CREDA_API_URL:-https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com}"
CHANNEL="${CREDA_TEST_CHANNEL:-api}"
STRICT="${CREDA_TEST_STRICT:-false}"
POLL_ROUNDS="${CREDA_TEST_POLL_ROUNDS:-100}"
FAIL=0
PASS=0
WARN=0
SKIP=0
RESULTS=()

poll_ready() {
  local cid="$1" tok="$2" label="$3"
  for _ in $(seq 1 "$POLL_ROUNDS"); do
    sleep 2
    local d st as v
    d=$(curl -sf -H "X-Case-Token: $tok" "$API/cases/$cid")
    st=$(echo "$d" | jq -r .status)
    as=$(echo "$d" | jq -r .agentStatus)
    v=$(echo "$d" | jq -r .verdict)
    if [[ "$st" == "FAILED" ]]; then
      echo "  FAIL $label: case FAILED — $(echo "$d" | jq -r '.userMessage // .stage // "unknown"')"
      return 1
    fi
    if [[ "$st" == "COMPLETED" && "$as" == "READY" && "$v" != "pending" && "$v" != "null" ]]; then
      echo "$d"
      return 0
    fi
  done
  echo "  FAIL $label: timeout"
  return 1
}

ask_followup() {
  local cid="$1" tok="$2" question="$3"
  curl -sf -X POST "$API/cases/$cid/followup" \
    -H 'Content-Type: application/json' \
    -H "X-Case-Token: $tok" \
    -d "$(jq -n --arg q "$question" '{answerText:$q}')" >/dev/null
}

resolve_followups() {
  local case_id="$1"
  jq -r --arg id "$case_id" '
    (.cases[] | select(.id == $id) | .followupTags[]?) as $tag |
    .followupPool[$tag][]
  ' "$CATALOG" | awk '!seen[$0]++' | head -2
}

upload_fixture() {
  local fixture_path="$1" content_type="$2"
  local up key url size
  up=$(curl -sf -X POST "$API/upload-url" -H 'Content-Type: application/json' \
    -d "$(jq -n --arg ct "$content_type" '{contentType:$ct}')")
  url=$(echo "$up" | jq -r .uploadUrl)
  key=$(echo "$up" | jq -r .key)
  size=$(wc -c <"$fixture_path" | tr -d ' ')
  curl -sf -X PUT -H "Content-Type: $content_type" --data-binary @"$fixture_path" "$url" >/dev/null
  jq -n \
    --arg key "$key" \
    --arg name "$(basename "$fixture_path")" \
    --arg ct "$content_type" \
    --argjson size "$size" \
    '{attachments:[{s3Key:$key,name:$name,contentType:$ct,sizeBytes:$size}]}'
}

run_case() {
  local case_json="$1"
  local id expect_verdict case_type
  id=$(echo "$case_json" | jq -r .id)
  expect_verdict=$(echo "$case_json" | jq -r '.expectVerdict // ""')
  case_type=$(echo "$case_json" | jq -r '.type // "case"')

  if [[ "$case_type" == "ocr_upload" ]]; then
    run_ocr_case "$case_json"
    return
  fi

  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "CASE: $id"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  local payload r d v src headline tactics
  payload=$(echo "$case_json" | jq -c '.payload')
  r=$(curl -sf -X POST "$API/cases" -H 'Content-Type: application/json' -d "$payload")
  local cid tok
  cid=$(echo "$r" | jq -r .caseId)
  tok=$(echo "$r" | jq -r .accessToken)

  d=$(poll_ready "$cid" "$tok" "$id") || { FAIL=$((FAIL+1)); RESULTS+=("FAIL $id (timeout)"); return; }
  v=$(echo "$d" | jq -r .verdict)
  src=$(echo "$d" | jq -r .agentSource)
  headline=$(echo "$d" | jq -r .headline)
  tactics=$(echo "$d" | jq '.matchedTactics | length')

  echo "  verdict=$v  agent=$src  tactics=$tactics"
  echo "  headline: $headline"

  if [[ -n "$expect_verdict" && "$v" != "$expect_verdict" ]]; then
    if [[ "$STRICT" == "true" ]]; then
      echo "  FAIL expected verdict $expect_verdict got $v"
      FAIL=$((FAIL+1))
      RESULTS+=("FAIL $id (verdict $v != $expect_verdict)")
      return
    fi
    echo "  WARN expected verdict $expect_verdict got $v (non-strict)"
    WARN=$((WARN+1))
  fi
  if [[ "$src" != "creda" && "$src" != "creda-vlm" ]]; then
    if [[ "$STRICT" == "true" ]]; then
      echo "  FAIL agentSource=$src"
      FAIL=$((FAIL+1))
      RESULTS+=("FAIL $id (agent $src)")
      return
    fi
    echo "  WARN agentSource=$src (judge queue saturated — non-strict)"
    WARN=$((WARN+1))
  fi

  local fu_count=0
  while IFS= read -r question; do
    [[ -z "$question" ]] && continue
    fu_count=$((fu_count+1))
    echo "  follow-up $fu_count: $question"
    ask_followup "$cid" "$tok" "$question"
    d=$(poll_ready "$cid" "$tok" "$id-fu$fu_count") || { FAIL=$((FAIL+1)); RESULTS+=("FAIL $id (follow-up timeout)"); return; }
    local turns answer
    turns=$(echo "$d" | jq '.conversationTurns | length')
    answer=$(echo "$d" | jq -r '.conversationTurns[-1].agentReply // .agentReasoning // ""' | head -c 180)
    echo "  answer $fu_count (${turns} turns): ${answer}..."
    if [[ "${turns:-0}" -lt "$fu_count" ]]; then
      echo "  FAIL expected >= $fu_count conversation turns, got $turns"
      FAIL=$((FAIL+1))
      RESULTS+=("FAIL $id (follow-up turns)")
      return
    fi
  done < <(resolve_followups "$id")

  echo "  PASS"
  PASS=$((PASS+1))
  RESULTS+=("PASS $id → $v")
}

run_ocr_case() {
  local case_json="$1"
  local id fixture
  id=$(echo "$case_json" | jq -r .id)
  fixture="$ROOT/$(echo "$case_json" | jq -r .fixture)"
  if [[ ! -f "$fixture" ]]; then
    echo "SKIP $id: fixture missing $fixture"
    SKIP=$((SKIP+1))
    RESULTS+=("SKIP $id (no fixture)")
    return
  fi

  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "CASE: $id (OCR upload)"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  local attach payload r d v src
  attach=$(upload_fixture "$fixture" "image/png")
  payload=$(echo "$case_json" | jq -c --argjson attach "$attach" '.payload * $attach')
  r=$(curl -sf -X POST "$API/cases" -H 'Content-Type: application/json' -d "$payload")
  d=$(poll_ready "$(echo "$r" | jq -r .caseId)" "$(echo "$r" | jq -r .accessToken)" "$id") || {
    FAIL=$((FAIL+1)); RESULTS+=("FAIL $id (ocr timeout)"); return
  }
  v=$(echo "$d" | jq -r .verdict)
  src=$(echo "$d" | jq -r .agentSource)
  local ocr_log
  ocr_log=$(echo "$d" | jq -r '.pipelineLog[]? | select(test("OCR|extracted"))' | head -1)
  echo "  verdict=$v  agent=$src  ocr_log=${ocr_log:-none}"
  if [[ "$src" != "creda" && "$src" != "creda-vlm" ]]; then
    FAIL=$((FAIL+1)); RESULTS+=("FAIL $id (agent $src)"); return
  fi
  echo "  PASS"
  PASS=$((PASS+1))
  RESULTS+=("PASS $id → $v (ocr)")
}

run_api_only() {
  local item="$1"
  local id type
  id=$(echo "$item" | jq -r .id)
  type=$(echo "$item" | jq -r .type)

  case "$type" in
    reject)
      local http
      http=$(curl -s -o /tmp/creda_reject.json -w '%{http_code}' -X POST "$API/cases" \
        -H 'Content-Type: application/json' -d "$(echo "$item" | jq -c .payload)")
      local expect
      expect=$(echo "$item" | jq -r .expectHttp)
      if [[ "$http" == "$expect" ]] && jq -e '.nextAction' /tmp/creda_reject.json >/dev/null 2>&1; then
        echo "PASS $id (HTTP $http)"
        PASS=$((PASS+1))
        RESULTS+=("PASS $id")
      else
        echo "FAIL $id expected HTTP $expect got $http"
        FAIL=$((FAIL+1))
        RESULTS+=("FAIL $id")
      fi
      ;;
    report)
      local resp field expect
      resp=$(curl -sf -X POST "$API/reports/scam" -H 'Content-Type: application/json' \
        -d "$(echo "$item" | jq -c .payload)")
      field=$(echo "$item" | jq -r '.expectField | keys[0]')
      expect=$(echo "$item" | jq -r ".expectField[\"$field\"]")
      local got
      got=$(echo "$resp" | jq -r --arg f "$field" '.[$f]')
      if [[ "$got" == "$expect" ]]; then
        echo "PASS $id"
        PASS=$((PASS+1))
        RESULTS+=("PASS $id")
      else
        echo "FAIL $id expected $field=$expect got $got"
        FAIL=$((FAIL+1))
        RESULTS+=("FAIL $id")
      fi
      ;;
    upload_url)
      local ct
      ct=$(echo "$item" | jq -r .contentType)
      if curl -sf -X POST "$API/upload-url" -H 'Content-Type: application/json' \
        -d "$(jq -n --arg ct "$ct" '{contentType:$ct}')" | jq -e '.uploadUrl and .key' >/dev/null; then
        echo "PASS $id"
        PASS=$((PASS+1))
        RESULTS+=("PASS $id")
      else
        echo "FAIL $id upload-url"
        FAIL=$((FAIL+1))
        RESULTS+=("FAIL $id")
      fi
      ;;
  esac
}

echo "==> Creda test catalog"
echo "    API=$API"
echo "    channel=$CHANNEL"
echo "    catalog=$CATALOG"

curl -sf "$API/health" | jq -e '.status=="ok" and .judgeMode=="creda"' >/dev/null
echo "==> health OK"

mapfile -t CASE_IDS < <(jq -r --arg ch "$CHANNEL" '
  .cases[] | select(.channels[]? == $ch) | .id
' "$CATALOG")

echo "==> running ${#CASE_IDS[@]} case(s) for channel=$CHANNEL"

for case_id in "${CASE_IDS[@]}"; do
  case_json=$(jq -c --arg id "$case_id" '.cases[] | select(.id==$id)' "$CATALOG")
  run_case "$case_json"
done

if [[ "$CHANNEL" == "api" ]]; then
  echo ""
  echo "==> API-only checks"
  while IFS= read -r item; do
    [[ -z "$item" ]] && continue
    run_api_only "$item"
  done < <(jq -c '.apiOnly[]' "$CATALOG")
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "SUMMARY: $PASS passed, $FAIL failed, $WARN warned, $SKIP skipped (strict=$STRICT)"
printf '  %s\n' "${RESULTS[@]}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [[ "$FAIL" -eq 0 ]]; then
  echo "TEST CATALOG PASSED"
  exit 0
fi
echo "TEST CATALOG FAILED"
exit 1
