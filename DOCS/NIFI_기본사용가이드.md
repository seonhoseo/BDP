# Nifi 기본사용 가이드

---

# 1. 나이파이 DB 연결 세팅

#### 1-1. DB커넥션 생성
* 캔버스 > 빈 공간 우클릭 > Controller Services 클릭 > 우측 '+' 클릭 > DBCPConnectionPool 조회하여 Add
#### 1-2. DB커넥션 설정
* Database Connection URL : jdbc:mysql://<host>:<port>/<dbname>?allowPublicKeyRetrieval=true
(ex. jdbc:mysql://dfodev.iptime.org:32306/sakila?allowPublicKeyRetrieval=true)
* Database Driver Class Name : com.mysql.cj.jdbc.Driver
* Database Driver Location(s) : /opt/nifi/lib/mysql-connector-j-9.3.0.jar
* Database User : db유저명
* Password : db패스워드
<img width="1531" height="1012" alt="image" src="https://github.com/user-attachments/assets/f462d9d5-e5fd-448f-bc29-ccc2b80b2899" />

> [!NOTE]
> 설정 변경 완료 후, 해당 커넥션 우측 점3개 클릭하여 Enable.
> 프로세스 그룹 가장 상위에서 생성해야 전역 변수처럼 사용할 수 있다.

# 2. 나이파이 기본 ETL 프로세스 생성
#### 2-1. File to DB
* 사용 프로세서 : ListFile, FetchFile, PutSQL, PutDatabaseRecord
* **$${\color{blue}ListFile}$$** : 읽어올 파일의 메타데이터를 생성
  * Input Directory : /home/bdpadmin/input (실제 파일 경로 기입)
  * Listing Strategy : No Tracking
  * File Filter : .*\.csv (csv 파일만 읽겠다는 의미이다.)
  * Minimum File Age : 30 sec (생성 후 30초가 지난 파일만 읽는다. 만약 대용량 파일을 복사하는 중이라면 다른 파일을 바로 읽는것을 방지하고자 함이다.)
* **$${\color{blue}FecthFile}$$** : ListFile에서 생성된 파일의 메타데이터 정보를 사용하여 실제로 파일을 읽어온다.
  * File to Fetch : ${absolute.path}/${filename}
  * Completion Strategy : Move File (정상 수행 후 파일을 다른 경로로 옮긴다.)
  * Move Destination Directory : /home/bdpadmin/archieve
* <span style="color:#FF0000"><strong>PutSQL</strong></span> : Insert 전 Truncate를 수행한다.
  * JDBC Connection Pool : Target_Postgresql (생성한 DBCPConnectionPool 중 타겟 DB를 선택한다.)
  * SQL Statement : TRUNCATE TABLE public.customer_file;
* **PutDatabaseRecord** : DB에 데이터를 INSERT 한다.
  * Record Reader : CSVReader (CSV 파일을 읽기 위한 Controller Services다.)
  * Database Type : PostgreSQL (Generic으로 지정해도 무방하지만, 타입 변환 문제 등으로 인하여 실제 사용하는 DBMS로 지정해주는 것이 좋다.)
  * Statement Type : INSERT
  * Database Connection Pooling Service : Target_Postgresql
  * Table Name : customer_file (실제 엑셀 파일 데이터를 INSERT 하기 위해 생성한 테이블명을 기입한다.) 
<img width="338" height="716" alt="image" src="https://github.com/user-attachments/assets/b9dc1d0c-8d6f-4797-9d1f-6454b7400ca5" />

> [!WARNING]
> CSVReader, AvroReader 등 DBCPConnectionPool을 제외한 각종 프로세서에서 사용되는 Controller Services 등은 프로세스 그룹 가장 상위가 아닌 현재 작업중인 프로세스 그룹 내에서 선언하여 지역변수처럼 사용하여야 한다. 각 프로세스 그룹 내에서 사용되는 서비스의 상세 설정이 다를 수 있기 때문이다.

#### 2-1. SourceDB > TargerDB
* ODS (Staging)
  * 사용 프로세서 : QueryDatabseTableRecord, PutDatabaseRecord
  * **QueryDatabseTableRecord** : 소스DB 테이블을 조회한다.
    * Database Connection Pooling Service : Source_Mysql
    * Database Type : MySQL
    * Table Name : rental
    * Record Writer : AvroRecordSetWriter
  * **PutDatabaseRecord**
    * Record Reader : AvroReader
    * Database Type : PostgreSQL
    * Statement Type : INSERT
    * Database Connection Pooling Service : Target_Postgresql
    * Table Name : ods_rental
<img width="1621" height="867" alt="image" src="https://github.com/user-attachments/assets/049ff427-ac1a-47dc-b66f-781fd049bfc1" />

* DW
  * 사용 프로세서 : GenerateFlowFile, ExecuteGroovyScript, ExecuteSQL, PutDatabaseRecord, UpdateAttribute, ReplaceText, PutDatabaseRecord
  * **GenerateFlowFile** (트리거 프로세서) : 트리거 없이 실행될 수 있는 프로세서와 그렇지 않은 프로세서들이 있다. Querydatabaserecord와 같은 프로세서는 트리거 없이 독립 실행될 수 있지만, Execute~ 와 같이 트리거 없이 실행될 수 없는 프로세서들도 있어 GenerateFlowFile 프로세서를 트리거 역할로 사용해야 한다.
    * Default 값으로 진행한다.
  * **ExecuteGroovyScript** (전역/동적 변수 생성 프로세서) : Nifi에서는 동적 변수를 전역으로 선언할 수 없다. 지역 동적 변수를 사용하기 위해서는 해당 프로세서처럼 스크립트로 선언해야 한다.
    * Script Body : 아래 코드는 날짜 변수를 사용하기 위한 예시이다.
    ```
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
  * ExecuteSQL (SQL Query 실행 프로세서) : SQL 쿼리를 수행하는 프로세서. ODS에서 DW로 ETL 하는 조인쿼리문을 수행한다.
    * Database Connection Pooling Service : Target_Postgresql
    * SQL select query
    ```
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
           now() as etl_dt
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
    
    * Use Avro Logical Types : True
<img width="441" height="1065" alt="image" src="https://github.com/user-attachments/assets/5d0e70dd-a4f6-4d15-b782-cf9c93715314" />

3. 병렬 처리
4. 프로세서 상세 기능
