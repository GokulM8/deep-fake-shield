# DeepFake Shield: Project Review and Viva Guide

This guide is built only from what the repository actually contains and what was verified on 2026-10-24, updated on 2026-10-28 for the hybrid model and the D1–D3 fixes. The facts, file paths and numbers come from [`PROJECT_TECHNICAL_DOCUMENTATION.md`](PROJECT_TECHNICAL_DOCUMENTATION.md); the diagrams are in [`ARCHITECTURE.md`](ARCHITECTURE.md).

**Golden rule for the review:** say what is implemented, what is a placeholder, and what you measured. Reviewers forgive limitations you name yourself. They do not forgive overclaiming they discover.

---

## A. Two-minute project introduction

> "Deepfakes are AI-manipulated videos, usually face swaps, and they're increasingly hard to spot. Most detectors give you a bare 'real' or 'fake'. DeepFake Shield tries to show the evidence behind the answer.
>
> It's a web application with three parts. A React and TypeScript frontend lets you upload a video and explore the result. A FastAPI backend validates the upload and runs the analysis as a background job. And a PyTorch pipeline handles the dataset, training and evaluation.
>
> The model is a two-stage hybrid. The backend samples 16 frames, finds the face in each with OpenCV, and passes the face crops through an EfficientNet-B0 that I fine-tuned and then froze. It turns each face into a 1280-number embedding. A small learned head, a mean-pooling MLP, then reads all 16 embeddings together and makes the video-level decision. For every frame the UI also shows the frame classifier's own score and a Grad-CAM heatmap of which parts of the face pushed that score towards fake.
>
> On the 902-video test set, the hybrid reaches 98.9% ROC-AUC and 94.7% balanced accuracy, up from 88.1% and 79.8% for simply averaging frame probabilities. An ablation shows the gain comes from learning the aggregation, not from temporal modelling: a Transformer head over the same frames does slightly worse. The honest limitations are that the head is badly calibrated, the splits are by file rather than by identity, and there are only 107 real test videos.
>
> The backend has 31 passing tests, including all three serving modes, concurrency and failure handling."

**Why it works:** problem → idea → architecture → algorithm → honest results → evidence. Keep it to about 2 minutes.

---

## B. Five-minute technical walkthrough (demo order)

| Minute | Show | Say |
| --- | --- | --- |
| 0:00 | `ARCHITECTURE.md` §1 diagram | "Three parts: frontend, FastAPI, ml package. One process, in-memory state." |
| 0:45 | `curl /health` | "It reports the active model, `EfficientNet-B0 + MLP head`, and its threshold." |
| 1:00 | Upload a video at `/analyze` → processing page → dashboard | "202 Accepted, then the UI polls every 800 ms." |
| 1:45 | Dashboard: verdict, frame-level evidence, open the inspector, drag the overlay slider | "The verdict is the head's video-level decision; frame scores and Grad-CAM are frame-level evidence from the CNN." |
| 2:45 | `backend/app/services/video_detector.py`: `EmbeddingHeadDetector._score_with_gradcam` | "One backbone pass gives the embeddings for the head, the frame scores and the Grad-CAM maps." |
| 3:30 | `artifacts/evaluations/ablation_table.md` | "Mean of frame probabilities 88%; learned MLP head 98.9%; Transformer 97.8%: the gain is learned aggregation." |
| 4:15 | `training_curves.png` | "Transformer inner-val loss rises from epoch 1; we keep epoch 6, the best inner-val ROC-AUC." |
| 4:40 | Terminal: `python -m pytest -q` → 31 passed | "Tests use the real checkpoints, not mocks." |

---

## C. Architecture explanation script

> "Let me follow one video through the system.
>
> In the browser, `analyze.tsx` calls `analyzeMedia` in `lib/api.ts`, which posts the file as multipart form data to `/api/v1/analyze`.
>
> In FastAPI, `create_analysis` first reduces the filename to its base name and checks the extension. It streams the file to the temp directory in 1 MB chunks, stopping at 100 MB. It checks the magic bytes to confirm the content matches the extension, hashes the file, stores a 'processing' record in the in-memory repository, schedules a background task, and returns 202 with the analysis ID.
>
> The background task calls `AnalysisService.run`. For video it calls `VideoDetector.predict`, which takes a lock so only one analysis uses the model at a time. It opens the file with OpenCV and samples 16 evenly spaced frames. It finds the largest face in each with a Haar cascade, crops it with 20% padding, and normalizes it to 224 by 224. One pass through the frozen EfficientNet-B0 gives three things per face: a 1280-number embedding, the frame classifier's own fake probability, and, with a backward pass from the fake logit, a Grad-CAM map. The embeddings go into their frame slots, and the mean-pool MLP head turns them into one video-level fake probability, which is compared with the threshold stored in its checkpoint. Frame images and heatmaps are saved as JPEGs the same size as the frame.
>
> The record becomes 'completed'. The processing page, which has been polling, redirects to the dashboard. `toAnalysis` maps the backend JSON to UI types, and the frame cards load their JPEGs from the frames endpoint.
>
> If there's no face, or the file can't be decoded, the record is marked 'failed' with a message, and the UI stops polling."

---

## D. Technology-stack defense

