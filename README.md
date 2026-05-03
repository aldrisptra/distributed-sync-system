# Distributed Synchronization System

Project ini dibuat untuk memenuhi Tugas 2 mata kuliah Sistem Parallel dan Terdistribusi dengan topik Sinkronisasi dan Distributed Systems.

Sistem ini mensimulasikan distributed system yang terdiri dari beberapa node. Setiap node dapat saling berkomunikasi untuk menjalankan fitur distributed lock, distributed queue, dan distributed cache coherence.

---

## Identitas

Nama: Muhammad Aldri Saputra  
NIM: 11231050  
Mata Kuliah: Sistem Parallel dan Terdistribusi  
Judul Tugas: Implementasi Distributed Synchronization System

---

## Deskripsi Singkat

Distributed Synchronization System adalah sistem simulasi yang terdiri dari 3 node utama dan Redis sebagai penyimpanan state tambahan. Sistem ini dibuat menggunakan Python, aiohttp, Redis, Docker, dan Docker Compose.

Fitur utama yang diimplementasikan:

1. Distributed Lock Manager menggunakan simplified Raft Consensus.
2. Distributed Queue menggunakan consistent hashing.
3. Distributed Cache Coherence menggunakan protokol MESI.
4. Containerization menggunakan Docker dan Docker Compose.

---

## Fitur Sistem

### 1. Distributed Lock Manager

Distributed Lock Manager digunakan untuk mengatur akses client terhadap resource tertentu.

Fitur yang tersedia:

- Leader election menggunakan Raft Consensus.
- Operasi lock hanya diproses oleh leader.
- Support shared lock.
- Support exclusive lock.
- Replication command lock ke node lain.
- Simulasi network partition.
- Deadlock detection menggunakan wait-for graph.

Jenis lock:

- Shared lock dapat digunakan oleh beberapa client secara bersamaan.
- Exclusive lock hanya dapat digunakan oleh satu client.

Endpoint utama:

- `POST /lock/acquire`
- `POST /lock/release`
- `GET /lock/status`
- `GET /raft/status`

---

### 2. Distributed Queue

Distributed Queue digunakan untuk menangani producer dan consumer secara terdistribusi.

Fitur yang tersedia:

- Consistent hashing untuk menentukan owner queue.
- Support multiple producer.
- Support multiple consumer.
- Message persistence menggunakan Redis.
- At-least-once delivery guarantee.
- ACK mechanism untuk memastikan message sudah diproses.
- Recovery untuk message yang belum di-ACK.

Endpoint utama:

- `POST /queue/enqueue`
- `POST /queue/dequeue`
- `POST /queue/ack`
- `POST /queue/recover`
- `GET /queue/status`

---

### 3. Distributed Cache Coherence

Distributed Cache digunakan untuk menyimpan data cache pada beberapa node dengan mekanisme coherence.

Protocol yang digunakan adalah MESI.

State MESI:

- `M` = Modified
- `E` = Exclusive
- `S` = Shared
- `I` = Invalid

Fitur yang tersedia:

- Multiple cache nodes.
- Cache hit dan cache miss.
- Cache invalidation.
- Update propagation.
- LRU replacement policy.
- Metrics collection.

Endpoint utama:

- `POST /cache/{key}`
- `GET /cache/{key}`
- `DELETE /cache/{key}`
- `GET /cache/status`
- `GET /metrics`

---

## Teknologi yang Digunakan

Project ini menggunakan beberapa teknologi berikut:

- Python 3.11
- asyncio
- aiohttp
- Redis
- Docker
- Docker Compose
- pytest
- locust

---

## Struktur Project

Project ini memiliki beberapa folder utama:

- `src/`  
  Berisi source code utama aplikasi.

- `src/nodes/`  
  Berisi implementasi node untuk lock manager, queue, dan cache.

- `src/consensus/`  
  Berisi implementasi algoritma Raft Consensus.

- `src/communication/`  
  Berisi modul komunikasi antar node dan failure detector.

- `src/utils/`  
  Berisi konfigurasi dan utility tambahan.

- `docker/`  
  Berisi Dockerfile dan docker-compose untuk menjalankan sistem menggunakan container.

- `docs/`  
  Berisi dokumentasi teknis, API specification, dan deployment guide.

- `benchmarks/`  
  Berisi skenario load testing dan performance testing.

- `tests/`  
  Berisi folder untuk unit test, integration test, dan performance test.

- `requirements.txt`  
  Berisi daftar dependency Python.

- `.env.example`  
  Berisi contoh konfigurasi environment.

- `README.md`  
  Berisi penjelasan project dan cara menjalankan sistem.

