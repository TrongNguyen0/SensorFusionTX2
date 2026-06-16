# 16 - Collect UI Unicode Image Save Fix

## Van de
Khi collect bang UI, file JSON duoc luu nhung anh color/depth/depth_colormap/pair co the khong duoc luu dung nhu collect_calibration.py cu.

## Nguyen nhan
Duong dan workspace co ky tu tieng Viet: F:\\Mon Hoc... / F:\\Môn Học... Tren Windows, cv2.imwrite co the fail khi path co Unicode. JSON van luu duoc vi Python open(..., encoding=utf-8) ho tro Unicode path tot hon.

## Da sua
Trong src/core/collect_core.py:
- Them imwrite_unicode(path, image).
- Ghi anh bang cv2.imencode(ext, image) roi encoded.tofile(path).
- Thay tat ca cv2.imwrite trong save_sample bang imwrite_unicode.

## Ket qua mong doi
UI collect khi Accept Sample se luu day du nhu collect cu:
- data/captured_data/color/color_<timestamp>.png
- data/captured_data/depth/depth_<timestamp>.png
- data/captured_data/depth_colormap/depth_colormap_<timestamp>.png
- data/captured_data/pair/pair_<timestamp>.png
- data/captured_data/pair/pair_<timestamp>.json

## Kiem chung
Da chay:
python -m py_compile src/core/collect_core.py src/app_pyqt.py

Ket qua: pass.

## Can test thuc te
Chay UI, collect mot sample moi, bam Accept Sample va kiem tra 5 file tren co du trong cac folder khong.
