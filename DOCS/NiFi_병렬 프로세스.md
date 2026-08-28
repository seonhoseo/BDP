# NiFi 병렬 처리

---

# 1. 프로세서 단위 병렬 처리

### 1-1. Concurrent Tasks 설정

* NiFi에서는 프로세서별로 `Concurrent Tasks` 값을 설정하여 동일한 프로세서를 여러 개의 Task로 동시에 실행할 수 있다.
* 설정 경로
  * 프로세서 우클릭 > `Configure`
  * `Scheduling` 탭 이동
  * `Concurrent Tasks` 값 수정
* 기본값은 `1`이다.

  <details>
  <summary><strong>Concurrent Tasks 설정 예시</strong></summary>
  
  `Concurrent Tasks = 4`로 설정하면 해당 프로세서는 최대 4개의 FlowFile을 동시에 처리할 수 있다.
  
  ```text
  FlowFile 1 ──┐
  FlowFile 2 ──┤
  FlowFile 3 ──┼──> [Processor]
  FlowFile 4 ──┘
                │
        Concurrent Tasks = 4
  ```
  
  단, `Concurrent Tasks = 4`라고 설정했다고 항상 4개의 작업이 동시에 실행되는 것은 아니다.
  
  실제로 처리할 FlowFile이 충분히 존재해야 하며, NiFi 전체 Thread Pool과 DB Connection 등의 자원도 충분해야 한다.
  
  </details>

---

# 2. 데이터 분할을 통한 병렬 처리

### 2-1. 데이터 분할

* 하나의 FlowFile에 대량의 데이터가 들어있는 경우 여러 개의 FlowFile로 분할하면 후속 프로세서에서 병렬 처리가 가능하다.
* 대표적인 데이터 분할 프로세서
  * `SplitRecord`
  * `SplitText`
  * `SplitJson`
  * `GenerateTableFetch`

### 2-2. SplitRecord를 이용한 병렬 처리

* 예를 들어 100만 건의 데이터를 `10,000`건 단위로 분할하면 약 100개의 FlowFile이 생성된다.
* 이후 후속 프로세서의 `Concurrent Tasks = 5`로 설정하면 최대 5개의 FlowFile을 동시에 처리할 수 있다.

  <details>
  <summary><strong>SplitRecord</strong> - 대용량 데이터를 여러 FlowFile로 분할</summary>
  
  ```text
  원본 데이터
  100만 건
      │
      ▼
  [SplitRecord]
  10,000건 단위로 분할
      │
      ├── FlowFile 1
      ├── FlowFile 2
      ├── FlowFile 3
      ├── FlowFile 4
      ├── FlowFile 5
      ├── ...
      └── FlowFile 100
  ```
  
  후속 프로세서에서 `Concurrent Tasks = 5`로 설정하면 최대 5개의 FlowFile을 동시에 처리한다.
  
  ```text
  [PutDatabaseRecord]
  Concurrent Tasks = 5
       │
       ├── Task 1 → FlowFile
       ├── Task 2 → FlowFile
       ├── Task 3 → FlowFile
       ├── Task 4 → FlowFile
       └── Task 5 → FlowFile
  ```
  
  5개의 작업이 완료되면 대기 중인 다음 FlowFile을 가져와 다시 처리한다.
  
  </details>

> [!NOTE]
> `Concurrent Tasks`를 증가시키는 것만으로 병렬 처리 성능이 향상되는 것은 아니다.
>
> 데이터가 여러 FlowFile로 충분히 분할되어 있어야 하며, NiFi 전체 Thread Pool, DB Connection Pool, Source/Target DB의 처리 능력 등을 함께 고려해야 한다.

---

# 3. 병렬 처리 시 주의사항

### 3-1. DB Connection Pool

* NiFi에서 여러 프로세서가 동시에 DB에 접근하면 여러 개의 DB Connection이 동시에 사용될 수 있다.
* 따라서 `DBCPConnectionPool`의 `Max Total Connections` 값을 함께 확인해야 한다.

  <details>
  <summary><strong>Concurrent Tasks와 DB Connection Pool 관계</strong></summary>
  
  예를 들어 다음과 같이 설정되어 있다고 가정한다.
  
  ```text
  PutDatabaseRecord
  Concurrent Tasks = 10
  
  DBCPConnectionPool
  Max Total Connections = 8
  ```
  
  최대 10개의 Task가 동시에 DB Connection을 필요로 하더라도 Connection Pool에서 제공할 수 있는 Connection은 최대 8개이다.
  
  따라서 Connection을 확보하지 못한 Task는 Connection이 반환될 때까지 대기할 수 있다.
  
  ```text
  Concurrent Tasks = 10
          │
          ▼
  Connection Pool = 8
          │
          ├── Connection 1
          ├── Connection 2
          ├── ...
          ├── Connection 8
          │
          └── 나머지 Task는 Connection 대기
  ```
  
  </details>