| Tech | Why use it? | Role | Why not an alternative? | Limitations |
| --- | --- | --- | --- | --- |
| **Python** | The ML ecosystem standard | Backend + ML | The model is PyTorch, so one language end to end | GIL; slower request handling than Go/Node, which doesn't matter here |
| **FastAPI** | Typed request/response models, automatic OpenAPI docs, async support | HTTP API | Flask lacks built-in validation and docs; Django is heavy with an ORM we don't use yet | Background tasks are in-process: no durability or retries |
| **Pydantic v2** | Declarative validation with range checks | `schemas.py` | Manual dicts are error-prone | Needs care with version-2 API changes |
| **Uvicorn** | Standard ASGI server | Runs FastAPI | Gunicorn would be needed for multiple workers, but in-memory state prevents that | Single process here |
| **PyTorch + torchvision** | Research standard; EfficientNet-B0 with ImageNet weights built in | Training, inference, Grad-CAM | TensorFlow is fine but less common in current research code | Large install (~1 GB); CPU inference only on this machine |
| **EfficientNet-B0** | Strong accuracy per FLOP; 4.0 M parameters; under 1 s per video on CPU | Frame classifier | Xception/B4 are more accurate but slower; ViTs need more data | Frame-level only; no motion cues |
| **OpenCV** | One library for decoding, face detection, resizing and colormaps | Video I/O, Haar faces, artifacts | PyAV/decord for decoding, RetinaFace for faces: more dependencies | Haar misses profile and small faces; the shared classifier is not thread-safe, so inference runs under a lock |
| **scikit-learn** | Trusted metric implementations | `ml/evaluation/metrics.py` | Hand-coded AUC risks bugs | Offline only |
| **React 19 + TypeScript** | Component UI with type-safe API mapping | Frontend | Vue/Svelte are fine; React has the largest ecosystem | Bundle size |
| **TanStack Start/Router/Query** | File-based typed routes, loaders, SSR, server-state caching | Routing + data fetching | Next.js is comparable; this came with the Lovable template | SSR complicates browser-only values (object URLs must be read after mount) |
| **Tailwind + Radix (shadcn)** | Fast, consistent, accessible UI | Styling and primitives | CSS modules are slower to build | Many unused template components |
| **pytest** | Simple, standard | Backend tests | unittest is more verbose | No frontend tests exist |

---

## E. Technical viva questions with model answers

Each question has: **A** (the answer), **Follow-up** (a harder question), and **Trap** (a weak answer to avoid).

### E1. Project fundamentals

**1. What problem does your project solve?**
**A:** It detects face-manipulated videos and *explains* the decision with frame images, face boxes and Grad-CAM heatmaps, instead of returning a bare label.
**Follow-up:** "Who would use it?" Investigators, journalists and trust-and-safety analysts, as a triage aid, not as proof.
**Trap:** claiming it detects "all deepfakes" or "images and audio". It doesn't.

**2. What exactly is implemented versus planned?**
**A:**
- **Implemented:** video inference, Grad-CAM, the dashboard, the async API, dataset audit and splits, and the training and evaluation scripts.
- **Placeholder:** image and audio scores.
- **Experimental:** the temporal Transformer.
- **Not implemented:** database, authentication, metadata/compression/provenance forensics, deployment.

**Trap:** presenting the PDF vision as the current state.

**3. What are the inputs and outputs?**
**A:** The input is one media file of up to 100 MB. For video, the output is an `AnalysisRecord` containing the verdict, confidence, per-frame probabilities and timestamps, face boxes, artifact URLs, and evidence signals, plus two JPEGs per frame.

**4. Why video-first?**
**A:** One genuinely working modality is more valuable than three fake ones. Video is also where temporal and explainability features matter most. The labelled data available was video (Celeb-DF style).

**5. What dataset did you use?**
**A:**
- 6,529 `.mp4` videos: 482 Celeb-real, 230 YouTube-real, 5,299 fake, and 518 unlabelled test videos.
- That gives 6,011 labelled videos, split 4,207 / 902 / 902.
- The folder layout matches Celeb-DF v2.

**Follow-up:** "The README links DFDC, so which is it?" The README links are inconsistent with the data actually used. The folder names indicate Celeb-DF, and I'd correct the README.
**Trap:** naming a dataset you can't verify.

### E2. Languages and frameworks

**6. Why FastAPI rather than Flask?**
**A:** Pydantic validation at the boundary, automatic `/docs`, `UploadFile` streaming, and built-in `BackgroundTasks`. Flask would need several extensions to match that.

**7. How does FastAPI run your background task?**
**A:** `BackgroundTasks.add_task` runs `AnalysisService.run` after the response is sent. Because it is a normal (sync) function, Starlette runs it in a thread pool.
**Follow-up:** "Consequences?" Several analyses can start at once on the shared model. That exposed a thread-safety bug, now fixed with a lock (see Q30).

**8. Why TanStack Start / SSR?**
**A:** The frontend scaffold came from a Lovable TanStack Start template. SSR gives fast first paint and typed routes.
**Follow-up:** "What did SSR break?" The uploaded-video object URL exists only in the browser, so it has to be read in a `useEffect` after mount. Otherwise the server and client HTML differ (a hydration mismatch).

**9. What does React Query do here?**
**A:** It caches server data. `analysisQuery(id)` is loaded in the route loader with `ensureQueryData` and read with `useSuspenseQuery`.

