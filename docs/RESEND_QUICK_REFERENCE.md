# Quick Reference: Resend Environment Variables

## Required Environment Variables

### For Render Deployment

Add these in your Render Dashboard → Environment tab:

```bash
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxx
RESEND_FROM_EMAIL=onboarding@resend.dev
```

### For Local Development

Add these to your `.env` file:

```bash
# Resend Email Configuration
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxx
RESEND_FROM_EMAIL=onboarding@resend.dev
```

## How to Get the Values

### RESEND_API_KEY
1. Go to https://resend.com/api-keys
2. Click "Create API Key"
3. Name it (e.g., "Aurora Production")
4. Select "Sending access"
5. Copy the key (starts with `re_`)
6. Paste it as the value for `RESEND_API_KEY`

### RESEND_FROM_EMAIL

**Option 1: Use default (for testing)**
```bash
RESEND_FROM_EMAIL=onboarding@resend.dev
```
⚠️ Only sends to verified email addresses in your Resend account

**Option 2: Use your domain (for production)**
```bash
RESEND_FROM_EMAIL=noreply@yourdomain.com
```
✅ Requires domain verification in Resend dashboard

## Quick Test

After setting up, test with curl:

```bash
curl -X POST "https://your-app.onrender.com/api/admin/auth/send-otp" \
  -H "Content-Type: application/json" \
  -d '{"email": "your-test-email@example.com"}'
```

Expected response:
```json
{
  "message": "OTP sent to your email",
  "temp_token": "...",
  "expires_in": 900
}
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "API key is invalid" | Double-check `RESEND_API_KEY` - no spaces, starts with `re_` |
| "Email not delivered" | Verify recipient email in Resend dashboard if using `onboarding@resend.dev` |
| "Rate limit exceeded" | Free tier: 100/day limit. Wait or upgrade plan |
| No email received | Check Resend dashboard → Emails for delivery status |

## Important Notes

✅ **Remove old SMTP variables from Render**:
- `SMTP_SERVER`
- `SMTP_PORT`
- `SMTP_EMAIL`
- `SMTP_PASSWORD`

✅ **Don't commit API keys to git** - they're in `.env` which is in `.gitignore`

✅ **For production** - Add your own domain in Resend dashboard

---

Need help? Check `docs/RESEND_SETUP.md` for detailed instructions.
