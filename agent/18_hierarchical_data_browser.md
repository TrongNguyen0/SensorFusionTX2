# 18 - Hierarchical Data Browser

## Muc tieu

Dieu chinh Data Browser trong `src/app_pyqt.py` theo yeu cau UI:

- Man hinh dau cua Data Browser chi hien cac thu muc cap dau trong `data/`.
- Khi bam vao mot thu muc, UI moi hien cac thu muc/file ben trong.
- File anh duoc hien thi o khung ben trai.
- File JSON/text/markdown duoc hien thi o khung ben trai duoi dang text.

## Thay doi da thuc hien

- Them che do `Data` vao mode chinh cua PyQt UI.
- Them `data_preview_stack` gom:
  - `ImageView` cho anh.
  - `QPlainTextEdit` cho JSON/text.
- Thay Data Browser tu danh sach nut co dinh sang duyet thu muc dong.
- O cap `data/`, chi hien 3 thu muc dau theo thu tu sap xep:
  - `calibration_result`
  - `captured_data`
  - `fusion_output`
- Khi vao thu muc con, hien cac thu muc va file co dinh dang ho tro:
  - anh: `.png`, `.jpg`, `.jpeg`, `.bmp`
  - van ban: `.json`, `.txt`, `.md`
- Anh duoc doc bang ham unicode-safe `imread_unicode()` de tranh loi duong dan tieng Viet tren Windows.
- Anh depth 16-bit duoc chuyen sang colormap truoc khi preview.
- JSON duoc pretty-print voi `ensure_ascii=False` de giu tieng Viet neu co.

## Dieu chinh UI lan 2

Data Browser da duoc doi lai theo bo cuc thao tac ro rang hon:

- Phan tren cung la 3 nut nhom du lieu cap dau.
- Phan giua la danh sach noi dung cua nhom dang chon.
- Item trong danh sach co tien to:
  - `[Folder]` cho thu muc.
  - `[Image]` cho file anh.
  - `[Text]` cho JSON/text/markdown.
- Nut `Back to parent folder` chi quay ve cap thu muc cha trong vung du lieu dang duyet.
- `Previous` va `Next` chi dung cho tap anh trong thu muc hien tai.

Muc tieu cua lan sua nay la lam luong thao tac de nhin, khong thay doi thuat toan collect/compute/fusion.

## Dieu chinh UI lan 3

Sua loi trang thai khi duyet qua lai nhieu thu muc:

- Truoc do, khi dang xem mot anh, neu back ra roi vao thu muc khac, preview ben trai co the van giu anh/cu phap dieu huong cua thu muc truoc.
- Nguyen nhan: `populate_data_browser()` chi cap nhat danh sach ben phai, chua reset `data_files`, `data_index` va pixmap preview ben trai.
- Da them `ImageView.clear_image()` de xoa anh preview cu.
- Da them `reset_data_preview()` va goi moi khi mo/back sang thu muc moi.
- Nguyen tac moi:
  - Mo thu muc: chi hien danh sach noi dung, xoa preview cu.
  - Mo anh: moi nap danh sach anh cua dung thu muc do.
  - Mo JSON/text: hien text va xoa danh sach anh hien tai.

## Dieu chinh UI lan 4

Doi Data Browser tu kieu chon tung file sang kieu duyet theo thu muc:

- Danh sach giua chi hien `[Folder]`, khong hien tung file anh/json nua.
- Khi click vao mot thu muc co file preview, UI tu dong hien file dau tien hoac file co cung timestamp voi mau dang xem.
- `Previous` va `Next` la cach chuyen mau trong thu muc hien tai.
- Khi dang xem `color_<timestamp>.png`, neu Back ra va chon `depth` hoac `depth_colormap`, UI uu tien mo file co cung `<timestamp>`.
- Khoa dong bo mau duoc lay tu cum so cuoi trong ten file, vi cac file collect hien co dung chung timestamp:
  - `color_<timestamp>.png`
  - `depth_<timestamp>.png`
  - `depth_colormap_<timestamp>.png`
  - `pair_<timestamp>.json/.png`

## Dieu chinh UI lan 5

Chot lai Data Browser theo mo hinh nguon du lieu:

- Khong cho Data Browser di vao danh sach file rieng le trong thu muc.
- O cap nhom nhu `captured_data`, danh sach giua chi hien cac thu muc con:
  - `Color`
  - `Depth`
  - `Depth Colormap`
  - `Pair`
- Click vao thu muc con se cap nhat preview ben trai ngay, danh sach khong bien thanh danh sach file.
- Neu thu muc con co nhieu kieu preview cung timestamp, vi du `pair` co `.png` va `.json`, danh sach chuyen sang lua chon kieu:
  - `[Image] Preview image`
  - `[Text] JSON/Text`
- Khi doi giua `[Image]` va `[Text]`, UI uu tien giu cung timestamp dang xem.
- `Previous` va `Next` van la cach chuyen timestamp/mau trong nguon du lieu dang chon.
- Hanh vi nay ap dung tong quat cho cac thu muc khac neu co dong thoi anh va JSON/text.

## Kiem tra

Da chay:

```powershell
python -m py_compile src/app_pyqt.py
```

Ket qua: pass.

## Ghi chu

Chua launch GUI trong buoc nay. Can test bang thao tac thuc te:

1. Chay `python src/app_pyqt.py`.
2. Chuyen sang mode `Data`.
3. Bam mot trong ba thu muc cap dau.
4. Chon anh hoac JSON de kiem tra preview ben trai.
