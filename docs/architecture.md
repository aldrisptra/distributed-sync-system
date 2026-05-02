## 3. Komponen Sistem

Pada sistem ini terdapat beberapa komponen utama yang saling bekerja sama. Setiap komponen memiliki fungsi yang berbeda, tetapi tetap terhubung dalam satu alur distributed system.

### 3.1 Base Node

Base Node adalah komponen dasar yang digunakan oleh setiap node di dalam sistem. Komponen ini bertugas untuk menangani komunikasi antar node.

Komunikasi dilakukan menggunakan HTTP request secara asynchronous. Dengan cara ini, satu node dapat mengirim pesan ke node lain tanpa harus menunggu proses secara blocking.

Base Node digunakan oleh komponen lain seperti Raft Consensus, Distributed Queue, dan Distributed Cache untuk melakukan komunikasi antar node.

Fungsi utama Base Node adalah:

- mengirim pesan ke node tertentu,
- melakukan broadcast pesan ke beberapa node,
- menangani timeout ketika node lain tidak dapat dihubungi,
- menangani error komunikasi antar node.

Contoh penggunaan Base Node adalah ketika leader Raft mengirim heartbeat ke follower, atau ketika cache node mengirim invalidation ke node lain.

---

### 3.2 Raft Consensus

Raft Consensus digunakan untuk menentukan node mana yang menjadi leader di dalam cluster. Dalam sistem ini terdapat tiga node, yaitu `node1`, `node2`, dan `node3`.

Pada awal sistem berjalan, setiap node berada dalam state follower. Jika dalam beberapa waktu follower tidak menerima heartbeat dari leader, maka node tersebut dapat berubah menjadi candidate dan memulai proses election.

Node candidate akan meminta vote dari node lain. Jika candidate mendapatkan mayoritas vote, maka node tersebut akan menjadi leader. Setelah menjadi leader, node akan mengirim heartbeat secara berkala ke follower.

State yang digunakan pada Raft:

- `follower`
- `candidate`
- `leader`

Dalam implementasi ini, operasi distributed lock hanya boleh diproses oleh leader. Jika client mengirim request lock ke follower, maka follower akan menolak request tersebut dan mengembalikan informasi `leader_id`.

Raft digunakan untuk:

- leader election,
- heartbeat antar node,
- replikasi command lock,
- menjaga konsistensi operasi lock pada mayoritas node.

Dengan adanya Raft, sistem dapat menentukan satu node utama yang bertanggung jawab memproses operasi lock sehingga konflik antar node dapat dikurangi.

---

### 3.3 Distributed Lock Manager

Distributed Lock Manager digunakan untuk mengatur akses client terhadap resource tertentu. Komponen ini mendukung dua jenis lock, yaitu shared lock dan exclusive lock.

Shared lock dapat digunakan oleh beberapa client secara bersamaan selama tidak ada exclusive lock pada resource tersebut. Exclusive lock hanya dapat digunakan oleh satu client dan tidak boleh ada shared lock aktif pada resource yang sama.

Operasi lock diproses melalui leader Raft. Setelah leader menerima request lock, command akan direplikasi ke node lain menggunakan mekanisme log replication.

Fitur yang tersedia pada Distributed Lock Manager:

- acquire shared lock,
- acquire exclusive lock,
- release lock,
- lock status,
- deadlock detection.

Aturan lock yang digunakan:

- Shared lock boleh dimiliki lebih dari satu client.
- Exclusive lock hanya boleh dimiliki oleh satu client.
- Exclusive lock tidak dapat diberikan jika masih ada shared lock aktif.
- Shared lock tidak dapat diberikan jika resource sedang dikunci secara exclusive oleh client lain.

Deadlock detection dilakukan menggunakan wait-for graph. Wait-for graph menyimpan informasi client mana yang sedang menunggu client lain.

Contoh kondisi deadlock:

