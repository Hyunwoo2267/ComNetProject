# Docker 사용 가이드 (v2.0)

## 개요

이 프로젝트는 **Docker Compose 멀티 컨테이너 방식**으로 네트워크 보안 게임 환경을 구성합니다.

**v2.0 아키텍처**:
- **서버**: Docker 컨테이너 (172.20.0.254)
- **플레이어 (Player1~4)**: 각각 독립된 Docker 컨테이너 (172.20.0.1~4)
- **네트워크**: 사용자 정의 브리지 네트워크 (game_network)
- **통신**: Flask + Socket.IO 웹 기반

**장점**:
- ✅ 완전한 격리된 환경에서 게임 실행
- ✅ 실제 네트워크 환경 시뮬레이션
- ✅ Wireshark로 Docker 네트워크 패킷 캡처 가능
- ✅ P2P 공격 시스템 지원 (플레이어 간 직접 TCP 연결)
- ✅ 웹 브라우저로 게임 플레이
- ✅ 한 명의 컴퓨터에서 여러 플레이어 시뮬레이션 가능

## Docker 설치

### Windows

1. [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/) 다운로드
2. WSL 2 설치 (필수)
   ```powershell
   wsl --install
   ```
3. Docker Desktop 실행 및 설정
4. 설정에서 "Use the WSL 2 based engine" 활성화

**시스템 요구사항**:
- Windows 10 64-bit: Pro, Enterprise, or Education (Build 19041 이상)
- WSL 2 설치
- BIOS에서 가상화 기능 활성화

### Linux

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install docker.io docker-compose

# Docker 서비스 시작
sudo systemctl start docker
sudo systemctl enable docker

# 사용자 권한 추가 (sudo 없이 docker 사용)
sudo usermod -aG docker $USER
# 로그아웃 후 재로그인

# CentOS/RHEL
sudo yum install docker docker-compose
sudo systemctl start docker
```

### macOS

1. [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/) 다운로드
2. 설치 후 Docker Desktop 실행
3. Applications 폴더에서 Docker 아이콘 클릭

**시스템 요구사항**:
- macOS 11 Big Sur 이상
- Intel 칩 또는 Apple Silicon (M1/M2)

## 프로젝트 네트워크 구조

```
┌─────────────────────────────────────────────────────────────┐
│ Docker Network: game_network (172.20.0.0/16)                │
│                                                              │
│  ┌──────────────────┐                                       │
│  │  Game Server     │ 172.20.0.254                          │
│  │  - Flask Web     │ Port 9999 (게임 서버)                 │
│  │  - Socket.IO     │ Port 5001 (웹 인터페이스)             │
│  └────────┬─────────┘                                       │
│           │                                                  │
│           ├──────────┬──────────┬──────────┐                │
│           │          │          │          │                │
│  ┌────────▼─────┐ ┌──▼────────┐ ┌─▼────────┐ ┌────▼──────┐ │
│  │  Player 1    │ │ Player 2  │ │ Player 3 │ │ Player 4  │ │
│  │  172.20.0.1  │ │ 172.20.0.2│ │172.20.0.3│ │172.20.0.4 │ │
│  │  Port: 5002  │ │ Port: 5003│ │Port: 5004│ │Port: 5005 │ │
│  │  P2P: 10001  │ │ P2P: 10002│ │P2P: 10003│ │P2P: 10004 │ │
│  └──────────────┘ └───────────┘ └──────────┘ └───────────┘ │
│                                                              │
│  [P2P Attack: 플레이어 간 직접 TCP 연결 (10001~10004)]       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                         │
                         │ Port Forwarding
                         │
┌─────────────────────────▼────────────────────────────────────┐
│ Host OS (Windows/macOS/Linux)                                │
│                                                              │
│  웹 브라우저에서 접속:                                         │
│  - http://localhost:5001  →  서버 관리 인터페이스            │
│  - http://localhost:5002  →  Player1 게임 화면               │
│  - http://localhost:5003  →  Player2 게임 화면               │
│  - http://localhost:5004  →  Player3 게임 화면               │
│  - http://localhost:5005  →  Player4 게임 화면               │
│                                                              │
│  ┌─────────────────────────────┐                            │
│  │  Wireshark                  │                            │
│  │  Interface: docker0 또는     │                            │
│  │             br-xxxxxx        │                            │
│  │  (Docker 네트워크 캡처)      │                            │
│  └─────────────────────────────┘                            │
└──────────────────────────────────────────────────────────────┘
```

## 사용 방법

### 1. 컨테이너 시작

프로젝트 루트 디렉토리에서:

```bash
# 이미지 빌드 및 모든 컨테이너 시작
docker-compose up --build

