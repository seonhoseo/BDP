1. 나이파이 DB 연결 세팅
* DB커넥션 생성
캔버스 > 빈 공간 우클릭 > Controller Services 클릭 > 우측 '+' 클릭 > DBCPConnectionPool 조회하여 Add
* DB커넥션 설정
Database Connection URL : jdbc:mysql://<host>:<port>/<dbname>?allowPublicKeyRetrieval=true
(ex. jdbc:mysql://dfodev.iptime.org:32306/sakila?allowPublicKeyRetrieval=true)
Database Driver Class Name : com.mysql.cj.jdbc.Driver
Database Driver Location(s) : /opt/nifi/lib/mysql-connector-j-9.3.0.jar
Database User : db유저명
Password : db패스워드
<img width="1531" height="1012" alt="image" src="https://github.com/user-attachments/assets/f462d9d5-e5fd-448f-bc29-ccc2b80b2899" />

> [!NOTE]
> 설정 변경 완료 후, 해당 커넥션 우측 점3개 클릭하여 Enable.
> 프로세스 그룹 가장 상위에서 생성해야 전역 변수처럼 사용할 수 있습니다.

2. 나이파이 기본 ETL 프로세스 생성
  2-1. File to DB
  2-2. SourceDB > TargerDB
3. 병렬 처리
4. 프로세서 상세 기능
