# NiFi_주요 프로세서

---

# 1. GenerateFlowFile

  <details>
  <summary><strong>GenerateFlowFile</strong> - FlowFile 생성 및 프로세스 트리거</summary>
  
    FlowFile을 생성하는 프로세서로, 테스트 데이터 생성 또는 후속 프로세서를 실행하기 위한 트리거 용도로 사용한다.
  
  ### 주요 Properties
  
  | Property | 설명 |
  |---|---|
  | **Custom Text** | 생성할 FlowFile의 Content를 직접 지정한다. |
  | **Batch Size** | 한 번 실행할 때 생성할 FlowFile의 개수를 지정한다. |
  | **Data Format** | 생성되는 데이터의 형식을 지정한다. |
  | **Unique FlowFiles** | 생성되는 FlowFile의 Content를 서로 다르게 생성할지 여부를 지정한다. |
  | **File Size** | 생성할 FlowFile의 크기를 지정한다. |
  | **Character Set** | 텍스트 데이터의 문자 인코딩을 지정한다. 일반적으로 `UTF-8`을 사용한다. |
  | **Mime Type** | 생성되는 FlowFile의 MIME Type을 지정한다. |
  | **Run Schedule** | 프로세서의 실행 주기를 지정한다. |
  
  ### 주요 설정
  
  **트리거 용도로 사용하는 경우**
  
  * **Batch Size** : `1`
  * **Custom Text** : 필요에 따라 설정
  * **Run Schedule** : ETL 실행 구조에 맞게 설정
</details>

> [!WARNING]
> GenerateFlowFile을 주기적으로 실행하도록 설정하면 후속 프로세서도 해당 주기마다 반복 실행된다.
>
> 특히 `ExecuteSQL`, `PutDatabaseRecord` 등의 DB 처리 프로세서와 연결되어 있는 경우 의도하지 않은 중복 실행이 발생할 수 있으므로 주의해야 한다.
---

# 2. ExecuteGroovyScript
  <details>
  <summary><strong>ExecuteGroovyScript</strong> - Groovy Script 실행 및 FlowFile Attribute 생성</summary>
  
    Groovy Script를 실행하여 FlowFile의 Content 또는 Attribute를 동적으로 생성·변경할 수 있는 프로세서이다.
  
    날짜 계산, 변수 생성, 문자열 처리, 조건 분기 등 NiFi 기본 Expression Language만으로 처리하기 어려운 로직을 구현할 때 사용할 수 있다.
  
  ### 주요 Properties
  
  | Property | 설명 |
  |---|---|
  | **Script Body** | 실행할 Groovy Script를 직접 작성한다. |
  | **Script File** | 별도의 Groovy Script 파일을 지정하여 실행한다. |
  | **Module Directory** | Script에서 사용할 외부 라이브러리가 있는 디렉터리를 지정한다. |
  | **Script Engine** | Script를 실행할 Engine을 지정한다. 일반적으로 Groovy를 사용한다. |
  
  ### Script Body
  
  Groovy Script를 직접 작성하는 경우 사용한다.
  
  예를 들어 현재 날짜를 기준으로 ETL에 사용할 날짜를 생성할 수 있다.
  
  ```groovy
  import java.time.LocalDate
  import java.time.format.DateTimeFormatter
  
  def flowFile = session.get()
  if (!flowFile) return
  
  LocalDate today = LocalDate.now()
  
  // 전일
  LocalDate endDate = today.minusDays(1)
  
  // 3개월 전 1일
  LocalDate startDate = today.minusMonths(3).withDayOfMonth(1)
  
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
  
  ---

# 3. ExecuteSQL
  <details>
  <summary><strong>ExecuteSQL</strong> - SQL Query 실행 및 데이터 조회</summary>
  
    Database Connection을 통해 SQL Query를 실행하고, 조회 결과를 FlowFile로 생성하는 프로세서이다.
  
    주로 ODS 데이터를 조회하여 DW에 적재하거나, 특정 조건의 데이터를 조회하는 ETL 작업에 사용한다.
  
  ### 주요 Properties
  
  | Property | 설명 |
  |---|---|
  | **Database Connection Pooling Service** | SQL Query를 실행할 Database Connection을 지정한다. |
  | **SQL select query** | 실행할 SELECT SQL Query를 입력한다. |
  | **Max Rows Per Flow File** | 하나의 FlowFile에 포함할 최대 Row 수를 지정한다. |
  | **Output Batch Size** | 결과 데이터를 처리하는 Batch 크기를 지정한다. |
  | **Normalize Table/Column Names** | 결과의 테이블명 및 컬럼명을 정규화할지 여부를 지정한다. |
  | **Use Avro Logical Types** | DATE, TIME, TIMESTAMP 등의 데이터 타입을 Avro Logical Type으로 변환할지 여부를 지정한다. |
  | **Default Decimal Precision** | DECIMAL 타입의 기본 Precision을 지정한다. |
  | **Default Decimal Scale** | DECIMAL 타입의 기본 Scale을 지정한다. |
  
  ### Database Connection Pooling Service
  
  SQL Query를 실행할 Database Connection Pool을 지정한다.
  
  예:
  
  ```text
  TaDatabase Connection Pool : rget_Postgresql

  SQL Query :
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
  </details>
  
  ---