> [!WARNING]
> `Concurrent Tasks`보다 `Max Total Connections`가 작다고 해서 반드시 Connection Timeout이 발생하는 것은 아니다.
>
> 다만 동시에 DB Connection을 필요로 하는 작업이 많아지면 Connection 대기 시간이 증가할 수 있으므로 두 값을 함께 고려해야 한다.

---

### 3-2. PostgreSQL Max Connections 확인

* PostgreSQL에서 DB가 허용하는 최대 Connection 수는 다음 명령어로 확인할 수 있다.

```sql
SHOW max_connections;
```

예:

```text
 max_connections
----------------
 100
```

* 이 값은 PostgreSQL 전체에서 사용할 수 있는 최대 Connection 수이다.
* NiFi에서 모든 Connection을 사용하는 것은 권장하지 않는다.
* Airflow, 관리자, 모니터링 시스템 등 다른 서비스에서 사용할 Connection도 고려해야 한다.

---

### 3-3. Connection Pool 적정값

* `DBCPConnectionPool`의 `Max Total Connections`는 다음 항목을 함께 고려하여 설정한다.
  * 프로세서의 `Concurrent Tasks`
  * 동시에 실행되는 DB 프로세서 수
  * PostgreSQL의 `max_connections`
  * Airflow 및 기타 DB 사용자
  * PostgreSQL 서버의 CPU 및 Memory

예를 들어 9개의 `PutDatabaseRecord`가 각각 `Concurrent Tasks = 2`라면 이론적인 최대 동시 작업 수는 다음과 같다.

```text
9 × 2 = 18
```

따라서 DB Connection Pool은 이론적인 동시 DB 접근량을 고려하여 설정한다.

```text
Concurrent Tasks 총합
= 18

DBCPConnectionPool
Max Total Connections
= 20 ~ 25
```

> [!NOTE]
> `Concurrent Tasks 총합 + 2~3`은 단순한 예시일 뿐 절대적인 공식은 아니다.
>
> 모든 Task가 항상 동시에 DB Connection을 사용하는 것은 아니므로 실제 Connection 사용량과 대기 여부를 확인하면서 적정값을 결정해야 한다.

---

### 3-4. Connection Pool 부족 확인

* Connection Pool이 부족한 경우 NiFi 로그에서 다음과 같은 메시지가 발생할 수 있다.

```text
Cannot get connection from pool
```

또는

```text
Timeout waiting for connection
```

* 이러한 오류가 발생하면 다음 항목을 확인한다.
  * `DBCPConnectionPool`의 `Max Total Connections`
  * 실제 DB Connection 사용량
  * 프로세서의 `Concurrent Tasks`
  * PostgreSQL의 `max_connections`

> [!TIP]
> Connection Pool을 무조건 증가시키는 것도 적절하지 않다.
>
> Connection 수가 증가하면 PostgreSQL의 CPU, Memory, I/O 및 Lock 경합이 증가할 수 있으므로 DB 서버 상태를 함께 확인해야 한다.

---

### 3-5. 데이터 순서(Ordering)

* 병렬 처리를 사용하면 FlowFile의 **처리 완료 순서가 달라질 수 있다.**
* 따라서 데이터 처리 순서가 중요한 작업에서는 병렬 처리 사용에 주의해야 한다.

예:

```text
FlowFile A → INSERT
FlowFile B → UPDATE
```

* 위와 같이 `INSERT`가 완료된 후 `UPDATE`가 실행되어야 하는 경우 병렬 처리로 인해 예상하지 못한 순서로 작업이 수행될 수 있다.

* 순서가 중요한 경우
  * 해당 구간의 `Concurrent Tasks`를 `1`로 설정
  * 순차 처리 구조로 변경
  * 필요한 경우 `EnforceOrder` 사용

> [!WARNING]
> 병렬 처리 구간에서는 FlowFile의 생성 순서와 처리 완료 순서가 동일하다고 가정하면 안 된다.

---

### 3-6. Deadlock

