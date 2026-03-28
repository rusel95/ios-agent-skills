#!/bin/bash
# iOS Security Quick Scan — grep-based pre-scan for CRITICAL and HIGH patterns
# Usage: ./quick-scan.sh <project-root>
# Returns non-zero exit code if CRITICAL findings detected
#
# LIMITATIONS: This script only catches single-line literal patterns (e.g.,
# `UserDefaults.standard.set(token, forKey: "authToken")` on one line).
# It will NOT detect: multi-line calls, constant-based keys, indirect references,
# or patterns requiring data-flow analysis. Use this as a first pass — the full
# audit workflow in SKILL.md covers contextual and semantic analysis.

set -euo pipefail

PROJECT_ROOT="${1:-.}"
CRITICAL_COUNT=0
HIGH_COUNT=0

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

echo "=== iOS Security Quick Scan ==="
echo "Scanning: $PROJECT_ROOT"
echo ""

# --- CRITICAL PATTERNS ---

echo -e "${RED}--- CRITICAL PATTERNS ---${NC}"

# C1: Hardcoded secrets
echo -n "[C1] Hardcoded secrets: "
MATCHES=$(grep -rn --include="*.swift" --include="*.m" --include="*.mm" --include="*.h" \
    -E '(apiKey|api_key|apiSecret|api_secret|secretKey|secret_key|PRIVATE_KEY|client_secret|clientSecret)\s*[:=]' \
    "$PROJECT_ROOT" 2>/dev/null | grep -vE '^\s*//' | grep -v "test" | grep -v "Test" | grep -v "mock" | grep -v "Mock" || true)
if [ -n "$MATCHES" ]; then
    COUNT=$(echo "$MATCHES" | wc -l | tr -d ' ')
    echo -e "${RED}$COUNT potential finding(s)${NC}"
    echo "$MATCHES"
    CRITICAL_COUNT=$((CRITICAL_COUNT + COUNT))
else
    echo -e "${GREEN}None found${NC}"
fi
echo ""

# C2: Sensitive data in UserDefaults
echo -n "[C2] Sensitive data in UserDefaults: "
MATCHES=$(grep -rn --include="*.swift" --include="*.m" \
    -E 'UserDefaults.*set.*forKey.*("|@")(.*[Pp]assword|.*[Tt]oken|.*[Ss]ecret|.*[Cc]redential|.*[Ss]ession[Ii]d|.*[Aa]uth)' \
    "$PROJECT_ROOT" 2>/dev/null || true)
if [ -n "$MATCHES" ]; then
    COUNT=$(echo "$MATCHES" | wc -l | tr -d ' ')
    echo -e "${RED}$COUNT potential finding(s)${NC}"
    echo "$MATCHES"
    CRITICAL_COUNT=$((CRITICAL_COUNT + COUNT))
else
    echo -e "${GREEN}None found${NC}"
fi
echo ""

# C3: Disabled ATS
echo -n "[C3] Globally disabled ATS: "
MATCHES=$(grep -rn --include="*.plist" \
    -A1 'NSAllowsArbitraryLoads' \
    "$PROJECT_ROOT" 2>/dev/null | grep -i 'true\|YES' || true)
if [ -n "$MATCHES" ]; then
    COUNT=$(echo "$MATCHES" | wc -l | tr -d ' ')
    echo -e "${RED}$COUNT potential finding(s)${NC}"
    echo "$MATCHES"
    CRITICAL_COUNT=$((CRITICAL_COUNT + COUNT))
else
    echo -e "${GREEN}None found${NC}"
fi
echo ""

# C4: Hardcoded crypto keys
echo -n "[C4] Hardcoded crypto keys: "
MATCHES=$(grep -rn --include="*.swift" --include="*.m" --include="*.mm" \
    -E 'SymmetricKey\(data:|getCString:.*maxLength:.*encoding:.*kCCKeySizeAES|\[UInt8\]\s*=\s*\[0x' \
    "$PROJECT_ROOT" 2>/dev/null || true)
if [ -n "$MATCHES" ]; then
    COUNT=$(echo "$MATCHES" | wc -l | tr -d ' ')
    echo -e "${RED}$COUNT potential finding(s)${NC}"
    echo "$MATCHES"
    CRITICAL_COUNT=$((CRITICAL_COUNT + COUNT))
else
    echo -e "${GREEN}None found${NC}"
fi
echo ""

# C5: Insecure deserialization
echo -n "[C5] Insecure deserialization: "
MATCHES=$(grep -rn --include="*.swift" --include="*.m" \
    -E 'unarchiveObject\(with(File|Data):|unarchiveObjectWith(File|Data):|unarchiveTopLevelObjectWithData:' \
    "$PROJECT_ROOT" 2>/dev/null || true)
if [ -n "$MATCHES" ]; then
    COUNT=$(echo "$MATCHES" | wc -l | tr -d ' ')
    echo -e "${RED}$COUNT potential finding(s)${NC}"
    echo "$MATCHES"
    CRITICAL_COUNT=$((CRITICAL_COUNT + COUNT))
else
    echo -e "${GREEN}None found${NC}"
fi
echo ""

# C6: Hardcoded/zero IVs (Swift)
echo -n "[C6] Hardcoded/zero IVs: "
MATCHES=$(grep -rn --include="*.swift" --include="*.m" \
    -E 'Data\(repeating:\s*0,\s*count:\s*(8|12|16|24|32)' \
    "$PROJECT_ROOT" 2>/dev/null || true)
