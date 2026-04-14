# YouTube Watch History Export Guide

> This app requires your YouTube watch history data. Please follow the steps below to export your viewing history.

---

## Table of Contents

1. [Apply for YouTube Data API Key](#apply-for-youtube-data-api-key-optional) (Optional)
2. [Export YouTube Data](#export-youtube-data)

---

---

# Apply for YouTube Data API Key (Optional)

> ⚠️ **Note**: This step is **optional**. If you only want to use the exported data (watch history HTML), you can skip this step.
> 
> If you want to get detailed video tags, categories, channel information, etc., you need to apply for an API key.

---

### Why API?

| Data Source | Content Available | API Required |
|------------|-------------------|--------------|
| Watch History HTML | Video URL, Watch time | ❌ No |
| YouTube API | Title, Description, Tags, Category, Channel | ✅ Yes |

---

### Step 1: Create Google Cloud Project

1. Visit [Google Cloud Console](https://console.cloud.google.com/)

2. Click **"Select a project"** at the top → **"New project"**

3. Enter project name:
   ```
   YouTube Data Analyzer
   ```

4. Click **"Create"**

---

### Step 2: Enable YouTube Data API v3

1. In the left menu, click **"APIs & Services"** → **"Library"**

2. Search for **"YouTube Data API v3"**

3. Click on **YouTube Data API v3** in the results

4. Click **"Enable"**

---

### Step 3: Create API Key

1. In the left menu, click **"APIs & Services"** → **"Credentials"**

2. Click **"+ Create Credentials"** → **"API key"**

3. System will automatically create an API key, format like:
   ```
   AIzaSyCxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

4. **Copy and save the key securely!**

---

### Step 4: Configure in Your Project

1. Open `config.json` in your project

2. Paste your API key:
   ```json
   {
       "api": {
           "key": "Paste your API key here",
           "proxy": {
               "http": "http://proxy-dku.oit.duke.edu:3128",
               "https": "http://proxy-dku.oit.duke.edu:3128"
           }
       },
       "paths": {
           "takeout_dir": "Your Takeout folder path"
       }
   }
   ```

---

### API Quota Limits

| Item | Limit |
|------|-------|
| Free Daily Quota | 10,000 units |
| videos.list() | 1 unit/request |
| Videos per day | ~10,000 |

```
💡 Tip: Fetching 1000 videos = 1000 units consumed
```

---

---

# Export YouTube Data

## Before You Start

- A Google account
- A stable internet connection
- Estimated time: 30 minutes - 2 hours

---

## Step 1: Access Google Takeout

### 1.1 Open Takeout Page

Visit in your browser:

```
https://takeout.google.com
```

### 1.2 Sign in to Google

If you're not signed in, you'll be prompted to sign in with your Google account.

```
⚠️ Note: Make sure to sign in with your main YouTube account
```

---

## Step 2: Select Data to Export

### 2.1 Click "Select services to include"

You'll see a list of all Google services available for export.

### 2.2 Find and Check YouTube

Locate **YouTube and YouTube Music** and check the box.

```
☑️ YouTube and YouTube Music
```

### 2.3 Click "All Google services checkbox" to expand

Additional options will appear.

---

## Step 3: Configure YouTube Export Options

### 3.1 Select Data Types to Export

Click "Multiple formats" or "Next" and choose:

| Data Type | Description | Recommended |
|-----------|-------------|-------------|
| Watch History | Your viewing records | ✅ Required |
| Search History | Your search records | ❌ Optional |
| Comments | Your comments | ❌ Optional |

### 3.2 Choose Export Format

| Format | Pros | Recommended |
|--------|------|-------------|
| **HTML** | Easy to parse, contains complete info | ✅ Recommended |
| JSON | Easy for programs to process | ⭐ Alternative |

```
Recommendation: HTML format
Reason: HTML contains richer information for classification
```

---

## Step 4: Set Delivery Method

### 4.1 Choose Delivery Method

| Method | Description | Recommended |
|--------|-------------|-------------|
| **Send download link via email** | Download link sent to your email | ✅ Recommended |
| Direct download | Download files directly | ❌ Not recommended (large files) |
| Add to Drive | Save to Google Drive | ⭐ Alternative |

### 4.2 Set File Size Limit

If choosing "Send download link via email", you can set the split size:

```
Recommendation: 2 GB or larger
Reason: Avoid having too many file splits
```

---

## Step 5: Create Export

### 5.1 Click "Create Export"

```
⚠️ Note: This process may take 30 minutes to several hours
```

### 5.2 Wait for Processing

The page will show the progress.

---

## Step 6: Download Data

### 6.1 Check Email Notification

Once complete, you'll receive an email from Google.

### 6.2 Click Download Link

Open the email and click the download link.

```
⚠️ Link expires in 7 days
⚠️ Please download promptly
```

### 6.3 Save the File

Save the downloaded file to a convenient location.

---

## Step 7: Prepare for Upload

### 7.1 Extract the File (if needed)

Downloaded files may be in `.zip` format and need extraction.

### 7.2 Locate the Watch History File

After extraction, the folder structure:

```
Google_Takeout/
└── YouTube and YouTube Music/
    └── History/
        ├── watch-history.html  ← Main file!
        └── search-history.html
```

---

## FAQ

### Q1: How long does the export take?

A: Usually 30 minutes to 2 hours, depending on your data volume.

### Q2: What if the download link expired?

A: Simply go to https://takeout.google.com again and click "Create new export".

### Q3: Is my data safe?

A: Your data stays on your own device. We don't upload or store your raw data.

### Q4: Can I export only watch history?

A: Yes, only check "Watch History" when selecting data types.

### Q5: What if the file is too large?

A: You can set a smaller split size (like 500MB) to divide the file into smaller chunks.

---

## Next Steps

Once export is complete, prepare the `watch-history.html` file and let's start analyzing your viewing habits!

---

## Need Help?

If you encounter any issues during export, please contact our support team.

---

*Document Version: v1.1*
*Last Updated: 2026-04-14*
