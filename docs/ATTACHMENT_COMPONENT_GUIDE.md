# Attachment Component System - Complete Guide

## Overview

The LandTen MVP 3.0 chat system includes a comprehensive attachment rendering system that displays photos, files, galleries, and AI-generated property issue analysis directly in the chat window.

**Status:** ✅ Production Ready
**Date Implemented:** 2025-12-15
**Branch:** claude/create-attachment-component-SkNzD

---

## 🎯 Features

### Core Capabilities

1. **Image Attachments**
   - Single image display with lightbox
   - Click to zoom/expand
   - Download functionality
   - AI vision analysis badge
   - Lazy loading with blur placeholder

2. **Gallery Attachments**
   - Multiple image grid layout (2-4 columns)
   - Lightbox with keyboard navigation (←/→/Esc)
   - Image counter
   - AI analysis for each image
   - Responsive design

3. **File Attachments**
   - Document display (PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX, TXT)
   - File type icons (automatic detection)
   - File size display
   - Download functionality
   - MIME type badge

4. **PropertyAI Interactive Cards**
   - Incident cards
   - Discovery cards
   - Job cards
   - Bid cards
   - Approval cards
   - Completion cards

5. **AI Vision Integration**
   - Automatic property issue detection
   - Severity assessment (minor, moderate, severe)
   - Repair recommendations
   - Visual badge on images
   - Full analysis in lightbox

6. **Stream Default Handlers**
   - Video playback (delegates to ReactPlayer)
   - Audio playback
   - Scraped content cards (og_scrape_url)

---

## 📁 File Structure

```
frontend/src/components/ai/
├── CustomAttachment.tsx       # Main attachment router
├── ImageAttachment.tsx        # Single image display
├── GalleryAttachment.tsx      # Multiple image gallery
├── FileAttachment.tsx         # File download cards
├── MessageCards.tsx           # PropertyAI cards (existing)
└── CustomMessageUI.tsx        # (existing)

frontend/src/components/
└── StreamChatPane.tsx         # Chat UI integration

backend/app/routes/
├── incidents.py               # Photo upload endpoint with AI vision
├── chat.py                    # Chat message handling
└── chat_stream.py             # Webhook endpoint

backend/app/services/
└── gpt_vision.py              # GPT-4o Vision analysis service
```

---

## 🔧 Component Architecture

### 1. CustomAttachment (Main Router)

**File:** `frontend/src/components/ai/CustomAttachment.tsx`

**Purpose:** Routes attachments to appropriate renderers based on type

**Attachment Type Detection:**
```typescript
// PropertyAI cards
["incident", "discovery", "job", "bids", "approval", "completion"]

// Images
type === 'image' || mime_type.startsWith('image/') || url.endsWith('.jpg|.png|...')

// Files
type === 'file' || mime_type (non-image/video/audio)

// Stream default (video, audio, scraped content)
Everything else
```

**Props:**
```typescript
interface CustomAttachmentProps extends AttachmentProps {
  attachments: any[];
  onActionClick?: (actionValue: string) => void;
}
```

**Usage:**
```tsx
<Channel channel={activeChannel} Attachment={CustomAttachment}>
  <MessageList />
  <MessageInput />
</Channel>
```

---

### 2. ImageAttachment (Single Image)

**File:** `frontend/src/components/ai/ImageAttachment.tsx`

**Features:**
- Lazy loading with blur placeholder
- Click to expand in lightbox
- Download button (top-right corner)
- AI analysis badge (below image)
- Zoom icon on hover

**Props:**
```typescript
interface ImageAttachmentProps {
  url?: string;
  image_url?: string;
  thumb_url?: string;
  fallback?: string;
  title?: string;
  alt?: string;
  aiAnalysis?: string;        // AI-generated property issue summary
  aiAnalysisError?: string;   // Error if analysis failed
}
```

**Example:**
```tsx
<ImageAttachment
  url="https://s3.amazonaws.com/landten/photo123.jpg"
  title="Water damage on ceiling"
  aiAnalysis="Moderate water damage visible on ceiling with brown staining..."
/>
```

**AI Analysis Display:**
```tsx
{aiAnalysis && (
  <div className="mt-2 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30">
    <span className="text-emerald-400 text-xs font-semibold">🤖 AI Analysis:</span>
    <p className="text-slate-300 text-sm mt-1">{aiAnalysis}</p>
  </div>
)}
```

---

### 3. GalleryAttachment (Multiple Images)