if [ -n "$MATCHES" ]; then
    COUNT=$(echo "$MATCHES" | wc -l | tr -d ' ')
    echo -e "${RED}$COUNT potential finding(s)${NC}"
    echo "$MATCHES"
    CRITICAL_COUNT=$((CRITICAL_COUNT + COUNT))
else
    echo -e "${GREEN}None found${NC}"
fi
echo ""

# C6b: NULL IV in CCCrypt (ObjC)
echo -n "[C6b] NULL IV in CCCrypt: "
MATCHES=$(grep -rn --include="*.m" --include="*.mm" \
    -E 'CCCrypt\([^)]*,\s*NULL,' \
    "$PROJECT_ROOT" 2>/dev/null || true)
if [ -n "$MATCHES" ]; then
    COUNT=$(echo "$MATCHES" | wc -l | tr -d ' ')
    echo -e "${RED}$COUNT potential finding(s)${NC}"
    echo "$MATCHES"
    CRITICAL_COUNT=$((CRITICAL_COUNT + COUNT))
else
    echo -e "${GREEN}None found${NC}"
fi
echo ""

# --- HIGH PATTERNS ---

echo -e "${YELLOW}--- HIGH PATTERNS ---${NC}"

# H2: Deprecated Keychain accessibility
echo -n "[H2] Deprecated Keychain accessibility: "
MATCHES=$(grep -rn --include="*.swift" --include="*.m" \
    'kSecAttrAccessibleAlways' \
    "$PROJECT_ROOT" 2>/dev/null || true)
if [ -n "$MATCHES" ]; then
    COUNT=$(echo "$MATCHES" | wc -l | tr -d ' ')
    echo -e "${YELLOW}$COUNT potential finding(s)${NC}"
    echo "$MATCHES"
    HIGH_COUNT=$((HIGH_COUNT + COUNT))
else
    echo -e "${GREEN}None found${NC}"
fi
echo ""

# H3: Deprecated crypto
echo -n "[H3] Deprecated crypto algorithms: "
MATCHES=$(grep -rn --include="*.swift" --include="*.m" --include="*.mm" \
    -E 'CC_MD5\(|CC_SHA1\(|kCCAlgorithmDES|kCCAlgorithm3DES|kCCAlgorithmRC4|Insecure\.MD5|Insecure\.SHA1' \
    "$PROJECT_ROOT" 2>/dev/null || true)
if [ -n "$MATCHES" ]; then
    COUNT=$(echo "$MATCHES" | wc -l | tr -d ' ')
    echo -e "${YELLOW}$COUNT potential finding(s)${NC}"
    echo "$MATCHES"
    HIGH_COUNT=$((HIGH_COUNT + COUNT))
else
    echo -e "${GREEN}None found${NC}"
fi
echo ""

# H4: ECB mode
echo -n "[H4] ECB mode encryption: "
MATCHES=$(grep -rn --include="*.swift" --include="*.m" --include="*.mm" \
    'kCCOptionECBMode' \
    "$PROJECT_ROOT" 2>/dev/null || true)
if [ -n "$MATCHES" ]; then
    COUNT=$(echo "$MATCHES" | wc -l | tr -d ' ')
    echo -e "${YELLOW}$COUNT potential finding(s)${NC}"
    echo "$MATCHES"
    HIGH_COUNT=$((HIGH_COUNT + COUNT))
else
    echo -e "${GREEN}None found${NC}"
fi
echo ""

# H5: Insecure randomness
echo -n "[H5] Insecure random number generation: "
MATCHES=$(grep -rn --include="*.swift" --include="*.m" --include="*.mm" --include="*.c" \
    -E '\brand\(\)|\brandom\(\)|\bsrand\(' \
    "$PROJECT_ROOT" 2>/dev/null || true)
if [ -n "$MATCHES" ]; then
    COUNT=$(echo "$MATCHES" | wc -l | tr -d ' ')
    echo -e "${YELLOW}$COUNT potential finding(s)${NC}"
    echo "$MATCHES"
    HIGH_COUNT=$((HIGH_COUNT + COUNT))
else
    echo -e "${GREEN}None found${NC}"
fi
echo ""

# H6: UIWebView
echo -n "[H6] UIWebView usage: "
MATCHES=$(grep -rn --include="*.swift" --include="*.m" --include="*.mm" --include="*.h" --include="*.xib" --include="*.storyboard" \
    'UIWebView' \
    "$PROJECT_ROOT" 2>/dev/null || true)
if [ -n "$MATCHES" ]; then
    COUNT=$(echo "$MATCHES" | wc -l | tr -d ' ')
    echo -e "${YELLOW}$COUNT potential finding(s)${NC}"
    echo "$MATCHES"
    HIGH_COUNT=$((HIGH_COUNT + COUNT))
else
    echo -e "${GREEN}None found${NC}"
fi
echo ""

# --- SUMMARY ---

echo "=== SUMMARY ==="
if [ "$CRITICAL_COUNT" -gt 0 ]; then
    echo -e "${RED}CRITICAL findings: $CRITICAL_COUNT${NC}"
fi
if [ "$HIGH_COUNT" -gt 0 ]; then
    echo -e "${YELLOW}HIGH findings: $HIGH_COUNT${NC}"
fi
if [ "$CRITICAL_COUNT" -eq 0 ] && [ "$HIGH_COUNT" -eq 0 ]; then
    echo -e "${GREEN}No CRITICAL or HIGH patterns detected in quick scan.${NC}"
    echo "Run a full audit for MEDIUM/LOW and contextual findings."
fi

# Exit with non-zero if CRITICAL findings
if [ "$CRITICAL_COUNT" -gt 0 ]; then
    exit 1
fi
exit 0