**10. Why TypeScript strict mode with `exactOptionalPropertyTypes`?**
**A:** It forces the code to separate "property missing" from "property is undefined". That's why the code spreads optional props (`...(url ? { src: url } : {})`). It catches contract mismatches between the backend JSON and the UI types at compile time.

### E3. Architecture and design

**11. Describe the architecture.**
**A:** Browser → frontend SSR server for pages. Browser → FastAPI directly for data. FastAPI has three layers: routes (validation), `AnalysisService` (orchestration) and `VideoDetector` (ML). Records live in an in-memory repository; files in the temp directory. See `ARCHITECTURE.md` §1.

**12. Why 202 + polling instead of returning the result directly?**
**A:** Inference can take seconds, and real deployments take longer. Returning immediately keeps the HTTP request short and lets the UI show progress.
**Follow-up:** "Alternatives?" WebSockets or Server-Sent Events for push, or a real job queue (Celery/RQ).
**Trap:** saying the processing page shows real progress. The stage animation is cosmetic. Only the final status is real.

**13. What design patterns are used?**
**A:**
- **Repository** (`AnalysisRepository`, swappable for a database).
- **Service layer** (`AnalysisService`).
- **Adapter** (`toAnalysis` maps the backend contract to UI types).
- **Shared library between training and serving** (the `ml/` package).

**14. How do you avoid training/serving skew?**
**A:** The backend imports `FaceCropper`, `sample_frame_indices` and `build_model` from `ml/`, so the cropping, transform and architecture are the same code that training used.
**Follow-up:** "Is there any remaining skew?" For the heads, no: their embeddings were extracted on Colab with the backend's own `sample_faces` and transform, and the served pipeline reproduces their test ROC-AUC within 0.15 points. For the frame encoder, yes: its original training fell back to the full frame when no face was found (the backend skips that frame) and was trained on 2 frames.

**15. Where is state stored, and what happens on restart?**
**A:** Records are in a Python dict, so they're lost on restart (including `--reload`). Artifacts are in `$TMPDIR` and wiped at startup on purpose, so they stay consistent with the records.

### E4. Algorithms and implementation

**16. Explain EfficientNet-B0 briefly.**
**A:**
- A CNN from neural architecture search, built from MBConv blocks: inverted residuals, depthwise convolutions and squeeze-and-excitation.
- It's scaled jointly in depth, width and resolution ("compound scaling").
- We replace the head with `Dropout(0.3) → Linear(1280, 2)`.

**17. How are frames chosen?**
**A:** `np.linspace(0, n-1, 16)`: 16 evenly spaced frames (it was 2 until 2026-10-26; see Q47).
**Follow-up:** "Weakness?" They are about 1 s apart, so short-range temporal artifacts between consecutive frames are invisible.

**18. How is the face found?**
**A:** OpenCV Haar cascade (Viola–Jones) on the grayscale frame (`scaleFactor` 1.1, `minNeighbors` 5, `minSize` 32). It keeps the largest face and pads it by 20%. Frames without a face are skipped. If no frame has a face, the analysis fails cleanly.

**19. How is the video-level decision made?**
**A:**
- Default (`mlp`): the head's softmax fake probability over the 16 embeddings; FAKE if it is ≥ 0.9993, the threshold stored in the checkpoint (val Youden's J).
- `temporal`: the Transformer head, threshold 0.8795. `baseline`: mean of frame probabilities, threshold 0.3654.
- `confidence` is the probability of the chosen class.

**Trap:** calling confidence "accuracy" or "certainty". It's an uncalibrated model probability, and the code says so in the evidence text.

**20. Explain Grad-CAM in your implementation.**
**A:**
- A forward hook on `model.features[-1]` saves the 1280×7×7 activations and calls `retain_grad()`.
- We backpropagate from the fake-class logit.
- The channel weights are the spatial mean of the gradients; the map is the ReLU of the weighted sum of channels.
- Each map is normalized per frame, upsampled to the face crop, JET-coloured, and placed on a black frame-sized canvas, so it overlays the frame exactly with a screen blend.

**Follow-up:** "Does computing gradients change the score?" No. I checked that it equals the `no_grad` probability (0.020694 for both).
**Trap:** saying the heatmap "proves" where the manipulation is. It's an explanation of the model, not ground truth.

**21. Why the logit and not the softmax probability?**
**A:** Standard Grad-CAM uses the pre-softmax score. Softmax gradients saturate when the model is confident, which gives weak or noisy maps.

**22. Why is one backward pass enough for a batch of 16 frames?**
**A:** In eval mode BatchNorm uses running statistics, so samples don't interact. The gradient of the summed logits with respect to each sample's activations is just that sample's own gradient.

**23. How did you split the data, and why?**
**A:**
- Group by SHA-256 so byte-identical duplicates stay together.
- Refuse to split if a group has conflicting labels.
- Per class, shuffle with seed 42 and greedily fill 70/15/15.
- Assert that no hash crosses splits.

**Follow-up:** "Does that prevent leakage?" Only duplicate-file leakage. The same celebrity can appear in train and test (identity leakage), and the files were renamed to integers, so the source IDs are lost. That's a known limitation.

