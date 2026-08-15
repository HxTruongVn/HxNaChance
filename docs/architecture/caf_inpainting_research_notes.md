# Research notes: Python inpainting backends

LaMa (Resolution-robust Large Mask Inpainting with Fourier Convolutions) uses fast Fourier convolutions for an image-wide receptive field, a high-receptive-field perceptual loss, and large training masks. The paper reports strong behavior on large missing areas, geometric structures and periodic textures, with generalization beyond training resolution. Source: https://arxiv.org/abs/2109.07161

The official LaMa repository provides pretrained inference, CPU/GPU Docker paths and an optional refinement pass. Its reference model is trained around 256px inputs but is documented as generalizing to roughly 2K resolution. Source: https://github.com/advimman/lama

MAT (Mask-Aware Transformer for Large Hole Image Inpainting) is the second candidate for large holes and photo-realistic completion. It combines transformer context with convolutional processing and explicitly models the mask. The project should treat MAT as a heavier optional backend, not as a Core dependency. Source: https://arxiv.org/abs/2203.15270

Inpainting quality should not be judged only with pixel metrics. A benchmark should combine masked-region reconstruction metrics on held-out ground truth, perceptual metrics such as LPIPS, structural/edge continuity checks, and human review/self-consistency because the real missing content is unknown in production. Source: https://arxiv.org/html/2405.16263v1

Recommended architecture: deterministic geometry and mask generation remain in Core/Workshop code; an optional neural backend performs semantic synthesis; OpenCV/Telea and edge extension remain explicit fallbacks with status labels and quality warnings. Model files must be declared as Core-managed resources and verified by SHA-256.