* 여러 Task가 동시에 동일한 테이블 또는 동일한 데이터에 접근하여 `INSERT`, `UPDATE`, `DELETE` 등을 수행하면 DB Lock 경합이 증가할 수 있다.
* 특히 여러 FlowFile이 동일한 데이터를 대상으로 UPDATE 작업을 수행하는 경우 Deadlock 발생 가능성이 증가한다.

  <details>
  <summary><strong>Deadlock</strong> - DB Lock 경합 예시</summary>
  
  ```text
  Thread 1
      │
      ├── 데이터 A Lock 획득
      │
      └── 데이터 B Lock 대기
  
  Thread 2
      │
      ├── 데이터 B Lock 획득
      │
      └── 데이터 A Lock 대기
  ```
  
  Thread 1은 Thread 2가 가진 Lock을 기다리고,
  Thread 2는 Thread 1이 가진 Lock을 기다리는 상황이다.
  
  서로 상대방의 Lock이 해제되기를 기다리기 때문에 Deadlock이 발생할 수 있다.
  
  </details>

> [!TIP]
> 병렬 처리 수준을 증가시킨 후 Deadlock이 발생한다면 `Concurrent Tasks`를 낮추고 PostgreSQL의 Lock 및 Query 실행 상태를 확인한다.

---

# 4. NiFi 전체 Thread 설정

### 4-1. Max Timer Driven Thread Count

* NiFi에서는 프로세서별 `Concurrent Tasks` 외에도 NiFi 전체에서 사용할 수 있는 Thread Pool을 관리한다.
* `Max Timer Driven Thread Count`는 Timer-Driven 방식으로 실행되는 프로세서에서 사용할 수 있는 최대 Thread 수를 설정한다.
* 해당 설정은 NiFi의 `nifi.properties`에서 확인할 수 있다.

> [!NOTE]
> NiFi 버전에 따라 설정 항목의 명칭이나 관련 설정 방식이 다를 수 있으므로 현재 사용 중인 NiFi 버전의 `nifi.properties`를 기준으로 확인해야 한다.

---

### 4-2. Thread 수 설정 기준

* NiFi 전체 Thread 수를 단순히 `CPU 코어 수 × 2` 또는 `CPU 코어 수 × 4`로 설정하는 것은 절대적인 기준이 아니다.
* NiFi는 CPU 연산뿐만 아니라 DB, 네트워크, 파일 등의 I/O 작업도 수행하기 때문에 실제 작업 특성에 따라 필요한 Thread 수가 달라질 수 있다.

예를 들어 8 Core 서버라면 초기값으로 다음 범위를 검토할 수 있다.

```text
CPU = 8 Core

초기 검토
→ 16 ~ 32 Threads
```

* 이후 실제 CPU 사용률과 NiFi 처리량을 확인하면서 조정한다.

---

### 4-3. Thread Pool 부족 여부 확인

* NiFi UI에서 현재 사용 중인 Thread 수와 설정된 최대 Thread 수를 확인할 수 있다.

예:

```text
0 / 32
```

* 피크 시간에 최대 Thread 수가 지속적으로 사용된다면 Thread Pool이 병목인지 확인해야 한다.

```text
32 / 32
```

* 반대로 Thread 수를 과도하게 증가시키면 CPU 경쟁 및 Context Switching이 증가하여 전체 성능이 떨어질 수 있다.

> [!TIP]
> Thread 수는 많을수록 좋은 값이 아니다.
>
> 실제 처리량과 CPU 사용률을 확인하면서 적정 Thread 수를 찾아야 한다.

---

### 4-4. Thread 증가 전 확인사항

* 대용량 데이터 처리 속도가 느리다고 무조건 Thread 수를 증가시키는 것은 적절하지 않다.
* 다음 항목을 순서대로 확인하는 것을 권장한다.

```text
① 데이터 분할 크기
        ↓
② Fetch Size
        ↓
③ Max Rows Per FlowFile
        ↓
④ Batch Size
        ↓
⑤ Concurrent Tasks
        ↓
⑥ NiFi 전체 Thread Pool
        ↓
⑦ DB Connection Pool
        ↓
⑧ PostgreSQL 서버 상태
```

> [!TIP]
> Thread를 증가시키는 것은 일꾼의 수를 늘리는 것과 같다.
>
> Batch Size나 FlowFile 크기를 증가시키는 것은 일꾼 한 명이 한 번에 처리하는 작업량을 늘리는 것과 같다.
>
> 따라서 성능이 낮다고 무조건 Thread 수를 늘리기보다는 데이터 분할 크기와 Batch Size를 먼저 확인하는 것이 좋다.

