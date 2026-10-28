# Mean-pool MLP head: training note

**Source:** Colab (T4) cell output, run on 2026-10-28. These values were printed during training but
not saved in the checkpoint (`models/deepfake_shield_meanpool_mlp_v1.pt` has no `best_epoch` key)
or in `history.csv`, which records the Transformer run only.

- Best epoch: **75** of 100
- Inner-val ROC-AUC at the best epoch: **0.9797**

Training config (shared with the Transformer head, as stored in both checkpoints' `config`):

- 100 epochs, no early stopping (`patience=100`); the kept checkpoint is the epoch with the best
  inner-val ROC-AUC
- Inner-val: 15% of train; val split used only to tune the threshold (Youden's J); test only for reporting
- AdamW, lr 3e-4, weight decay 1e-2, batch 64, cosine LR schedule
- Frame dropout 0.25, class-weighted cross-entropy, seed 42
- Head: masked mean of 16 × 1280-d embeddings → LayerNorm → Linear(1280→256) → GELU → Dropout(0.2) → Linear(256→2)
- Stored threshold: 0.9993 (Youden's J on val)
