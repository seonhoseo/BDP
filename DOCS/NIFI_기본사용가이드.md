# NiFi 기본 사용 가이드

---

# 1. NiFi DB 연결 설정

### 1-1. DB Connection 생성

* 캔버스 > 빈 공간 우클릭 > Controller Services 클릭 > 우측 `+` 클릭 > `DBCPConnectionPool` 조회하여 Add

### 1-2. DB Connection 설정

* **Database Connection URL** : `jdbc:mysql://<host>:<port>/<dbname>?allowPublicKeyRetrieval=true`
  * 예: `jdbc:mysql://dfodev.iptime.org:32306/sakila?allowPublicKeyRetrieval=true`
* **Database Driver Class Name** : `com.mysql.cj.jdbc.Driver`
* **Database Driver Location(s)** : `/opt/nifi/lib/mysql-connector-j-9.3.0.jar`
* **Database User** : DB 유저명
* **Password** : DB 패스워드



> [!NOTE]
> 설정 변경 완료 후, 해당 커넥션 우측 점 3개 클릭하여 **Enable**한다.
> DBCPConnectionPool은 프로세스 그룹 가장 상위에서 생성해야 하위 프로세스 그룹에서 공통으로 사용할 수 있다.

---

# 2. NiFi 기본 ETL 프로세스 생성

### 2-1. File to DB

* 사용 프로세서 : `ListFile` → `FetchFile` → `PutSQL` → `PutDatabaseRecord`

  <details>
  <summary><strong>ListFile</strong> - 읽어올 파일의 메타데이터 생성</summary>
  
  * **Input Directory** : `/home/bdpadmin/input`
    * 실제 파일이 존재하는 경로를 입력한다.
  * **Listing Strategy** : `No Tracking`
  * **File Filter** : `.*\.csv`
    * CSV 파일만 읽는다.
  * **Minimum File Age** : `30 sec`
    * 파일 생성 후 30초가 지난 파일만 읽는다.
    * 대용량 파일을 복사하는 중인 경우 파일이 완전히 생성되기 전에 읽는 것을 방지하기 위한 설정이다.
  
  </details>

  <details>
  <summary><strong>FetchFile</strong> - 실제 파일 읽기</summary>
  
  `ListFile`에서 생성된 파일의 메타데이터 정보를 사용하여 실제 파일을 읽어온다.
  
  * **File to Fetch** : `${absolute.path}/${filename}`
  * **Completion Strategy** : `Move File`
    * 정상 수행 후 파일을 다른 경로로 이동한다.
  * **Move Destination Directory** : `/home/bdpadmin/archieve`
  
  </details>

  <details>
  <summary><strong>PutSQL</strong> - INSERT 전 TRUNCATE 수행</summary>
  
  INSERT 전 대상 테이블을 `TRUNCATE`한다.
  
  * **JDBC Connection Pool** : `Target_Postgresql`
    * 생성한 DBCPConnectionPool 중 Target DB를 선택한다.
  * **SQL Statement**
  
  ```sql
  TRUNCATE TABLE public.customer_file;
  ```
  
  </details>

  <details>
  <summary><strong>PutDatabaseRecord</strong> - DB에 데이터 INSERT</summary>
  
  CSV 파일의 데이터를 DB 테이블에 INSERT한다.
  
  * **Record Reader** : `CSVReader`
    * CSV 파일을 읽기 위한 Controller Service
  * **Database Type** : `PostgreSQL`
    * `Generic`으로 지정해도 무방하지만, 타입 변환 문제 등을 방지하기 위해 실제 사용하는 DBMS로 지정하는 것을 권장한다.
  * **Statement Type** : `INSERT`
  * **Database Connection Pooling Service** : `Target_Postgresql`
  * **Table Name** : `customer_file`
    * CSV 파일 데이터를 INSERT할 대상 테이블명을 입력한다.
  
  </details>
  <details>
  <summary><strong>File to DB 프로세스 이미지</strong></summary>
  
  <img width="334" height="717" alt="image" src="https://github.com/user-attachments/assets/568c7aed-4799-46ab-b175-5d9a03adf900" />
  
  </details>

> [!WARNING]
> `CSVReader`, `AvroReader` 등 DBCPConnectionPool을 제외한 Controller Service는 현재 작업 중인 프로세스 그룹 내부에서 생성하는 것을 권장한다.
>
> 프로세스 그룹마다 사용하는 Controller Service의 상세 설정이 다를 수 있기 때문이다.