**24. How was training done?**
**A:**
- `scripts/train_baseline.py`: EfficientNet-B0 (optionally ImageNet-initialized), AdamW, lr 1e-4, weight decay 1e-4.
- Each video gives T frames. The logits are averaged across frames before cross-entropy, so the supervision is video-level.
- The best checkpoint is chosen by validation ROC-AUC.
- The frame encoder was trained off-machine on Colab and records epoch 2; the checkpoint metadata fits a `--limit 1000` run (~1,000 of 4,207 training videos, 2 frames).
- The heads were then trained on frozen embeddings; see Q49–Q51 for their exact settings.

**Trap:** inventing hyperparameters for the frame encoder. Its exact run isn't recorded in the repo. Say so.

**25. What is the temporal Transformer?**
**A:** A video-level head over the 16 frozen EfficientNet embeddings: LayerNorm + projection to 256, learned positions, a 2-layer, 4-head pre-norm Transformer encoder, masked mean pooling and a linear classifier. It reaches 97.83% test ROC-AUC and is selectable with `DEEPFAKE_MODEL=temporal`, but the simpler mean-pool MLP beats it, so the MLP is served (Q48).

### E5. APIs and data

**26. List your endpoints.**
**A:**
- `GET /health`;
- `POST /api/v1/analyze` (202);
- `GET /api/v1/analyze` (list);
- `GET /api/v1/analyze/{id}`;
- `GET .../evidence`;
- `GET .../report`;
- `GET .../frames/{frame_id}/{frame|heatmap}`;
- plus `/docs`.

**27. How do you validate uploads?**
**A:**
- extension allow-list per media type;
- streaming size limit of 100 MiB (413);
- empty files rejected (400);
- magic bytes, with the RIFF subtype checked for WEBP/WAV/AVI (415);
- the filename reduced to its base name;
- the stored name is server-generated.

**Follow-up:** "Any weakness?" `validate_signature` reads the whole file just to check 16 bytes. And magic bytes only show the file type looks right; they don't prove the file is valid.

**28. Is there a database?**
**A:** No. It's an in-memory repository behind a repository interface, so swapping in SQLite/PostgreSQL only means rewriting that class. `DATABASE_URL` in `.env.example` is a placeholder that no code reads.

**29. Could the frames endpoint be abused for path traversal?**
**A:** No. It first requires an existing analysis ID from the repository. `frame_id` is typed `int` and `kind` is a `Literal["frame", "heatmap"]`, so FastAPI rejects anything else with 422 before a path is built.

### E6. Testing and debugging

**30. How do you know it works under load?**
**A:** I found it didn't, fixed it, and added a test. Running 4 threads calling `predict` at once showed two bugs:
- with Grad-CAM, one thread's forward hook captured another thread's activation: an `AttributeError` crash, and wrong scores in 15 of 48 runs (D1);
- even the `no_grad` path gave different scores (up to 0.29) in 5 of 24 runs, from the shared OpenCV cascade (D2).

The fix is a `threading.Lock` held for the whole of `predict()`, so analyses run one at a time per process. `test_concurrent_predictions_are_safe_and_identical` now runs 4 threads and requires identical scores (to 1e-6). A related bug (D3), where any unexpected exception left a record stuck in `processing`, is fixed with a catch-all that marks it `failed` and a `try/finally` that always deletes the upload, with its own test.
**Trap:** claiming it scales. The lock makes it correct, not fast: one video at a time per process.

**31. What do your tests cover?**
**A:** 31 tests:
- health (active model and threshold) and CORS;
- upload → completed → evidence; history ordering; rejecting bad extensions and mismatched content;
- an unexpected detector error → `failed` and upload deleted (D3);
- model load on CPU; preprocessing shape; the real-video inference contract; the clean failure on a faceless video;
- Grad-CAM artifacts written and served, with 404s;
- 4-thread concurrency (D1/D2); the no-Grad-CAM path matching served scores;
- both head checkpoints loading strictly; `mlp` as the default; stored vs overridden thresholds; invalid `DEEPFAKE_MODEL`, threshold or frame count rejected;
- a real video through each of `baseline`, `mlp` and `temporal`.

All 31 passed on 2026-10-28.
**Follow-up:** "Gaps?" No frontend tests; nothing for 413/400 or a missing checkpoint. Some tests need an untracked dataset video, so they fail or skip on a clean clone.

**32. Do you mock the model in tests?**
**A:** No. They load the real checkpoint and run real inference, so they would catch shape or preprocessing regressions. The cost is that they're slower and depend on data.

**33. Tell me about a bug you debugged.**
**A:** Two good ones:
1. The dashboard showed a stock photo instead of the uploaded video. The cause was a hard-coded `sample-frame.jpg` passed as the `<video>` poster.
2. `Backend request failed (404)`. The cause was `.env.local` pointing at port 8001, where an unrelated Docker service was running.

Both were found by tracing from the symptom to the data source.

### E7. Security and performance

**34. What security controls exist and what is missing?**
**A:**
- **Exist:** upload validation, path-traversal-safe storage and routes, CORS limited to localhost.
- **Missing:**
  - authentication (anyone who can reach the port can list every analysis);
  - rate limiting;
  - inference timeouts;
  - safe checkpoint loading (`torch.load(weights_only=False)` can execute code from a malicious file).

