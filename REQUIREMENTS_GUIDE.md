# Requirements Files Guide

## 📁 Files Overview

| File | Packages | Size | Build Time | Use Case |
|------|----------|------|------------|----------|
| `requirements.txt` | 141 | ~2.5 GB | 10-12 min | ❌ Development only |
| `requirements.prod.txt` | 107 | ~1.8 GB | 6-8 min | ✅ **Render production** |
| `requirements.minimal.txt` | 28 | ~1.5 GB | 5-7 min | ❌ Missing Playwright |
| `requirements.production.txt` | 110 | ~2.0 GB | 6-8 min | ❌ Still has test deps |

---

## ✅ RECOMMENDED: Use `requirements.prod.txt` for Render

### Why?
- ✅ Includes **all production features** (URL scraping with Playwright)
- ✅ Removes testing dependencies (pytest, selenium, faker)
- ✅ 30% smaller than original
- ✅ Faster builds
- ✅ Lower memory usage

### What Was Removed?
```
❌ pytest, pytest-asyncio, pytest-cov, pytest-mock, pytest-benchmark
❌ selenium, selenium-stealth, webdriver-manager
❌ Faker (fake data generation)
❌ coverage (test coverage)
❌ py-cpuinfo (benchmarking)
❌ trio, PySocks, pyee (unused async libraries)
```

### What Was Kept?
```
✅ playwright (needed for URL scraping in app/utils/url_scraper.py)
✅ torch + transformers (needed for sentence-transformers embeddings)
✅ langchain (needed for text chunking)
✅ APScheduler (needed for background jobs)
✅ All FastAPI, Supabase, Groq, Auth dependencies
```

---

## 🚀 How to Use in Render

### Option 1: Update render.yaml (Recommended)

Edit `render.yaml`:
```yaml
buildCommand: pip install -r requirements.prod.txt
```

Commit and push:
```bash
git add requirements.prod.txt render.yaml
git commit -m "Switch to production requirements"
git push origin main
```

### Option 2: Update Render Dashboard Manually

1. Go to your Render service
2. Click "Settings" → "Build & Deploy"
3. Update **Build Command** to:
   ```
   pip install -r requirements.prod.txt
   ```
4. Click "Save Changes"
5. Click "Manual Deploy" → "Deploy latest commit"

---

## 🔧 Development vs Production

### Local Development
```bash
# Use full requirements with testing tools
pip install -r requirements.txt
```

### Render Production
```bash
# Use optimized production requirements
pip install -r requirements.prod.txt
```

### Run Tests Locally
```bash
# Install dev requirements
pip install -r requirements.txt

# Run tests
pytest
```

---

## 📊 Expected Results with requirements.prod.txt

### Build Time
- Before: 10-12 minutes
- After: 6-8 minutes
- **Improvement: 33% faster**

### Memory Usage
- Before: ~1.2 GB RAM
- After: ~900 MB RAM
- **Improvement: 25% less memory**

### Deployment Cost
- Can potentially stay on **Starter plan** ($7/mo) instead of Standard ($25/mo)

---

## ⚠️ Important Notes

### Playwright Installation
After pip install, Playwright needs browser binaries:
```bash
playwright install chromium
```

**In Render**, add this to your build command:
```yaml
buildCommand: pip install -r requirements.prod.txt && playwright install --with-deps chromium
```

### Python Version
Make sure `runtime.txt` specifies Python 3.11:
```
python-3.11.9
```

---

## 🆘 Troubleshooting

### If URL scraping fails
- Check Playwright installed: `playwright install chromium`
- Check browser dependencies: `playwright install-deps`

### If builds are slow
- Render caches dependencies between builds
- First build: 6-8 min
- Subsequent builds: 2-3 min (with cache)

### If memory errors occur
- Upgrade to Standard plan (2GB RAM)
- Playwright + Torch can be memory-intensive

---

## 📝 File Cleanup Recommendations

After switching to `requirements.prod.txt`:

```bash
# Keep for local development
requirements.txt

# Use for production
requirements.prod.txt

# Can delete (incorrect filtering)
rm requirements.minimal.txt
rm requirements.production.txt
```

---

**Last Updated:** 2025-10-23
**Status:** Ready for production deployment
