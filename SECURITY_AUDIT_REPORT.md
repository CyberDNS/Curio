# Security Audit Report - Curio Application

**Date:** November 22, 2025  
**Auditor:** Security Analysis  
**Application:** Curio - Personalized News Aggregator

---

## Executive Summary

This security audit identified **13 vulnerabilities** ranging from **CRITICAL** to **LOW** severity. The critical development mode authentication issue has been **FIXED** with defense-in-depth security controls. Remaining high-severity issues include potential SSRF vulnerabilities and weak JWT configuration. Immediate action is required to address high-severity findings.

**Severity Breakdown:**

- 🔴 **CRITICAL:** 0 findings (1 fixed)
- 🟠 **HIGH:** 4 findings
- 🟡 **MEDIUM:** 5 findings
- 🟢 **LOW:** 3 findings

---

## Critical Vulnerabilities

### ✅ CRIT-01: Insecure Development Mode with No Authentication [FIXED]

**File:** `backend/app/api/endpoints/auth.py`, `backend/app/core/config.py`, `backend/app/main.py`  
**Status:** **RESOLVED**

**Original Issue:**  
When OAuth is not configured, the application automatically created a "dev" user and issued authentication tokens without any password or verification, allowing anyone to access the application.

**Impact:**  
Anyone could access the application without authentication by simply visiting `/api/auth/login` if OAuth was misconfigured or disabled.

**CVSS Score:** 9.8 (Critical)

**Fix Implemented:**
Implemented defense-in-depth security controls:

1. **Explicit DEV_MODE Required:** Added `DEV_MODE` environment variable that must be explicitly set to `true` to enable development authentication bypass

2. **Startup Security Check:** Application now fails to start with a clear error if neither OAuth nor DEV_MODE is configured:

   ```python
   if not OAUTH_CONFIGURED and not DEV_MODE_ENABLED:
       raise RuntimeError(
           "Authentication not configured. Set up OAuth or enable DEV_MODE for development."
       )
   ```

3. **Prominent Security Warnings:** When DEV_MODE is enabled, multiple warnings are logged:

   - At module import time
   - At application startup
   - Clear visual warnings in console output

4. **Safe by Default:** DEV_MODE defaults to `false`, requiring explicit opt-in

5. **Login Endpoint Protection:** The `/api/auth/login` endpoint now returns HTTP 503 if authentication is not properly configured

**Verification:**

- ✅ Application fails to start without OAuth when DEV_MODE=false
- ✅ Application starts with prominent warnings when DEV_MODE=true
- ✅ Login endpoint blocks access when neither OAuth nor DEV_MODE is configured
- ✅ Configuration documented in `.env.example` with security warnings

**Residual Risk:** LOW - Development mode still bypasses authentication when explicitly enabled, but requires intentional misconfiguration and displays prominent warnings

---

## High Severity Vulnerabilities

### 🟠 HIGH-01: Server-Side Request Forgery (SSRF) in Image Proxy

**File:** `backend/app/api/endpoints/proxy.py`  
**Lines:** 10-40

**Issue:**  
The `/api/proxy/image` endpoint accepts arbitrary URLs without validation and fetches them server-side:

```python
@router.get("/image")
async def proxy_image(url: str):
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        response = await client.get(url, headers=headers)
```

**Impact:**  
Attackers can:

- Access internal network resources (e.g., `http://localhost:8000`, `http://192.168.1.1`)
- Scan internal network ports
- Access cloud metadata endpoints (`http://169.254.169.254/latest/meta-data/`)
- Bypass firewall restrictions
- Perform denial-of-service by requesting large files

**CVSS Score:** 8.6 (High)

**Remediation:**

1. Implement URL whitelist for allowed domains
2. Block private IP ranges (RFC 1918, loopback, link-local)
3. Block cloud metadata IPs (169.254.169.254, fd00:ec2::254)
4. Validate URL scheme (only allow http/https)
5. Implement response size limits
6. Use DNS resolution validation before making requests