# 백그라운드 실행 (추천)
docker-compose up -d --build
```

**시작되는 컨테이너**:
1. `game_server` - 게임 서버 (172.20.0.254)
2. `game_player1` - Player1 클라이언트 (172.20.0.1)
3. `game_player2` - Player2 클라이언트 (172.20.0.2)
4. `game_player3` - Player3 클라이언트 (172.20.0.3)
5. `game_player4` - Player4 클라이언트 (172.20.0.4)

### 2. 웹 브라우저로 접속

컨테이너가 시작되면 웹 브라우저를 열고:

**서버 관리 인터페이스** (게임 시작/중지):
```
http://localhost:5001
```

**플레이어 게임 화면**:
```
http://localhost:5002   # Player1
http://localhost:5003   # Player2
http://localhost:5004   # Player3
http://localhost:5005   # Player4
```

**멀티 플레이어 테스트**:
1. 브라우저 창을 여러 개 열어서
2. 각 창에서 다른 플레이어 포트로 접속
3. 서버 인터페이스에서 게임 시작

### 3. 컨테이너 관리

#### 컨테이너 중지
```bash
docker-compose down
```

#### 컨테이너 재시작
```bash
# 모든 컨테이너 재시작
docker-compose restart

# 특정 컨테이너만 재시작
docker-compose restart server
docker-compose restart player1
```

#### 로그 확인
```bash
# 모든 컨테이너 로그 확인
docker-compose logs

# 특정 컨테이너 로그 (실시간)
docker-compose logs -f server
docker-compose logs -f player1

# 또는 docker logs 명령 사용
docker logs game_server -f
docker logs game_player1 -f
```

#### 컨테이너 상태 확인
```bash
# 실행 중인 컨테이너 목록
docker-compose ps

# 또는
docker ps
```

#### 컨테이너 접속 (디버깅용)
```bash
# 서버 컨테이너 접속
docker exec -it game_server bash

# 플레이어 컨테이너 접속
docker exec -it game_player1 bash

# 컨테이너 내에서 파일 확인
ls -la
cat /app/server/web_server_gui.py
```

### 4. 완전 초기화 (문제 발생 시)

```bash
# 1. 모든 컨테이너 중지 및 삭제
docker-compose down

# 2. 이미지 삭제 (선택사항)
docker rmi comnetproject-server
docker rmi comnetproject-player1
docker rmi comnetproject-player2
docker rmi comnetproject-player3
docker rmi comnetproject-player4

# 3. Docker 시스템 정리 (주의: 다른 프로젝트 영향 가능)
docker system prune -a

# 4. 재빌드 및 시작
docker-compose up --build -d
```

## Wireshark 패킷 캡처

### Windows 환경

1. **Wireshark 실행**

2. **Docker 네트워크 인터페이스 선택**
   - 인터페이스 목록에서 "vEthernet (WSL)" 선택
   - 또는 Docker Desktop 설정에서 확인한 네트워크 어댑터

3. **필터 설정**
   ```
   tcp.port == 9999 || (tcp.port >= 10001 && tcp.port <= 10020)
   ```

4. **캡처 시작**
   - 게임을 시작하면 모든 네트워크 트래픽이 캡처됩니다

### Linux 환경

1. **Docker 네트워크 인터페이스 확인**
   ```bash
   ip addr | grep docker
   # 또는
   docker network inspect game_network
   ```

2. **Wireshark에서 docker0 또는 br-xxxx 선택**

3. **권한 문제 시**
   ```bash
   sudo wireshark
   # 또는
   sudo usermod -aG wireshark $USER
   ```

### macOS 환경

1. **Docker Desktop 네트워크 인터페이스 확인**

2. **Wireshark에서 해당 인터페이스 선택**
   - 일반적으로 "bridge" 또는 "any" 사용

3. **필터 적용 및 캡처**

### 패킷 분석 팁

**실제 IP vs 가상 IP**:
- Wireshark에서는 **실제 IP** (172.20.0.x)가 보입니다
- 게임 내부에서는 **가상 IP** (172.20.1.x)를 사용합니다
- 방어 제출 시: 실제 IP를 가상 IP로 변환하여 입력

**IP 매핑 테이블**:
| 컨테이너 | 실제 IP (Wireshark) | 가상 IP (게임) | 웹 포트 | P2P 포트 |
|----------|---------------------|----------------|---------|----------|
| Server   | 172.20.0.254        | N/A            | 5001    | 9999     |
| Player1  | 172.20.0.1          | 172.20.1.1     | 5002    | 10001    |
| Player2  | 172.20.0.2          | 172.20.1.2     | 5003    | 10002    |
| Player3  | 172.20.0.3          | 172.20.1.3     | 5004    | 10003    |
| Player4  | 172.20.0.4          | 172.20.1.4     | 5005    | 10004    |

**P2P 공격 필터** (Player2를 대상으로 하는 공격):
```
(tcp.port >= 10001 && tcp.port <= 10020) && ip.dst == 172.20.0.2
```

**결과 해석**:
- Source IP가 172.20.0.1 → 게임에서 172.20.1.1 제출
- Source IP가 172.20.0.3 → 게임에서 172.20.1.3 제출

## docker-compose.yml 설명

프로젝트의 `docker-compose.yml` 파일 구조:

```yaml
version: '3.8'

