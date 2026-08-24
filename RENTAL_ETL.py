"""
==============================================================================
DAG NAME    : RENTAL_ETL
AUTHOR      : seoseonho
DESCRIPTION : Rental ETL Orchestration
==============================================================================

■ 목적
------------------------------------------------------------------------------
본 DAG는 Apache Airflow를 이용하여 Apache NiFi ETL 작업과
PostgreSQL MART 생성 작업을 순차적으로 실행하는 오케스트레이션 DAG이다.

Airflow는 실제 데이터를 처리하지 않는다.

데이터 추출 및 적재(ETL)는 NiFi가 수행하며,
Airflow는 각 작업의 실행 순서와 성공/실패를 제어하는 역할을 담당한다.

즉,

Airflow = "지휘자"
NiFi     = "실제 작업자"

라고 생각하면 이해하기 쉽다.

------------------------------------------------------------------------------

■ 전체 실행 순서
------------------------------------------------------------------------------

① ODS 테이블 초기화(TRUNCATE)

↓

② NiFi ODS Process Group 실행

↓

③ ODS 적재 완료 대기

↓

④ ODS Process Group 종료

↓

⑤ NiFi DW Process Group 실행

↓

⑥ DW 완료 대기

↓

⑦ DW Process Group 종료

↓

⑧ PostgreSQL Stored Procedure 실행

↓

⑨ MART 생성 완료

------------------------------------------------------------------------------

■ Architecture
------------------------------------------------------------------------------

                +----------------------+
                |      Airflow         |
                |  (Orchestration)     |
                +----------+-----------+
                           |
                           
                           |
                           ▼
                +----------------------+
                |     NiFi ODS         |
                | MySQL → PostgreSQL   |
                +----------+-----------+
                           |
                           ▼
                     PostgreSQL ODS
                           |
                           ▼
                +----------------------+
                |      NiFi DW         |
                | Business Logic ETL   |
                +----------+-----------+
                           |
                           ▼
                     PostgreSQL DW
                           |
                           ▼
                Stored Procedure
                           |
                           ▼
                        MART TABLE

------------------------------------------------------------------------------

■ 역할 분담
------------------------------------------------------------------------------

Airflow
    - ETL 실행 순서 관리
    - 스케줄 관리
    - 실패 감지
    - 재실행
    - 모니터링

NiFi
    - 데이터 추출
    - 데이터 변환
    - 데이터 적재
    - DW 생성

PostgreSQL
    - ODS 저장
    - DW 저장
    - MART 생성

------------------------------------------------------------------------------
"""
from airflow import DAG
# ============================================================================
# PythonOperator
# ============================================================================
# Airflow에서 Python 함수를 하나의 Task로 실행하기 위한 Operator이다.
#
# 예를 들어 truncate_ods() 라는 함수를 Airflow Task로 등록할 수 있다.
from airflow.providers.standard.operators.python import PythonOperator
# ============================================================================
# PostgresHook
# ============================================================================
# Airflow Connection에 등록된 PostgreSQL 정보를 이용하여 SQL 실행, Stored Procedure 호출 등을 수행하기 위한 Hook이다.
#
# 직접 psycopg2를 사용할 필요 없이 Airflow Connection만 지정하면 된다.
from airflow.providers.postgres.hooks.postgres import PostgresHook

# ============================================================================
# pendulum
# ============================================================================
# Airflow에서 권장하는 날짜/시간 라이브러리 timezone 처리가 매우 편리하다.
# 예)
# pendulum.now("Asia/Seoul")는 현재 한국 시간을 반환한다.
import pendulum
# ============================================================================
# requests
# ============================================================================
# NiFi REST API 호출을 위한 라이브러리
#
# 본 프로젝트에서는 Access Token 발급, Process Group 상태 조회, Process Group 실행, Process Group 중지 등을 수행한다.
import requests
import urllib3
import time


urllib3.disable_warnings()


# ==========================================================
# NiFi
# ==========================================================

NIFI_URL = "https://dfodev.iptime.org:8443"