---

## Cara Menjalankan Project dengan Docker

Pastikan Docker dan Docker Compose sudah terinstall.

Jalankan command berikut dari root folder project:

```bash
docker compose -f docker/docker-compose.yml up --build
```

Service yang akan berjalan:

Service Port

---

Redis 6379
node1 8001
node2 8002
node3 8003

Untuk mengecek container yang berjalan:

```bash
docker ps
```

---

## Verifikasi Node

Setelah Docker Compose berjalan, cek status masing-masing node:

```bash
curl http://127.0.0.1:8001/health
curl http://127.0.0.1:8002/health
curl http://127.0.0.1:8003/health
```

Jika berhasil, setiap node akan mengembalikan status `ok`.

---

## Cek Status Raft

Untuk mengecek leader dan follower:

```bash
curl http://127.0.0.1:8001/raft/status
curl http://127.0.0.1:8002/raft/status
curl http://127.0.0.1:8003/raft/status
```

Sistem berjalan normal jika terdapat satu node dengan state `leader` dan node lain sebagai `follower`.

Contoh:

```text
node1 = leader
node2 = follower
node3 = follower
```

Leader dapat berubah jika terjadi timeout atau network partition.

---

## Contoh Pengujian

Contoh command berikut menggunakan PowerShell.

### 1. Distributed Lock Manager

Acquire shared lock:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8001/lock/acquire `
  -ContentType "application/json" `
  -Body '{"resource":"file-A","client_id":"client-1","lock_type":"shared"}'
```

Acquire shared lock dari client lain:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8001/lock/acquire `
  -ContentType "application/json" `
  -Body '{"resource":"file-A","client_id":"client-2","lock_type":"shared"}'
```

Mencoba exclusive lock ketika shared lock masih aktif:

```powershell
try {
  Invoke-RestMethod -Method Post http://127.0.0.1:8001/lock/acquire `
    -ContentType "application/json" `
    -Body '{"resource":"file-A","client_id":"client-3","lock_type":"exclusive"}'
} catch {
  $_.ErrorDetails.Message
}
```

Melihat status lock:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/lock/status | ConvertTo-Json -Depth 10
```

Catatan: jika request dikirim ke follower, sistem akan mengembalikan informasi `leader_id`. Request lock harus dikirim ke node yang sedang menjadi leader.

---

### 2. Deadlock Detection

Contoh skenario deadlock:

Client-X memegang `deadlock-X`, Client-Y memegang `deadlock-Y`, lalu keduanya saling menunggu resource yang sedang dipegang client lain.

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8001/lock/acquire `
  -ContentType "application/json" `
  -Body '{"resource":"deadlock-X","client_id":"client-X","lock_type":"exclusive"}'
```

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8001/lock/acquire `
  -ContentType "application/json" `
  -Body '{"resource":"deadlock-Y","client_id":"client-Y","lock_type":"exclusive"}'