---

### 2-2. Source DB → Target DB

#### ODS (Staging)

* 사용 프로세서 : `QueryDatabaseTableRecord` → `PutDatabaseRecord`

  <details>
  <summary><strong>QueryDatabaseTableRecord</strong> - Source DB 테이블 조회</summary>
  
  Source DB의 테이블 데이터를 조회한다.
  
  * **Database Connection Pooling Service** : `Source_Mysql`
  * **Database Type** : `MySQL`
  * **Table Name** : `rental`
  * **Record Writer** : `AvroRecordSetWriter`
  
  </details>

  <details>
  <summary><strong>PutDatabaseRecord</strong> - ODS 테이블에 데이터 INSERT</summary>
  
  Source DB에서 조회한 데이터를 PostgreSQL ODS 테이블에 INSERT한다.
  
  * **Record Reader** : `AvroReader`
  * **Database Type** : `PostgreSQL`
  * **Statement Type** : `INSERT`
  * **Database Connection Pooling Service** : `Target_Postgresql`
  * **Table Name** : `ods_rental`
  
  </details>
  <details>
  <summary><strong>ODS 프로세스 이미지</strong></summary>
  
  <img width="1621" height="867" alt="image" src="https://github.com/user-attachments/assets/049ff427-ac1a-47dc-b66f-781fd049bfc1" />
  
  </details>

---

#### DW

* 사용 프로세서 : `GenerateFlowFile` → `ExecuteGroovyScript` → `ExecuteSQL` → `PutDatabaseRecord`

  <details>
  <summary><strong>GenerateFlowFile</strong> - 트리거 프로세서</summary>
  
  트리거 없이 실행될 수 있는 프로세서와 그렇지 않은 프로세서들이 있다.
  
  `QueryDatabaseTableRecord`와 같은 프로세서는 트리거 없이 독립 실행될 수 있지만, `ExecuteSQL`과 같이 트리거가 필요한 프로세서들도 있다.
  
  이 경우 `GenerateFlowFile` 프로세서를 트리거 역할로 사용한다.
  
  * 기본값으로 진행한다.
  
  </details>

  <details>
  <summary><strong>ExecuteGroovyScript</strong> - 동적 변수 생성</summary>
  
  NiFi에서는 동적 변수를 전역으로 선언할 수 없다.
  
  동적 변수를 사용하기 위해서는 `ExecuteGroovyScript`와 같은 프로세서를 이용하여 FlowFile Attribute를 생성할 수 있다.
  
  생성된 Attribute는 이후 프로세서에서 `${변수명}` 형태로 사용할 수 있다.
  
  **Script Body**
  
  ```groovy
  import java.time.LocalDate
  import java.time.format.DateTimeFormatter
  
  def flowFile = session.get()
  if (!flowFile) return
  
  LocalDate today = LocalDate.now()
  
  // 전일
  LocalDate endDate = today.minusDays(1)
  
  // 3개월 전 1일
  // LocalDate startDate = today.minusMonths(3).withDayOfMonth(1)
  LocalDate startDate = LocalDate.of(2005, 1, 1)
  
  // Formatter
  def dashFmt = DateTimeFormatter.ofPattern("yyyy-MM-dd")
  def ymdFmt = DateTimeFormatter.ofPattern("yyyyMMdd")
  def ymFmt = DateTimeFormatter.ofPattern("yyyyMM")
  
  flowFile = session.putAllAttributes(flowFile, [
      "RUN_DATE"      : today.format(dashFmt),
      "RUN_YYYYMM"    : today.format(ymFmt),
      "RUN_YYYYMMDD"  : today.format(ymdFmt),
  
      "START_DATE"    : startDate.format(dashFmt),
      "END_DATE"      : endDate.format(dashFmt),
  
      "START_DATE8"   : startDate.format(ymdFmt),
      "END_DATE8"     : endDate.format(ymdFmt)
  ])
  
  session.transfer(flowFile, REL_SUCCESS)
  ```
  
  </details>

  <details>
  <summary><strong>ExecuteSQL</strong> - SQL Query 실행</summary>
  
  ODS에서 DW로 ETL하기 위한 JOIN Query를 수행한다.
  
  * **Database Connection Pooling Service** : `Target_Postgresql`
  * **SQL select query**
  
  ```sql
  SELECT r.rental_id,
         r.rental_date,
         r.return_date,
         c.customer_id,
         CONCAT(c.first_name, ' ', c.last_name) AS customer_name,
         a.address,
         ct.city,
         co.country,
         f.film_id,
         f.title,
         s.staff_id,
         CONCAT(s.first_name, ' ', s.last_name) AS staff_name,
         st.store_id,
         now() AS etl_dt
    FROM ods_rental r
    JOIN ods_customer c
      ON r.customer_id = c.customer_id
    JOIN ods_inventory i
      ON r.inventory_id = i.inventory_id
    JOIN ods_film f
      ON i.film_id = f.film_id
    JOIN ods_staff s
      ON r.staff_id = s.staff_id
    JOIN ods_store st
      ON i.store_id = st.store_id
    JOIN ods_address a
      ON c.address_id = a.address_id
    JOIN ods_city ct
      ON a.city_id = ct.city_id
    JOIN ods_country co
      ON ct.country_id = co.country_id
   WHERE r.rental_date >= '${START_DATE}'
     AND r.rental_date <= '${END_DATE}';
  ```
  
  * **Use Avro Logical Types** : `True`
  
  </details>

  <details>
  <summary><strong>PutDatabaseRecord</strong> - DW 테이블에 데이터 적재</summary>
  
  Update, Insert, Upsert 등 다양한 동작을 제공한다.
  
  해당 프로세스에서는 `UPSERT`를 사용하며, 반드시 Update Key를 지정해야 한다.
  
  * **Record Reader** : `AvroReader`
  * **Database Type** : `PostgreSQL`
  * **Statement Type** : `UPSERT`
  * **Database Connection Pooling Service** : `Target_Postgresql`
  * **Table Name** : `dw_rental`
  * **Update Keys** : `rental_id`
    * 생성한 `dw_rental` 테이블의 PK
  
  </details>

  <details>
  <summary><strong>DW 프로세스 이미지</strong></summary>
  
  <img width="441" height="1065" alt="image" src="https://github.com/user-attachments/assets/5d0e70dd-a4f6-4d15-b782-cf9c93715314" />
  
  </details>