**File:** `frontend/src/components/ai/GalleryAttachment.tsx`

**Features:**
- Grid layout (2/3/4 columns based on count)
- Lightbox with navigation arrows
- Keyboard shortcuts (←/→/Esc)
- Image counter (e.g., "3 / 5")
- AI analysis per image in lightbox

**Props:**
```typescript
interface GalleryImage {
  url?: string;
  image_url?: string;
  thumb_url?: string;
  title?: string;
  alt?: string;
  aiAnalysis?: string;
}

interface GalleryAttachmentProps {
  images: GalleryImage[];
}
```

**Grid Layout Logic:**
```typescript
const gridCols =
  images.length === 2 ? 'grid-cols-2' :
  images.length === 3 ? 'grid-cols-3' :
  'grid-cols-2 md:grid-cols-4';  // 4+ images
```

**Example:**
```tsx
<GalleryAttachment
  images={[
    { url: "photo1.jpg", aiAnalysis: "Water damage..." },
    { url: "photo2.jpg", aiAnalysis: "Crack in wall..." },
    { url: "photo3.jpg", aiAnalysis: "Mold growth..." },
  ]}
/>
```

---

### 4. FileAttachment (Documents)

**File:** `frontend/src/components/ai/FileAttachment.tsx`

**Features:**
- File type icons (automatic detection from MIME type)
- File size display (KB/MB)
- Download button
- Hover effects
- Click to open in new tab

**Props:**
```typescript
interface FileAttachmentProps {
  url?: string;
  asset_url?: string;
  title?: string;
  title_link?: string;
  text?: string;
  file_size?: number;
  mime_type?: string;
}
```

**Supported File Types:**
| Type | Extensions | Icon Color |
|------|-----------|-----------|
| PDF | .pdf | Red |
| Word | .doc, .docx | Blue |
| Excel | .xls, .xlsx, .csv | Green |
| PowerPoint | .ppt, .pptx | Orange |
| Code | .js, .ts, .py, .java, etc. | Purple |
| Image | .jpg, .png, .gif | Cyan |
| Video | .mp4, .mov, .avi | Pink |
| Audio | .mp3, .wav, .ogg | Yellow |
| Default | Other | Gray |

**Example:**
```tsx
<FileAttachment
  url="https://s3.amazonaws.com/landten/contract.pdf"
  title="Lease Agreement.pdf"
  file_size={1048576}  // 1MB
  mime_type="application/pdf"
/>
```

---

## 🔄 Message Flow

### 1. User Uploads Photo

```
User clicks (+) → Selects photo → Photo appears in MessageInput
```

**MessageInput State:**
```typescript
{
  text: "",
  attachments: [
    {
      type: "image",
      mime_type: "image/jpeg",
      file: File,
      url: "blob:http://...",  // Temporary blob URL
    }
  ]
}
```

### 2. Message Submission

**StreamChatPane.tsx:**
```typescript
const handleSubmit = async (input: any) => {
  // ✅ FIXED: Extract attachments from input
  const attachments = input?.attachments || input?.message?.attachments || [];

  // Send to Stream with attachments
  const messagePayload = {
    text,
    attachments,  // ✅ No longer hardcoded as []
    metadata: { agentEnabled, persona: 'tenant' },
  };

  await sendMessage(text, messagePayload);
};
```

### 3. Message Display

**Stream processes message → CustomAttachment renders:**

```typescript
// CustomAttachment.tsx
const imageAttachments = attachments.filter(att =>
  att.type === 'image' ||
  att.mime_type?.startsWith('image/')
);

if (imageAttachments.length === 1) {
  return <ImageAttachment {...imageAttachments[0]} />;
} else if (imageAttachments.length > 1) {
  return <GalleryAttachment images={imageAttachments} />;
}
```

---

## 🤖 AI Vision Integration

### Backend Processing

**Endpoint:** `POST /api/v1/incidents/{incident_id}/photos`

**Flow:**
1. User uploads photo via chat
2. Photo uploaded to S3
3. **GPT-4o Vision analyzes image** (new!)
4. Analysis stored in DynamoDB
5. Presigned URL returned with AI analysis

**Response:**
```json
{
  "success": true,
  "photo_id": "photo_abc123",
  "url": "https://s3.amazonaws.com/landten/uploads/photo123.jpg",
  "ai_analysis": "Water damage visible on ceiling with brown staining and peeling paint. Severity: Moderate. Likely caused by roof leak or plumbing issue above. Recommend immediate inspection by plumber and ceiling repair.",
  "ai_analysis_error": null
}
```

