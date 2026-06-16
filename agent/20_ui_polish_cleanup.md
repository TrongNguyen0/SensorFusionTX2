# 20 - UI Polish And Cleanup

## Muc tieu

Lam UI PyQt gon, ro thao tac hon va don code du thua sau nhieu vong sua Data Browser.

## Thay doi giao dien

- Them stylesheet chung cho app:
  - nen sang hon;
  - nut bam co hover/pressed/disabled state;
  - `QGroupBox`, `QListWidget`, `QPlainTextEdit` co border va spacing thong nhat;
  - khung preview anh co nen toi va vien ro.
- Data Browser duoc don lai:
  - section `1. Data group`;
  - section `2. Source folder`;
  - nut `Back` ngan gon;
  - danh sach source hien ten thu muc truc tiep, khong hien tien to ky thuat nhu `[Folder]`.
- Cum `path + Back + source list` duoc boc trong frame rieng de tach ro khoi cac nut group va nut Previous/Next.
- Lua chon trong thu muc co nhieu kieu preview duoc doi thanh:
  - `Preview Image`;
  - `JSON / Text`.
- Data preview mac dinh hien thong diep ngan, khong con noi dung nham voi chon file rieng le.

## Don code

- Bo import `render_sparse_depth` khoi `app_pyqt.py` vi Sparse Depth UI hien raw grayscale bang `prepare_image_for_display()`.
- Rut signal `FusionWorker.frame_ready` tu 7 tham so xuong 6 tham so, bo `sparse_cm`.
- Xoa logic file-browser cu:
  - `open_data_path()`;
  - `selected_file`;
  - cac bien trang thai khong con dung: `data_current_dir`, `data_selected_folder`, `data_view_kind`.
- Gom dinh dang file preview thanh constants:
  - `IMAGE_EXTS`;
  - `TEXT_EXTS`.

## Kiem tra

Da chay:

```powershell
python -m py_compile src/app_pyqt.py
```

Ket qua: pass.

Da ra soat khong con cac tham chieu cu:

- `open_data_path`
- `selected_file`
- `render_sparse_depth`
- `sparse_cm`
- tien to list cu `[Folder]`, `[Image]`, `[Text]`
