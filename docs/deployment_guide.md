Dokumen ini berisi panduan untuk menjalankan project Distributed Synchronization System. Project ini dapat dijalankan menggunakan Docker Compose atau secara lokal menggunakan beberapa terminal.

Cara yang paling direkomendasikan adalah menggunakan Docker Compose karena Redis, node1, node2, dan node3 dapat dijalankan sekaligus.

---

## 1. Prerequisites

Sebelum menjalankan project, pastikan perangkat sudah memiliki beberapa tools berikut:

- Python 3.8 atau versi lebih baru
- Docker
- Docker Compose
- Git
- Terminal atau PowerShell

Untuk mengecek versi tools, jalankan command berikut:

```bash
python --version
docker --version
docker compose version
git --version
```

Jika semua command berhasil menampilkan versi, berarti environment sudah siap digunakan.

---

## 2. Menjalankan Project dengan Docker Compose

Docker Compose digunakan untuk menjalankan semua service dalam project secara bersamaan.

Service yang dijalankan:

- Redis
- node1
- node2
- node3

Masuk ke root folder project:

```bash
cd distributed-sync-system
```

Lalu jalankan command berikut:

```bash
docker compose -f docker/docker-compose.yml up --build
```

Command tersebut akan melakukan proses build image untuk node dan menjalankan semua container.

Jika berhasil, terminal akan menampilkan log dari beberapa service seperti:

```text
distributed-redis
distributed-node1
distributed-node2
distributed-node3
```

Biarkan terminal Docker Compose tetap berjalan. Untuk melakukan testing, buka terminal baru.

---

## 3. Service dan Port

Setiap service berjalan pada port yang berbeda.

Service Port

---

Redis 6379
node1 8001
node2 8002
node3 8003

Node dapat diakses dari host menggunakan alamat berikut:

```text
http://127.0.0.1:8001
http://127.0.0.1:8002
http://127.0.0.1:8003
```

---

## 4. Verifikasi Container

Untuk memastikan semua container berjalan, buka terminal baru lalu jalankan:

```bash
docker ps
```

Container yang seharusnya muncul:

```text
distributed-redis
distributed-node1
distributed-node2
distributed-node3
```

Jika semua container muncul dengan status running, maka deployment berhasil.

---

## 5. Verifikasi Health Check

Setelah container berjalan, cek endpoint health pada setiap node.

Menggunakan curl:

```bash
curl http://127.0.0.1:8001/health
curl http://127.0.0.1:8002/health
curl http://127.0.0.1:8003/health
```

Jika menggunakan PowerShell:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/health
Invoke-RestMethod http://127.0.0.1:8002/health
Invoke-RestMethod http://127.0.0.1:8003/health
```

Jika berhasil, setiap node akan mengembalikan response dengan status `ok`.

Contoh response:

```json
{
  "status": "ok",
  "node_id": "node1",
  "port": 8001,
  "message": "Distributed sync node is running"
}
```

---

## 6. Verifikasi Raft Leader Election

Sistem menggunakan Raft Consensus untuk memilih leader. Untuk mengecek status Raft, jalankan:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/raft/status
Invoke-RestMethod http://127.0.0.1:8002/raft/status
Invoke-RestMethod http://127.0.0.1:8003/raft/status
```

Cluster berjalan normal jika terdapat satu node dengan state `leader` dan node lainnya dengan state `follower`.

Contoh hasil:

```text
node1 = leader
node2 = follower
node3 = follower
```

Leader dapat berubah ketika terjadi timeout, restart, atau simulasi network partition.

---

## 7. Menjalankan Project Secara Lokal

Selain menggunakan Docker Compose, project juga dapat dijalankan secara lokal.

Cara ini membutuhkan Redis yang berjalan terlebih dahulu, lalu setiap node dijalankan pada terminal yang berbeda.

### 7.1 Membuat Virtual Environment

Masuk ke root folder project:

```bash
cd distributed-sync-system
```

Buat virtual environment:

```bash
python -m venv venv
```

Aktifkan virtual environment di Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

Jika berhasil, terminal akan menampilkan tanda seperti berikut:

```text
(venv)
```

### 7.2 Install Dependency

Install semua dependency dari `requirements.txt`:

```bash
pip install -r requirements.txt
```

### 7.3 Menjalankan Redis

Redis dapat dijalankan menggunakan Docker:

```bash
docker run --name redis-dss -p 6379:6379 -d redis:7-alpine
```

Cek apakah Redis sudah berjalan:

```bash
docker ps
```

Jika container `redis-dss` muncul, berarti Redis sudah aktif.

---

## 8. Menjalankan Tiga Node Secara Lokal

