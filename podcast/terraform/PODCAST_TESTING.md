# Podcast Testing Guide

This guide helps you test your podcast RSS feed in various podcast clients and platforms.

## 🎯 RSS Feed URL
```
https://cedarmountainnews.todschmidt.com/rss.xml
```

## 🖥️ Local Testing (Fastest)

### **1. VLC Media Player (Recommended)**
1. Open VLC Media Player
2. Go to **View** → **Playlist**
3. Click **Internet** tab
4. Paste RSS URL: `https://cedarmountainnews.todschmidt.com/rss.xml`
5. Click **Go** - Should show your episode
6. Double-click episode to play

### **2. Web-Based Testing**
- **Podcast Player Online**: https://podcastplayer.net/
  - Paste your RSS URL
  - Should immediately show your episode
  
- **RSS.com Podcast Player**: https://www.rss.com/podcast-player/
  - Enter RSS URL
  - Test playback

### **3. Windows Store Apps**
- **Grover Podcast** (Free)
- **Podcast Addict** (if available)
- **Castbox** (if available)

## 📱 Mobile Testing

### **iOS (iPhone/iPad)**
1. Open **Apple Podcasts** app
2. Go to **Library** → **Shows** → **+** (Add Show)
3. Paste RSS URL: `https://cedarmountainnews.todschmidt.com/rss.xml`
4. Tap **Subscribe**

### **Android**
1. **Google Podcasts** app
2. **Spotify** app (search for your podcast)
3. **Podcast Addict** app

## 🌐 Platform Submission

### **Apple Podcasts Connect**
1. Go to: https://podcastsconnect.apple.com/
2. Sign in with Apple ID
3. Click **+** to add new show
4. Enter RSS URL: `https://cedarmountainnews.todschmidt.com/rss.xml`
5. Fill in show details:
   - **Show Name**: Canteen Calendar Podcast
   - **Author**: Cedar Mountain Canteer Team
   - **Description**: Weekly podcast covering Cedar Mountain Community news
   - **Category**: Society & Culture
6. Submit for review (24-48 hours)

### **Spotify for Podcasters**
1. Go to: https://podcasters.spotify.com/
2. Sign up/Sign in
3. Click **Get started** → **Add your podcast**
4. Enter RSS URL: `https://cedarmountainnews.todschmidt.com/rss.xml`
5. Verify ownership
6. Submit (usually approved within hours)

### **Google Podcasts Manager**
1. Go to: https://podcastsmanager.google.com/
2. Sign in with Google account
3. Click **Add show**
4. Enter RSS URL
5. Verify ownership
6. Submit for review

## 🧪 Testing Checklist

### **Before Submission:**
- [ ] RSS feed loads in browser
- [ ] Episode plays in VLC
- [ ] Episode metadata is correct
- [ ] Audio quality is good
- [ ] Episode title/description make sense

### **After Submission:**
- [ ] Check platform-specific requirements
- [ ] Monitor for approval notifications
- [ ] Test playback on platform
- [ ] Verify metadata display

## 🔧 Troubleshooting

### **RSS Feed Issues:**
```bash
# Test RSS feed validity
curl -s https://cedarmountainnews.todschmidt.com/rss.xml | head -10

# Check for XML errors
xmllint --noout https://cedarmountainnews.todschmidt.com/rss.xml
```

### **Common Issues:**
1. **Episode not playing**: Check audio file URL accessibility
2. **Metadata missing**: Verify ID3 tags in MP3 file
3. **Platform rejection**: Check RSS feed compliance

### **RSS Feed Validation:**
- **W3C Feed Validator**: https://validator.w3.org/feed/
- **Podbase Validator**: https://podba.se/validate/

## 📊 Current Episode Info

**Episode**: Episode 20250910 2328 Cedar Mountain Community News Update September 11th 2025
**Duration**: ~32MB MP3 file
**URL**: https://cedarmountainnews.todschmidt.com/episode_20250910_2328_cedar_mountain_community_news_update_september_11th_2025.mp3

## 🎯 Next Steps

1. **Test locally** with VLC or web player
2. **Submit to Spotify** (fastest approval)
3. **Submit to Apple Podcasts** (most important)
4. **Monitor** for approval and feedback
5. **Prepare** intro/outro for future episodes

## 💡 Tips

- **Test first, submit second** - Always verify locally before platform submission
- **Start with Spotify** - Usually fastest approval for testing
- **Apple Podcasts is key** - Most podcast apps use Apple's directory
- **Keep RSS URL handy** - You'll need it for all submissions
