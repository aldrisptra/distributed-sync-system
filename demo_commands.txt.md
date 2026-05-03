<!-- 1 -->

docker ps

<!-- 2 -->

Invoke-RestMethod http://127.0.0.1:8001/raft/status
Invoke-RestMethod http://127.0.0.1:8002/raft/status
Invoke-RestMethod http://127.0.0.1:8003/raft/status

<!-- 3 -->
<!-- cl1 -->

Invoke-RestMethod -Method Post http://127.0.0.1:8001/lock/acquire `  -ContentType "application/json"`
-Body '{"resource":"docker-file-A","client_id":"client-1","lock_type":"shared"}'

<!-- cl2 -->

cls
Invoke-RestMethod -Method Post http://127.0.0.1:8001/lock/acquire `  -ContentType "application/json"`
-Body '{"resource":"docker-file-A","client_id":"client-2","lock_type":"shared"}'

  <!-- 4 -->

try {
Invoke-RestMethod -Method Post http://127.0.0.1:8002/lock/acquire `    -ContentType "application/json"`
-Body '{"resource":"docker-file-A","client*id":"client-3","lock_type":"exclusive"}'
} catch {
$*.ErrorDetails.Message
}

<!-- 5 -->

Invoke-RestMethod http://127.0.0.1:8001/lock/status | ConvertTo-Json -Depth 10

<!-- 6 -->

Invoke-RestMethod -Method Post http://127.0.0.1:8001/partition/enable

Invoke-RestMethod http://127.0.0.1:8001/raft/status
Invoke-RestMethod http://127.0.0.1:8002/raft/status
Invoke-RestMethod http://127.0.0.1:8003/raft/status

Invoke-RestMethod -Method Post http://127.0.0.1:8001/partition/disable

<!-- 7 -->

Invoke-RestMethod -Method Post http://127.0.0.1:8001/queue/enqueue `  -ContentType "application/json"`
-Body '{"queue_name":"docker-orders","producer_id":"producer-1","payload":{"order_id":201,"item":"mouse"}}'

Invoke-RestMethod -Method Post http://127.0.0.1:8001/queue/dequeue `  -ContentType "application/json"`
-Body '{"queue_name":"docker-orders","consumer_id":"consumer-1"}'Invoke-RestMethod -Method Post http://127.0.0.1:8001/queue/ack `  -ContentType "application/json"`
-Body '{"queue_name":"docker-orders","message_id":"ISI_MESSAGE_ID","consumer_id":"consumer-1"}'

  <!-- 8 -->

Invoke-RestMethod -Method Post http://127.0.0.1:8001/cache/product-1 `  -ContentType "application/json"`
-Body '{"client_id":"client-1","value":{"name":"Keyboard","stock":50},"propagation":"invalidate"}'

Invoke-RestMethod http://127.0.0.1:8002/cache/product-1 | ConvertTo-Json -Depth 5

Invoke-RestMethod http://127.0.0.1:8002/cache/product-1 | ConvertTo-Json -Depth 5

Invoke-RestMethod -Method Post http://127.0.0.1:8001/cache/product-1 `  -ContentType "application/json"`
-Body '{"client_id":"client-1","value":{"name":"Keyboard","stock":30},"propagation":"invalidate"}'

Invoke-RestMethod http://127.0.0.1:8002/cache/status | ConvertTo-Json -Depth 10

  <!-- 9 -->

Invoke-RestMethod http://127.0.0.1:8001/cache/status | ConvertTo-Json -Depth 10
