```
∘ OS 터미널(SSH) 접속정보
  ∘ HOST : dfodev.iptime.org
  ∘ PORT : 10130
  ∘ ID/PW : bdpadmin / BDPadminPW!
∘ App. 접속정보
  ∘ EB-URL : https://dfodev.iptime.org:8443/nifi
  ∘ ID/PW : bdpadmin / BDPadminPW!!
```
---
# 1. 설치 환경 세팅
##### 1-1. root 계정 전환 및 패키지 업데이트
```bash
sudo su
apt update
```
##### 1-2. Java 다운로드
```bash
apt install openjdk-21-jdk -y

* 다운로드 확인 *
java -version
```
##### 1-3. JAVA_HOME 환경변수 등록
```bash
nano /etc/profile

* 파일 하단에 아래 코드 추가 *
export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
export PATH=$JAVA_HOME/bin:$PATH

* 변경 사항 적용 *
source /etc/profile
echo $JAVA_HOME
```

# 2. NIFI 설치
##### 2-1. NIFI 파일 다운로드
```bash
* opt 경로에 압축파일 다운로드 *
cd /opt
wget https://archive.apache.org/dist/nifi/2.2.0/nifi-2.2.0-bin.zip

* 압축 해제 *
apt install unzip -y
unzip nifi-2.2.0-bin.zip
```
##### 2-2. 폴더명 및 소유주 변경
```bash
* 경로 탐색 용이 위해 nifi-2.2.0 > nifi 로 폴더명 변경 *
mv nifi-2.2.0 nifi

* 현재 소유주 확인 *
ls -ld /opt/nifi

* 소유주 변경 *
chown -R bdpadmin:bdpadmin /opt/nifi
ls -ld /opt/nifi

* Java 설치 및 등록여부 재확인 *
java -version
echo $JAVA_HOME
```

# 3. NIFI 설정
##### 3-1. https 세팅
```bash
* NIFI 설정 파일 경로로 이동 *
cd /opt/nifi/conf

* Keystore 생성 *
* 아래 코드 그대로 사용하되 서버 정보 변경 시 DNS, IP는 서버 정보 입력, storepass, keypass는 변경 가능) *
keytool -genkeypair \
-alias nifi \
-keyalg RSA \
-keysize 2048 \
-validity 3650 \
-storetype PKCS12 \
-keystore keystore.p12 \
-storepass 'BDPadminPW!!' \
-keypass 'BDPadminPW!!' \
-dname "CN=dfodev.iptime.org, OU=IT, O=Company, L=Seoul, ST=Seoul, C=KR" \
-ext SAN=DNS:dfodev.iptime.org,IP:192.168.0.130

* 인증서 export *
keytool -exportcert \
-rfc \
-alias nifi \
-keystore keystore.p12 \
-storepass 'BDPadminPW!!' \
-file nifi-cert.pem

* Truststore 생성 *
keytool -importcert \
-alias nifi \
-file nifi-cert.pem \
-keystore truststore.p12 \
-storetype PKCS12 \
-storepass 'BDPadminPW!!' \
-noprompt

* 인증서 생성 확인((keystore.p12, truststore.p12, nifi-cert.pem) *
ls

* 인증서[Keystore.p12] 정상 반영 확인 (Alias name: nifi) *
keytool \
-list \
-v \
-keystore keystore.p12 \
-storepass 'BDPadminPW!!'

* 인증서[truststore.p12] 정상 반영 확인 (Alias name: nifi) *
keytool \
-list \
-v \
-keystore truststore.p12 \
-storepass 'BDPadminPW!!'
```
##### 3-2. nifi.properties 세팅
```bash
* 기존 파일 백업 *
cp nifi.properties nifi.properties.bak

* nifi.properties 수정 *
nano nifi.properties

--->
nifi.web.http.host=
nifi.web.http.port=
	
nifi.web.https.host=192.168.0.130
nifi.web.https.port=8443
	
nifi.security.keystore=/opt/nifi/conf/keystore.p12
nifi.security.keystoreType=PKCS12
nifi.security.keystorePasswd=BDPadminPW!!
nifi.security.keyPasswd=BDPadminPW!!
	
nifi.security.truststore=/opt/nifi/conf/truststore.p12
nifi.security.truststoreType=PKCS12
nifi.security.truststorePasswd=BDPadminPW!!
	
nifi.sensitive.props.key=NiFiStudy2026!
nifi.web.proxy.host=dfodev.iptime.org:8443
```

