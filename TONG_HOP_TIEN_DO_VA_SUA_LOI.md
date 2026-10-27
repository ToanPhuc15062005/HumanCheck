# BAO CAO TONG HOP TIEN DO VA DANH SACH LOI DA XU LY
DU AN: HUMANCHECK - HE THONG GIAM SAT THONG MINH VA DEM NGUOI QUA LAI (PURE DIP)
MON HOC: XU LY ANH - PTIT HCM
GIANG VIEN PHU TRACH: TS. HUYNH TRUNG TRU

---

## I. TONG QUAN CAC HANG MUC DA HOAN THANH

Trong phien lam viec nay, he thong da duoc ra soat toan dien, mo rong kien truc phan mem, tai thiet ke giao dien nguoi dung theo chuan toi gian cao cap va dong goi source code len GitHub repository ca nhan.

Chi tiet cac hang muc da hoan thanh bao gom:

### 1. Ra soat tien do va danh gia chat luong de tai
- Kiem tra toan bo kien truc 3 module thuat toan Pure DIP (Digital Image Processing) khong dung Deep Learning:
  + Module 1: Pipeline thi giac, phan doan dang nguoi theo Spatial Moments va ty le khung bao (Height/Width >= 0.85), bo theo doi Centroid Tracker (khoang cach Euclidean), may trang thai dong Hysteresis State Machine chong dem lap.
  + Module 2: Giai tich hinh hoc vach ao, bo cau hinh tuong tac chuot Calibrator, luu tru file JSON.
  + Module 3: Bo thich ung moi truong 5 tru cot gom: Fast Background Reset khi doi sang dot ngot, keo sang thich ung Gamma ket hop CLAHE ban dem, khu bong do nguoi trong khong gian HSV, khu rung lac bang phep toan hinh thai hoc Morphological Opening, va co che dong hoa do vat vao nen (Background Absorption).
- Kiem thu tu dong toan bo he thong voi bo test suite: 12/12 unit tests va integration tests deu dat ket qua Passed tuyet doi.

### 2. Nang cap giao dien Streamlit Demo
- Tich hop cong cu Interactive Camera Overlay cho phep nguoi dung ve truc tiep vach ranh gioi phan cach tren khung hinh camera.
- Ho tro 2 che do tuong tac:
  + Keo va tha chuot (Drag and Drop Line).
  + Click lan luot 2 diem A va B.
- Hien thi truc quan tren frame: Diem moc A va B kem toa do, duong ranh gioi mau tuong phan cao, mui ten chi huong Vao (IN) vuong goc voi vach, va 2 duong bien bieu thi vung dem an toan Hysteresis (+/- d px).
- Dong bo 2 chieu tu dong voi cac o nhap so tai Sidebar va tu dong cap nhat vao file tripwire_config.json.
- Bo sung tinh nang xuat du lieu nhat ky cac luot cat vach ra file CSV (Export CSV).

