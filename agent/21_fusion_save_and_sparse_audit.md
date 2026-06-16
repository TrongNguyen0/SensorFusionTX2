# 21 - Fusion Save And Sparse Audit

## Van de kiem tra

Nguoi dung bao:

- Fusion UI khong luu dung nhu mong muon.
- File output khong theo dang so thu tu `000000`.
- `depth_sparse` tren Fusion UI nhin den va chi co vai cham sang.
- Nghi ngo thuat toan fusion UI khac voi code cu.

## Ket qua kiem tra

### 1. Luu file fusion bi lech

`core/fusion_core.py` truoc do luu bang:

- `rgb_<timestamp>.png`
- `depth_dense_<timestamp>.png`
- `depth_sparse_<timestamp>.png`
- `fusion_<timestamp>.png`
- `metrics_<timestamp>.json`

Trong khi thu muc hien co lai dang co anh theo dang:

- `rgb/000000.png`
- `depth_dense/000000.png`
- `depth_sparse/000000.png`
- `fusion/000000.png`

Metrics cu ghi path timestamp, nhung anh timestamp khong co trong thu muc. Nguyen nhan quan trong: ham save dung `cv2.imwrite()` truc tiep voi duong dan co tieng Viet, co nguy co fail am tham tren Windows.

### 2. Da sua save fusion

Da sua `core/fusion_core.py`:

- Them `imwrite_unicode()` dung `cv2.imencode(...).tofile(...)`.
- Them `next_output_index()` de lay index tiep theo tu cac file numeric dang co.
- Save moi dung cung mot `frame_id`:
  - `rgb/000004.png`
  - `depth_dense/000004.png`
  - `depth_sparse/000004.png`
  - `fusion/000004.png`
  - `metrics/000004.json`
- Payload metrics co them:
  - `frame_id`
  - `sequence_index`

Da test save vao thu muc tam: pass, tat ca file anh va metrics deu duoc tao.

### 3. Depth sparse hien thi den va cham sang

Kiem tra file sparse hien co:

- shape `(480, 640)`, dtype `uint16`.
- nonzero pixels chi khoang 27-30 pixel/anh.
- ty le nonzero khoang `0.009%`.

Ket luan: neu hien raw sparse depth, anh den voi vai cham sang la dung ban chat sparse depth. Sparse depth chi chua cac diem LiDAR project vao anh, khong co bien/mang day nhu dense depth RealSense.

### 4. Thuat toan Fusion UI khac code cu

Co khac:

- `fusion_calibration.py` cu dua raw scan vao `process_scan()`.
- `app_pyqt.py` hien tai loc scan bang `filter_scan()`, gom buffer, roi `denoise_scans(..., FUSION_DENOISE_SCAN_COUNT=5)` truoc khi dua vao `process_scan()`.

Trong buoc nay chua thay doi thuat toan fusion UI, chi ghi nhan diem khac biet.

## Kiem tra

Da chay:

```powershell
python -m py_compile src/core/fusion_core.py src/app_pyqt.py
```

Ket qua: pass.
