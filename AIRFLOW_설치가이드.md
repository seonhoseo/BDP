# Airflow 설치 가이드

---

# 1. 설치 환경 세팅

##### 1-1. root 계정 전환 및 패키지 업데이트

```bash
sudo su

apt update
apt upgrade -y
```

##### 1-2. Airflow 설치에 필요한 패키지 설치

```bash
apt install -y \
python3.14-venv \
curl \
wget \
vim \
nano \
git \
unzip \
zip \
net-tools \
lsof \
build-essential \
libssl-dev \
libffi-dev \
libpq-dev
```

##### 1-3. OS 재부팅

```bash
sudo reboot
```

---

# 2. 사용자 및 설치 경로 확인

별도 계정을 생성하지 않고 현재 계정(`bdpadmin`)으로 Airflow를 설치한다.

##### 2-1. 현재 경로 확인

```bash
pwd
```

```text
/home/bdpadmin
```

---

# 3. Airflow 환경 변수 설정

##### 3-1. AIRFLOW_HOME 환경 변수 등록

```bash
echo "export AIRFLOW_HOME=/home/bdpadmin/airflow" >> ~/.bashrc

source ~/.bashrc
```

##### 3-2. 환경 변수 확인

```bash
echo $AIRFLOW_HOME
```

```text
/home/bdpadmin/airflow
```

---

# 4. Python 가상환경 생성

Airflow는 별도의 Python 가상환경에서 설치 및 운영한다.

##### 4-1. 가상환경 생성

```bash
python3.14 -m venv ~/airflow_venv
```

##### 4-2. 가상환경 활성화

```bash
source ~/airflow_venv/bin/activate
```

##### 4-3. Python 경로 확인

```bash
which python
```

```text
/home/bdpadmin/airflow_venv/bin/python
```

> **Note**
>
> 이후 Airflow 관련 설치 및 명령어는 가상환경이 활성화된 상태에서 진행한다.
>
> ```bash
> source ~/airflow_venv/bin/activate
> ```

---

# 5. Apache Airflow 설치

##### 5-1. Python 패키지 도구 업데이트

```bash
pip install --upgrade pip setuptools wheel
```

##### 5-2. Airflow Constraint URL 설정

```bash
export CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-3.3.0/constraints-3.14.txt"
```

##### 5-3. Airflow 3.3.0 설치

```bash
pip install "apache-airflow==3.3.0" --constraint "${CONSTRAINT_URL}"
```

##### 5-4. Airflow 버전 확인

```bash
airflow version
```


---

# 6. DAG 폴더 생성

##### 6-1. DAG 폴더 생성

```bash
mkdir -p ~/airflow/dags
```

##### 6-2. Airflow 홈 디렉터리 확인

```bash
ls ~/airflow
```

```text
dags
logs
```

---

# 7. PostgreSQL 설치 및 Airflow Database 구성

Airflow Metadata Database로 PostgreSQL을 사용한다.

##### 7-1. PostgreSQL 설치

```bash
sudo apt update

sudo apt install -y postgresql postgresql-contrib
```

##### 7-2. PostgreSQL 서비스 상태 확인

```bash
sudo systemctl status postgresql
```

##### 7-3. PostgreSQL 접속

```bash
sudo -u postgres psql
```

##### 7-4. Airflow용 사용자 생성

```sql
CREATE USER bdpadmin WITH PASSWORD 'bdpadminPW!';
```

##### 7-5. Airflow Database 생성

```sql
CREATE DATABASE airflow OWNER bdpadmin;
```

##### 7-6. PostgreSQL 종료

```sql
\q
```

##### 7-7. PostgreSQL Port 확인

```bash
sudo ss -lntp | grep 5432
```

```text
LISTEN 0 244 127.0.0.1:5432 ...
```

---

# 8. PostgreSQL Provider 설치 및 연결 설정

##### 8-1. 현재 Python 및 pip 경로 확인

```bash
which python
which pip
```

```text
/home/bdpadmin/airflow_venv/bin/python
/home/bdpadmin/airflow_venv/bin/pip
```

##### 8-2. PostgreSQL Provider 및 psycopg2 설치

```bash
pip install apache-airflow-providers-postgres psycopg2-binary
```

##### 8-3. Provider 설치 확인

```bash
pip show apache-airflow-providers-postgres
```

##### 8-4. Airflow Database Connection 환경 변수 등록

```bash
echo "export AIRFLOW__DATABASE__SQL_ALCHEMY_CONN='postgresql+psycopg2://bdpadmin:bdpadminPW%21@dfodev.iptime.org:5432/airflow'" >> ~/.bashrc

source ~/.bashrc
```

##### 8-5. 환경 변수 확인

```bash
echo $AIRFLOW__DATABASE__SQL_ALCHEMY_CONN
```

```text
postgresql+psycopg2://bdpadmin:bdpadminPW%21@dfodev.iptime.org:5432/airflow
```

---

# 9. PostgreSQL 연결 테스트 및 Airflow DB 초기화

##### 9-1. 가상환경 활성화

```bash
source ~/airflow_venv/bin/activate
```

##### 9-2. PostgreSQL 연결 테스트

```bash
python -c "import psycopg2; conn=psycopg2.connect('postgresql://bdpadmin:bdpadminPW%21@dfodev.iptime.org:5432/airflow'); print('PostgreSQL connection OK'); conn.close()"
```