# 4. PutDatabaseRecord
  <details>
  <summary><strong>PutDatabaseRecord</strong> - Record 데이터를 DB에 INSERT / UPDATE / UPSERT</summary>
  
    Record Reader를 통해 FlowFile의 데이터를 읽어 DB 테이블에 저장하는 프로세서이다.
  
    `CSVReader`, `AvroReader`, `JsonTreeReader` 등의 Record Reader를 사용하여 데이터를 읽고, 지정된 Database Connection을 통해 Target DB에 INSERT, UPDATE, UPSERT 등의 작업을 수행한다.
  
  ### 주요 Properties
  
  | Property | 설명 |
  |---|---|
  | **Record Reader** | FlowFile의 Record 데이터를 읽기 위한 Controller Service를 지정한다. |
  | **Database Type** | Target DBMS의 종류를 지정한다. |
  | **Statement Type** | DB에 수행할 작업 유형을 지정한다. |
  | **Database Connection Pooling Service** | 데이터를 적재할 Target DB Connection을 지정한다. |
  | **Table Name** | 데이터를 적재할 Target DB 테이블명을 지정한다. |
  | **Update Keys** | UPDATE 또는 UPSERT 수행 시 기준이 되는 Key 컬럼을 지정한다. |
  | **Translate Field Names** | Record의 Field Name을 DB 컬럼명으로 변환할지 여부를 지정한다. |
  | **Unmatched Field Behavior** | Record의 Field와 DB 컬럼이 일치하지 않을 경우 처리 방법을 지정한다. |
  | **Unmatched Column Behavior** | DB 컬럼과 Record의 Field가 일치하지 않을 경우 처리 방법을 지정한다. |
  | **Quote Column Names** | DB 컬럼명을 SQL에서 Quote 처리할지 여부를 지정한다. |
  | **Rollback On Failure** | 하나의 FlowFile 처리 중 오류가 발생했을 때 전체 작업을 Rollback할지 여부를 지정한다. |
  

  </details>
 
  ---

