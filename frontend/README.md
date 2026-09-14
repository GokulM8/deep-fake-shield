# Deepfake Shield Pro

## Local backend integration

The frontend can use the FastAPI backend already included in this repository. From `frontend/`, install dependencies and start the Vite app:

```bash
npm install
npm run dev
```

Start the backend separately from the repository root:

```bash
cd backend
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The frontend defaults to `http://127.0.0.1:8000`. Copy `.env.example` to `.env.local` to override `VITE_API_BASE_URL` or enable the original fixture mode with `VITE_USE_MOCK_DATA=true`. Real mode requires an uploaded file and uses the multipart upload, status, evidence, and report endpoints.

Build a polished, production-quality frontend web application called:

DEEPFAKE SHIELD

Tagline:

"Detect. Localize. Explain. Investigate."

DeepFake Shield is an AI-assisted digital media authenticity and forensic analysis platform. The long-term product supports image, video, and audio analysis, but for this implementation the primary working experience should be VIDEO-FIRST.

IMPORTANT:

- Build the frontend only.

- Do NOT build the ML model.

- Do NOT invent a real AI backend.

- Use realistic mock analysis data for the UI.

- Architect the frontend so the mock API can later be replaced by a FastAPI backend without redesigning the UI.

- The frontend must be fully functional using mock data.

- Do not claim that mock results are real predictions.

- Image and audio should appear as supported/future modalities, but video should receive the most complete UI.

- Make the application feel like a serious digital-forensics investigation platform, NOT a generic AI SaaS dashboard.

==================================================

TECH STACK

==================================================

Use:

- React / Next.js

- TypeScript

- Tailwind CSS

- Modern component architecture

- Lucide icons or another clean icon library

- Responsive design

- Dark-first interface

Use reusable components and clean TypeScript types.

==================================================

DESIGN DIRECTION

==================================================

Create a premium cybersecurity / digital-forensics aesthetic.

Visual identity:

- Deep charcoal / near-black background

- Subtle graphite panels

- Signal-jade / emerald accent color

- White and muted-gray typography

- Very subtle borders

- Minimal gradients

- No excessive glassmorphism

- No giant colorful gradients

- No cartoon illustrations

- No generic AI robot graphics

The interface should feel like:

"Digital forensic investigation workstation + modern AI research platform."

Use typography similar to Poppins / Inter.

Design should be clean, spacious, technical, precise and professional.

Use subtle animations:

- page transitions

- upload progress

- analysis progress

- timeline hover

- card hover

- expandable evidence sections

- smooth heatmap transitions

Do not over-animate the interface.

==================================================

GLOBAL NAVIGATION

==================================================

Create a persistent top navigation.

Left:

DEEPFAKE SHIELD

Small shield-style icon.

Navigation:

- Analyze

- Investigations

- About

Right:

- System Status: ONLINE

- Theme toggle

- Small user/profile button

Primary CTA:

"Analyze Media"

==================================================

PAGE 1 — LANDING / HOME

==================================================

Create a professional landing page.

Hero:

DEEPFAKE SHIELD

Detect. Localize. Explain. Investigate.

"AI-assisted digital media authenticity and forensic analysis."

Primary button:

[ Analyze Media ]

Secondary button:

[ Explore Investigation ]

Below hero, create three modality cards:

VIDEO

Temporal analysis

Frame-level detection

Suspicious timestamp localization

IMAGE

Visual manipulation detection

Face-region analysis

Explainable heatmaps

AUDIO

Synthetic speech detection

Spectral analysis

Audio segment analysis

Video should visually be marked:

"ACTIVE"

Image and Audio:

"COMING NEXT"

Add a short section:

WHY DEEPFAKE SHIELD?

Instead of simply returning REAL or FAKE, DeepFake Shield presents multiple evidence signals:

- Visual anomalies

- Temporal inconsistencies

- Face-region anomalies

- Compression signals

- Metadata

- Provenance

- Explainability

Use an evidence visualization rather than a huge text block.

Add a final CTA:

"Start a forensic analysis"

[ Analyze Media ]

==================================================

PAGE 2 — ANALYZE / UPLOAD

==================================================

Route:

/analyze

This is the primary page.

Header:

Analyze Digital Media

"Upload an image, video, or audio file for AI-assisted forensic analysis."

Create a large drag-and-drop upload zone.