**35. How fast is inference?**
**A:** Measured on an Apple M4, 16 frames with Grad-CAM, median of 5: plugged in, the baseline took 3.9 s on CPU and 0.6 s on the GPU (MPS); on battery with Low Power Mode every mode took 7–9 s CPU and 1.2–1.3 s MPS. The head itself adds only 0.05 ms (MLP) or 1.1 ms (Transformer), so the cost is decoding, face detection and the backbone. EfficientNet-B0 is about 0.39 GFLOPs per 224 image. The server uses CUDA or CPU.

**36. How would you scale it?**
**A:**
- Move records to PostgreSQL and artifacts to object storage.
- Run inference in a separate GPU worker behind a queue, with batched inputs and one model per worker.
- Then add API replicas behind a load balancer.

Today's in-memory state blocks multiple Uvicorn workers.

### E8. Results and evaluation

**37. What are your results?**
**A:** On the test split (902 videos: 107 real, 795 fake), thresholds tuned on validation:

| Model | Balanced acc. | Real recall | Fake recall | ROC-AUC |
| --- | ---: | ---: | ---: | ---: |
| Baseline: mean of 16 frame probabilities | 79.75% | 86.92% | 72.58% | 88.13% |
| Hybrid: EfficientNet + Transformer head | 91.75% | 88.79% | 94.72% | 97.83% |
| **Hybrid: EfficientNet + mean-pool MLP head (served)** | **94.67%** | 96.26% | 93.08% | **98.86%** |

I also re-ran both heads through the actual served pipeline on all 902 val and test videos: MLP 98.73% ROC-AUC and 94.17% balanced accuracy at its stored threshold, Transformer 97.71% and 91.81%, within 0.15 ROC-AUC points of Colab.

**38. Why do you report balanced accuracy and ROC-AUC instead of accuracy?**
**A:** 88% of the test set is fake, so a model that always says "fake" gets 88% accuracy while catching zero real videos. Balanced accuracy is the mean of real recall and fake recall, so each class counts equally. ROC-AUC is threshold-free: it is the probability that a random fake scores above a random real video, so it measures ranking ability separately from the choice of threshold.