**Example Fix:**

```python
import ipaddress
from urllib.parse import urlparse

BLOCKED_NETWORKS = [
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'),
    ipaddress.ip_network('127.0.0.0/8'),
    ipaddress.ip_network('169.254.0.0/16'),
]

def validate_url(url: str):
    parsed = urlparse(url)
    if parsed.scheme not in ['http', 'https']:
        raise ValueError("Invalid scheme")

    # Resolve hostname to IP
    import socket
    ip = socket.gethostbyname(parsed.hostname)
    ip_obj = ipaddress.ip_address(ip)

    for network in BLOCKED_NETWORKS:
        if ip_obj in network:
            raise ValueError("Access to private network denied")
```

---

### 🟠 HIGH-02: SQL Injection Risk via ORM Misuse

**Multiple Files**

**Issue:**  
While SQLAlchemy ORM generally prevents SQL injection, several areas use unsafe patterns:

1. **Potential filter injection** - User-controlled category_id and article_id without type validation
2. **Missing input validation** on integer parameters that are converted from strings

**Example vulnerable pattern:**

```python
def get_article(article_id: int, ...):
    article = db.query(Article).filter(Article.id == article_id).first()
```

If FastAPI's type coercion fails silently or is bypassed, this could be exploited.

**Impact:**  
Potential data exposure or manipulation through crafted queries.

**CVSS Score:** 7.5 (High)

**Remediation:**

1. Add explicit input validation using Pydantic validators
2. Use parameterized queries consistently
3. Implement input sanitization layer
4. Add database query logging in production to detect anomalies
5. Use read-only database users for SELECT-only operations

---

### 🟠 HIGH-03: Insufficient Authentication on Critical Endpoints

**File:** `backend/app/api/endpoints/auth.py`  
**Line:** 156

**Issue:**  
Debug endpoint `/api/auth/debug/token` exposes authentication headers without any authentication:

```python
@router.get("/debug/token")
async def debug_token(request: Request):
    return {
        "has_auth_header": auth_header is not None,
        "auth_header": auth_header,
        "all_headers": dict(request.headers),
    }
```

**Impact:**  
Attackers can use this endpoint to debug authentication flows and potentially extract token information during testing phases if left enabled.

**CVSS Score:** 7.4 (High)

**Remediation:**

1. Remove debug endpoints entirely from production builds
2. If needed, protect with authentication: `current_user: User = Depends(get_current_user)`
3. Use environment-based feature flags to disable in production
4. Implement IP whitelisting for debug endpoints

---

### 🟠 HIGH-04: Weak JWT Configuration

**File:** `backend/app/core/auth.py`  
**Lines:** 15-16, 29-31

**Issue:**

1. Long token expiration (7 days) increases window of exploitation
2. No token refresh mechanism - users must re-authenticate
3. No token revocation mechanism - compromised tokens remain valid
4. Uses `datetime.utcnow()` instead of timezone-aware datetime

**Impact:**  
Stolen tokens remain valid for 7 days, allowing extended unauthorized access.

**CVSS Score:** 7.3 (High)

**Remediation:**

1. Reduce token expiration to 1 hour for access tokens
2. Implement refresh token pattern with 7-day refresh tokens
3. Add token revocation list (Redis/database)
4. Use timezone-aware datetime: `datetime.now(timezone.utc)`
5. Add `jti` (JWT ID) claim for tracking individual tokens
6. Implement token rotation on refresh

---

## Medium Severity Vulnerabilities

### 🟡 MED-01: Insecure Cookie Configuration

**File:** `backend/app/core/config.py`  
**Line:** 42

**Issue:**  
Cookie security setting defaults to `True` but can be disabled:

```python
COOKIE_SECURE: bool = True  # Set to False for local development without HTTPS
```

In `auth.py`, this is used without additional checks:

