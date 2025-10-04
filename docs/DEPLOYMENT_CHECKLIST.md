# 🚀 Deployment Checklist - Resend Email Integration

## Pre-Deployment

- [x] ✅ Code changes completed
- [x] ✅ Dependencies updated (`resend` added to `requirements.txt`)
- [x] ✅ Configuration files updated (`render.yaml`, `.env.example`)
- [x] ✅ Documentation created
- [x] ✅ No syntax errors in code

## Resend Setup

- [ ] Create Resend account at https://resend.com
- [ ] Verify your email address
- [ ] Create API key in Resend dashboard
- [ ] Copy API key (starts with `re_`)
- [ ] (Optional) Add and verify custom domain

## Local Testing

- [ ] Create/update `.env` file with:
  ```bash
  RESEND_API_KEY=re_xxxxxxxxxxxxxxxxx
  RESEND_FROM_EMAIL=onboarding@resend.dev
  ```
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Run locally: `uvicorn main:app --reload`
- [ ] Test OTP endpoint:
  ```bash
  curl -X POST "http://localhost:8000/api/admin/auth/send-otp" \
    -H "Content-Type: application/json" \
    -d '{"email": "your-email@example.com"}'
  ```
- [ ] Check email received
- [ ] Verify OTP works correctly

## Render Dashboard Configuration

### Remove Old Variables
- [ ] Remove `SMTP_SERVER`
- [ ] Remove `SMTP_PORT`
- [ ] Remove `SMTP_EMAIL`
- [ ] Remove `SMTP_PASSWORD`

### Add New Variables
- [ ] Add `RESEND_API_KEY` (set to your actual API key)
- [ ] Add `RESEND_FROM_EMAIL` (set to `onboarding@resend.dev` or your domain email)

### Verify Other Variables Still Set
- [ ] `TWILIO_ACCOUNT_SID`
- [ ] `TWILIO_AUTH_TOKEN`
- [ ] `TWILIO_PHONE_NUMBER`
- [ ] `CEREBRAS_API_KEY`
- [ ] `GROQ_API_KEY`
- [ ] `SECRET_KEY`
- [ ] `FIREBASE_WEB_API_KEY`
- [ ] `FIREBASE_DATABASE_URL`
- [ ] All Firebase credential variables
- [ ] `REDIS_HOST`
- [ ] `REDIS_PORT`
- [ ] `REDIS_USERNAME`
- [ ] `REDIS_PASSWORD`
- [ ] `TELEGRAM_BOT_TOKEN`

## Git Deployment

- [ ] Stage changes: `git add .`
- [ ] Commit changes: `git commit -m "feat: migrate from SMTP to Resend for email functionality"`
- [ ] Push to repository: `git push origin feature/api`
- [ ] Monitor Render deployment in dashboard

## Post-Deployment Testing

- [ ] Wait for Render build to complete
- [ ] Check deployment logs for errors
- [ ] Test OTP endpoint on production URL:
  ```bash
  curl -X POST "https://your-app.onrender.com/api/admin/auth/send-otp" \
    -H "Content-Type: application/json" \
    -d '{"email": "your-email@example.com"}'
  ```
- [ ] Verify email received
- [ ] Check Resend dashboard for email delivery status
- [ ] Test full registration flow
- [ ] Test OTP verification endpoint

## Monitoring

- [ ] Check Render logs for any errors
- [ ] Monitor Resend dashboard for:
  - Email delivery status
  - Bounce rates
  - Usage statistics
- [ ] Set up alerts in Resend (optional)

## Documentation

- [ ] Update team on email system change
- [ ] Share `docs/RESEND_SETUP.md` with team
- [ ] Update any API documentation
- [ ] Document API key location securely

## Rollback Plan (If Needed)

If something goes wrong:

1. Revert git commit: `git revert HEAD`
2. Or switch to port 465 SSL for SMTP:
   ```python
   SMTP_PORT = 465
   with smtplib.SMTP_SSL(config.SMTP_SERVER, config.SMTP_PORT) as server:
       server.login(config.SMTP_EMAIL, config.SMTP_PASSWORD)
       server.sendmail(...)
   ```
3. Push changes and redeploy

## Success Criteria

✅ All checks passed when:
- Emails are delivered successfully
- No errors in Render logs
- Resend dashboard shows successful deliveries
- OTP verification flow works end-to-end
- No increase in error rates

## Troubleshooting Resources

- **Resend Docs**: https://resend.com/docs
- **Local Setup Guide**: `docs/RESEND_SETUP.md`
- **Quick Reference**: `docs/RESEND_QUICK_REFERENCE.md`
- **Migration Summary**: `docs/EMAIL_MIGRATION_SUMMARY.md`
- **Resend Support**: help@resend.com

## Notes

- **Free Tier Limits**: 100 emails/day, 3,000/month
- **Testing**: Use `onboarding@resend.dev` + verified emails
- **Production**: Add custom domain for better deliverability
- **Security**: Never commit API keys to git

---

## Quick Command Reference

```bash
# Local development
pip install -r requirements.txt
uvicorn main:app --reload

# Git deployment
git add .
git commit -m "feat: migrate to Resend"
git push origin feature/api

# Test OTP (local)
curl -X POST "http://localhost:8000/api/admin/auth/send-otp" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'

# Test OTP (production)
curl -X POST "https://your-app.onrender.com/api/admin/auth/send-otp" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'
```

---

**Last Updated**: October 4, 2025
**Status**: Ready for Deployment ✅