services:
  # 게임 서버
  server:
    build:
      context: .
      dockerfile: Dockerfile
      target: server
    container_name: game_server
    networks:
      game_network:
        ipv4_address: 172.20.0.254
    ports:
      - "5001:5001"  # 웹 인터페이스
      - "9999:9999"  # 게임 서버 포트
    environment:
      - PYTHONUNBUFFERED=1
    command: python -m server.web_server_gui

  # Player 1
  player1:
    build:
      context: .
      dockerfile: Dockerfile
      target: client
    container_name: game_player1
    networks:
      game_network:
        ipv4_address: 172.20.0.1
    ports:
      - "5002:5000"  # 웹 인터페이스
      - "10001:10001"  # P2P 공격 포트
    environment:
      - PLAYER_ID=Player1
      - SERVER_HOST=172.20.0.254
      - SERVER_PORT=9999
      - PYTHONUNBUFFERED=1
    depends_on:
      - server

  # Player 2, 3, 4 (유사한 구조)
  # ...

networks:
  game_network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

**주요 설정**:
- `build.target`: 멀티 스테이지 빌드 (server/client 분리)
- `networks.ipv4_address`: 고정 IP 할당
- `ports`: 호스트-컨테이너 포트 매핑
- `depends_on`: 서버가 먼저 시작되도록 의존성 설정
- `environment`: 환경 변수 (플레이어 ID, 서버 주소 등)

## Dockerfile 설명

프로젝트의 `Dockerfile`은 **멀티 스테이지 빌드**를 사용합니다:

```dockerfile
# Stage 1: Base
FROM python:3.9-slim as base
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Stage 2: Server
FROM base as server
CMD ["python", "-m", "server.web_server_gui"]

# Stage 3: Client
FROM base as client
CMD ["python", "-m", "client.web_client"]
```

**장점**:
- 하나의 Dockerfile로 서버와 클라이언트 모두 빌드
- 공통 의존성 공유 (레이어 캐싱)
- 이미지 크기 최적화

## 게임 실행 시나리오

### 시나리오 1: 2인 게임

1. **컨테이너 시작**:
   ```bash
   docker-compose up -d
   ```

2. **브라우저 창 열기**:
   - 창 1: http://localhost:5001 (서버 관리)
   - 창 2: http://localhost:5002 (Player1)
   - 창 3: http://localhost:5003 (Player2)

3. **Wireshark 시작**:
   - Docker 네트워크 인터페이스 선택
   - 필터 적용: `tcp.port == 9999 || (tcp.port >= 10001 && tcp.port <= 10020)`

4. **게임 시작**:
   - 서버 관리 페이지에서 "게임 시작" 버튼 클릭

5. **게임 플레이**:
   - Player1/Player2 화면에서 공격 수행
   - Wireshark에서 패킷 분석
   - 방어 제출

### 시나리오 2: 4인 게임

1. **컨테이너 시작** (동일)

2. **브라우저 창 열기**:
   - 창 1: http://localhost:5001 (서버)
   - 창 2~5: Player1~4 (포트 5002~5005)

3. **멀티 플레이어 공격 테스트**:
   - 각 플레이어가 다른 플레이어를 공격
   - Wireshark에서 복잡한 트래픽 분석

### 시나리오 3: 원격 플레이어 추가 (고급)

**서버 호스트 (192.168.1.100)**:
```bash
# docker-compose.yml에서 서버 포트 노출 확인
# ports:
#   - "5001:5001"
#   - "9999:9999"

docker-compose up -d server
```