Untuk menjalankan sistem secara lokal, buka tiga terminal berbeda.

### Terminal 1 untuk node1

```powershell
cd C:\Users\ALDRI\Documents\PROYEK\distributed-sync-system
.\venv\Scripts\Activate.ps1

$env:NODE_ID="node1"
$env:NODE_HOST="127.0.0.1"
$env:NODE_PORT="8001"
$env:CLUSTER_NODES="http://127.0.0.1:8001,http://127.0.0.1:8002,http://127.0.0.1:8003"

python -m src.main
```

### Terminal 2 untuk node2

```powershell
cd C:\Users\ALDRI\Documents\PROYEK\distributed-sync-system
.\venv\Scripts\Activate.ps1

$env:NODE_ID="node2"
$env:NODE_HOST="127.0.0.1"
$env:NODE_PORT="8002"
$env:CLUSTER_NODES="http://127.0.0.1:8001,http://127.0.0.1:8002,http://127.0.0.1:8003"

python -m src.main
```

### Terminal 3 untuk node3

```powershell
cd C:\Users\ALDRI\Documents\PROYEK\distributed-sync-system
.\venv\Scripts\Activate.ps1

$env:NODE_ID="node3"
$env:NODE_HOST="127.0.0.1"
$env:NODE_PORT="8003"
$env:CLUSTER_NODES="http://127.0.0.1:8001,http://127.0.0.1:8002,http://127.0.0.1:8003"

python -m src.main
```

Setelah semua node berjalan, buka terminal baru untuk testing.

---

## 9. Pengujian Distributed Lock Manager

Sebelum melakukan operasi lock, cek dulu node mana yang menjadi leader:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/raft/status
Invoke-RestMethod http://127.0.0.1:8002/raft/status
Invoke-RestMethod http://127.0.0.1:8003/raft/status
```

Operasi lock harus dikirim ke node leader.

Jika leader adalah `node1`, gunakan port `8001`.

### Acquire Shared Lock

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8001/lock/acquire `
  -ContentType "application/json" `
  -Body '{"resource":"file-A","client_id":"client-1","lock_type":"shared"}'
```

### Acquire Shared Lock dari Client Lain

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8001/lock/acquire `
  -ContentType "application/json" `
  -Body '{"resource":"file-A","client_id":"client-2","lock_type":"shared"}'
