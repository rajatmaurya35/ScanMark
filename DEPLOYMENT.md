# Deployment Guide for Attendance System

## 1. Prerequisites
- Python 3.8+
- Git
- Heroku CLI (for Heroku deployment)
- PostgreSQL (for production database)

## 2. Environment Variables
Create a `.env` file with the following variables:
```env
FLASK_ENV=production
SECRET_KEY=your-secure-secret-key
DATABASE_URL=postgresql://user:password@host:port/dbname
PUBLIC_URL=https://your-domain.com
CORS_ORIGINS=https://your-domain.com
```

## 3. Deployment Options

### Option A: Heroku Deployment
1. Login to Heroku:
```bash
heroku login
```

2. Create a new Heroku app:
```bash
heroku create your-app-name
```

3. Add PostgreSQL addon:
```bash
heroku addons:create heroku-postgresql:hobby-dev
```

4. Set environment variables:
```bash
heroku config:set FLASK_ENV=production
heroku config:set SECRET_KEY=your-secure-secret-key
heroku config:set PUBLIC_URL=https://your-app-name.herokuapp.com
```

5. Deploy to Heroku:
```bash
git push heroku main
```

### Option B: Custom Server Deployment
1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up PostgreSQL database

3. Start Gunicorn:
```bash
gunicorn wsgi:application
```

### Option C: Railway/Render Deployment
1. Connect your GitHub repository
2. Add environment variables
3. Deploy automatically from main branch

## 4. Custom Domain Setup
1. Purchase a domain (e.g., from GoDaddy, Namecheap)
2. Add DNS records:
   ```
   CNAME record: www -> your-app-url
   A record: @ -> your-server-ip
   ```
3. Update PUBLIC_URL in environment variables

## 5. SSL Certificate
1. Use Let's Encrypt for free SSL
2. For Heroku: SSL is automatically provided
3. For custom server: Use Certbot

## 6. Testing Deployment
1. Visit your domain: https://your-domain.com
2. Test QR code generation
3. Verify attendance marking
4. Check student dashboard

## 7. Security Checklist
- [ ] HTTPS enabled
- [ ] Environment variables set
- [ ] Database credentials secure
- [ ] Rate limiting configured
- [ ] CORS settings correct
- [ ] Session security enabled

## 8. Troubleshooting
- Check application logs: `heroku logs --tail`
- Verify database connection
- Check environment variables
- Test network connectivity
- Verify domain DNS propagation

## Support
For issues or questions, please create a GitHub issue or contact support.