- `client-X` memegang `deadlock-X`
- `client-Y` memegang `deadlock-Y`
- `client-X` menunggu `deadlock-Y`
- `client-Y` menunggu `deadlock-X`

Kondisi tersebut membentuk siklus seperti berikut:

```text
client-X -> client-Y -> client-X
```

Jika siklus ditemukan, sistem akan mengembalikan response `deadlock detected`.

---

### 3.4 Distributed Queue

Distributed Queue digunakan untuk menangani komunikasi antara producer dan consumer secara terdistribusi.

Pada sistem ini, queue menggunakan consistent hashing untuk menentukan node mana yang menjadi owner dari sebuah queue. Dengan consistent hashing, setiap `queue_name` akan dipetakan ke salah satu node dalam cluster.

Jika request queue dikirim ke node yang bukan owner, maka node tersebut akan meneruskan request ke owner yang benar.

Redis digunakan untuk menyimpan data queue agar message tetap tersedia walaupun salah satu node mengalami restart atau failure.

Alur enqueue:

1. Producer mengirim message ke salah satu node.
2. Sistem menghitung owner queue menggunakan consistent hashing.
3. Jika node penerima bukan owner, request diteruskan ke node owner.
4. Node owner menyimpan message ke Redis ready queue.

Alur dequeue:

1. Consumer meminta message dari queue.
2. Message diambil dari ready queue.
3. Message dipindahkan ke processing queue.
4. Consumer menerima message untuk diproses.

Alur ACK:

1. Consumer mengirim ACK setelah message selesai diproses.
2. Sistem menghapus message dari processing queue.
3. Message dianggap selesai diproses.

At-least-once delivery dicapai dengan menyimpan message yang sedang diproses pada processing queue. Jika message tidak di-ACK, message dapat direcovery dan dikembalikan ke ready queue.

Dengan cara ini, message tidak langsung hilang ketika sudah diambil consumer. Message baru dianggap selesai jika consumer sudah mengirim ACK.

---

### 3.5 Distributed Cache Coherence

Distributed Cache Coherence digunakan agar data cache pada beberapa node tetap konsisten.

Protocol yang digunakan adalah MESI. MESI memiliki empat state, yaitu Modified, Exclusive, Shared, dan Invalid.

State MESI:

- `M` berarti Modified, yaitu data sudah dimodifikasi pada cache lokal.
- `E` berarti Exclusive, yaitu data hanya dimiliki oleh satu node.
- `S` berarti Shared, yaitu data dibaca oleh lebih dari satu node.
- `I` berarti Invalid, yaitu data cache sudah tidak valid dan perlu diambil ulang.

Redis digunakan sebagai backing store untuk menyimpan data utama. Cache lokal pada setiap node digunakan untuk mempercepat pembacaan data.

Alur write cache:

1. Client menulis data ke salah satu node.
2. Node menyimpan data ke Redis.
3. Node menyimpan data pada cache lokal dengan state `M`.
4. Node mengirim invalidation ke node lain.
5. Cache pada node lain berubah menjadi state `I`.

Alur read cache:

1. Jika data tersedia di cache lokal dan state masih valid, maka terjadi cache hit.
2. Jika data tidak tersedia atau state invalid, maka node mengambil data dari Redis.
3. Data yang diambil dari Redis disimpan kembali ke cache lokal.

Sistem juga menggunakan LRU replacement policy. Jika kapasitas cache penuh, data yang paling lama tidak digunakan akan dikeluarkan dari cache.

LRU digunakan agar cache tidak menyimpan data terlalu banyak di memory lokal node.

---

### 3.6 Redis

Redis digunakan sebagai penyimpanan tambahan untuk beberapa kebutuhan sistem.

Pada Distributed Queue, Redis digunakan untuk menyimpan:

- ready queue,
- processing queue,
- queue metrics.

Pada Distributed Cache, Redis digunakan sebagai backing store agar data utama tetap tersedia walaupun cache lokal pada node berubah atau invalid.