Visual:

---

        DROP MEDIA HERE

     Drag & drop your file

             or

        [ Select File ]

Supported:

JPG PNG WEBP

MP4 MOV AVI WEBM

WAV MP3 FLAC M4A

---

Allow:

- drag and drop

- file picker

- file preview

- remove selected file

- analyze button

After selecting a video show:

Filename

File size

Video thumbnail / preview

Duration if available

File type

Example:

deepfake_sample.mp4

18.4 MB

00:12

VIDEO

Button:

[ Start Analysis ]

Also show a small security note:

"Files are processed as forensic evidence. Uploaded media should never be executed."

For now, clicking Start Analysis should create a mock analysis ID and navigate to:

/analysis/{id}/processing

==================================================

PAGE 3 — PROCESSING

==================================================

Route:

/analysis/[id]/processing

Create a serious forensic processing screen.

Header:

ANALYSIS IN PROGRESS

Analysis ID:

DF-2026-000124

Filename:

deepfake_sample.mp4

Create a vertical processing pipeline:

✓ Uploading

✓ Media identification

✓ Frame extraction

✓ Face detection

● Deep learning analysis

○ Temporal analysis

○ Forensic analysis

○ Evidence fusion

○ Report generation

Animate the current step.

Show:

Analyzing video

Frame 127 / 360

Progress bar.

Also show a small video preview on the right.

After a few seconds using mock state, automatically transition to:

/analysis/{id}

==================================================

PAGE 4 — ANALYSIS DASHBOARD

==================================================

Route:

/analysis/[id]

THIS IS THE MAIN SHOWCASE PAGE.

Create a professional forensic dashboard.

Top header:

FORENSIC ANALYSIS

deepfake_sample.mp4

Analysis ID:

DF-2026-000124

Status:

COMPLETED

==================================================

VERDICT CARD

==================================================

Large card.

AUTHENTICITY ASSESSMENT

LIKELY MANIPULATED

91.7%

Model Confidence

Add a circular/radial confidence visualization.

Under it:

AI-assisted forensic assessment

Not legal certainty

Do not say:

"100% Fake"

"Definitely Fake"

==================================================

EVIDENCE SUMMARY

==================================================

Create evidence cards:

VISUAL ANALYSIS

HIGH

91%

TEMPORAL ANALYSIS

HIGH

88%

FACE ANOMALIES

HIGH

86%

COMPRESSION

MEDIUM

74%

METADATA

LOW

20%

PROVENANCE

UNKNOWN

Each card should have:

- icon

- evidence name

- severity

- score where applicable

- small progress visualization

Important:

Keep MODEL CONFIDENCE separate from OVERALL FORENSIC ASSESSMENT.

==================================================

MODEL ANALYSIS

==================================================

Create a section:

MODEL ANALYSIS

Frame Model

EfficientNet

91.2%

Temporal Model

Temporal Transformer

88.4%

Overall Model Confidence

91.7%

Use clean horizontal bars.

Also provide:

Model architecture

Input frames

Frames analyzed

Face crops analyzed

Example:

Frames analyzed: 120

Faces detected: 117

Faces analyzed: 117

==================================================

VIDEO VIEWER

==================================================

Create a large video player section.

Left:

Video preview

Right:

Frame analysis summary

Video controls:

- play

- pause

- seek

- volume

- fullscreen

Below the player create:

FRAME AUTHENTICITY TIMELINE

A horizontal timeline from:

00:00 → 00:12

Represent frame-level prediction probability.

Example:

00:00 08%

00:01 11%

00:02 16%

00:03 63%

00:04 81%

00:05 92%

00:06 88%

00:07 42%

00:08 25%

00:09 78%

00:10 84%

Visualize suspicious regions on the timeline.

High-risk frames should be visually obvious but not overly colorful.

Allow clicking timeline points.

When clicking a suspicious timestamp:

Open the corresponding frame inspection panel.

==================================================

SUSPICIOUS FRAMES

==================================================

Create a grid/list of suspicious frames.

Example:

Frame 091

00:03.04

Score 89%

Frame 120

00:04.00

Score 94%

Frame 150

00:05.00

Score 92%

Frame 270

00:09.00

Score 86%

Each card should show:

- frame thumbnail

- timestamp

- prediction score

- severity

Clicking a frame opens detailed inspection.

