# MARSLOG Image Assets

This directory contains image assets for the MARSLOG application.

## 📁 Current Files:

- ✅ **favicon.ico** - Browser favicon (3.1KB)
- ✅ **MARSLOGS.png** - Main MARSLOG logo (253KB) 
- ✅ **machine-learning.png** - AI features icon (19.4KB)
- ✅ **image.jpg** - Login background image (528KB)
- ✅ **loading.svg** - Loading animation (957B)
- ✅ **line-icon.svg** - LINE social icon (1.1KB)
- ✅ **telegram-icon.svg** - Telegram social icon (641B)

## 🎯 Usage in Application:

### Login Page (`/auth/login.php`):
- Logo: `MARSLOGS.png`
- Background: `image.jpg` with gradient overlay
- Favicon: `favicon.ico`

### AI Test Page (`/ai-test.html`):
- AI Icon: `machine-learning.png`
- Loading: `loading.svg`

### Authentication:
- Loading animation: `loading.svg` (replacing FontAwesome spinner)

## 📤 Ready for Upload:

All required assets are now present and properly referenced in the code.

Upload to Linux with WinSCP:
```bash
# Target path: /opt/marslog/app/frontend/assets/image/
# Set permissions after upload:
chmod 644 *
```

## 🚀 Test URLs:

After upload, test these URLs:
- http://your-server/assets/image/favicon.ico
- http://your-server/assets/image/MARSLOGS.png
- http://your-server/assets/image/machine-learning.png