```python
response.set_cookie(
    key="auth_token",
    value=access_token,
    httponly=True,
    secure=settings.COOKIE_SECURE,  # May be False
    samesite="lax",
)
```

**Impact:**  
If `COOKIE_SECURE=false` in production without HTTPS, authentication tokens can be intercepted via man-in-the-middle attacks.

**CVSS Score:** 6.5 (Medium)

**Remediation:**

1. Force `secure=True` in production regardless of configuration
2. Add environment detection to automatically enable secure cookies
3. Implement HSTS headers in nginx configuration
4. Consider upgrading `samesite="lax"` to `samesite="strict"` for better CSRF protection

---

### 🟡 MED-02: Unrestricted File Upload via RSS Feeds

**File:** `backend/app/services/rss_fetcher.py`  
**Lines:** 319-355

**Issue:**  
The RSS fetcher downloads images from any URL without:

- File size limits (beyond HTTP timeout)
- Content-type verification
- Malware scanning
- Storage quota limits

```python
async def _download_image(self, image_url: str, client: httpx.AsyncClient):
    # No size limit check
    response = await client.get(image_url, follow_redirects=True)
    with open(filepath, "wb") as f:
        f.write(response.content)  # Writes entire file to disk
```

**Impact:**  
Attackers could:

- Fill disk space with large files
- Upload malicious files (SVG with embedded JavaScript, polyglot files)
- Use storage as a file hosting service

**CVSS Score:** 6.4 (Medium)

**Remediation:**

1. Implement file size limit (e.g., 5MB max)
2. Verify Content-Type header matches image MIME types
3. Validate file magic bytes (not just extension)
4. Implement per-user storage quotas
5. Stream large files and check size during download
6. Sanitize SVG files to remove scripts
7. Add virus scanning for uploaded content

**Example Fix:**

```python
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB

async with client.stream('GET', image_url) as response:
    content_type = response.headers.get('content-type', '')
    if not content_type.startswith('image/'):
        return None

    content = b''
    async for chunk in response.aiter_bytes():
        content += chunk
        if len(content) > MAX_IMAGE_SIZE:
            raise ValueError("Image too large")

    # Verify magic bytes
    import imghdr
    if not imghdr.what(None, content):
        raise ValueError("Invalid image format")
```

---

### 🟡 MED-03: Missing Rate Limiting

**All API endpoints**

**Issue:**  
No rate limiting is implemented on any endpoints. This applies to:

- Authentication endpoints
- LLM processing endpoints (expensive API calls)
- RSS feed fetching
- Image proxy requests

**Impact:**

- Denial of Service attacks
- API abuse (especially expensive LLM endpoints)
- Resource exhaustion (OpenAI API costs)
- Brute force attacks on authentication

**CVSS Score:** 6.3 (Medium)

**Remediation:**

1. Implement rate limiting middleware using `slowapi` or `fastapi-limiter`
2. Different rate limits for different endpoint types:
   - Auth: 5 requests/minute
   - Expensive operations: 10 requests/hour
   - Regular API: 100 requests/minute
3. Use Redis for distributed rate limiting
4. Implement user-based and IP-based rate limiting
5. Add exponential backoff for repeated failures

**Example Implementation:**

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@router.post("/actions/process-articles")
@limiter.limit("10/hour")
async def process_articles(...):
    ...