---

# 5. NiFi 대용량 데이터 조회 설정

### 5-1. 주요 설정값

* 대용량 데이터를 처리할 때는 `Fetch Size`, `Max Rows Per FlowFile`, `Partition Size`를 서로 다른 개념으로 이해해야 한다.

| 프로세서 | 관련 주요 속성 | 역할 |
|---|---|---|
| ExecuteSQL | Fetch Size | JDBC에서 데이터를 가져오는 Fetch 단위 |
| ExecuteSQLRecord | Max Rows Per FlowFile | 하나의 FlowFile에 저장할 최대 Record 수 |
| QueryDatabaseTable | Fetch Size | JDBC 조회 시 Fetch 단위 |
| QueryDatabaseTableRecord | Max Rows Per FlowFile | 하나의 FlowFile에 저장할 최대 Record 수 |
| GenerateTableFetch | Partition Size | 조회 작업을 여러 개로 분할 |

---

### 5-2. Fetch Size

* `Fetch Size`는 JDBC 드라이버가 DB에서 결과 데이터를 가져올 때 사용하는 Fetch 단위이다.
* 대량 데이터 조회 시 DB와 NiFi 간의 데이터 전달 방식과 네트워크 Round-trip 등에 영향을 줄 수 있다.

예:

```text
Fetch Size = 10,000
```

> [!NOTE]
> `Fetch Size`의 실제 동작은 사용하는 JDBC 드라이버와 DB 설정에 따라 달라질 수 있다.
>
> 따라서 `Fetch Size = 10,000`이라고 설정했다고 해서 항상 정확히 10,000건이 JVM 메모리에 한 번에 올라간다고 단정할 수 없다.

---

### 5-3. Max Rows Per FlowFile

* `Max Rows Per FlowFile`은 하나의 FlowFile에 저장할 최대 Record 수를 결정한다.
* 대량 데이터를 여러 FlowFile로 분할하여 후속 프로세서의 병렬 처리를 유도할 수 있다.

예:

```text
1,000,000건
     ↓
Max Rows Per FlowFile = 50,000
     ↓
약 20개 FlowFile
```

> [!WARNING]
> `Max Rows Per FlowFile = 0`은 제한을 두지 않는 설정이다.
>
> 대량의 데이터가 하나의 FlowFile에 집중되면 후속 프로세서의 처리 시간이 길어지고 병렬 처리 효과가 떨어질 수 있다.

---

### 5-4. GenerateTableFetch의 Partition Size

* `GenerateTableFetch`는 대용량 테이블의 조회 작업을 여러 개로 분할하는 데 사용할 수 있다.
* `Partition Size`를 통해 하나의 조회 작업에서 처리할 데이터의 분할 크기를 설정한다.

예:

```text
10,000,000건
      ↓
GenerateTableFetch
Partition Size = 50,000
      ↓
약 200개의 조회 작업
```

---

# 6. 대용량 데이터 병렬 처리 권장 설정

### 6-1. 권장 초기값

* 아래 값은 절대적인 기준이 아니라 대용량 데이터 병렬 처리 시 사용할 수 있는 초기 튜닝값이다.

| 설정 | 권장 초기 범위 | 주요 목적 |
|---|---:|---|
| Partition Size | 10,000 ~ 100,000건 | 조회 작업 분할 |
| Fetch Size | 1,000 ~ 10,000건 | JDBC Fetch 단위 조절 |
| Max Rows Per FlowFile | 10,000 ~ 50,000건 | FlowFile 크기 조절 |
| Concurrent Tasks | 2 ~ 8 | 프로세서 병렬 처리 |
| DB Connection Pool | 실제 동시 DB 접근량에 맞춰 설정 | DB Connection 관리 |

> [!NOTE]
> 위의 값은 일반적인 초기 튜닝 범위이다.
>
> 실제 적정값은 Record 크기, SQL 복잡도, DB 성능, NiFi JVM Heap, 네트워크 환경 등에 따라 달라진다.

---

### 6-2. Record 크기에 따른 설정 예시

* Record 크기가 작은 경우

```text
Record 크기 < 1KB

Partition Size
→ 50,000 ~ 100,000

Fetch Size
→ 5,000 ~ 10,000

Max Rows Per FlowFile
→ 50,000
```

* Record 크기가 큰 경우

```text
TEXT / JSON / BLOB 등 대용량 데이터

Partition Size
→ 10,000 ~ 20,000

Fetch Size
→ 1,000 ~ 5,000

Max Rows Per FlowFile
→ 10,000 ~ 20,000
```