```

Client-X mencoba mengambil resource milik Client-Y:

```powershell
try {
  Invoke-RestMethod -Method Post http://127.0.0.1:8001/lock/acquire `
    -ContentType "application/json" `
    -Body '{"resource":"deadlock-Y","client_id":"client-X","lock_type":"exclusive"}'
} catch {
  $_.ErrorDetails.Message
}
```

Client-Y mencoba mengambil resource milik Client-X:

```powershell
try {
  Invoke-RestMethod -Method Post http://127.0.0.1:8001/lock/acquire `
    -ContentType "application/json" `
    -Body '{"resource":"deadlock-X","client_id":"client-Y","lock_type":"exclusive"}'
} catch {
  $_.ErrorDetails.Message
}
```

Jika deadlock terdeteksi, response akan berisi:

```json
{
  "success": false,
  "reason": "deadlock detected"
}
```

---

### 3. Distributed Queue

Menambahkan message ke queue:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8001/queue/enqueue `
  -ContentType "application/json" `
  -Body '{"queue_name":"orders","producer_id":"producer-1","payload":{"order_id":101,"item":"laptop"}}'
```

Mengambil message dari queue:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8001/queue/dequeue `
  -ContentType "application/json" `
  -Body '{"queue_name":"orders","consumer_id":"consumer-1"}'
```

Melakukan ACK setelah message diproses:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8001/queue/ack `
  -ContentType "application/json" `
  -Body '{"queue_name":"orders","message_id":"ISI_MESSAGE_ID","consumer_id":"consumer-1"}'
```

Melihat status queue:

```powershell
Invoke-RestMethod "http://127.0.0.1:8001/queue/status?queue_name=orders" | ConvertTo-Json -Depth 5
```

---

### 4. Distributed Cache Coherence

Menulis data ke cache:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8001/cache/product-1 `
  -ContentType "application/json" `
  -Body '{"client_id":"client-1","value":{"name":"Keyboard","stock":50},"propagation":"invalidate"}'
```

Membaca data dari node lain:

```powershell
Invoke-RestMethod http://127.0.0.1:8002/cache/product-1 | ConvertTo-Json -Depth 5
```

Read pertama biasanya menghasilkan `cache_hit: false` karena data diambil dari Redis backing store.

Read kedua:

```powershell
Invoke-RestMethod http://127.0.0.1:8002/cache/product-1 | ConvertTo-Json -Depth 5
```

Read kedua biasanya menghasilkan `cache_hit: true` karena data sudah tersedia di local cache.

Update data dari node1:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8001/cache/product-1 `
  -ContentType "application/json" `
  -Body '{"client_id":"client-1","value":{"name":"Keyboard","stock":30},"propagation":"invalidate"}'
```

Cek status cache node2:

```powershell
Invoke-RestMethod http://127.0.0.1:8002/cache/status | ConvertTo-Json -Depth 10
```

Jika invalidation berhasil, state cache pada node2 akan menjadi `I`.

---

### 5. LRU Replacement

Kapasitas cache lokal diset menjadi 3 item. Jika lebih dari 3 item dimasukkan, item yang paling lama tidak digunakan akan dihapus.

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

## Network Partition Simulation

Network partition dapat disimulasikan dengan endpoint berikut:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8001/partition/enable
```

Cek status Raft:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/raft/status
Invoke-RestMethod http://127.0.0.1:8002/raft/status
Invoke-RestMethod http://127.0.0.1:8003/raft/status
```

Untuk menonaktifkan partition:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8001/partition/disable
```

---

## Metrics

Sistem menyediakan endpoint metrics:

```bash
curl http://127.0.0.1:8001/metrics
```

Metrics yang tersedia meliputi:

- Raft status
- Lock status
- Wait-for graph
- Cache hits
- Cache misses
- Cache invalidations
- Cache evictions
- Cache writes

---

## Dokumentasi Tambahan

Dokumentasi lengkap tersedia pada folder `docs/`.

- `docs/architecture.md` berisi penjelasan arsitektur sistem.
- `docs/api_spec.yaml` berisi dokumentasi API dengan format OpenAPI.
- `docs/deployment_guide.md` berisi panduan deployment dan troubleshooting.

---

## Screenshot Pengujian

Screenshot hasil pengujian disimpan sebagai bukti bahwa setiap fitur berjalan.

Screenshot yang digunakan:

1. Docker container berjalan.
2. Raft leader dan follower.
3. Shared lock berhasil.
4. Exclusive lock conflict.
5. Deadlock detection.
6. Queue enqueue, dequeue, dan ACK.
7. Cache write dengan state Modified.
8. Cache miss dan cache hit.
9. Cache invalidation.
10. LRU eviction.

---

## Link Video Demo

Link YouTube: https://youtu.be/MFytktbxrgc

---

## Status Implementasi

Requirement Status

---

Distributed Lock Manager Selesai
Raft Consensus Selesai
Shared Lock Selesai
Exclusive Lock Selesai
Network Partition Simulation Selesai
Deadlock Detection Selesai
Distributed Queue Selesai
Consistent Hashing Selesai
Message Persistence Selesai
At-least-once Delivery Selesai
Cache Coherence MESI Selesai
Cache Invalidation Selesai
LRU Replacement Policy Selesai
Metrics Collection Selesai
Dockerfile Selesai
Docker Compose Selesai

---

## Kendala Singkat

Beberapa kendala yang ditemukan selama implementasi:

1. Leader Raft dapat berubah saat testing, sehingga request lock harus dikirim ke leader aktif.
2. Redis port dapat bentrok jika sebelumnya sudah ada container Redis yang berjalan.
3. Dalam Docker Compose, node perlu menggunakan `NODE_ADDRESS` agar dapat mengenali alamat dirinya sendiri.
4. Cache invalidation perlu diuji dari node berbeda untuk memastikan state berubah menjadi Invalid.

---

## Kesimpulan

Project ini berhasil mengimplementasikan simulasi distributed synchronization system dengan 3 node. Sistem mendukung distributed lock berbasis Raft, distributed queue berbasis consistent hashing, serta distributed cache coherence menggunakan protokol MESI.

Dengan adanya Docker Compose, seluruh node dan Redis dapat dijalankan secara bersamaan sehingga proses pengujian distributed behavior menjadi lebih mudah.