### Frontend Display

**ImageAttachment automatically displays AI analysis:**

```tsx
{aiAnalysis && (
  <div className="mt-2 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30">
    <span className="text-emerald-400 text-xs font-semibold">🤖 AI Analysis:</span>
    <p className="text-slate-300 text-sm mt-1 leading-relaxed">
      {aiAnalysis}
    </p>
  </div>
)}
```

**In Lightbox (expanded view):**
```tsx
<div className="absolute bottom-4 left-4 max-w-md p-4 rounded-lg bg-slate-900/90 border border-emerald-500/30">
  <span className="text-emerald-400 text-sm font-semibold">🤖 AI Analysis:</span>
  <p className="text-slate-200 text-sm mt-2">{aiAnalysis}</p>
</div>
```

---

## 🎨 Styling & Theming

### Color Scheme

```css
/* AI Analysis Badge */
bg-emerald-500/10        /* Background */
border-emerald-500/30    /* Border */
text-emerald-400         /* Text */

/* Image Borders */
border-slate-700         /* Default */
hover:border-blue-500    /* Hover */

/* Lightbox */
bg-black/95              /* Overlay */
bg-slate-800/80          /* Buttons */
```

### Responsive Breakpoints

```css
/* Gallery Grid */
grid-cols-2              /* Mobile (default) */
md:grid-cols-3           /* Tablet (768px+) */
md:grid-cols-4           /* Desktop (for 4+ images) */

/* Image Max Size */
max-w-md                 /* 448px */
max-h-[400px]            /* 400px height */
max-h-[90vh]             /* 90% viewport in lightbox */
```

---

## 🔍 Debugging

### Console Logs

**CustomAttachment:**
```javascript
console.log('[CustomAttachment] Processing attachments:', {
  total: attachments.length,
  types: attachments.map(a => a.type),
  details: attachments.map(a => ({
    type: a.type,
    mime_type: a.mime_type,
    hasUrl: !!a.url,
    aiAnalysis: a.ai_analysis ? 'present' : 'none',
  })),
});
```

**StreamChatPane:**
```javascript
console.log('[MessageInputWithWebhook] ✅ Extracted from input:', {
  text: messageText.substring(0, 100),
  attachmentCount: attachments.length,
  attachments: attachments.map(a => ({
    type: a.type,
    name: a.name,
    file_size: a.file_size,
    mime_type: a.mime_type,
  })),
});
```

### Backend Logs

**Photo Upload:**
```python
logger.info(f"📸 [incidents] Uploading photo to S3: {s3_key}")
logger.info(f"🤖 [incidents] Starting AI vision analysis...")
logger.info(f"✅ [incidents] AI analysis complete: {ai_analysis[:100]}...")
```

**Chat Send:**
```python
logger.info(f"📨 [CHAT/SEND] Received message from user_id={user_id}, role={role}")
logger.info(f"📎 [CHAT/SEND] ✅ Message has {len(attachments)} attachment(s)")
```

---

## 🐛 Troubleshooting

### Problem: Photos not appearing in chat

**Checklist:**
1. ✅ Check browser console for `[CustomAttachment] Processing attachments`
2. ✅ Verify `attachmentCount > 0` in logs
3. ✅ Check attachment has `url`, `image_url`, or `asset_url`
4. ✅ Verify S3 presigned URL is accessible (click to test)
5. ✅ Check CORS settings on S3 bucket

**Common Causes:**
- Attachments hardcoded as `[]` (FIXED in this PR)
- Missing `Attachment={CustomAttachment}` in Channel component
- S3 URL expired (presigned URLs expire after 1 hour)
- CORS blocked (check browser network tab)

### Problem: AI analysis not showing

**Checklist:**
1. ✅ Check `OPENAI_API_KEY` is set in backend environment
2. ✅ Verify `Pillow` is installed (`pip list | grep Pillow`)
3. ✅ Check backend logs for `🤖 Starting AI vision analysis`
4. ✅ Look for error in `ai_analysis_error` field
5. ✅ Verify attachment object has `ai_analysis` property

**Common Causes:**
- OpenAI API key missing or invalid
- Pillow not installed (required for image processing)
- Image too large (>20MB limit)
- Rate limit exceeded (50 requests/minute)

### Problem: Download not working