**39. Why are thresholds tuned on validation and not on test?**
**A:** Anything chosen by looking at the test set makes the test score optimistic, because the threshold has been fitted to those exact videos. So there are three separate roles: the inner-val split (15% of train) picks the epoch, the validation split picks the threshold (Youden's J, which maximizes TPR − FPR), and the test split is only read once, for the report.

**40. Why is the MLP's threshold 0.9993? Isn't that strange?**
**A:** Yes, and I report it as a limitation. The heads are overconfident: almost every video gets a fake probability near 1, and real videos are separated only in the last few decimals. The *ranking* is excellent (98.9% ROC-AUC), so a threshold exists that separates the classes well, but the number itself is not a trustworthy probability. The fix is calibration, for example temperature scaling on validation, which rescales the logits without changing the ranking.

**41. How do you know the numbers are real and reproducible?**
**A:**
- Every local run writes `metrics.json` with the git commit, checkpoint hashes and cached per-video predictions (`artifacts/evaluations/`).
- The Colab re-run of the local baseline gave 88.19% vs 88.13% ROC-AUC (fp16 extraction shifted its tuned threshold from 0.3654 to 0.2917, giving 81.55% vs 79.75% balanced accuracy).
- Re-scoring all 902 val and 902 test videos through the served pipeline (`mlp_served`, `temporal_served`) reproduced test ROC-AUC within 0.15 points (MLP 98.73% vs 98.86%, Transformer 97.71% vs 97.83%); at the stored thresholds, balanced accuracy was 94.17% (MLP; Colab 94.67%) and 91.81% (Transformer; Colab 91.75%). The stored thresholds themselves do not fully reproduce on locally served val scores (MLP 0.9996 vs 0.9993, Transformer 0.9797 vs 0.8795), another sign of saturated, uncalibrated scores.

### E9. Limitations and future work

**42. What are the biggest limitations?**
**A:**
1. **Calibration:** head thresholds of 0.8795 and 0.9993 mean the probabilities are overconfident.
2. **Identity leakage:** splits are by file hash, and Celeb-DF reuses the same celebrities, so test faces may have been seen in training.
3. **Small real class:** 107 real test videos; one video is ~0.9 points of real recall.
4. **Encoder trained on ~1,000 videos** (of 4,207) and then frozen.
5. **Sparse sampling:** 16 frames about 1 s apart, so no short-range temporal cues.
6. One dataset family; image/audio are placeholders; no persistence or authentication.

**43. What would you do with another month?**
**A:**
- **Week 1:** temperature scaling and calibration curves; an identity-aware re-split and re-evaluation.
- **Week 2:** dense consecutive-frame clips to test temporal modelling properly; compare MLP vs Transformer again.
- **Week 3:** fine-tune the encoder on the full training split; cross-dataset tests (FaceForensics++, DFDC).
- **Week 4:** SQLite persistence; an explicit "unsupported" for image/audio; Playwright end-to-end tests.

**44. Why not just use a pretrained deepfake detector from the internet?**
**A:** It wouldn't show I understand training, evaluation and leakage. Most also aren't tuned for this data distribution. The value here is the end-to-end, explainable, measured pipeline.

**45. Why should this design be preferred over a simpler script?**
**A:** A script gives one label. This gives a reusable API, asynchronous and thread-safe processing, explanations a human can check, traceable evaluations, and tests. For a single offline use, a script *would* be simpler, and `scripts/infer_video.py` exists for exactly that.

### E10. The hybrid model

**46. What makes the model "hybrid"? Why two stages?**
**A:** Stage 1 is a CNN, EfficientNet-B0, that works on one face crop at a time and turns it into a 1280-d embedding. Stage 2 is a small learned head that works on the whole video: it takes the 16 embeddings and outputs one real/fake decision. The CNN was fine-tuned for real/fake frames and then frozen. Freezing it has three benefits: embeddings are extracted once (6,011 videos × 16 frames, ~3.5 h on a T4) and the heads then train in minutes; the head has only ~0.3 M (MLP) or ~1.9 M (Transformer) parameters, so it can't overfit the images themselves; and the same backbone still gives per-frame scores and Grad-CAM for explanations.

**47. Why 16 frames?**
**A:** Measured, not guessed. With the same baseline model, 16 frames beat 2 frames on every test metric (ROC-AUC 88.13% vs 83.17%), and 2-frame sampling skipped 6 videos with no detectable face while 16 frames skipped none. 16 frames costs about 3.9 s plugged in (7–9 s on battery in Low Power Mode) per video on a laptop CPU with Grad-CAM, which is acceptable for an upload-and-wait workflow.

**48. Is the improvement from temporal modelling?**
**A:** No, and the ablation shows it. The MLP head takes the *mean* of the embeddings, so it cannot see frame order at all, and it beats the Transformer, which has positional encodings and self-attention across frames (98.86% vs 97.83% ROC-AUC). Fixed aggregations of frame probabilities (mean, median, top-3, max) stay at 85–88%. So the gain comes from learning the video-level decision on rich embeddings instead of averaging already-squashed probabilities. A likely reason the Transformer can't use time: 16 evenly spaced frames are about 1 s apart, too sparse to see flicker or blending jitter. Testing temporal modelling properly needs dense consecutive-frame clips.

**49. Why train for 100 epochs, and why were epochs 6 and 75 chosen?**
**A:** Training ran for a fixed 100 epochs with no early stopping (`patience=100`), and after every epoch the checkpoint was kept if inner-val ROC-AUC improved. So 100 is a budget, not the choice; the inner-val split chose epoch 6 for the Transformer (inner-val ROC-AUC 0.9699) and epoch 75 for the MLP (0.9797). The MLP's best epoch was printed in the Colab cell output but not saved in its checkpoint, which is noted in `artifacts/evaluations/hybrid_colab/mlp_training_note.md`.

**50. What does the overfitting curve show?**
**A:** For the Transformer, inner-val loss is lowest at epoch 1 (0.277) and rises steadily to 0.618 by epoch 100, while training loss falls to almost zero. That is classic overfitting: the model keeps getting more confident on training videos and more confidently wrong on unseen ones. Inner-val ROC-AUC peaks later, at epoch 6, because ranking can still improve while confidence on mistakes grows; we keep epoch 6. The rising loss is also consistent with the overconfident thresholds in Q40.

**51. How exactly were training settings chosen?**
**A:** AdamW (lr 3e-4, weight decay 1e-2), cosine LR schedule, batch 64, class-weighted cross-entropy (the training set is about 7:1 fake to real, so unweighted loss would favour "fake"), frame dropout 0.25 (randomly hiding frames so the head can't rely on any single one, and copes with no-face frames), dropout 0.2, seed 42. They are standard defaults for a small head, not the result of a search on the test set.

**52. Why do frame scores and the verdict use different thresholds?**
**A:** They come from different models. Frame scores are the frame classifier's own outputs and are flagged at its val-tuned 0.3654. The verdict is the head's output at the head's val-tuned threshold. Using the head's 0.9993 on frame scores would flag almost nothing. The UI labels them separately: "frame-level evidence (EfficientNet-B0)" and "video-level decision (EfficientNet-B0 + MLP head)".

---

## F. Code-level questions a reviewer may point at

| Code | Likely question | Answer |
| --- | --- | --- |
| `video_detector.py:18-20`: `sys.path.insert(0, ML_ROOT)` | "Why modify `sys.path`?" | To import the training code (`ml/`) without packaging it, keeping train and serve identical. Better long-term: make `ml` an installable package. |
| `VideoDetector.__init__`: `try: self.model = self._load_model() except Exception as error: self.load_error = error` | "Why swallow the exception?" | So the API still starts and `/health` reports `degraded`; video jobs then fail with a clear message instead of the whole app crashing on import. |
| `_predict_with_gradcam`: `output.retain_grad()` | "What does `retain_grad` do?" | PyTorch normally keeps gradients only for leaf tensors. `retain_grad` keeps `.grad` on this intermediate activation so we can read it after `backward()`. |
| `logits[:, 1].sum().backward()` | "Why sum?" | `backward()` needs a scalar. Summing gives each sample its own gradient, because the samples don't interact in eval mode. |
| `cams / peaks` | "Why normalize per frame?" | To show relative importance within each frame. The trade-off: even a low-probability frame shows a bright hotspot. |
| `_write_frame_artifacts`: `colored * face_cam[..., None]` | "Why multiply by the CAM?" | It fades low-activation areas to black, so they disappear under a screen blend. Only salient regions show colour. |
| `sample_frame_indices`: `np.linspace(..., dtype=int64)` | "What if frame_count is 1?" | Both indices are 0, so the same frame is used twice. If it's 0, `predict` raises earlier. |
| `FaceCropper.locate`: `max(faces, key=area)` | "Multiple faces?" | Only the largest face is analyzed, which is a limitation for group videos. |
| `split_dataset.create_splits`: conflict check | "Why raise an error?" | Identical files with different labels mean label noise. Silently splitting them would leak an answer into test. |
| `scripts/train_baseline.py`: `logits.reshape(batch, steps, 2).mean(dim=1)` | "Why average logits?" | Video-level supervision: the label belongs to the video, not to each frame. |
| `main.py`: `shutil.rmtree(ARTIFACT_ROOT)` at import | "Isn't that dangerous?" | It only removes our own temp folder, and the records it belongs to are already gone after a restart. With multiple workers it would be wrong. |
| `api.ts` `toAnalysis()`: `scoreSeverity` | "Where do 75/45 come from?" | They match the timeline colour bands in `VideoTimeline.tsx`, so the cards and the timeline agree. They are display bands, not model thresholds. |
| `FramePreview.tsx`: `aspectRatio` style | "Why not a fixed 16:9?" | With `object-cover` in a 16:9 box, a 944×500 frame gets cropped, so percentage face boxes and heatmaps wouldn't line up. |
| `analysis.$id.index.tsx`: `useEffect(() => setUploadedUrl(getUploadedMediaUrl(id)))` | "Why not read it during render?" | SSR: the object URL exists only in the browser. Reading it during render would make the server and client HTML differ. |
| `analysis.py` `_placeholder_result` | "Is this a model?" | No. The scores come from the file's SHA-256 bytes. It's scaffolding so the UI works end to end for every media type. |

---

## G. Critical reviewer questions, answered honestly

**"What exactly did you implement yourself?"**
Answer from the evidence, and be accurate:
- **Your own work:** the ML package (dataset audit, splits, training, evaluation), the backend integration, the model training on Colab, and the experiments.
- **The frontend:** generated from a Lovable TanStack Start template, then connected to the real API.
- **AI-assisted parts:** the concurrency and failure-handling fixes, the evaluation and embedding pipeline, the hybrid serving code and these documents were written with an AI coding assistant.

Say this plainly, and show that you understand every line you're asked about.

**"How do you know it works?"**
- 31 backend tests against the real checkpoints, in every serving mode;
- the served pipeline re-scored on all 902 test videos (MLP 98.73% vs Colab 98.86% ROC-AUC);
- a live API round trip on a real and a fake video;
- a 4-thread concurrency test with identical scores.

**"What evidence supports your claimed results?"**
`artifacts/evaluations/`: `metrics.json` per run with commit and checkpoint hashes, cached per-video predictions, ROC/PR/confusion plots, and the Colab outputs in `hybrid_colab/`. Admit that the MLP's best epoch comes from the Colab cell output, not a saved file.

**"What happens if an important dependency fails?"**
- **Missing or corrupt checkpoint:** the app still starts, `/health` says `degraded`, and video jobs fail with "Model loading failed".
- **Invalid `DEEPFAKE_MODEL`, threshold or frame count:** the server refuses to start with a clear message.
- **OpenCV can't decode the file / no face / any unexpected error:** a `failed` record; the upload is always deleted.
- **The backend is down:** the frontend shows `Backend request failed`, but the navbar still says "Online" (D4).

**"What are the weakest parts?"**
- calibration (thresholds 0.88 and 0.9993);
- possible identity leakage between splits;
- 107 real test videos;
- an encoder fine-tuned on ~1,000 videos;
- placeholder modalities; no persistence or authentication; no frontend tests.

**"What are the limitations of the current results?"**
- one dataset family (Celeb-DF style), so cross-dataset generalization is untested;
- splits by file, not identity;
- uncalibrated probabilities;
- the Transformer's advantage (or lack of it) is only tested with sparse frames.

---

## H. Demonstration checklist

**Before the review (the day before):**

- [ ] Delete the `._*` files: `find . -name '._*' -not -path './frontend/node_modules/*' -delete`
- [ ] `cd backend && python -m pytest -q`. Expect `31 passed`.
- [ ] Pick 2–3 demo videos from `datasets/raw/` with visible faces. Include one from `Celeb-Youtube-fake` and one from `Celeb-real`.
- [ ] Copy the demo videos to the laptop's internal disk, in case the SanDisk drive is slow.
- [ ] Check that `frontend/.env.local` has `VITE_API_BASE_URL=http://127.0.0.1:8000` and `VITE_USE_MOCK_DATA=false`.
- [ ] Take screenshots of a completed dashboard and the frame inspector as a fallback.

**Live demo:**

1. **Terminal 1:** `cd backend && source .venv/bin/activate && python -m uvicorn app.main:app --reload`. Expect `Application startup complete`.
2. **Check:** `curl http://127.0.0.1:8000/health`. Expect `{"status":"ok",...}`.
3. **Terminal 2:** `cd frontend && npm run dev`. Open the printed URL (port 8080 on this machine).
4. **Analyze → upload the fake demo video.** Expect the processing screen, then the dashboard within about 1–2 s.
5. **Dashboard:** verdict and confidence → video player (your real video) → timeline → Suspicious Frames → open the inspector → drag the overlay slider.
6. **Repeat with the real video,** and point out the weak, diffuse heatmap.
7. **Report page:** use "Print" (optional).
8. **Show `/docs`** (Swagger) for the API contract.

Concurrent uploads are safe (they queue behind the inference lock), but each waits for the previous one, so upload one at a time for a smooth demo.

**Fallbacks:**

| Failure | Fallback |
| --- | --- |
| Backend won't start | Show `python -m pytest -q` output and the screenshots |
| Analysis stuck on processing | Restart the backend, then upload again (one at a time) |
| Frontend issue | `curl -F "file=@video.mp4;type=video/mp4" http://127.0.0.1:8000/api/v1/analyze`, then GET the record, then open the `heatmap_url` in the browser |
| "No detectable face" | Explain that it's a deliberate clean failure; use another video |
| Nothing works | `VITE_USE_MOCK_DATA=true npm run dev` shows the UI with fixtures; say clearly that it's mock data |

---

## I. Glossary

| Term | Simple explanation | In this project |
| --- | --- | --- |
| Deepfake | AI-generated or face-swapped media | Celeb-DF-style face swaps |
| CNN | Neural network that learns image filters | EfficientNet-B0 |
| Transfer learning | Start from weights trained on another task | `--pretrained` ImageNet weights |
| Logit | Raw model score before softmax | `logits[:, 1]` is the fake logit |
| Softmax | Turns logits into probabilities that sum to 1 | `torch.softmax(logits, 1)[:, 1]` |
| Threshold | Cut-off that turns a probability into a label | Stored in each head checkpoint (MLP 0.9993, Transformer 0.8795); baseline 0.3654; all tuned on validation |
| Calibration | Whether "80%" really means right 80% of the time | Not done; confidence is uncalibrated |
| ROC-AUC | Probability that a random fake scores above a random real; threshold-free | 98.86% (served MLP head) vs 88.13% (baseline) |
| PR-AUC | Area under the precision–recall curve; sensitive to imbalance | ≈ 0.97 (inflated by 88% positives) |
| Precision / recall | Of predicted fakes, how many are fake / of real fakes, how many were caught | 97% / 51–56% |
| Majority baseline | Always predict the most common class | 88.1% accuracy on the test split |
| Data leakage | Test information leaking into training | Prevented for duplicate files; identity leakage possible |
| Haar cascade | Classic fast face detector using rectangle features | `FaceCropper` |
| Grad-CAM | Heatmap from gradient-weighted activations | `_predict_with_gradcam` |
| Forward hook | Callback that runs when a layer produces output | Captures `features[-1]` activations |
| Eval mode | Disables dropout; BatchNorm uses stored statistics | `model.eval()` |
| ASGI | Python async web-server interface | Uvicorn runs FastAPI |
| 202 Accepted | "Received, processing later" HTTP status | `POST /api/v1/analyze` |
| CORS | Browser rule for cross-origin requests | Allows the frontend at `:8080` to call `:8000` |
| SSR / hydration | Server renders HTML; React then attaches in the browser | Why object URLs are read after mount |
| Magic bytes | File-type signature at the start of a file | `MAGIC_SIGNATURES` |
| Race condition | Result depends on thread timing | Defect D1, fixed with a lock |

---

## J. What to study before the review (by priority)

1. **Evaluation metrics under class imbalance.** Precision, recall, ROC-AUC, PR-AUC, confusion matrix, majority baseline, threshold selection. *Most likely to be questioned.*
2. **Grad-CAM.** The formula, why the last conv layer, why the logit, and its limits (coarse, not ground truth).
3. **CNN basics and EfficientNet.** Convolutions, depthwise separable convolutions, squeeze-and-excitation, compound scaling, transfer learning.
4. **Data leakage and splitting.** Why video-level, hash-level and identity-level splits matter.
5. **FastAPI request lifecycle.** Pydantic, `UploadFile`, `BackgroundTasks`, status codes 202/400/404/413/415/422.
6. **Concurrency basics.** Threads, shared state, locks, the race condition you found.
7. **React data flow.** Route loaders, React Query, SSR and hydration.
8. **Viola–Jones face detection** at a high level.
9. **Calibration** (temperature scaling, reliability diagrams).
10. **Transformers for sequences** (only if asked about the temporal model).

---

## K. Revision plan (3 days)

| Day | Morning | Afternoon | Evening |
| --- | --- | --- | --- |
| 1 | Read technical doc §1–5; trace `create_analysis` → `predict` in the code | Study metrics (J1), and redo the 404/11/96/391 confusion-matrix arithmetic by hand | Practise the 2-minute intro (A) aloud 3 times |
| 2 | Grad-CAM + EfficientNet (J2–J3); re-read `_predict_with_gradcam` | Answer E1–E22 aloud without looking | Run the full demo checklist (H) end to end |
| 3 | E23–E44 and the critical questions (G) | Section F: explain each code location from memory | Dry-run the 5-minute walkthrough (B); prepare the fallback screenshots |