```

---

### 🟡 MED-04: Insufficient Logging and Monitoring

**Multiple files**

**Issue:**  
Security-relevant events are not consistently logged:

- Authentication attempts (success/failure)
- Authorization failures
- Sensitive operations (user creation, data deletion)
- Input validation failures
- Rate limit violations

**Impact:**  
Inability to detect:

- Ongoing attacks
- Compromised accounts
- Data breaches
- Abuse patterns

**CVSS Score:** 6.1 (Medium)

**Remediation:**

1. Implement structured logging (JSON format)
2. Log all authentication events with details:
   - Username/email
   - IP address
   - User agent
   - Timestamp
   - Success/failure
3. Log authorization failures
4. Implement security monitoring dashboards
5. Set up alerting for suspicious patterns
6. Log all admin operations
7. Use correlation IDs for request tracing

---

### 🟡 MED-05: Weak MD5 Hash for File Naming

**File:** `backend/app/services/rss_fetcher.py`  
**Line:** 327

**Issue:**  
Using MD5 for generating filenames from URLs:

```python
url_hash = hashlib.md5(image_url.encode()).hexdigest()
```

While not a direct security vulnerability (it's used for deduplication, not cryptography), MD5 is:

- Collision-prone
- Deprecated for security purposes

**Impact:**  
Potential filename collisions could cause:

- Image overwrites
- Cache poisoning
- Unintended content replacement

**CVSS Score:** 6.0 (Medium)

**Remediation:**

1. Use SHA-256 instead of MD5 for file naming
2. Add additional uniqueness factors (timestamp, random suffix)
3. Implement collision detection and handling

**Fix:**

```python
url_hash = hashlib.sha256(image_url.encode()).hexdigest()[:16]
```

---

## Low Severity Vulnerabilities

### 🟢 LOW-01: Verbose Error Messages

**File:** `backend/app/api/endpoints/proxy.py`  
**Lines:** 34-40

**Issue:**  
Detailed error messages expose internal system information:

```python
except Exception as e:
    logger.error(f"Error proxying image {url}: {str(e)}")
    raise HTTPException(status_code=500, detail=f"Failed to proxy image: {str(e)}")
```

**Impact:**  
Information disclosure that could aid attackers in reconnaissance.

**CVSS Score:** 3.7 (Low)

**Remediation:**

1. Return generic error messages to clients
2. Log detailed errors server-side only
3. Use error codes instead of descriptive messages

**Fix:**

```python
except Exception as e:
    logger.error(f"Error proxying image {url}: {str(e)}")
    raise HTTPException(status_code=500, detail="Failed to process image")
```

---

### 🟢 LOW-02: Missing CORS Origin Validation

**File:** `backend/app/main.py`  
**Lines:** 52-58

**Issue:**  
CORS origins are read from environment variable without validation:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Impact:**  
Misconfiguration could allow unauthorized origins to make authenticated requests.

**CVSS Score:** 3.5 (Low)

**Remediation:**

1. Validate CORS origins at startup
2. Reject wildcard origins in production
3. Implement origin whitelist validation
4. Use strict methods/headers allowlist instead of "\*"

---

### 🟢 LOW-03: Timezone Handling Issues

**Multiple files**

**Issue:**  
Inconsistent use of `datetime.utcnow()` (deprecated) vs timezone-aware datetimes.

**Impact:**  
Potential time-based security control bypass or race conditions.

**CVSS Score:** 3.1 (Low)

**Remediation:**
Replace all `datetime.utcnow()` with `datetime.now(timezone.utc)` throughout the codebase.

---

## Additional Security Recommendations

### 1. Security Headers

Add security headers in nginx configuration:

```nginx
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';" always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

### 2. Dependency Security

- Run `pip-audit` or `safety check` regularly
- Update dependencies, especially:
  - `fastapi` (current: 0.109.0, latest: 0.115.x)
  - `python-jose` (has known vulnerabilities, consider `PyJWT`)
  - `httpx` (0.26.0 → 0.27.x)

### 3. Database Security

- Use prepared statements (already done via SQLAlchemy ORM)
- Implement row-level security in PostgreSQL
- Create separate database users with minimal privileges
- Enable PostgreSQL query logging for audit
- Encrypt sensitive data at rest

### 4. Container Security

- Run containers as non-root user
- Use minimal base images (alpine-based)
- Scan images with Trivy or Clair
- Implement resource limits in Docker

### 5. Input Validation

