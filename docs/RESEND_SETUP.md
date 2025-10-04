# Resend Email Setup Guide

## Why Resend Instead of SMTP?

Render's free tier **blocks outbound connections on ports 25 and 587**, which prevents traditional SMTP from working. Resend is a modern email API service that works reliably on Render and other cloud platforms.

## Benefits of Resend

- ✅ **Works on Render** - No port restrictions
- ✅ **Free Tier** - 3,000 emails/month (100 emails/day)
- ✅ **Fast Delivery** - API-based, no SMTP handshakes
- ✅ **Easy Setup** - Just an API key needed
- ✅ **Better Deliverability** - Built-in SPF/DKIM configuration
- ✅ **Email Tracking** - View delivery status in dashboard

## Setup Instructions

### 1. Create a Resend Account

1. Go to [resend.com](https://resend.com)
2. Sign up for a free account
3. Verify your email address

### 2. Get Your API Key

1. Navigate to **API Keys** in the Resend dashboard
2. Click **Create API Key**
3. Give it a name (e.g., "Aurora Production")
4. Select **Sending access**
5. Copy the API key (starts with `re_`)

### 3. Add Domain (Optional but Recommended)

For production, you should add your own domain:

1. Go to **Domains** in Resend dashboard
2. Click **Add Domain**
3. Enter your domain name
4. Add the DNS records provided by Resend to your domain's DNS settings
5. Wait for verification (usually a few minutes)

**For Testing:** You can use the default `onboarding@resend.dev` email address (only delivers to your verified email addresses).

### 4. Configure Environment Variables

#### Local Development (.env file)

```bash
# Resend Email Configuration
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxx
RESEND_FROM_EMAIL=onboarding@resend.dev  # or your-email@yourdomain.com
```

#### Render Dashboard

1. Go to your service in Render dashboard
2. Navigate to **Environment** tab
3. Add these environment variables:
   - `RESEND_API_KEY` = `re_xxxxxxxxxxxxxxxxx` (your actual API key)
   - `RESEND_FROM_EMAIL` = `onboarding@resend.dev` (or your verified domain email)

### 5. Verify Email Addresses (For Testing)

If using the free tier with `onboarding@resend.dev`:

1. In Resend dashboard, go to **Settings** → **Email Addresses**
2. Add the email addresses you want to test with
3. Verify them via the confirmation email

## Testing the Integration

### Test Locally

```bash
# Install dependencies
pip install resend

# Run your FastAPI server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Test OTP Endpoint

```bash
curl -X POST "http://localhost:8000/api/admin/auth/send-otp" \
  -H "Content-Type: application/json" \
  -d '{"email": "your-email@example.com"}'
```

### Check Resend Dashboard

1. Go to **Emails** in Resend dashboard
2. You'll see all sent emails with their delivery status
3. View email content, delivery time, and any errors

## Troubleshooting

### Error: "API key is invalid"

- Double-check your `RESEND_API_KEY` in environment variables
- Ensure it starts with `re_`
- Make sure there are no extra spaces

### Error: "Email not delivered"

- If using `onboarding@resend.dev`, ensure recipient email is verified in Resend dashboard
- Check Resend dashboard for delivery status and error messages
- For production, use your own verified domain

### Error: "Rate limit exceeded"

- Free tier: 100 emails/day, 3,000/month
- Wait for the rate limit to reset or upgrade your Resend plan

## Upgrade Options

If you need more emails:

- **Free**: 100 emails/day, 3,000/month
- **Pro ($20/mo)**: 50,000 emails/month
- **Business**: Custom pricing for higher volumes

## Migration Checklist

- [x] Install `resend` package
- [x] Remove SMTP dependencies
- [x] Update `Config` class with Resend settings
- [x] Replace `send_otp_email()` function
- [x] Update `render.yaml` environment variables
- [x] Update `.env.example` documentation
- [ ] Get Resend API key
- [ ] Update environment variables in Render dashboard
- [ ] Test OTP email functionality
- [ ] (Optional) Add custom domain to Resend

## Code Changes Summary

### Before (SMTP)

```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
    server.starttls()
    server.login(email, password)
    server.sendmail(from_email, to_email, message)
```

### After (Resend)

```python
import resend

resend.api_key = "re_xxxxxxxxx"

params: resend.Emails.SendParams = {
    "from": "onboarding@resend.dev",
    "to": ["user@example.com"],
    "subject": "Hello World",
    "html": "<strong>it works!</strong>",
}

email: resend.Email = resend.Emails.send(params)
```

## Additional Resources

- [Resend Documentation](https://resend.com/docs)
- [Resend Python SDK](https://github.com/resendlabs/resend-python)
- [Email Best Practices](https://resend.com/docs/send-with-resend/best-practices)

## Support

If you encounter issues:

1. Check Resend dashboard for email delivery logs
2. Review Render deployment logs
3. Verify environment variables are set correctly
4. Contact Resend support at [help@resend.com](mailto:help@resend.com)