NIFI_USER = "bdpadmin"
NIFI_PASSWORD = "BDPadminPW!!"

# ============================================================================
# Process Group Dictionary
# ============================================================================
# Process Group 이름과 ID를 매핑한다.
#
# Key(사람이 이해하기 쉬운 이름) = {
#
#   Value(NiFi 내부 Process Group ID)
#   }
# Airflow에서는 PG["ODS"] 처럼 사용한다.
PG = {

    "ODS": "7d509820-019f-1000-5849-5f0db9654090",

    "DW": "461052c9-019f-1000-36a9-7f337cdec358"

}


# ==========================================================
# PostgreSQL
# ==========================================================

POSTGRES_CONN_ID = "postgres_rnd"



# ==========================================================
# NiFi Common
# ==========================================================
"""
    ==========================================================
    def get_nifi_token() 목적
    ==========================================================

    NiFi REST API 인증 토큰을 발급받는다.

    NiFi는 대부분의 REST API 호출 시

        Bearer Token

    인증을 요구한다.

    따라서 Process Group 실행/중지/조회 전에
    반드시 이 함수를 호출해야 한다.

    ==========================================================
    처리 순서

    1. username/password 전달

    2. /access/token 호출

    3. JWT Token 반환

    ==========================================================
    반환값

    str

        Bearer Token

    ==========================================================
    사용 함수

    change_pg_state()

    wait_until_finished()

    ==========================================================
    """
def get_nifi_token():


    response = requests.post(

        f"{NIFI_URL}/nifi-api/access/token",

        headers={
            "Content-Type": "application/x-www-form-urlencoded"
        },

        data={

            "username": NIFI_USER,

            "password": NIFI_PASSWORD

        },

        verify=False

    )


    response.raise_for_status()


    return response.text


"""
    ==========================================================
    def change_pg_state(pg_id, state) 목적
    ==========================================================

    지정한 Process Group의 실행 상태를 변경한다.

    실행

        RUNNING

    중지

        STOPPED

    ==========================================================

    왜 Revision을 먼저 조회하는가?

    NiFi는 동시 수정(Concurrency)을 방지하기 위해

        Revision

    정보를 이용한다.

    따라서 상태 변경 전에

    현재 Revision을 반드시 조회해야 한다.

    조회하지 않으면

    HTTP 409 Conflict

    오류가 발생한다.

    ==========================================================

    처리 순서

    ① Access Token 발급

    ② 현재 Revision 조회

    ③ Payload 생성

    ④ PUT 요청

    ==========================================================

    Parameter

    pg_id

        Process Group ID

    state

        RUNNING

        STOPPED

    ==========================================================
    """
def change_pg_state(pg_id, state):


    token = get_nifi_token()


    headers = {

        "Authorization": f"Bearer {token}",

        "Content-Type": "application/json"

    }


    response = requests.get(

        f"{NIFI_URL}/nifi-api/process-groups/{pg_id}",

        headers=headers,

        verify=False

    )


    response.raise_for_status()


    revision = response.json()["revision"]


    payload = {

        "revision": revision,

        "id": pg_id,

        "state": state

    }


    response = requests.put(

        f"{NIFI_URL}/nifi-api/flow/process-groups/{pg_id}",

        headers=headers,

        json=payload,

        verify=False

    )


    response.raise_for_status()


    print(f"{state} : {pg_id}")




def wait_until_finished(pg_id):


    token = get_nifi_token()


    headers = {

        "Authorization": f"Bearer {token}"

    }

    # ---------------------------------------------------------
    # ETL 완료 여부 확인 Loop
    #
    # Active Thread가 0이 될 때까지
    # 계속 조회한다.
    # ---------------------------------------------------------
    while True:


        response = requests.get(

            f"{NIFI_URL}/nifi-api/flow/process-groups/{pg_id}/status",

            headers=headers,

            verify=False

        )


        response.raise_for_status()

        # -----------------------------------------------------
        # 현재 Process Group에서 실행 중인 Thread 개수
        # -----------------------------------------------------
        active_thread = (

            response.json()

            ["processGroupStatus"]

            ["aggregateSnapshot"]

            ["activeThreadCount"]

        )


        print(f"Active Thread : {active_thread}")

        # -----------------------------------------------------
        # Active Thread가 0이면
        #
        # 모든 Processor가 종료된 상태
        # -----------------------------------------------------
        if active_thread == 0:

            print("Process Group Finished")

            break


        time.sleep(3)