##### 9-3. Airflow Database Migration

```bash
airflow db migrate
```

```text
Database migration done!
```

---

# 10. Airflow 인증 관리자 설정

Airflow Web UI의 인증을 위해 FAB Provider를 설치한다.

##### 10-1. FAB Provider 설치

```bash
pip install apache-airflow-providers-fab
```

##### 10-2. Auth Manager 환경 변수 등록

```bash
echo 'export AIRFLOW__CORE__AUTH_MANAGER="airflow.providers.fab.auth_manager.fab_auth_manager.FabAuthManager"' >> ~/.bashrc

source ~/.bashrc
```

##### 10-3. Auth Manager 설정 확인

```bash
echo $AIRFLOW__CORE__AUTH_MANAGER
```

```text
airflow.providers.fab.auth_manager.fab_auth_manager.FabAuthManager
```

> **Note**
>
> 환경 변수 등록 후 가상환경에 다시 진입한다.
>
> ```bash
> source ~/airflow_venv/bin/activate
> ```
>
> 이후 Database Migration을 다시 수행한다.
>
> ```bash
> airflow db migrate
> ```

---

# 11. Airflow Admin 계정 생성

##### 11-1. 관리자 계정 생성

```bash
airflow users create \
--username admin \
--firstname Airflow \
--lastname Admin \
--role Admin \
--email admin@test.com \
--password 'AdminPW!'
```

```text
User "admin" created with role "Admin"
```

##### 11-2. 사용자 목록 확인

```bash
airflow users list
```

정상적으로 생성되었다면 다음과 같이 확인할 수 있다.

```text
id | username | email          | first_name | last_name | roles
===+==========+================+============+===========+======
1  | admin    | admin@test.com | Airflow    | Admin     | Admin
```

> **Note**
>
> `airflow users list` 실행 시 `PendingDeprecationWarning` 등의 경고 메시지가 출력될 수 있으나, 사용자 목록이 정상적으로 출력되면 Admin 계정 생성은 완료된 것이다.

---

# 12. Airflow 서버 실행

Airflow 3.x에서는 API Server, Scheduler, DAG Processor, Triggerer를 각각 실행한다.

##### 12-1. 가상환경 활성화

```bash
source ~/airflow_venv/bin/activate
```

##### 12-2. API Server 실행

```bash
airflow api-server
```

정상 실행 시 다음과 같이 확인된다.

```text
Running on http://0.0.0.0:8080
```

##### 12-3. 백그라운드 실행

터미널을 종료해도 프로세스가 유지되도록 `nohup`을 사용한다.

```bash
nohup airflow api-server > ~/airflow/logs/api-server.log 2>&1 &
nohup airflow scheduler > ~/airflow/logs/scheduler.log 2>&1 &
nohup airflow dag-processor > ~/airflow/logs/dag-processor.log 2>&1 &
nohup airflow triggerer > ~/airflow/logs/triggerer.log 2>&1 &
```

##### 12-4. 프로세스 실행 여부 확인

```bash
ps -ef | grep airflow
```

또는

```bash
ps -ef | grep -E "api-server|scheduler|dag-processor|triggerer"
```

##### 12-5. API Server Port 확인

```bash
sudo ss -lntp | grep 8080
```

정상적으로 API Server가 실행 중이라면 `8080` Port가 LISTEN 상태로 표시된다.

---

# 13. Airflow Web UI 접속

브라우저에서 다음 주소로 접속한다.

```text
http://dfodev.iptime.org:8080
```

관리자 계정:

```text
ID : admin
PW : AdminPW!
```

---

# 14. 주요 설치 경로 및 명령어 정리

| 항목 | 경로 / 명령 |
|---|---|
| 현재 사용자 | `bdpadmin` |
| Airflow Home | `/home/bdpadmin/airflow` |
| DAG 경로 | `/home/bdpadmin/airflow/dags` |
| Log 경로 | `/home/bdpadmin/airflow/logs` |
| Python 가상환경 | `/home/bdpadmin/airflow_venv` |
| Python | `/home/bdpadmin/airflow_venv/bin/python` |
| pip | `/home/bdpadmin/airflow_venv/bin/pip` |
| PostgreSQL | `dfodev.iptime.org:5432` |
| Airflow DB | `airflow` |
| Airflow DB 사용자 | `bdpadmin` |
| Airflow API Server | `0.0.0.0:8080` |

---

# 15. Airflow 프로세스 관리

##### 15-1. 프로세스 확인

```bash
ps -ef | grep airflow
```

##### 15-2. API Server 로그 확인

```bash
tail -f ~/airflow/logs/api-server.log
```

##### 15-3. Scheduler 로그 확인

```bash
tail -f ~/airflow/logs/scheduler.log
```

##### 15-4. DAG Processor 로그 확인

```bash
tail -f ~/airflow/logs/dag-processor.log
```

##### 15-5. Triggerer 로그 확인

```bash
tail -f ~/airflow/logs/triggerer.log
```

---

> [!Note]
> 해당 문서는 dfodev.iptime.org 도메인 명으로 작성된 문서로, 개인 로컬 PC에서 진행할 시 localhost 등으로 적절히 변경하여 사용해야 합니다.
