import matplotlib.pyplot as plt
import numpy as np

# --- 1. Dữ liệu từ bảng tính toán ---
# Độ rộng kênh W (đơn vị: nm)
W_nm = np.array([120, 500, 1000, 1500, 2000])

# Điện trở Ron của NMOS (đơn vị: kOhm)
# Các giá trị tương ứng: 12.34, 2.94, 1.47, 0.98, 0.73
#Ron_NMOS = np.array([12.34, 2.94, 1.47, 0.98, 0.73])
Ron_NMOS = np.array([12.339, 2.942, 1.468, 0.979, 0.734])
# Điện trở Ron của PMOS (đơn vị: kOhm)
# Các giá trị tương ứng: 29.33, 6.72, 3.34, 2.22, 1.66
#Ron_PMOS = np.array([29.33, 6.72, 3.34, 2.22, 1.66])
Ron_PMOS = np.array([29.332, 6.719, 3.336, 2.218, 1.668 ])
# --- 2. Thiết lập biểu đồ ---
plt.figure(figsize=(10, 6))  # Kích thước hình (ngang, dọc)

# Vẽ đường Ron cho NMOS (Màu xanh dương, marker hình tròn)
plt.plot(W_nm, Ron_NMOS, marker='o', linestyle='-', color='green', label='$R_{on}$ (NMOS)', linewidth=2)

# Vẽ đường Ron cho PMOS (Màu đỏ, marker hình vuông)
plt.plot(W_nm, Ron_PMOS, marker='s', linestyle='--', color='orange', label='$R_{on}$ (PMOS)', linewidth=2)

# --- 3. Trang trí biểu đồ ---
plt.title('Sự phụ thuộc của điện trở dẫn ($R_{on}$) vào độ rộng kênh ($W$)', fontsize=14, fontweight='bold')
plt.xlabel('Độ rộng kênh W (nm)', fontsize=12)
plt.ylabel('Điện trở dẫn $R_{on}$ ($k\Omega$)', fontsize=12)
plt.grid(True, linestyle='--', alpha=0.7)  # Hiển thị lưới mờ
plt.legend(fontsize=12)  # Hiển thị chú thích
plt.xticks(W_nm)  # Đảm bảo trục hoành hiện đúng các giá trị W

# --- 4. Hiển thị giá trị lên từng điểm ---
for i, txt in enumerate(Ron_NMOS):
    plt.annotate(f'{txt}', (W_nm[i], Ron_NMOS[i]), textcoords="offset points", 
                 xytext=(0, -15), ha='center', color='blue', fontsize=10)

for i, txt in enumerate(Ron_PMOS):
    plt.annotate(f'{txt}', (W_nm[i], Ron_PMOS[i]), textcoords="offset points", 
                 xytext=(0, 10), ha='center', color='red', fontsize=10)

# --- 5. Xuất hình ảnh ---
plt.tight_layout()
plt.show()