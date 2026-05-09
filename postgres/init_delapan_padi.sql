CREATE USER admin_dp1 WITH PASSWORD 'password_rahasia';
CREATE DATABASE d_padi_db OWNER admin_dp1;

GRANT ALL PRIVILEGES ON DATABASE d_padi_db TO admin_dp1;

\c d_padi_db

CREATE TABLE IF NOT EXISTS fnb_inventory (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    quantity DECIMAL(10,2) DEFAULT 0.00,
    uom VARCHAR(20),
    cost_price DECIMAL(15,2) DEFAULT 0.00,
    min_stock DECIMAL(10,2) DEFAULT 0.00,
    stock_status VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS fnb_menu (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    image TEXT,
    price DECIMAL(15,2) DEFAULT 0.00,
    category VARCHAR(50),
    is_available BOOLEAN DEFAULT TRUE,
    description TEXT
);

CREATE TABLE IF NOT EXISTS fnb_recipe_line (
    id SERIAL PRIMARY KEY,
    menu_id INT REFERENCES fnb_menu(id) ON DELETE CASCADE,
    inventory_id INT REFERENCES fnb_inventory(id) ON DELETE CASCADE,
    uom VARCHAR(20),
    quantity DECIMAL(10,2) DEFAULT 0.00
);

CREATE TABLE IF NOT EXISTS fnb_order (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    customer_name VARCHAR(100),
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_amount DECIMAL(15,2) DEFAULT 0.00,
    status VARCHAR(50),
    payment_status VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS fnb_order_line (
    id SERIAL PRIMARY KEY,
    order_id INT REFERENCES fnb_order(id) ON DELETE CASCADE,
    menu_id INT REFERENCES fnb_menu(id) ON DELETE CASCADE,
    price_unit DECIMAL(15,2) DEFAULT 0.00,
    quantity DECIMAL(10,2) DEFAULT 1.00,
    subtotal DECIMAL(15,2) DEFAULT 0.00
);

CREATE TABLE IF NOT EXISTS fnb_payment (
    id SERIAL PRIMARY KEY,
    order_id INT REFERENCES fnb_order(id) ON DELETE CASCADE,
    amount DECIMAL(15,2) DEFAULT 0.00,
    payment_method VARCHAR(50),
    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reference_number VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS fnb_table (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    capacity INT DEFAULT 1,
    location VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS fnb_reservation (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    customer_name VARCHAR(100),
    customer_phone VARCHAR(20),
    date_start TIMESTAMP,
    date_stop TIMESTAMP,
    table_id INT REFERENCES fnb_table(id) ON DELETE SET NULL,
    number_of_people INT DEFAULT 1,
    status VARCHAR(50),
    note TEXT
);



-- Tabel Role (Menyimpan daftar peran: Kasir, Pelayan, Manajer, dll)
CREATE TABLE IF NOT EXISTS role_karyawan (
    id_role SERIAL PRIMARY KEY,
    nama_role VARCHAR(50) UNIQUE NOT NULL,
    deskripsi TEXT
);


CREATE TABLE IF NOT EXISTS modul_aplikasi (
    id_modul SERIAL PRIMARY KEY,
    nama_modul VARCHAR(50) UNIQUE NOT NULL
);

-- Tabel Hak Akses (Memetakan Role ke Modul beserta Tingkat Aksesnya)
CREATE TABLE IF NOT EXISTS hak_akses_role (
    id_hak_akses SERIAL PRIMARY KEY,
    id_role INT REFERENCES role_karyawan(id_role) ON DELETE CASCADE,
    id_modul INT REFERENCES modul_aplikasi(id_modul) ON DELETE CASCADE,
    tingkat_akses VARCHAR(20) NOT NULL, -- Contoh: 'Blank', 'User', 'Administrator'
    UNIQUE(id_role, id_modul) -- Memastikan 1 role hanya punya 1 aturan per modul
);

CREATE TABLE IF NOT EXISTS karyawan (
    id SERIAL PRIMARY KEY,
    nama VARCHAR(100) NOT NULL

);

ALTER TABLE karyawan 
ADD COLUMN IF NOT EXISTS username VARCHAR(50) UNIQUE,
ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255), -- Menyimpan password yang sudah dienkripsi
ADD COLUMN IF NOT EXISTS id_role INT REFERENCES role_karyawan(id_role),
ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE, -- Untuk blokir akun jika karyawan resign
ADD COLUMN IF NOT EXISTS last_login TIMESTAMP;


-- 1. Relasi antara Pesanan (fnb_order) dengan Meja (fnb_table)
ALTER TABLE fnb_order ADD COLUMN IF NOT EXISTS table_id INT REFERENCES fnb_table(id) ON DELETE SET NULL;

-- 2. Relasi Audit / Tracking Karyawan (Accountability)
ALTER TABLE fnb_order ADD COLUMN IF NOT EXISTS karyawan_id INT REFERENCES karyawan(id) ON DELETE SET NULL;
ALTER TABLE fnb_reservation ADD COLUMN IF NOT EXISTS karyawan_id INT REFERENCES karyawan(id) ON DELETE SET NULL;
ALTER TABLE fnb_payment ADD COLUMN IF NOT EXISTS karyawan_id INT REFERENCES karyawan(id) ON DELETE SET NULL;

-- 3. Tabel Komplain Pelanggan
CREATE TABLE IF NOT EXISTS fnb_complaint (
    id SERIAL PRIMARY KEY,
    customer_name VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    urgency_level VARCHAR(20), -- Contoh: 'Low', 'Medium', 'High'
    status VARCHAR(50), -- Contoh: 'Open', 'In Progress', 'Resolved', 'Closed'
    karyawan_id INT REFERENCES karyawan(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);