from flask import Flask, render_template, request, jsonify
import json
import os
from datetime import datetime
from collections import defaultdict

app = Flask(__name__)

DATA_FILE = 'data_penjualan.json'

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}

    with open(DATA_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def load_pengeluaran():
    try:
        with open('data_penjualan.json', 'r') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

    hasil = []
    for tanggal, transaksi in data.items():
        for p in transaksi.get("pengeluaran", []):
            p = p.copy()
            p['tanggal'] = tanggal
            hasil.append(p)
    return hasil

@app.route('/')
def index():
    data = load_data()
    today = datetime.now().strftime('%Y-%m-%d')

    penjualan = []
    pengeluaran = []

    if today in data:
        if isinstance(data[today], dict):
            penjualan = data[today].get('penjualan', [])
            pengeluaran = data[today].get('pengeluaran', [])
        elif isinstance(data[today], list):  # data lama (penjualan saja)
            penjualan = data[today]

    total_penjualan = sum(item.get('total', 0) for item in penjualan)
    total_pengeluaran = sum(item.get('jumlah', 0) for item in pengeluaran)
    total_transaksi = len(penjualan)
    keuntungan_bersih = total_penjualan - total_pengeluaran

    return render_template(
        'index.html',
        penjualan=penjualan,
        pengeluaran=pengeluaran,
        total_transaksi=total_transaksi,
        total_penjualan=total_penjualan,
        total_pengeluaran=total_pengeluaran,
        keuntungan_bersih=keuntungan_bersih
    )

@app.route('/tambah', methods=['POST'])
def tambah_transaksi():
    data = load_data()

    # Jika data bukan dictionary (misalnya list atau corrupt), reset ke dict kosong
    if not isinstance(data, dict):
        data = {}

    today = datetime.now().strftime('%Y-%m-%d')
    jam = datetime.now().strftime('%H:%M')

    # Ambil data dari form
    barang = request.form.get('barang')
    jumlah = int(request.form.get('jumlah', 1))
    harga = int(request.form.get('harga', 0))
    total = jumlah * harga

    # Siapkan data item
    item = {
        'waktu': jam,
        'barang': barang,
        'jumlah': jumlah,
        'harga': harga,
        'total': total
    }

    # Pastikan struktur data harian valid
    if today not in data or not isinstance(data[today], dict):
        data[today] = {
            "penjualan": [],
            "pengeluaran": []
        }

    # Pastikan key 'penjualan' ada
    if "penjualan" not in data[today] or not isinstance(data[today]["penjualan"], list):
        data[today]["penjualan"] = []

    # Tambahkan item penjualan
    data[today]["penjualan"].append(item)

    # Simpan data ke file
    save_data(data)

    return jsonify({'status': 'success'})

@app.route('/pengeluaran', methods=['POST'])
def tambah_pengeluaran():
    data = load_data()
    today = datetime.now().strftime('%Y-%m-%d')
    jam = datetime.now().strftime('%H:%M')

    keterangan = request.form['keterangan']
    jumlah = int(request.form['jumlah'])

    item = {
        'waktu': jam,
        'keterangan': keterangan,
        'jumlah': jumlah
    }

    if today not in data or isinstance(data[today], list):
        data[today] = {
            "penjualan": data.get(today, []) if isinstance(data.get(today), list) else [],
            "pengeluaran": []
        }

    data[today]["pengeluaran"].append(item)
    save_data(data)
    return jsonify({'status': 'success'})


@app.route('/riwayat')
def riwayat():
    data = load_data()
    riwayat_data = {}

    for tanggal, isi in data.items():
        if isinstance(isi, dict):
            penjualan = isi.get("penjualan", [])
            pengeluaran = isi.get("pengeluaran", [])
        else:
            # format lama hanya penjualan langsung
            penjualan = isi
            pengeluaran = []

        riwayat_data[tanggal] = {
            "penjualan": penjualan,
            "pengeluaran": pengeluaran
        }

    return render_template('riwayat.html', riwayat=riwayat_data)

@app.route('/statistik')
def statistik():
    data = load_data()
    filter = request.args.get('filter', 'bulan')

    now = datetime.now()
    tahun_str = now.strftime('%Y')
    bulan_str = now.strftime('%Y-%m')

    total_penjualan = 0
    total_pengeluaran = 0
    total_transaksi = 0
    penjualan_per_hari = defaultdict(int)

    for tanggal, catatan in data.items():
        if not isinstance(catatan, dict):
            continue  # skip format lama

        if filter == 'tahun' and not tanggal.startswith(tahun_str):
            continue
        elif filter == 'bulan' and not tanggal.startswith(bulan_str):
            continue
        elif filter == 'semua':
            pass

        penjualan = catatan.get('penjualan', [])
        pengeluaran = catatan.get('pengeluaran', [])

        total_penjualan += sum(item.get('total', 0) for item in penjualan)
        total_pengeluaran += sum(item.get('jumlah', 0) for item in pengeluaran)
        total_transaksi += len(penjualan)

        penjualan_per_hari[tanggal] += sum(item.get('total', 0) for item in penjualan)

    keuntungan_bersih = total_penjualan - total_pengeluaran

    # urutkan tanggalnya
    tanggal_urut = sorted(penjualan_per_hari)
    labels = tanggal_urut
    values = [penjualan_per_hari[t] for t in tanggal_urut]

    return render_template(
        'statistik.html',
        total_penjualan=total_penjualan,
        total_pengeluaran=total_pengeluaran,
        total_transaksi=total_transaksi,
        keuntungan_bersih=keuntungan_bersih,
        bulan=now.strftime('%B %Y'),
        tahun=tahun_str,
        filter=filter,
        labels=labels,
        values=values
    )

if __name__ == '__main__':
    app.run(debug=True)
