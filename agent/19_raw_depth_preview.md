# 19 - Raw Depth Preview

## Van de

Trong Data Browser va Fusion UI, raw depth dang bi hien thi giong colormap:

- `data/captured_data/depth/*.png` la depth tho 16-bit.
- `data/fusion_output/depth_sparse/*.png` la sparse depth 16-bit.
- Tuy nhien ham preview trong UI dang apply `COLORMAP_JET` cho moi anh 2D, lam nguoi dung nham voi `depth_colormap`.

## Xac minh du lieu

Da kiem tra bang `cv2.imdecode(..., IMREAD_UNCHANGED)`:

- `captured_data/depth/depth_*.png`: shape `(480, 640)`, dtype `uint16`.
- `captured_data/depth_colormap/depth_colormap_*.png`: shape `(480, 640, 3)`, dtype `uint8`.
- `fusion_output/depth_sparse/*.png`: shape `(480, 640)`, dtype `uint16`.

Ket luan: file luu dung. Loi nam o cach preview trong UI.

## Thay doi

- `prepare_image_for_display()` khong con apply `COLORMAP_JET` cho anh 2D.
- Anh 2D/raw depth duoc scale ve 8-bit va chuyen sang grayscale BGR de QLabel hien thi duoc.
- `depth_colormap` van hien thi mau vi ban than file da la anh 3 kenh.
- Fusion panel `Sparse LiDAR Depth` hien thi tu `sparse_depth` raw bang grayscale preview, khong dung `sparse_cm` colormap nua.

## Kiem tra

Da chay:

```powershell
python -m py_compile src/app_pyqt.py
```

Ket qua: pass.