**Checklist:**
1. ✅ Check S3 presigned URL is still valid
2. ✅ Verify CORS allows downloads
3. ✅ Check browser network tab for failed requests
4. ✅ Try opening URL in new tab as fallback

**Fix:**
```typescript
const handleDownload = async (e: React.MouseEvent) => {
  try {
    const response = await fetch(imageUrl);
    const blob = await response.blob();
    // ... download logic
  } catch (error) {
    console.error('[ImageAttachment] Download failed, opening in new tab');
    window.open(imageUrl, '_blank');  // Fallback
  }
};
```

---

## 📊 Performance

### Image Loading

**Lazy Loading:**
```tsx
const [imageLoaded, setImageLoaded] = useState(false);

<img
  src={thumbnailUrl}
  onLoad={() => setImageLoaded(true)}
  className={imageLoaded ? 'opacity-100' : 'opacity-0'}
/>
```

**Thumbnail Priority:**
```typescript
const imageUrl = thumb_url || url || image_url || fallback;
```

### Cost Optimization

**AI Vision:**
- Cost per photo: ~$0.002
- Monthly (100 photos/day): ~$6
- With compression: ~$1.80/month

**S3 Storage:**
- Storage: ~$0.023 per GB/month
- Requests: ~$0.0004 per 1,000 GET requests
- Data transfer: First 100GB free/month

---

## 🚀 Deployment Checklist

### Frontend
- [x] CustomAttachment integrated into StreamChatPane
- [x] Image, Gallery, File components created
- [x] AI analysis display implemented
- [x] Download functionality working
- [x] Lightbox keyboard navigation
- [x] Responsive design tested

### Backend
- [x] GPT vision service created (`gpt_vision.py`)
- [x] Photo upload endpoint enhanced
- [x] AI analysis fields added to models
- [x] Comprehensive logging added
- [x] Pillow dependency added to requirements.txt
- [x] OPENAI_API_KEY configured

### Environment
- [ ] Verify `OPENAI_API_KEY` in production
- [ ] Check `Pillow` installed on Heroku
- [ ] Verify S3 CORS allows chat domain
- [ ] Test presigned URL generation
- [ ] Monitor API costs (OpenAI dashboard)

---

## 🎉 Usage Examples

### 1. Single Photo with AI Analysis

**User sends:** 📸 "Water leak in bathroom"

**Chat displays:**
```
┌─────────────────────────────────┐
│ [Image: bathroom-leak.jpg]      │
│ 🔍 Click to expand               │
│                                  │
│ 🤖 AI Analysis:                  │
│ Moderate water damage visible... │
└─────────────────────────────────┘
```

### 2. Multiple Photos (Gallery)

**User sends:** 📸📸📸 "Property inspection photos"

**Chat displays:**
```
┌──────┬──────┬──────┐
│ [1]  │ [2]  │ [3]  │  <- Grid layout
│ 🤖   │ 🤖   │ 🤖   │  <- AI badges
└──────┴──────┴──────┘
3 images  <- Counter
```

### 3. File Attachment

**User sends:** 📄 "Lease agreement.pdf"

**Chat displays:**
```
┌─────────────────────────────────┐
│ 📄 Lease Agreement.pdf           │
│ PDF • 1.2 MB                     │
│                          [⬇️]    │
└─────────────────────────────────┘
```

---

## 📚 Related Documentation

- [AI Vision Photo Analysis](./AI_VISION_PHOTO_ANALYSIS.md) - GPT-4o Vision implementation
- [Stream Chat React Docs](https://getstream.io/chat/docs/sdk/react/) - Official Stream docs
- [OpenAI Vision API](https://platform.openai.com/docs/guides/vision) - Vision API reference

---

## 🔮 Future Enhancements

1. **Video Thumbnails**
   - Generate thumbnails for video attachments
   - Show first frame as preview

2. **Batch Download**
   - Download all images in gallery as ZIP
   - Progress indicator

3. **Image Editing**
   - Crop/rotate images before sending
   - Add annotations/arrows to highlight issues

4. **AI Video Analysis**
   - Analyze video frames for property issues
   - Generate timestamped summaries

5. **Voice Recordings**
   - Audio waveform visualization
   - Transcription with Whisper API

6. **Geolocation**
   - Display property location on map
   - Pin incidents to specific rooms

---

**Last Updated:** 2025-12-15
**Maintainer:** Claude Code (Anthropic)
**Branch:** claude/create-attachment-component-SkNzD