**클라이언트 호스트 (다른 컴퓨터)**:
```bash
# 환경 변수로 서버 주소 지정
docker run -p 5002:5000 \
  -e PLAYER_ID=Player5 \
  -e SERVER_HOST=192.168.1.100 \
  -e SERVER_PORT=9999 \
  comnetproject-player1
```

**주의**: 방화벽에서 포트 9999 허용 필요

## 트러블슈팅

### 1. "Address already in use" 오류

**원인**: 포트가 이미 사용 중

**해결**:
```bash
# 기존 컨테이너 중지
docker-compose down

# 포트 사용 중인 프로세스 확인 (Windows)
netstat -ano | findstr :5001
netstat -ano | findstr :9999

# 포트 사용 중인 프로세스 확인 (Linux/macOS)
lsof -i :5001
lsof -i :9999

# 프로세스 종료 후 재시작
docker-compose up -d
```

### 2. 컨테이너가 시작 직후 종료됨

**원인**: 코드 오류 또는 의존성 문제

**해결**:
```bash
# 로그 확인
docker-compose logs server
docker-compose logs player1

# 컨테이너 내부 확인
docker run -it comnetproject-server bash
python -m server.web_server_gui
```

### 3. 웹 페이지에 접속 안 됨

**원인 1**: 컨테이너가 실행되지 않음
```bash
docker-compose ps
# 모든 컨테이너가 "Up" 상태인지 확인
```

**원인 2**: 포트 포워딩 문제
```bash
# docker-compose.yml의 ports 설정 확인
# 브라우저에서 localhost:5001 대신 127.0.0.1:5001 시도
```

**원인 3**: 방화벽 차단
- Windows Defender Firewall에서 포트 허용
- 또는 일시적으로 방화벽 비활성화하여 테스트

### 4. Wireshark에 패킷이 안 보임

**해결**:
```bash
# Docker 네트워크 확인
docker network ls
docker network inspect game_network

# Wireshark에서 올바른 인터페이스 선택
# - Windows: vEthernet (WSL)
# - Linux: docker0 또는 br-xxxx
# - macOS: bridge

# 필터 적용 확인 (녹색으로 표시되어야 함)
tcp.port == 9999 || (tcp.port >= 10001 && tcp.port <= 10020)
```

### 5. 플레이어가 서버에 연결 안 됨

**해결**:
```bash
# 서버 컨테이너 로그 확인
docker logs game_server -f

# 플레이어 컨테이너 로그 확인
docker logs game_player1 -f

# 네트워크 연결 테스트
docker exec game_player1 ping 172.20.0.254
docker exec game_player1 curl http://172.20.0.254:9999
```

### 6. P2P 공격이 실패함

**원인**: P2P 포트가 열려있지 않음

**해결**:
```bash
# P2P 포트가 노출되어 있는지 확인
docker-compose ps

# 컨테이너 간 직접 연결 테스트
docker exec game_player1 nc -zv 172.20.0.2 10002

# 로그에서 P2P 연결 상태 확인
docker logs game_player1 | grep "P2P"
```

### 7. 이미지 빌드 실패

**해결**:
```bash
# Docker 캐시 클리어 후 재빌드
docker-compose build --no-cache

# 의존성 문제 시 requirements.txt 확인
docker run -it python:3.9-slim bash
pip install -r requirements.txt
```

## 개발 팁

### 코드 수정 후 재시작

**방법 1: 특정 서비스만 재빌드**
```bash
# 서버 코드 수정 후
docker-compose up -d --build server

# 클라이언트 코드 수정 후
docker-compose up -d --build player1
```

**방법 2: 볼륨 마운트 사용 (개발 중)**

`docker-compose.yml`에 volumes 추가:
```yaml
services:
  server:
    volumes:
      - .:/app  # 호스트 디렉토리를 컨테이너에 마운트
    command: python -m server.web_server_gui
```

이렇게 하면 코드 수정 시 재빌드 없이 컨테이너만 재시작하면 됩니다.

### 컨테이너 내부 디버깅

```bash
# Python 인터프리터 실행
docker exec -it game_server python

# 특정 모듈 테스트
docker exec -it game_server python -c "from server import game_manager; print(game_manager)"

# 로그 파일 확인
docker exec -it game_server cat /app/logs/server.log
```

### 네트워크 분석

```bash
# 컨테이너 네트워크 정보
docker network inspect game_network

# 컨테이너 IP 확인
docker inspect game_server | grep IPAddress

# 컨테이너 간 연결 테스트
docker exec game_player1 ping -c 3 172.20.0.254
docker exec game_player1 telnet 172.20.0.254 9999
```

