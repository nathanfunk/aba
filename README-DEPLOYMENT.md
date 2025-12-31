# Deployment Guide Overview

This directory contains multiple deployment guides for different use cases. Choose the one that fits your needs.

## 📚 Available Guides

### 1. **[CPANEL-APPLICATION-MANAGER.md](CPANEL-APPLICATION-MANAGER.md)** ⭐ **RECOMMENDED**
**For: First-time cPanel users**

Easiest deployment method using GoDaddy's cPanel Application Manager GUI interface.

- ✅ No command-line Passenger configuration needed
- ✅ GUI-based setup and management
- ✅ Automatic virtual environment creation
- ✅ Built-in log viewer
- ✅ Perfect for beginners

**Start here if:** You're new to cPanel or prefer GUI-based deployment.

---

### 2. **[CICD-SETUP.md](CICD-SETUP.md)** 🚀
**For: Setting up automated deployments**

Quick start guide for GitHub Actions CI/CD pipeline.

- ✅ Automated testing on every commit
- ✅ Automatic deployment on push to `main`
- ✅ Frontend build automation
- ✅ Zero-downtime deployments

**Use this after:** Initial application setup via Application Manager.

---

### 3. **[DEPLOYMENT.md](DEPLOYMENT.md)** 🔧
**For: Advanced users and manual deployment**

Comprehensive manual deployment guide with full control.

- ✅ Manual SSH deployment
- ✅ Direct Passenger configuration
- ✅ Advanced troubleshooting
- ✅ Custom configurations

**Use this if:** You need full control or are troubleshooting issues.

---

### 4. **[PASSENGER-SETUP.md](PASSENGER-SETUP.md)** 📖
**For: Understanding how it works**

Technical deep-dive into ASGI/WSGI compatibility and Passenger architecture.

- ✅ Explains ASGI vs WSGI
- ✅ How FastAPI runs on Passenger
- ✅ WebSocket support details
- ✅ Performance tuning

**Read this if:** You want to understand the technical details.

---

## 🎯 Quick Decision Guide

**Choose based on your goal:**

```
┌─────────────────────────────────────┐
│ What do you want to do?             │
└─────────────────────────────────────┘
              │
              ├─► First deployment to cPanel?
              │   └─► Use: CPANEL-APPLICATION-MANAGER.md
              │
              ├─► Set up automatic deployments?
              │   └─► Use: CICD-SETUP.md
              │
              ├─► Troubleshoot deployment issues?
              │   └─► Use: DEPLOYMENT.md (Troubleshooting section)
              │
              ├─► Understand ASGI/WSGI compatibility?
              │   └─► Read: PASSENGER-SETUP.md
              │
              └─► Deploy to non-cPanel server?
                  └─► See: Main README.md (Local Development)
```

---

## 📋 Deployment Checklist

### Before You Start

- [ ] GoDaddy cPanel hosting account with SSH access
- [ ] OpenRouter API key (from https://openrouter.ai/keys)
- [ ] GitHub repository forked/cloned
- [ ] Node.js installed locally (for frontend build)

### Initial Deployment

- [ ] Follow **CPANEL-APPLICATION-MANAGER.md** to set up application
- [ ] Upload or clone code to server
- [ ] Install Python dependencies
- [ ] Build React frontend
- [ ] Configure environment variables (API key)
- [ ] Test application at your domain

### CI/CD Setup (Optional but Recommended)

- [ ] Follow **CICD-SETUP.md** to configure GitHub Actions
- [ ] Generate SSH deployment key
- [ ] Add GitHub secrets (SSH key, host, user, path)
- [ ] Test automatic deployment

### Verification

- [ ] Application loads at https://singularsys.com/aba
- [ ] React frontend displays correctly
- [ ] Can select and chat with agents
- [ ] WebSocket streaming works
- [ ] API documentation accessible at /docs

---

## 🆘 Common Issues

### Application won't start
→ Check logs in Application Manager or `~/aba-app/logs/error_log`
→ See CPANEL-APPLICATION-MANAGER.md "Troubleshooting" section

### Frontend shows blank page
→ Build the frontend: `cd web-ui && npm run build`
→ See CPANEL-APPLICATION-MANAGER.md "Frontend Not Loading"

### WebSocket not connecting
→ Check CloudFlare WebSocket support (if using CF)
→ See DEPLOYMENT.md "WebSocket Connection Issues"

### CI/CD deployment fails
→ Verify GitHub secrets are set correctly
→ See CICD-SETUP.md "Troubleshooting" section

---

## 📁 File Structure

```
aba/
├── README.md                           # Main project README
├── README-DEPLOYMENT.md               # This file
├── CPANEL-APPLICATION-MANAGER.md      # ⭐ GUI deployment guide
├── CICD-SETUP.md                      # 🚀 CI/CD setup guide
├── DEPLOYMENT.md                      # 🔧 Advanced deployment guide
├── PASSENGER-SETUP.md                 # 📖 Technical documentation
├── .github/workflows/deploy.yml       # GitHub Actions workflow
├── passenger_wsgi.py                  # WSGI entry point
├── .htaccess                          # Passenger config (WSGI mode)
├── .htaccess.asgi                     # Passenger config (ASGI mode)
├── deploy.sh                          # Deployment script
└── .env.example                       # Environment template
```

---

## 🔗 Quick Links

- **OpenRouter API Keys:** https://openrouter.ai/keys
- **GoDaddy cPanel Login:** https://singularsys.com:2083
- **GitHub Actions:** https://github.com/YOUR_USERNAME/aba/actions
- **Application Docs:** https://singularsys.com/aba/docs (after deployment)

---

## 💡 Recommended Deployment Path

**For most users, we recommend this approach:**

1. **Start with Application Manager** (CPANEL-APPLICATION-MANAGER.md)
   - Set up application via cPanel GUI
   - Get everything working manually first
   - Understand the basics

2. **Add CI/CD** (CICD-SETUP.md)
   - Configure GitHub Actions for automatic deployments
   - Push to `main` and watch it deploy automatically
   - Enjoy zero-effort updates

3. **Learn the Details** (PASSENGER-SETUP.md)
   - Read about ASGI/WSGI if interested
   - Understand performance tuning
   - Optimize as needed

---

## 📞 Getting Help

If you encounter issues:

1. Check the **Troubleshooting** section in the relevant guide
2. Review application logs via Application Manager or SSH
3. Verify all prerequisites are met
4. See the main project README for local development

---

**Good luck with your deployment! 🚀**
