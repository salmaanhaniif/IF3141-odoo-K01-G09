CREATE USER admin_dp WITH PASSWORD 'password_rahasia';
CREATE DATABASE delapan_padi_db OWNER admin_dp;

GRANT ALL PRIVILEGES ON DATABASE delapan_padi_db TO admin_dp;

\c delapan_padi_db

-- Tabel Karyawan 
CREATE TABLE karyawan (
    id_karyawan SERIAL PRIMARY KEY,
    nama VARCHAR(100) NOT NULL,
    role VARCHAR(50) NOT NULL, 
    kontak VARCHAR(15)
);

-- Tabel Bahan Baku
CREATE TABLE bahan_baku (
    id_bahan SERIAL PRIMARY KEY,
    kode_bahan VARCHAR(20) UNIQUE NOT NULL,
    nama_bahan VARCHAR(100) NOT NULL,
    kategori VARCHAR(50),
    stok DECIMAL(10,2) DEFAULT 0.00,
    satuan VARCHAR(20),
    harga_satuan DECIMAL(15,2)
);

-- Tabel Reservasi 
CREATE TABLE reservasi (
    id_reservasi SERIAL PRIMARY KEY,
    nama_pelanggan VARCHAR(100) NOT NULL,
    kontak_pelanggan VARCHAR(15),
    waktu_reservasi TIMESTAMP NOT NULL,
    jumlah_tamu INT NOT NULL,
    nomor_meja VARCHAR(10),
    status VARCHAR(20) DEFAULT 'Pending', 
    id_karyawan INT REFERENCES karyawan(id_karyawan)
);

-- Tabel Komplain 
CREATE TABLE komplain (
    id_komplain SERIAL PRIMARY KEY,
    nama_pelanggan VARCHAR(100) NOT NULL,
    deskripsi_komplain TEXT NOT NULL,
    tingkat_urgensi VARCHAR(20) NOT NULL, 
    status_penyelesaian VARCHAR(20) DEFAULT 'Open', 
    kompensasi_diberikan TEXT,
    id_manajer INT REFERENCES karyawan(id_karyawan),
    waktu_komplain TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabel Master Menu
CREATE TABLE master_menu (
    id_menu SERIAL PRIMARY KEY,
    nama_menu VARCHAR(100) NOT NULL,
    kategori VARCHAR(50),
    harga DECIMAL(15,2) NOT NULL,
    status_tersedia BOOLEAN DEFAULT TRUE
);

-- Tabel Pesanan
CREATE TABLE pesanan (
    id_pesanan SERIAL PRIMARY KEY,
    nomor_meja VARCHAR(10) NOT NULL,
    total_tagihan DECIMAL(15,2) DEFAULT 0.00,
    status_pesanan VARCHAR(20) DEFAULT 'Draft', 
    metode_pembayaran VARCHAR(50), 
    waktu_pesanan TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    id_karyawan INT REFERENCES karyawan(id_karyawan)
);