# Step 8: Secret & Config Safety Check

Ask the LLM to scan for sensitive information **without printing** actual values.

## Safety Scanning Prompt

```
Scan the project structure for potentially sensitive files and data:

1. List files that might contain secrets (only file paths, no content):
   - .env files
   - API key files
   - Private keys (.pem, .key, .p12)
   - Configuration files with credentials
   - Database connection strings

2. Check if sensitive files are properly gitignored

3. Verify that example/template files exist for configuration:
   - .env.example
   - secrets.yaml.template
   - config.yaml.example

4. Recommendations for improving secret management

**Important**: Do NOT display actual secret values, only file paths and recommendations.
```

## Expected Output Format

```markdown
### Sensitive Files Found

**Properly Gitignored:**
- `.env` ✅
- `secrets.yaml` ✅
- `config/database.yml` ✅

**Missing .gitignore Entry:**
- `api_keys.json` ⚠️  (Recommendation: Add to .gitignore)

**Template Files Present:**
- `.env.example` ✅
- `secrets.yaml.template` ✅

**Recommendations:**
1. Add `api_keys.json` to `.gitignore`
2. Create `api_keys.json.example` with placeholder values
3. Consider using environment variables for all secrets
4. Document required secrets in README.md
```

## Security Checklist

### Secret Management
- [ ] All secrets in .gitignore
- [ ] Template files exist (.env.example)
- [ ] No hardcoded credentials in code
- [ ] Environment variables used properly
- [ ] Secrets documented (without values)

### Common Vulnerabilities
- [ ] SQL injection prevention
- [ ] XSS protection
- [ ] CSRF tokens implemented
- [ ] Input validation present
- [ ] Output encoding used
- [ ] Authentication/authorization correct

### Access Control
- [ ] Proper permission checks
- [ ] Role-based access control
- [ ] Secure session management
- [ ] Password hashing (never plain text)

## Security Tools

```bash
# Python
bandit -r src/
safety check
pip-audit

# JavaScript/Node.js
npm audit
npm audit fix
snyk test

# General
git secrets --scan
truffleHog --regex --entropy=False .
```

---

*Part of the LLM Codebase Interaction Guide - Step 8 of 8*