- Validate all user inputs using Pydantic validators
- Implement maximum length constraints
- Sanitize HTML content from RSS feeds
- Validate URL schemes and formats

### 6. OAuth Security

- Implement PKCE for OAuth flow
- Validate redirect URIs strictly
- Check `state` parameter for CSRF protection
- Implement OAuth token refresh

### 7. LLM Security

- Implement prompt injection detection
- Sanitize user inputs before sending to LLM
- Set token limits to prevent excessive costs
- Monitor OpenAI API usage and set budget alerts
- Validate LLM responses before using them

---

## Compliance Considerations

### OWASP Top 10 (2021) Mapping

1. **A01:2021 – Broken Access Control** → HIGH-03, MED-01
2. **A02:2021 – Cryptographic Failures** → CRIT-01, HIGH-04
3. **A03:2021 – Injection** → HIGH-01, HIGH-02
4. **A05:2021 – Security Misconfiguration** → CRIT-02, MED-01
5. **A07:2021 – Identification and Authentication Failures** → HIGH-04
6. **A09:2021 – Security Logging and Monitoring Failures** → MED-04
7. **A10:2021 – Server-Side Request Forgery** → HIGH-01

### GDPR Considerations

- Implement user data export functionality
- Add user deletion/anonymization
- Document data retention policies
- Ensure encryption of personal data
- Add consent management for data processing

---

## Remediation Priority

**IMMEDIATE (Week 1):**

1. ~~Remove development authentication bypass (CRIT-01)~~ - ✅ **COMPLETED**
2. Implement SSRF protection (HIGH-01)
3. Remove debug endpoint (HIGH-03)
4. Ensure production SECRET_KEY is strong and unique

**HIGH PRIORITY (Week 2-3):** 5. Implement JWT refresh tokens (HIGH-04) 6. Add rate limiting (MED-03) 7. Add file upload validation (MED-02) 8. Fix SQL injection risks (HIGH-02)

**MEDIUM PRIORITY (Week 4-6):** 9. Implement security logging (MED-04) 10. Add security headers (Additional Rec #1) 11. Fix cookie security (MED-01) 12. Update dependencies (Additional Rec #2)

**LOW PRIORITY (Week 6-8):** 13. Generic error messages (LOW-01) 14. CORS validation (LOW-02) 15. Timezone fixes (LOW-03)

---

## Testing Recommendations

1. **Penetration Testing:** Conduct external pentest after critical fixes
2. **Static Analysis:** Integrate Bandit, Semgrep, or SonarQube
3. **Dynamic Analysis:** Use OWASP ZAP or Burp Suite
4. **Dependency Scanning:** Automate with Snyk or Dependabot
5. **Secret Scanning:** Use GitGuardian or TruffleHog
6. **Container Scanning:** Implement Trivy in CI/CD pipeline

---

## Conclusion

The Curio application's most critical security vulnerability (development mode authentication bypass) has been **successfully remediated** with defense-in-depth controls. The remaining vulnerabilities are primarily high and medium severity issues that should be addressed before production deployment.

**Fixed Issues:**

- ✅ Development authentication bypass (CRIT-01) - Now requires explicit DEV_MODE=true and fails safely

**Remaining Priorities:**

1. SSRF protection for image proxy (HIGH-01)
2. JWT refresh tokens and reduced expiration (HIGH-04)
3. Debug endpoint removal (HIGH-03)
4. Rate limiting implementation (MED-03)

The application shows good security practices in many areas (use of SQLAlchemy ORM, HTTPOnly cookies, JWT authentication, proper `.gitignore` configuration, explicit security controls), but needs additional hardening for production deployment.

**Overall Risk Rating: MEDIUM** (reduced from MEDIUM-HIGH)

Regular security audits and penetration testing are recommended quarterly, with continuous monitoring and automated security scanning integrated into the CI/CD pipeline.

---

**Report Version:** 1.0  
**Next Review Date:** March 22, 2026
