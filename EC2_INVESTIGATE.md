# EC2 Investigation — Bank Adviser returning HTML instead of JSON

## Quick diagnosis (run these in order)

### 1. Check what code is deployed
```bash
cd ~/personal-intelligence
git log --oneline -5
# Should show: ce48131 fix(bank-adviser): remove nginx auth_request...
# If not, run: git pull origin main
```

### 2. Check agents service status
```bash
systemctl status personal-intelligence-agents
# Look for: Active: active (running) or Active: failed

journalctl -u personal-intelligence-agents -n 50 --no-pager
# Look for: startup errors, import errors, exception tracebacks
```

### 3. Check API service status
```bash
systemctl status personal-intelligence-api
journalctl -u personal-intelligence-api -n 30 --no-pager
```

### 4. Test bank adviser locally (bypasses CloudFront + nginx — hits port 8001 directly)
```bash
# Get a valid token first (from browser devtools → Application → Session Storage → adel_access_token)
TOKEN="paste_your_token_here"

curl -s -w "\n\nHTTP_STATUS: %{http_code}" \
  http://127.0.0.1:8001/api/banking/analyse \
  -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"mode": "ytd"}' | tail -5
# Expected: HTTP_STATUS: 200 (or 404 if no statements, or 503 if MCP not configured)
# If: HTTP_STATUS: 500 or connection refused → agents service is broken
```

### 5. Check nginx config that is actually running
```bash
cat /etc/nginx/conf.d/personal-intelligence.conf | grep -A3 "banking"
# Expected: location /api/banking/ { proxy_pass http://127.0.0.1:8001; (NO auth_request line)
# If you see auth_request: copy the new config manually (see Step 6)
```

### 6. Manually deploy nginx config (if Step 5 shows wrong config)
```bash
cp ~/personal-intelligence/nginx/personal-intelligence.conf /etc/nginx/conf.d/personal-intelligence.conf
nginx -t          # must say: syntax is ok
systemctl reload nginx
```

### 7. If agents service is failed — restart and watch logs live
```bash
systemctl restart personal-intelligence-agents
journalctl -u personal-intelligence-agents -f
# Then trigger a bank analysis from the browser and watch what logs appear
```

---

## Most likely root causes

| Symptom | Cause | Fix |
|---------|-------|-----|
| `agents: failed` in systemctl status | Import error or startup crash in new code | See journalctl output — likely a missing module or env var |
| HTTP 500 from port 8001 directly | BankAdviser throws exception during analysis | journalctl will show the traceback |
| nginx has `auth_request` for `/api/banking/` | nginx config was never redeployed | Step 6 above |
| Port 8001 connection refused | Agents service not running | Restart + check logs |

---

## After fixing — verify end-to-end
```bash
# 1. Service is active
systemctl is-active personal-intelligence-agents && echo "OK"

# 2. Test through nginx (bypasses CloudFront)
TOKEN="your_token"
curl -s -o /dev/null -w "%{http_code}" \
  http://127.0.0.1/api/banking/analyse \
  -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"mode": "ytd"}'
# Expected: 200 or 404 (not 500, not connection refused)
```