==================================================

FRAME INSPECTION / EXPLAINABILITY

==================================================

Create an expandable/modal investigation view.

Title:

FRAME ANALYSIS

Timestamp:

00:04.27

Show two large panels:

ORIGINAL FRAME

HEATMAP

The heatmap should look like a Grad-CAM visualization.

Since there is no real ML model yet, use a realistic placeholder/demo visualization and clearly structure the component so a real Grad-CAM image URL can later replace it.

Show:

Frame Score

94.8%

Suspicious Region

Face boundary

Model Attention

Eyes / Mouth

Explanation:

"The model assigned higher importance to facial boundary and facial feature regions."

Do NOT present this as a real model result.

==================================================

FORENSIC ANALYSIS

==================================================

Create a dedicated section.

Title:

DIGITAL FORENSICS

File Information:

File Type

MP4

File Size

18.4 MB

Resolution

1920 × 1080

Frame Rate

30 FPS

Video Codec

H.264

Audio Codec

AAC

Create subsections:

COMPRESSION ANALYSIS

Recompression

Detected

Blocking artifacts

Low

Compression consistency

Medium

ARTIFACT ANALYSIS

Face boundaries

HIGH

Texture anomalies

MEDIUM

Lighting consistency

LOW

Blending artifacts

MEDIUM

Add a note:

"These signals are forensic evidence, not definitive proof."

==================================================

METADATA

==================================================

Create metadata table:

Property | Value

Filename

deepfake_sample.mp4

Format

MP4

Size

18.4 MB

Resolution

1920 × 1080

Frame rate

30 FPS

Codec

H.264

Creation time

Unknown

Software tag

Unknown

Add note:

"Missing metadata does not automatically indicate manipulation."

==================================================

PROVENANCE

==================================================

Create a provenance panel.

Status:

UNKNOWN

Content Credentials:

Not detected

C2PA:

Not detected

Cryptographic provenance:

Not detected

Add information note:

"Missing provenance does not prove that media is manipulated."

==================================================

FINAL ASSESSMENT

==================================================

Create a final evidence summary.

LIKELY MANIPULATED

Model Confidence

91.7%

Evidence:

Visual anomalies — HIGH

Temporal inconsistencies — HIGH

Face-region anomalies — HIGH

Compression anomalies — MEDIUM

Metadata signal — LOW

Provenance — UNKNOWN

Create a short explanation:

"The available evidence indicates that the media is likely manipulated. Visual and temporal analysis produced strong anomaly signals."

Again:

"AI-assisted forensic assessment — not legal certainty."

==================================================

REPORT ACTIONS

==================================================

Buttons:

[ View Full Report ]

[ Export Report ]

[ Analyze Another File ]

Export Report can initially generate/download a nicely formatted mock report or show a print-friendly report view.

==================================================

PAGE 5 — FULL FORENSIC REPORT

==================================================

Route:

/analysis/[id]/report

Create a clean report page suitable for presentation/demo.

Header:

DEEPFAKE SHIELD

FORENSIC ANALYSIS REPORT

Analysis ID

DF-2026-000124

Media

deepfake_sample.mp4

Type

VIDEO

Status

COMPLETED

Then:

AUTHENTICITY ASSESSMENT

LIKELY MANIPULATED

91.7%

MODEL CONFIDENCE

Then sections:

1. Executive Assessment

2. Evidence Summary

3. Model Results

4. Suspicious Frames

5. Explainability

6. Video Timeline

7. Metadata

8. Compression Analysis

9. Provenance

10. Final Assessment

Add:

Generated:

14 September 2026

Add disclaimer:

"This report represents an AI-assisted forensic assessment. Model confidence does not constitute legal certainty."

Provide:

[ Print / Export ]

==================================================

PAGE 6 — INVESTIGATIONS

==================================================

Route:

/investigations

Create a history page.

Header:

INVESTIGATIONS

"Previously analyzed media."

Create table/cards:

Analysis ID

Filename

Type

Verdict

Confidence

Date

Status

Example:

DF-2026-000124

deepfake_sample.mp4

VIDEO

Likely Manipulated

91.7%

Completed

DF-2026-000123

sample_video.mp4

VIDEO

Likely Authentic

87.3%

Completed

Allow clicking an investigation to open its dashboard.

Use mock data.

==================================================