# 5. QueryDatabaseTableRecord
  <details>
  <summary><strong>QueryDatabaseTableRecord</strong> - DB 테이블의 데이터를 Record 형태로 조회</summary>
  
    QueryDatabaseTableRecord는 지정된 DB 테이블을 조회하여 Record 형식의 FlowFile로 생성하는 프로세서이다.
  
    `AvroReader`, `JsonTreeReader` 등의 Record 기반 Controller Service와 연계하여 조회 결과를 Record 데이터로 처리할 수 있으며, 증분 조회를 위한 Maximum-value Columns를 설정하여 이전 실행 이후 변경된 데이터만 가져오는 방식으로도 사용할 수 있다.
  
  ### 주요 Properties
  
  | Property | 설명 |
  |---|---|
  | **Database Connection Pooling Service** | 데이터를 조회할 Source DB의 Database Connection Pool을 지정한다. |
  | **Table Name** | 데이터를 조회할 DB 테이블명을 지정한다. |
  | **Columns to Return** | 조회할 컬럼을 지정한다. 비워두면 테이블의 전체 컬럼을 조회한다. |
  | **Maximum-value Columns** | 증분 조회 시 기준이 되는 컬럼을 지정한다. 해당 컬럼의 최대값을 저장하여 다음 실행 시 이후 데이터를 조회한다. |
  | **Maximum Wait Time** | DB Connection을 획득하기 위해 대기하는 최대 시간을 지정한다. |
  | **Fetch Size** | DB에서 한 번에 가져올 Record의 개수를 지정한다. |
  | **Record Writer** | 조회한 DB 데이터를 FlowFile의 Record 형식으로 변환하기 위한 Controller Service를 지정한다. |
  | **Output Batch Size** | 하나의 FlowFile에 포함할 Record의 최대 개수를 지정한다. |
  | **Initial Load Strategy** | Maximum-value Columns를 사용하는 경우 최초 실행 시 데이터를 어떻게 조회할지 지정한다. |
  | **Where Clause** | 조회 시 적용할 추가적인 조건절을 지정한다. |
  | **Normalize Table/Column Names** | 테이블 및 컬럼명을 정규화할지 여부를 지정한다. |
  | **Default Decimal Format** | Decimal 타입 데이터를 처리할 때 사용할 기본 형식을 지정한다. |
  | **Use Avro Logical Types** | 날짜, 시간 등의 데이터를 Avro Logical Type으로 처리할지 여부를 지정한다. |
  
  </details>
 
  ---

# 6. ListFile
  <details>
  <summary><strong>ListFile</strong> - 디렉터리의 파일 목록을 조회하여 FlowFile 생성</summary>
  
    ListFile은 지정된 디렉터리를 주기적으로 스캔하여 조건에 맞는 파일을 찾아 파일 목록 정보를 FlowFile의 Attribute로 생성하는 프로세서이다.
  
    실제 파일의 데이터를 읽어오는 프로세서는 아니며, 파일의 위치와 이름, 크기, 수정 시간 등의 정보를 확인한 후 `FetchFile` 등의 프로세서와 연계하여 파일을 가져오는 용도로 사용한다.
  
  ### 주요 Properties
  
  | Property | 설명 |
  |---|---|
  | **Input Directory** | 조회할 파일이 존재하는 디렉터리 경로를 지정한다. |
  | **File Filter** | 조회할 파일의 이름을 정규식으로 필터링한다. |
  | **Path Filter** | 조회할 하위 디렉터리 경로를 정규식으로 필터링한다. |
  | **Recurse Subdirectories** | 지정한 디렉터리의 하위 디렉터리까지 탐색할지 여부를 지정한다. |
  | **Minimum File Age** | 파일의 생성 또는 수정 후 일정 시간이 지난 파일만 조회하도록 설정한다. |
  | **Maximum File Age** | 지정된 시간보다 오래된 파일을 조회 대상에서 제외한다. |
  | **Minimum File Size** | 지정된 크기보다 작은 파일을 조회 대상에서 제외한다. |
  | **Maximum File Size** | 지정된 크기보다 큰 파일을 조회 대상에서 제외한다. |
  | **Polling Interval** | 디렉터리를 다시 스캔하는 주기를 지정한다. |
  | **Target System Timestamp Precision** | 파일의 수정 시간 등을 비교할 때 사용할 Timestamp 정밀도를 지정한다. |
  | **Entity Tracking State Cache** | 이미 처리한 파일을 추적하여 동일한 파일을 반복적으로 조회하지 않도록 관리한다. |
  
  ### Input Directory
  
  파일을 조회할 디렉터리의 절대 경로를 지정한다.
  
  예:
  
  ```text
  /opt/nifi/input

  </details>
 
  ---