```

### Mencoba Exclusive Lock

```powershell
try {
  Invoke-RestMethod -Method Post http://127.0.0.1:8001/lock/acquire `
    -ContentType "application/json" `
    -Body '{"resource":"file-A","client_id":"client-3","lock_type":"exclusive"}'
} catch {
  $_.ErrorDetails.Message
}
```

Jika shared lock masih aktif, exclusive lock akan ditolak.

### Melihat Status Lock

```powershell
Invoke-RestMethod http://127.0.0.1:8001/lock/status | ConvertTo-Json -Depth 10
```

---

## 10. Pengujian Deadlock Detection

Deadlock detection diuji dengan membuat dua client saling menunggu resource.

Pastikan semua command dikirim ke leader yang sama.

Contoh jika leader adalah `node1`, gunakan port `8001`.

### Client-X Mengambil deadlock-X

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8001/lock/acquire `
  -ContentType "application/json" `
  -Body '{"resource":"deadlock-X","client_id":"client-X","lock_type":"exclusive"}'
```

### Client-Y Mengambil deadlock-Y

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8001/lock/acquire `
  -ContentType "application/json" `
  -Body '{"resource":"deadlock-Y","client_id":"client-Y","lock_type":"exclusive"}'
```

### Client-X Menunggu Resource Client-Y

```powershell
try {
  Invoke-RestMethod -Method Post http://127.0.0.1:8001/lock/acquire `
    -ContentType "application/json" `
    -Body '{"resource":"deadlock-Y","client_id":"client-X","lock_type":"exclusive"}'
} catch {
  $_.ErrorDetails.Message
}
```

### Client-Y Menunggu Resource Client-X

```powershell
try {
  Invoke-RestMethod -Method Post http://127.0.0.1:8001/lock/acquire `
    -ContentType "application/json" `
    -Body '{"resource":"deadlock-X","client_id":"client-Y","lock_type":"exclusive"}'
} catch {
  $_.ErrorDetails.Message
}
```

Jika deadlock terdeteksi, response akan menampilkan:

```json
{
  "success": false,
  "reason": "deadlock detected"
}
```

Cek status lock:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/lock/status | ConvertTo-Json -Depth 10
```

Jika berhasil, `wait_for_graph` akan menunjukkan siklus antar client dan `deadlock_detected` bernilai `true`.

---

## 11. Pengujian Distributed Queue

Distributed Queue menggunakan consistent hashing untuk menentukan owner queue.

Request queue dapat dikirim ke node mana saja. Jika node penerima bukan owner queue, request akan diteruskan ke owner yang benar.

### Enqueue Message

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8001/queue/enqueue `
  -ContentType "application/json" `
  -Body '{"queue_name":"orders","producer_id":"producer-1","payload":{"order_id":101,"item":"laptop"}}'
```

### Dequeue Message

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8001/queue/dequeue `
  -ContentType "application/json" `
  -Body '{"queue_name":"orders","consumer_id":"consumer-1"}'
```

Dari hasil dequeue, copy nilai `message_id`.

### ACK Message

Ganti `ISI_MESSAGE_ID` dengan `message_id` dari hasil dequeue.

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8001/queue/ack `
  -ContentType "application/json" `
  -Body '{"queue_name":"orders","message_id":"ISI_MESSAGE_ID","consumer_id":"consumer-1"}'
```

Jika berhasil, response akan menampilkan message acknowledged.

### Status Queue

```powershell
Invoke-RestMethod "http://127.0.0.1:8001/queue/status?queue_name=orders" | ConvertTo-Json -Depth 5
```

---

## 12. Pengujian Distributed Cache Coherence

Distributed Cache menggunakan protokol MESI dan Redis sebagai backing store.

### Write Data dari node1

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8001/cache/product-1 `
  -ContentType "application/json" `
  -Body '{"client_id":"client-1","value":{"name":"Keyboard","stock":50},"propagation":"invalidate"}'
```

Jika berhasil, cache lokal node1 akan memiliki state `M`.

### Read Pertama dari node2

```powershell
Invoke-RestMethod http://127.0.0.1:8002/cache/product-1 | ConvertTo-Json -Depth 5
```

Read pertama biasanya menghasilkan:

```text
cache_hit: false
source: redis_backing_store
state: S
```

Hal ini terjadi karena data belum ada di cache lokal node2 dan harus diambil dari Redis.

### Read Kedua dari node2

```powershell
Invoke-RestMethod http://127.0.0.1:8002/cache/product-1 | ConvertTo-Json -Depth 5
```

Read kedua biasanya menghasilkan:

```text
cache_hit: true
source: local_cache
```

Hal ini menunjukkan bahwa data sudah tersedia pada cache lokal node2.

### Update Data dari node1

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8001/cache/product-1 `
  -ContentType "application/json" `
  -Body '{"client_id":"client-1","value":{"name":"Keyboard","stock":30},"propagation":"invalidate"}'
```

### Cek Invalidation pada node2

```powershell
Invoke-RestMethod http://127.0.0.1:8002/cache/status | ConvertTo-Json -Depth 10
```

Jika invalidation berhasil, cache pada node2 akan memiliki state `I`.

---

## 13. Pengujian LRU Replacement

Kapasitas cache lokal pada implementasi ini diset menjadi 3 item.

Jika lebih dari 3 item ditulis ke cache, maka item yang paling lama tidak digunakan akan dikeluarkan.

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8001/cache/a `
  -ContentType "application/json" `
  -Body '{"value":1,"client_id":"test"}'

Invoke-RestMethod -Method Post http://127.0.0.1:8001/cache/b `
  -ContentType "application/json" `
  -Body '{"value":2,"client_id":"test"}'

Invoke-RestMethod -Method Post http://127.0.0.1:8001/cache/c `
  -ContentType "application/json" `
  -Body '{"value":3,"client_id":"test"}'

Invoke-RestMethod -Method Post http://127.0.0.1:8001/cache/d `
  -ContentType "application/json" `
  -Body '{"value":4,"client_id":"test"}'
```

Cek status cache:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/cache/status | ConvertTo-Json -Depth 10
```

Jika LRU berjalan, metrics `evictions` akan bertambah.

---

## 14. Pengujian Network Partition

Network partition digunakan untuk mensimulasikan kondisi ketika salah satu node tidak dapat berkomunikasi secara normal.

Aktifkan partition pada node tertentu, misalnya node1:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8001/partition/enable
```

Tunggu beberapa detik, lalu cek status Raft:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/raft/status
Invoke-RestMethod http://127.0.0.1:8002/raft/status
Invoke-RestMethod http://127.0.0.1:8003/raft/status
```

Jika partition aktif, status node tersebut akan menunjukkan:

```text
partitioned: true
```

Untuk mengembalikan node ke kondisi normal:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8001/partition/disable
```

Setelah partition dinonaktifkan, node dapat kembali berkomunikasi dengan cluster.

---

## 15. Metrics

Sistem menyediakan endpoint metrics untuk melihat kondisi internal sistem.

```powershell
Invoke-RestMethod http://127.0.0.1:8001/metrics | ConvertTo-Json -Depth 10
```

Metrics yang ditampilkan meliputi:

- status Raft,
- status lock manager,
- wait-for graph,
- cache hit,
- cache miss,
- cache invalidation,
- cache eviction,
- cache writes.

Metrics ini dapat digunakan untuk membantu proses analisis performa sistem.

---

## 16. Stop Deployment

Untuk menghentikan Docker Compose, tekan `Ctrl + C` pada terminal yang menjalankan Docker Compose.

Setelah itu, jalankan:

```bash
docker compose -f docker/docker-compose.yml down
```

Jika ingin menghapus volume juga:

```bash
docker compose -f docker/docker-compose.yml down -v
```

---

## . Troubleshooting

Bagian ini berisi beberapa masalah yang mungkin muncul saat menjalankan sistem.

### 17.1 Port Redis Sudah Dipakai

Error yang mungkin muncul:

```text
Bind for 0.0.0.0:6379 failed: port is already allocated
```

Penyebabnya adalah port Redis sudah digunakan oleh container lain.

Solusi:

```bash
docker stop redis-dss
docker rm redis-dss
docker compose -f docker/docker-compose.yml down
docker compose -f docker/docker-compose.yml up --build
```

Jika container Redis lama memiliki nama berbeda, cek terlebih dahulu dengan:

```bash
docker ps
```

---

### 17.2 Request Lock Ditolak karena Bukan Leader

Error yang mungkin muncul:

```json
{
  "success": false,
  "reason": "this node is not the leader",
  "leader_id": "node2"
}
```

Hal ini normal karena operasi lock hanya diproses oleh leader.

Solusi:

1. Cek leader aktif menggunakan `/raft/status`.
2. Kirim ulang request lock ke node leader.

Mapping port:

Node Port

---

node1 8001
node2 8002
node3 8003

Jika leader adalah `node2`, maka gunakan:

```text
http://127.0.0.1:8002
```

---

### 17.3 Node Tidak Bisa Diakses

Jika node tidak dapat diakses, cek container terlebih dahulu:

```bash
docker ps
```

Cek log node:

```bash
docker logs distributed-node1
docker logs distributed-node2
docker logs distributed-node3
```

Restart Docker Compose:

```bash
docker compose -f docker/docker-compose.yml down
docker compose -f docker/docker-compose.yml up --build
```

---

### 17.4 Semua Node Menjadi Follower

Jika semua node menjadi follower dan tidak ada leader, kemungkinan node tidak mengenali alamat dirinya sendiri di dalam Docker network.

Pastikan setiap node memiliki environment variable `NODE_ADDRESS`.

Contoh:

```yaml
NODE_ADDRESS: http://node1:8001
```

Untuk setiap node:

```text
node1 -> NODE_ADDRESS: http://node1:8001
node2 -> NODE_ADDRESS: http://node2:8002
node3 -> NODE_ADDRESS: http://node3:8003
```

Setelah memperbaiki konfigurasi, build ulang Docker Compose:

```bash
docker compose -f docker/docker-compose.yml down
docker compose -f docker/docker-compose.yml up --build
```

---

### 17.5 PowerShell Tidak Mengenali Command touch

Pada Windows PowerShell, command `touch` tidak tersedia.

Gunakan command berikut untuk membuat file:

```powershell
New-Item nama_file.py -ItemType File -Force
```

Contoh:

```powershell
New-Item docs/deployment_guide.md -ItemType File -Force
```

---

## 18. Catatan Deployment

Untuk pengujian tugas, mode Docker Compose lebih disarankan karena lebih mudah dijalankan dan lebih konsisten.

Mode lokal tetap disediakan untuk keperluan debugging atau pengembangan.

File `.env.example` digunakan sebagai contoh konfigurasi. Jika membuat file `.env`, pastikan tidak berisi data sensitif.

---

## 19. Kesimpulan

Deployment project ini dapat dilakukan dengan Docker Compose atau secara lokal.

Docker Compose menjadi pilihan utama karena seluruh komponen dapat dijalankan sekaligus. Dengan menjalankan Redis, node1, node2, dan node3 secara bersamaan, sistem dapat menunjukkan perilaku distributed system seperti leader election, distributed lock, distributed queue, cache coherence, network partition, dan metrics monitoring.

Jika terjadi kendala seperti port bentrok, node bukan leader, atau container tidak berjalan, langkah troubleshooting pada dokumen ini dapat digunakan untuk memperbaiki masalah tersebut.