> [!WARNING]
> 데이터 건수만으로 적정값을 판단해서는 안 된다.
>
> 동일한 50,000건이라도 Record 하나의 크기가 500Byte인 경우와 50KB인 경우 실제 FlowFile 크기와 메모리 사용량이 크게 다르다.

---

# 7. 대용량 병렬 처리 권장 구조

### 7-1. GenerateTableFetch → ExecuteSQLRecord

* 대용량 테이블을 병렬 처리할 경우 `GenerateTableFetch`로 조회 작업을 분할하고, `ExecuteSQLRecord`의 `Concurrent Tasks`를 증가시키는 구조를 사용할 수 있다.

```text
[Source DB]
     │
     ▼
[GenerateTableFetch]
Partition Size = 50,000
     │
     ├── Query 1
     ├── Query 2
     ├── Query 3
     ├── Query 4
     ├── ...
     └── Query 200
             │
             ▼
[ExecuteSQLRecord]
Concurrent Tasks = 4 ~ 8
Fetch Size = 10,000
Max Rows Per FlowFile = 50,000
             │
             ▼
[PutDatabaseRecord]
Concurrent Tasks = DB 성능에 맞게 설정
             │
             ▼
[PostgreSQL]
```

### 7-2. 처리 원리

* 예를 들어 1,000만 건의 데이터를 `50,000`건 단위로 분할하면 약 200개의 조회 작업으로 나눌 수 있다.
* 이후 `ExecuteSQLRecord`의 `Concurrent Tasks = 4`로 설정하면 최대 4개의 조회 작업을 동시에 처리할 수 있다.

```text
10,000,000건
      │
      ▼
50,000건 단위 분할
      │
      ▼
약 200개 작업
      │
      ▼
ExecuteSQLRecord
Concurrent Tasks = 4
      │
      ├── 작업 1
      ├── 작업 2
      ├── 작업 3
      └── 작업 4
```

* 4개의 작업이 완료되면 대기 중인 다음 작업을 가져와 다시 처리한다.
* 따라서 `Concurrent Tasks = 4`라고 해서 전체 200개의 작업이 한 번에 실행되는 것은 아니다.

> [!NOTE]
> `GenerateTableFetch`를 사용하는 구조에서는 `Partition Size`가 조회 작업을 얼마나 잘게 나눌 것인지 결정하고, `Concurrent Tasks`는 나누어진 작업 중 몇 개를 동시에 처리할 것인지 결정한다.

---

# 8. 병렬 처리 튜닝 방법

### 8-1. 병렬 처리 튜닝 순서

* 대용량 데이터 처리 시 다음 항목을 순서대로 확인하는 것을 권장한다.

```text
① 데이터 분할
       ↓
② Partition Size
       ↓
③ Fetch Size
       ↓
④ Max Rows Per FlowFile
       ↓
⑤ Batch Size
       ↓
⑥ Concurrent Tasks
       ↓
⑦ NiFi 전체 Thread Pool
       ↓
⑧ DB Connection Pool
       ↓
⑨ PostgreSQL 서버 상태
```

### 8-2. 서버 상태 확인

* 병렬 처리 수준을 증가시킨 후에는 다음 항목을 함께 확인해야 한다.

```text
NiFi
├── CPU
├── Memory
├── JVM Heap
├── Thread 사용량
├── Queue 크기
└── 처리 시간

PostgreSQL
├── CPU
├── Memory
├── I/O
├── Connection
├── Lock
├── Deadlock
└── Query 실행 시간
```

> [!WARNING]
> `Concurrent Tasks`, `Thread Pool`, `DB Connection Pool`의 값을 무조건 크게 설정한다고 처리 속도가 빨라지는 것은 아니다.
>
> 병렬 처리량이 증가하면 PostgreSQL의 CPU, Memory, I/O, Connection, Lock 등의 사용량도 함께 증가할 수 있다.
>
> 따라서 처리시간뿐만 아니라 서버 자원 사용량을 함께 확인하면서 최적의 값을 찾아야 한다.

---

> [!TIP]
> NiFi 병렬 처리의 핵심은 단순히 Thread 수를 늘리는 것이 아니다.
>
> **데이터를 적절한 크기로 분할하고 → 여러 FlowFile을 생성한 뒤 → Concurrent Tasks를 이용하여 병렬 처리하고 → DB Connection Pool과 PostgreSQL의 처리 능력을 함께 조절하는 것**이 핵심이다.