### 리소스 모니터링

```bash
# 컨테이너 리소스 사용량
docker stats

# 특정 컨테이너 리소스
docker stats game_server game_player1 game_player2
```

## 성능 최적화

### 이미지 크기 줄이기

1. **멀티 스테이지 빌드 사용** (이미 적용됨)
2. **불필요한 파일 제외** (`.dockerignore` 사용)
3. **Alpine 이미지 사용** (선택사항):
   ```dockerfile
   FROM python:3.9-alpine as base
   ```

### 빌드 속도 개선

1. **레이어 캐싱 활용**:
   ```dockerfile
   # requirements.txt를 먼저 COPY하여 캐싱
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY . .  # 코드 변경 시에만 재실행
   ```

2. **BuildKit 사용**:
   ```bash
   DOCKER_BUILDKIT=1 docker-compose build
   ```

### 네트워크 성능

1. **bridge 네트워크 대신 host 네트워크** (Linux만 가능):
   ```yaml
   network_mode: host
   ```

2. **MTU 설정**:
   ```yaml
   networks:
     game_network:
       driver: bridge
       driver_opts:
         com.docker.network.driver.mtu: 1500
   ```

## 보안 고려사항

**교육용 프로젝트**이므로 다음 보안 기능은 구현되지 않았습니다:

- ❌ TLS/SSL 암호화
- ❌ 컨테이너 권한 제한 (root 사용자)
- ❌ 네트워크 정책
- ❌ 시크릿 관리

**프로덕션 환경에서는 다음을 추가해야 합니다**:

1. **비밀번호 및 토큰 관리**:
   ```yaml
   services:
     server:
       secrets:
         - db_password
   secrets:
     db_password:
       external: true
   ```

2. **컨테이너 권한 제한**:
   ```yaml
   services:
     server:
       user: "1000:1000"
       read_only: true
   ```

3. **네트워크 정책**:
   ```yaml
   networks:
     game_network:
       internal: true  # 외부 네트워크 차단
   ```

## 참고 자료

- [Docker 공식 문서](https://docs.docker.com/)
- [Docker Compose 문서](https://docs.docker.com/compose/)
- [Docker 네트워킹 가이드](https://docs.docker.com/network/)
- [Dockerfile 베스트 프랙티스](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)

## 빠른 참조

### 자주 사용하는 명령어

| 작업 | 명령어 |
|------|--------|
| 컨테이너 시작 | `docker-compose up -d` |
| 컨테이너 중지 | `docker-compose down` |
| 로그 확인 | `docker-compose logs -f [서비스명]` |
| 컨테이너 재시작 | `docker-compose restart [서비스명]` |
| 컨테이너 접속 | `docker exec -it [컨테이너명] bash` |
| 상태 확인 | `docker-compose ps` |
| 네트워크 확인 | `docker network inspect game_network` |
| 이미지 재빌드 | `docker-compose up -d --build` |
| 완전 초기화 | `docker-compose down && docker system prune -a` |

### 포트 매핑

| 서비스 | 컨테이너 포트 | 호스트 포트 | 용도 |
|--------|---------------|-------------|------|
| Server | 5001 | 5001 | 웹 인터페이스 |
| Server | 9999 | 9999 | 게임 서버 |
| Player1 | 5000 | 5002 | 웹 인터페이스 |
| Player1 | 10001 | 10001 | P2P 공격 |
| Player2 | 5000 | 5003 | 웹 인터페이스 |
| Player2 | 10002 | 10002 | P2P 공격 |
| Player3 | 5000 | 5004 | 웹 인터페이스 |
| Player3 | 10003 | 10003 | P2P 공격 |
| Player4 | 5000 | 5005 | 웹 인터페이스 |
| Player4 | 10004 | 10004 | P2P 공격 |

## 결론

Docker Compose를 사용하면 복잡한 멀티 컨테이너 환경을 간단하게 관리할 수 있습니다. 이 가이드를 참고하여 네트워크 보안 게임을 효과적으로 실행하고 테스트하세요.

**게임 시작 체크리스트**:
- ✅ Docker Desktop 실행 중
- ✅ `docker-compose up -d` 실행
- ✅ 브라우저에서 localhost:5001~5005 접속 확인
- ✅ Wireshark에서 Docker 네트워크 인터페이스 선택
- ✅ 필터 적용: `tcp.port == 9999 || (tcp.port >= 10001 && tcp.port <= 10020)`
- ✅ 서버 인터페이스에서 게임 시작!