# 3. NiFi 정적 변수 설정
### 3-1. Nifi 변수 사용에 대한 이해
* Nifi에서는 동적 변수를 전역으로 선언할 수 없다. 날짜 변수처럼 동적으로 사용해야 하는 경우 적용되어야 할 프로세스 그룹 내에서 Script 형식으로 선언해야 하며, 정적변수만 Nifi에서 제공하는 Parameter Contexts 기능을 사용하여 선언할 수 있다.

### 3-2. Parameter Contexts
* 정적 변수로 가장 사용하기 쉬운 예시는 파일 경로 지정이다.
  * 프로세스 그룹 가장 상위 경로로 이동
  * 가장 우측 햄버거(3단 선) 클릭
  * Parameter Conetexts 클릭
  * 우측 '+' 클릭
    <details>
    <summary><strong>Parameter Context 생성 화면</strong></summary>
    
    팝업창 `Settings`에서 이름을 지정하고, `Parameters`에서 아래 스크린샷과 같이 설정한다.
    
    <img width="1537" height="1001" alt="image" src="https://github.com/user-attachments/assets/728b59f1-e02b-4911-a4b4-673c3e54c139" />
    
    </details>

### 3-3. Parameter Contexts 사용
* Parameter Contexts에서 선언한 변수는 프로세스 그룹을 생성할 때 팝업창에서 설정할 수 있다. (프로세스 그룹 생성 버튼 드래그 후 나오는 팝업창)
  <details>
  <summary><strong>프로세스 그룹 생성 시 Parameter Context 설정</strong></summary>
  
  <img width="706" height="443" alt="image" src="https://github.com/user-attachments/assets/3be92c95-582b-47a4-912a-3caa395076af" />
  
  </details>

* 생성한 전역 변수는 아래와 같이 File to DB 실습을 진행할 때, 아래와 파일 경로로 사용한다.
  <details>
  <summary><strong>Parameter 사용 예시</strong></summary>
  
  <img width="1534" height="456" alt="image" src="https://github.com/user-attachments/assets/e405511b-1eaa-486b-aa33-a5bc9e07f621" />
  
  </details>

> [!TIP]
> 해당 문서는 Nifi에서 가장 기본적으로 사용되는 기능과 프로세스를 설명하고 있습니다. 보다 자세한 주석이나 상세기능 설정 참고를 위해서는 로컬 PC에 Nifi를 설치하여 제공된 Json파일을 업로딩 하시기 바랍니다.