### 3. Tai thiet ke toan bo Frontend sang nen tang React (Swiss Luxury Suite)
- Khoi tao va xay dung frontend doc lap bang Vite + React trong thu muc frontend/.
- Loai bo 100% cac emoji va ky tu bieu cam tren toan bo giao dien, thay the dong nhat bang thu vien Lucide-React icons.
- Thiet ke theo triet ly toi gian Swiss Luxury Spa:
  + Bang mau don nhat: Nen den quang hoc Obsidian (#090A0C), cac khoi giao dien phien da Slate (#101216), vien sieu mong 1px (rgba(255, 255, 255, 0.07)), chu mau Titan (#F8FAFC) va Platinum (#94A3B8).
  + Khong gian bo tri chuan luoi 8pt, can doi khoang cach le va dem, loai bo hoan toan khoang trong thua hoac cam giac chen chuc.
  + He thong kieu chu Inter va JetBrains Mono cho cac thong so ky thuat.
- Tich hop cac chuc nang tren Web Frontend:
  + Xem truc tiep 2 luong video MJPEG: Luong camera kem hop bao/HUD va luong mat na tien canh sach (Module 3).
  + 4 the chi so KPI chinh: So luong khach trong phong (Interior Occupancy), Luot vao (Ingress), Luot ra (Egress), va Toc do xu ly thuc te (Throughput FPS).
  + Ket noi WebSocket thoi gian thuc tan so 10Hz voi backend FastAPI de dong bo trang thai khong do tre.
  + Bang nhat ky luot nguoi (Transit Audit Log) kem nut xuat file CSV.
  + Bo tinh chinh tham so vung dem an toan Hysteresis.
- Tich hop he thong:
  + Bo sung che do khoi chay run.py --mode=frontend (chay Vite dev server tai cong 5173).
  + Mount truc tiep ban build production cua React (frontend/dist) vao FastAPI server, cho phep nguoi dung truy cap toan bo he thong chi qua 1 cong duy nhat (http://localhost:8000).

### 4. Bo sung nut dieu khien Start va Pause cho luong video
- Backend:
  + Bo sung co trang thai is_paused trong lop VideoSurveillanceService.
  + Bo sung 3 endpoint REST API: POST /api/v1/stream/play, POST /api/v1/stream/pause, va POST /api/v1/stream/toggle.
  + Worker thread tam dung doc frame moi khi pause nhung van duy tri frame hien tai de luong MJPEG khong bi ngat ket noi.
  + Cap nhat WebSocket va /api/v1/stats de broadcast trang thai is_paused cho moi client.
- Frontend:
  + Bo sung nut Start/Pause tren ca thanh Header chinh va thanh cong cu cua khung hinh camera.
  + Hien thi huy hieu Stream Paused noi tren video khi dang tam dung.
  + Cap nhat trang thai vien tin hieu thanh Engine Paused.

### 5. Dong goi ma nguon va Push len GitHub ca nhan
- Khoi tao Git repository cho toan bo du an.
- Thiet lap file .gitignore chuan de loai tru moi truong ao (.venv), thu vien Node (node_modules), cache Python (__pycache__) va cac file build tam.
- Commit toan bo ma nguon voi thong diep chuan.
- Lien ket remote repository: https://github.com/ToanPhuc15062005/HumanCheck.git.
- Xu ly xung dot rebase voi commit mac dinh tren remote va push toan bo nhanh main thanh cong.

---

## II. DANH SACH CAC LOI (BUGS) DA DUOC PHAT HIEN VA SUA CHUA TRIET DE

Trong qua trinh phat trien va tinh chinh theo phan hoi cua nguoi dung, cac van de ky thuat sau da duoc phan tich nguyen nhan goc re va xu ly hoan tat:

### 1. Loi nhan tren video qua to, che khuat khung hinh
- Hien tuong: Khung hinh video goc co do phan giai 320x240 pixel. Ham ve HUD cu trong visualizer.py ve mot hinh chu nhat mau den co kich thuoc 330x135 pixel voi co chu 0.7 o goc tren ben trai, che mat hon 50% dien tich video. Hop bao Bounding Box co chieu cao badge 22 pixel va dong chu phu ben duoi lam roi mat.
- Nguyen nhan: Cac tham so ve duoc thiet lap co dinh cho video do phan giai lon, khong tu dong co gian theo video 320x240.
- Giai phap da sua:
  + Trong core/module1_tracking/visualizer.py, thay the toan bo khoi HUD 330x135 bang thanh Micro-HUD nho gon cao 18 pixel, font scale giam xuong 0.30 o mep tren.
  + Thu nho chieu cao badge tren dau hop bao tu 22 pixel xuong 13 pixel, font scale giam con 0.30, hien thi ma ngan gon dang #ID.
  + Loai bo dong chu phu dai dong ben duoi chan doi tuong.
  + Thu nho font chu nhan vach tripwire ve 0.32.
  + Ket qua: Khung hinh video tro nen thong thoang, quan sat ro rang tung doi tuong di chuyen.

### 2. Kich thuoc website qua to (yeu cau ty le 75%)
- Hien tuong: Giao dien mac dinh o muc zoom 100% chiem nhieu dien tich man hinh, nguoi dung phai cuon trang de xem bang so lieu va camera.
- Giai phap da sua:
  + Thiet lap thuoc tinh CSS zoom: 0.75 tren the html trong frontend/src/index.css.
  + Dieu chinh lai ty le dem (padding) va khoang cach giua cac panel.
  + Ket qua: Toan bo dashboard hien thi vua van tren mot man hinh tieu chuan ma khong can cuon trang, dat mat do thong tin cao theo dung phong cach executive dashboard.

### 3. Loi chuc nang keo tha vach bi chap chon (Flickering / Rubberbanding)
- Hien tuong: Khi nguoi dung dung chuot keo duong ranh gioi moi, net ve vua tha ra thi bi giat nguoc ve vi vi tri cu roi moi nhay sang vi tri moi, tao cam giac chap chon khong on dinh.
- Nguyen nhan goc re: Luong WebSocket tu FastAPI server phat du lieu telemetry lien tuc 10 lan moi giay (10Hz). Trong goi tin co chua toa do tripwire hien tai cua server. Khi nguoi dung vua ket thuc thao tac keo, ham lang nghe WebSocket tren client lap tuc nhan toa do cu (do server chua kip luu request POST vua gui) va ghi de nguoc tro lai state currentLine cua React, dan den xung dot giua du lieu dang ve va du lieu tu server.
- Giai phap da sua:
  + Tao bo dem thoi gian va co kiem soat: lastEditTimeRef va isDraggingRef trong App.jsx.
  + Khi nguoi dung bat dau keo hoac vua keo xong trong vong 2.5 giay, WebSocket bi chan (debounce) khong duoc phep ghi de toa do vach.
  + Ket qua: Triet tieu 100% hien tuong vach bi giat hoac nhay nguoc ve vi tri cu.

### 4. Loi keo tha vach bi dinh chuot (Sticky Dragging)
- Hien tuong: Khi keo nhanh chuot hoac con tro chuot di chuyen ra khoi pham vi khung hinh canvas, chuc nang keo bi ket cung. Khi dua chuot quay lai man hinh thi net ve van tiep tuc bi dinh theo con tro du nguoi dung da nha nut chuot tu truoc.
- Nguyen nhan goc re gom 3 yeu to:
  + Yeu to 1: Su kien onMouseUp truoc day chi duoc gan cuc bo tren phan tu canvas. Khi chuot di chuyen vuot qua mep canvas, su kien nha chuot bi trinh duyet bo qua, lam co isDragging van giu gia tri true.
  + Yeu to 2: Trinh duyet kich hoat tinh nang keo anh mac dinh (HTML5 Native Drag) tren the img cua luong MJPEG nam ben duoi, tao ra bong ma cua anh va khoa chat con tro chuot.
  + Yeu to 3: Khi website duoc ap dung CSS zoom: 0.75, phep tinh toa do cu (e.clientX - rect.left) * (320 / canvas.width) bi lech do su khac biet giua toa do vat ly tren man hinh va toa do logic cua phan tu.
- Giai phap da sua:
  + Chuyen sang Pointer Events API (handlePointerDown) va dang ky su kien di chuyen/nha chuot toan cuc tren doi tuong window (window.addEventListener('pointermove'), window.addEventListener('pointerup'), window.addEventListener('pointercancel')). Dui nguoi dung nha chuot o bat ky dau tren man hinh hay ngoai cua so trinh duyet, thao tac keo deu duoc giai phong sach se va huy bo listener.
  + Khoa tinh nang keo anh mac dinh tren the img bang CSS: pointer-events: none, user-select: none, -webkit-user-drag: none.
  + Ap dung cong thuc tinh toa do chuan hoa theo ty le phan tram hop bao truc quan:
    nx = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width))
    ny = Math.max(0, Math.min(1, (clientY - rect.top) / rect.height))
    x = Math.round(nx * 320)
    y = Math.round(ny * 240)
    Cong thuc nay mien nhiem hoan toan voi moi muc zoom, do phan giai man hinh hay ty le DPI.
  + Ket qua: Thao tac keo tha tro nen muot ma, bat dinh chinh xac tuyet doi va khong bao gio con hien tuong dinh chuot.

---

## III. HUONG DAN VAN HANH VA KIEM TRA NHANH

Nguoi dung co the kiem tra lai toan bo cac chuc nang bang cac lenh sau:

### 1. Khoi chay Web Frontend React (Khuyen dung)
Mo terminal tai thu muc HumanCheck va chay:
python run.py --mode=frontend

Truy cap: http://localhost:5173

### 2. Khoi chay may chu FastAPI san xuat (Tich hop ca API va Frontend)
python run.py --mode=api

Truy cap: http://localhost:8000

### 3. Kiem tra tinh nang keo vach
- Bam nut "Calibrate Line" tren thanh cong cu.
- Nhan giu chuot tai diem bat dau tren khung hinh camera, keo den diem ket thuc va nha chuot.
- Vach moi se duoc cap nhat ngay lap tuc tren ca video va backend ma khong bi giat hay dinh chuot.
- Bam nut "Pause Stream" de tam dung xu ly video va "Start Stream" de tiep tuc.

### 4. Kiem tra kho luu tru GitHub
Toan bo du an da duoc cap nhat day du tai:
https://github.com/ToanPhuc15062005/HumanCheck