Redis membantu sistem agar data queue dan cache tidak hanya bergantung pada memory lokal masing-masing node. Dengan demikian, data tetap dapat dipulihkan ketika terjadi restart atau failure pada node tertentu.

---

### 3.7 Docker dan Docker Compose

Docker digunakan untuk menjalankan setiap komponen sistem dalam container. Dengan Docker, sistem dapat dijalankan dengan lebih mudah tanpa harus menjalankan node satu per satu secara manual.

Docker Compose digunakan untuk menjalankan beberapa service sekaligus, yaitu:

- Redis,
- node1,
- node2,
- node3.

Setiap node berjalan pada port berbeda:

| Service | Port |
| ------- | ---- |
| Redis   | 6379 |
| node1   | 8001 |
| node2   | 8002 |
| node3   | 8003 |

Dengan Docker Compose, seluruh sistem dapat dijalankan menggunakan satu command:

```bash
docker compose -f docker/docker-compose.yml up --build
```

Penggunaan Docker Compose juga memudahkan proses pengujian karena semua node dapat berjalan secara bersamaan dalam satu network yang sama.

---

### 3.8 Metrics

Metrics digunakan untuk melihat kondisi sistem saat berjalan.

Endpoint `/metrics` menampilkan beberapa informasi penting, seperti:

- status Raft,
- status lock manager,
- wait-for graph,
- cache hit,
- cache miss,
- cache invalidation,
- cache eviction,
- cache writes.

Metrics ini digunakan untuk membantu proses monitoring dan analisis performa sistem.

---

## 4. Failure Handling

Distributed system harus mampu menangani kemungkinan kegagalan. Pada sistem ini, beberapa skenario failure handling disimulasikan untuk menunjukkan bagaimana sistem tetap dapat berjalan ketika terjadi gangguan.

### 4.1 Network Partition

Network partition adalah kondisi ketika salah satu node tidak dapat berkomunikasi secara normal dengan node lain.

Pada sistem ini, network partition disimulasikan menggunakan endpoint:

- `POST /partition/enable`
- `POST /partition/disable`

Ketika partition diaktifkan, node akan mengabaikan beberapa komunikasi Raft seperti heartbeat atau vote request. Hal ini membuat cluster dapat melakukan election ulang jika leader tidak dapat dijangkau.

Contoh skenario:

1. `node1` sedang menjadi leader.
2. Partition diaktifkan pada `node1`.
3. `node2` dan `node3` tidak lagi menerima heartbeat normal dari `node1`.
4. Cluster dapat memilih leader baru.
5. Setelah partition dinonaktifkan, node dapat kembali bergabung ke cluster.

Simulasi ini digunakan untuk menunjukkan bahwa sistem dapat menangani kondisi komunikasi yang tidak stabil.

---

### 4.2 Node Failure pada Distributed Queue

Pada Distributed Queue, message disimpan di Redis. Dengan cara ini, message tidak hanya berada di memory lokal node.

Jika salah satu node mati atau restart, data queue tetap tersedia di Redis. Message yang sedang diproses juga disimpan pada processing queue.

Jika consumer mengambil message tetapi tidak mengirim ACK, message tersebut dapat direcovery dan dikembalikan ke ready queue. Dengan cara ini, sistem dapat mendukung at-least-once delivery.

Alur recovery:

1. Message berada di processing queue.
2. Consumer gagal mengirim ACK.
3. Sistem mendeteksi message yang sudah melewati visibility timeout.
4. Message dikembalikan ke ready queue.
5. Message dapat diproses ulang oleh consumer lain.

---

### 4.3 Cache Invalidation

Pada Distributed Cache, setiap node dapat memiliki cache lokal masing-masing. Masalah dapat terjadi jika satu node mengubah data, tetapi node lain masih menyimpan data lama.

Untuk mengatasi hal tersebut, sistem menggunakan cache invalidation.

Ketika satu node melakukan write, node tersebut akan:

1. menyimpan data baru ke Redis,
2. menyimpan data baru ke cache lokal,
3. mengirim invalidation ke node lain,
4. node lain menandai cache line sebagai `I`.

Jika node lain membaca data yang sudah invalid, maka node tersebut akan mengambil data terbaru dari Redis.

Dengan cara ini, cache antar node tetap konsisten.

---

### 4.4 Request ke Follower

Pada Distributed Lock Manager, operasi lock hanya boleh diproses oleh leader. Jika client mengirim request lock ke follower, maka follower akan menolak request tersebut.

Response yang dikembalikan berisi informasi leader aktif.

Contoh response:

```json
{
  "success": false,
  "reason": "this node is not the leader",
  "leader_id": "node2"
}
```

Client dapat menggunakan informasi `leader_id` tersebut untuk mengirim ulang request ke node leader.

---

## 5. Metrics dan Monitoring

Sistem menyediakan endpoint `/metrics` untuk melihat kondisi internal sistem.

Metrics yang dikumpulkan meliputi tiga bagian utama, yaitu Raft, Lock Manager, dan Cache.

### 5.1 Metrics Raft

Metrics Raft menampilkan informasi seperti:

- node id,
- state node,
- current term,
- leader id,
- panjang log,
- commit index,
- status partition.

Metrics ini digunakan untuk mengetahui node mana yang sedang menjadi leader dan node mana yang menjadi follower.

---

### 5.2 Metrics Lock Manager

Metrics Lock Manager menampilkan informasi seperti:

- daftar resource yang sedang dikunci,
- shared holder,
- exclusive holder,
- wait-for graph,
- status deadlock.

Metrics ini digunakan untuk melihat kondisi lock pada sistem dan mendeteksi apakah terdapat deadlock.

Contoh informasi yang penting adalah `deadlock_detected`. Jika nilainya `true`, berarti sistem menemukan siklus pada wait-for graph.

---

### 5.3 Metrics Cache

Metrics Cache menampilkan informasi seperti:

- cache hit,
- cache miss,
- writes,
- invalidations,
- updates received,
- evictions.

Metrics ini digunakan untuk menganalisis performa cache.

Contoh:

- `cache_hits` menunjukkan jumlah pembacaan yang berhasil dari cache lokal.
- `cache_misses` menunjukkan jumlah pembacaan yang harus mengambil data dari Redis.
- `invalidations` menunjukkan jumlah cache line yang dibuat invalid.
- `evictions` menunjukkan jumlah data yang dikeluarkan dari cache karena kapasitas penuh.

---

## 6. Kesimpulan Arsitektur

Arsitektur sistem ini dirancang untuk mensimulasikan beberapa konsep penting dalam distributed systems.

Konsep yang diterapkan dalam sistem ini meliputi:

- komunikasi antar node,
- leader election,
- consensus,
- log replication,
- distributed locking,
- shared dan exclusive lock,
- deadlock detection,
- consistent hashing,
- distributed queue,
- at-least-once delivery,
- cache coherence,
- cache invalidation,
- LRU replacement,
- metrics monitoring,
- containerization.

Dengan menggunakan tiga node dan Redis, sistem dapat menunjukkan bagaimana beberapa komponen distributed system saling bekerja sama.

Raft digunakan untuk menjaga operasi lock tetap konsisten melalui leader dan replikasi command. Distributed Queue menggunakan consistent hashing agar queue dapat dipetakan ke node tertentu. Distributed Cache menggunakan protokol MESI agar data cache antar node tetap terjaga konsistensinya.

Docker Compose digunakan agar sistem dapat dijalankan dengan lebih mudah. Dengan satu command, seluruh komponen seperti Redis, node1, node2, dan node3 dapat berjalan secara bersamaan.

Secara keseluruhan, arsitektur ini sudah memenuhi kebutuhan utama tugas, yaitu membuat sistem sinkronisasi terdistribusi yang mampu menangani multiple nodes, komunikasi antar node, konsistensi data, failure simulation, dan monitoring performa.