##### 3-3. users 생성
```bash
* PW는 12자 이상으로 설정 *
cd /opt/nifi/bin
./nifi.sh set-single-user-credentials bdpadmin 'BDPadminPW!!'
```

# 4. NIFI 실행
##### 4-1. NIFI 서비스 시작
```bash
./nifi.sh start
./nifi.sh status

* 아래와 같은 문구가 보인다면 성공 *
2026-07-06 02:34:04,029 INFO [main] org.apache.nifi.bootstrap.Command Application Process [4694] Command Status [SUCCESS] HTTP 200
2026-07-06 02:34:04,031 INFO [main] org.apache.nifi.bootstrap.Command Status: UP
```
##### 4-2. NIFI 웹 접속
+ https://dfodev.iptime.org:8443/nifi 로 접속
  + bdpadmin / BDPadminPW!!

##### 4-3. NIFI 서비스 등록
```bash
* 개발환경이므로 실제 등록 X, 참고용으로 AI 내용 기반으로 작성됨. 실제 적용 시에는 추가 검증이 필요함 *
sudo su
nano /etc/systemd/system/nifi.service

* 편집기 내 아래 코드 붙여넣기 *
[Unit]
Description=Apache NiFi
After=network.target

[Service]
Type=forking

User=bdpadmin
Group=bdpadmin

Environment=JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
Environment=NIFI_HOME=/opt/nifi

ExecStart=/opt/nifi/bin/nifi.sh start
ExecStop=/opt/nifi/bin/nifi.sh stop
ExecReload=/opt/nifi/bin/nifi.sh restart

Restart=on-failure
RestartSec=5

LimitNOFILE=50000
TimeoutStopSec=300

[Install]
WantedBy=multi-user.target

* 서비스 로드 및 등록(자동 시작) *
sudo systemctl daemon-reload
sudo systemctl enable nifi
```

# 5. NIFI Heap 설정
```bash
cd /opt/nifi/conf/bootstrap.conf

* Java Heap 설정은 bootstrap.conf 파일에서 수행하며, 아래와 같은 내용으로 적절히 반영 *
grep java.arg bootstrap.conf

* -Xms : 초기 Heap / -Xmx : 최대 Heap *
* 아래는 NIFI 설치 시 되어있는 기본 세팅 값 *
java.arg.2=-Xms1g
java.arg.3=-Xmx1g

* Java Heap은 서버 메모리에 따라 수정 반영 *
메모리 8GB
-Xms4g
-Xmx4g
메모리 16GB
-Xms8g
-Xmx8g
메모리 32GB
-Xms12g
-Xmx12g

* 현재 서버 메모리는 8GB로 사용하므로 수정 *
nano bootstrap.conf
* 개발환경이므로 1g > 2g로 변경. 운영 환경에서는 4g로 변경 요망 *
java.arg.2=-Xms2g
java.arg.3=-Xmx2g
```

> [!Note]
> 해당 문서는 dfodev.iptime.org 도메인 기준입니다. 개인 로컬 PC에서 진행할 시 localhost 등으로 적절히 변경하여 사용해야 하며, Keystore, Truststore 등 인증서 과정은 Skip 하시기 바랍니다.
> 
> 3절 NIFI 설정 부분에서 https 부분은 Default 값으로 두고 nifi.web.http.host=0.0.0.0, nifi.web.http.port=8080 부분만 수정하면 개인 로컬PC 환경 세팅이 됩니다.