# ==========================================================
# ODS
# ==========================================================

def truncate_ods():


    hook = PostgresHook(

        postgres_conn_id=POSTGRES_CONN_ID

    )


    hook.run(
    """
    TRUNCATE TABLE
        ods_rental,
        ods_customer,
        ods_inventory,
        ods_film,
        ods_staff,
        ods_store,
        ods_address,
        ods_city,
        ods_country;
    """
)



# ==========================================================
# ODS 프로세스 그룹 상태 전환 함수 선언
# ==========================================================
def start_ods():

    change_pg_state(

        PG["ODS"],

        "RUNNING"

    )




def wait_ods():

    wait_until_finished(

        PG["ODS"]

    )




def stop_ods():

    change_pg_state(

        PG["ODS"],

        "STOPPED"

    )





# ==========================================================
# DW 프로세스 그룹 상태 전환 함수 선언
# ==========================================================

def start_dw():

    change_pg_state(

        PG["DW"],

        "RUNNING"

    )




def wait_dw():

    wait_until_finished(

        PG["DW"]

    )




def stop_dw():

    change_pg_state(

        PG["DW"],

        "STOPPED"

    )





# ==========================================================
# MART 적재 프로시저 함수 선언
# ==========================================================

def execute_mart():


    hook = PostgresHook(

        postgres_conn_id=POSTGRES_CONN_ID

    )


    today = pendulum.now("Asia/Seoul")


    # 파라미터
    #start_date = (

    #    today

    #    .subtract(months=3)

    #    .start_of("month")

    #    .format("YYYY-MM-DD")

    #)
    

    #end_date = (

    #    today

    #    .subtract(days=1)

    #    .format("YYYY-MM-DD")

    #)
    # rental 테이블 내 데이터가 존재하는 기간으로 start_date와 end_date를 설정
    start_date = "2005-05-24"
    end_date = "2006-02-15"


    sql = f"""

    
        CALL sp_dm_rental_flag(

            '{start_date}',

            '{end_date}'

        );

    """


    hook.run(sql)


    print(

        f"""

        MART LOAD COMPLETE

        START DATE : {start_date}

        END DATE   : {end_date}

        """

    )





# ==========================================================
# DAG
# ==========================================================

with DAG(


    dag_id="RENTAL_ETL",


    start_date=pendulum.datetime(

        2026,

        1,

        1,

        tz="Asia/Seoul"

    ),


    # 매일 새벽 1시

    schedule="0 1 * * *",


    catchup=False,


    tags=[

        "NiFi",

        "ETL",

        "Rental"

    ]


) as dag:

    # 위에서 선언한 각 함수 호출

    truncate = PythonOperator(

        task_id="truncate_ods",

        python_callable=truncate_ods

    )



    ods_start = PythonOperator(

        task_id="start_ods",

        python_callable=start_ods

    )



    ods_wait = PythonOperator(

        task_id="wait_ods",

        python_callable=wait_ods

    )



    ods_stop = PythonOperator(

        task_id="stop_ods",

        python_callable=stop_ods

    )



    dw_start = PythonOperator(

        task_id="start_dw",

        python_callable=start_dw

    )



    dw_wait = PythonOperator(

        task_id="wait_dw",

        python_callable=wait_dw

    )



    dw_stop = PythonOperator(

        task_id="stop_dw",

        python_callable=stop_dw

    )



    mart = PythonOperator(

        task_id="execute_mart",

        python_callable=execute_mart

    )




    (

        truncate

        >> ods_start

        >> ods_wait

        >> ods_stop

        >> dw_start

        >> dw_wait

        >> dw_stop

        >> mart

    )