RESPONSIVE DESIGN

==================================================

Desktop:

Use a spacious dashboard.

Tablet:

Collapse grid layouts.

Mobile:

Stack cards vertically.

Video timeline must remain usable on mobile.

Navigation becomes a mobile menu.

==================================================

MOCK DATA ARCHITECTURE

==================================================

Create centralized mock data.

Example TypeScript structure:

Analysis {

id

filename

mediaType

status

verdict

confidence

modelResults

evidence

suspiciousFrames

timeline

metadata

compression

provenance

report

}

Do NOT scatter fake values throughout components.

Keep all mock values in:

lib/mockData.ts

Create API abstraction:

lib/api.ts

Functions:

analyzeMedia()

getAnalysis()

getEvidence()

getReport()

Initially these return mock data.

Later they will call:

POST /api/v1/analyze

GET /api/v1/analyze/{analysis_id}

GET /api/v1/analyze/{analysis_id}/evidence

GET /api/v1/analyze/{analysis_id}/report

Do not require the backend to run for the frontend demo.

==================================================

COMPONENT ARCHITECTURE

==================================================

Create reusable components:

layout/

Navbar

Footer

upload/

DropZone

FilePreview

UploadProgress

analysis/

AnalysisHeader

VerdictCard

ConfidenceScore

EvidencePanel

EvidenceCard

ModelScores

VideoPlayer

VideoTimeline

SuspiciousFrames

FrameInspector

HeatmapViewer

ForensicPanel

MetadataPanel

CompressionPanel

ProvenancePanel

FinalAssessment

report/

ReportHeader

EvidenceSummary

ReportSection

ReportExport

==================================================

IMPORTANT PRODUCT RULES

==================================================

1. Never present mock values as real ML predictions.

2. Keep model confidence separate from forensic assessment.

3. Use language:

   "Likely Authentic"

   "Likely Manipulated"

   "Likely Synthetic"

   "Inconclusive"

4. Never use:

   "Definitely Fake"

   "100% Fake"

   "Legally Proven Fake"

5. Missing metadata does not mean fake.

6. Missing provenance does not mean fake.

7. Evidence signals should remain individually visible.

8. The UI must communicate that this is AI-assisted forensic analysis.

==================================================

VIDEO-FIRST IMPLEMENTATION

==================================================

Although the product supports:

VIDEO

IMAGE

AUDIO

make VIDEO the only fully implemented analysis workflow.

Image and Audio upload cards should exist but be marked:

COMING NEXT

Do NOT create fake image/audio analysis results.

The architecture should make it easy to add:

/analysis/{id}/image

/analysis/{id}/audio

later.

==================================================

FINAL UX FLOW

==================================================

User opens:

/

↓

Clicks:

Analyze Media

↓

/analyze

↓

Uploads:

deepfake_sample.mp4

↓

Clicks:

Start Analysis

↓

/analysis/DF-2026-000124/processing

↓

Processing animation

↓

/analysis/DF-2026-000124

↓

Sees:

LIKELY MANIPULATED

91.7%

↓

Views:

Model scores

Evidence

Video

Timeline

Suspicious frames

Heatmap

Forensics

Metadata

Provenance

↓

Clicks suspicious timestamp

↓

Inspects frame + heatmap

↓

Clicks:

View Full Report

↓

/analysis/DF-2026-000124/report

==================================================

QUALITY BAR

==================================================

The finished frontend should look like a serious research/product demonstration that could be shown to:

- university evaluators

- hackathon judges

- researchers

- cybersecurity professionals

It should NOT look like a template dashboard.

Prioritize:

- excellent spacing

- typography

- information hierarchy

- clear evidence visualization

- professional dark forensic aesthetic

- polished interactions

- reusable components

- clean TypeScript

- responsive layout

Do not overpopulate the UI.

Every element should have a purpose.

Build the complete frontend now.

This project was built with [Lovable](https://lovable.dev).

## Build with Lovable

Continue developing this project in the [Lovable editor](https://lovable.dev/projects/df1998f0-875c-4a9e-b81d-3d668cb83366).

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: every change made in Lovable is committed straight to this repository.
- **Full ownership**: this code is yours. Push to `main` on GitHub and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? You need Node.js and npm — [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
git clone <this-repository-url>
cd <repository-name>
npm i
npm run dev
```
