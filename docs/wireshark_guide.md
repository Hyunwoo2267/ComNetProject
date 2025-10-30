# Wireshark 사용 가이드 (v2.0)

## 개요

이 가이드는 네트워크 보안 게임에서 Wireshark를 사용하여 패킷을 캡처하고 분석하는 방법을 설명합니다.

**v2.0 주요 변경사항**:
- P2P 공격 시스템: 플레이어 간 직접 TCP 연결
- 가상 IP vs 실제 IP: 게임 내 172.20.1.x vs Wireshark에서 보이는 172.20.0.x
- 다중 포트: 서버 포트 (9999) + P2P 포트 (10001~10020)

## Wireshark 설치

### Windows

1. [Wireshark 공식 웹사이트](https://www.wireshark.org/download.html)에서 다운로드
2. 설치 프로그램 실행
3. **Npcap 설치** (필수) - 설치 중 선택 옵션에서 반드시 체크
4. 재부팅 권장

### Linux

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install wireshark

# Fedora
sudo dnf install wireshark

# 사용자 권한 설정 (중요!)
sudo usermod -aG wireshark $USER
# 로그아웃 후 재로그인
```

### macOS

```bash
# Homebrew 사용
brew install --cask wireshark
```

## 기본 사용법

### 1. Wireshark 시작

1. Wireshark 실행
2. 네트워크 인터페이스 선택
   - **Docker 환경**: "docker0" 또는 Docker 네트워크 인터페이스
   - **Windows**: "Ethernet" 또는 "Wi-Fi"
   - **Linux**: `docker0`, `eth0`, `wlan0` 등
   - **macOS**: `en0`, `en1` 등

**중요**: Docker 컨테이너 간 통신을 캡처하려면 Docker 네트워크 인터페이스를 선택해야 합니다!

### 2. 캡처 시작

1. 인터페이스를 더블클릭하거나 선택 후 "Start" 클릭
2. 패킷 캡처가 시작됨

### 3. 캡처 중지

- 메뉴: Capture > Stop
- 단축키: `Ctrl+E` (Windows/Linux) 또는 `Cmd+E` (macOS)

## 게임용 필터 설정

### 기본 필터

#### 모든 게임 트래픽 보기

```
tcp.port == 9999 || (tcp.port >= 10001 && tcp.port <= 10020)
```

이 필터는 다음을 포함합니다:
- 서버-클라이언트 통신 (포트 9999)
- P2P 공격 통신 (포트 10001~10020)

#### 서버 통신만 보기

```
tcp.port == 9999
```

#### P2P 공격만 보기

```
tcp.port >= 10001 && tcp.port <= 10020
```

### 고급 필터

#### 특정 IP로부터의 패킷만 표시

```
tcp.port == 9999 && ip.src == 172.20.0.1
```

**주의**: Wireshark에서는 실제 IP (172.20.0.x)가 보이지만, 게임 내에서는 가상 IP (172.20.1.x)를 사용합니다!

#### 특정 IP로 가는 패킷만 표시

```
tcp.port == 9999 && ip.dst == 172.20.0.2
```

#### 나를 대상으로 하는 모든 통신 (내 IP가 172.20.0.2인 경우)

```
(tcp.port == 9999 || (tcp.port >= 10001 && tcp.port <= 10020)) && ip.dst == 172.20.0.2
```

#### P2P 공격 패킷 + 페이로드 필터

```
(tcp.port >= 10001 && tcp.port <= 10020) && tcp contains "ATTACK"
```

#### 특정 플레이어 간의 P2P 통신 (172.20.0.1 ↔ 172.20.0.2)

```
(tcp.port >= 10001 && tcp.port <= 10020) && ((ip.src == 172.20.0.1 && ip.dst == 172.20.0.2) || (ip.src == 172.20.0.2 && ip.dst == 172.20.0.1))
```

## 패킷 분석

### 패킷 상세 정보 보기

1. 패킷 목록에서 패킷 클릭
2. 중간 패널에서 계층별 정보 확인:
   - **Frame**: 프레임 정보 (캡처 시간, 길이 등)
   - **Ethernet II**: 이더넷 헤더 (MAC 주소)
   - **Internet Protocol**: IP 헤더 (출발지/목적지 IP 주소)
   - **Transmission Control Protocol**: TCP 헤더 (출발지/목적지 포트, 플래그)
   - **Data**: 페이로드 (JSON 메시지, Base64 인코딩)

### IP 주소 매핑 (중요!)

**Wireshark에서 보이는 IP (실제 IP, Transport Layer)**:
- 서버: `172.20.0.254`
- Player1: `172.20.0.1`
- Player2: `172.20.0.2`
- Player3: `172.20.0.3`
- Player4: `172.20.0.4`

**게임 내 IP (가상 IP, Application Layer)**:
- Player1: `172.20.1.1`
- Player2: `172.20.1.2`
- Player3: `172.20.1.3`
- Player4: `172.20.1.4`

**방어 제출 시**: 게임 웹 인터페이스에서 가상 IP (172.20.1.x)로 제출해야 합니다!

### 포트 번호 매핑

- **서버 포트**: 9999 (고정)
- **Player1 P2P 포트**: 10001 (index 0)
- **Player2 P2P 포트**: 10002 (index 1)
- **Player3 P2P 포트**: 10003 (index 2)
- **Player4 P2P 포트**: 10004 (index 3)

### 페이로드 확인

1. 패킷 선택
2. 하단 패널에서 16진수/ASCII 데이터 확인
3. 또는 "Data" 섹션을 확장하여 JSON 내용 확인
4. **Base64 디코딩 필요**: 페이로드는 Base64로 인코딩되어 있음

### Base64 디코딩 방법

#### 온라인 도구
- https://www.base64decode.org/
- Wireshark에서 페이로드 복사 → 디코더에 붙여넣기

#### Python 스크립트
```python
import base64
encoded = "QVRUQUNLX1RBUkdFVF9QbGF5ZXJI"
decoded = base64.b64decode(encoded).decode()
print(decoded)  # "ATTACK_TARGET_PlayerB"
```

#### 커맨드 라인 (Linux/macOS)
```bash
echo "QVRUQUNLX1RBUkdFVF9QbGF5ZXJI" | base64 -d
```

### Follow TCP Stream

특정 연결의 전체 대화를 보려면:

1. 패킷 우클릭
2. "Follow" > "TCP Stream" 선택
3. 새 창에서 전체 대화 내용 확인
4. 필터링 옵션:
   - **Entire conversation**: 양방향 전체
   - **Client to Server**: 클라이언트 → 서버
   - **Server to Client**: 서버 → 클라이언트

**유용한 경우**:
- 특정 플레이어의 모든 서버 통신 확인
- P2P 공격의 전체 과정 추적
- 메시지 순서 파악

## 게임 패킷 식별

### 1. 서버 더미 패킷 (DUMMY)

**특징**:
- 출발지: 서버 IP (172.20.0.254)
- 목적지: 모든 플레이어
- 포트: 9999
- 페이로드: `"type": "DUMMY"` (Base64 디코딩 후)

**필터**:
```
tcp.port == 9999 && ip.src == 172.20.0.254 && tcp contains "DUMMY"
```

**목적**: 트래픽을 복잡하게 만들어 공격 탐지를 어렵게 함

### 2. 노이즈 트래픽 (NOISE, R3+)

**특징**:
- 출발지: 서버 IP (172.20.0.254)
- 목적지: 특정 플레이어
- 포트: 9999
- 페이로드: `"type": "NOISE"` (Base64 디코딩 후)

**필터**:
```
tcp.port == 9999 && tcp contains "NOISE"
```

**목적**: 공격이 아닌 일반 통신을 시뮬레이션 (R3부터 활성화)

### 3. 실제 공격 패킷 (ATTACK, P2P)

**특징**:
- 출발지: 공격자 실제 IP (예: 172.20.0.1)
- 목적지: 대상자 실제 IP (예: 172.20.0.2)
- 포트: 대상자 P2P 포트 (예: 10002)
- 페이로드: `"type": "ATTACK"` (Base64 디코딩 후)

**중요**: 서버를 거치지 않고 플레이어 간 직접 전송!

**본인을 공격한 패킷 찾기 (내 IP가 172.20.0.2인 경우)**:
```
(tcp.port >= 10001 && tcp.port <= 10020) && ip.dst == 172.20.0.2 && tcp contains "ATTACK"
```

**결과 예시**:
- Source: 172.20.0.1 → 공격자 실제 IP
- Destination: 172.20.0.2 → 내 실제 IP
- Dst Port: 10002 → 내 P2P 포트

**방어 제출**: 172.20.0.1을 가상 IP로 변환 → **172.20.1.1** 제출!

### 4. 가짜 공격 패킷 (DECOY_ATTACK, R5만)

**특징**:
- 출발지: 서버 IP (172.20.0.254)
- 목적지: 특정 플레이어
- 포트: 9999 (서버 포트!)
- 페이로드: `"type": "DECOY_ATTACK"` (Base64 디코딩 후)
- 가짜 from_ip (존재하지 않는 IP, 예: 172.20.1.99)

**필터**:
```
tcp.port == 9999 && tcp contains "DECOY"
```

**실제 공격과 구분 방법**:
- 실제 공격: P2P 포트 (10001~10020) 사용, 플레이어 IP에서 옴
- 가짜 공격: 서버 포트 (9999) 사용, 서버 IP에서 옴

**함정**: Base64 디코딩하면 실제 공격처럼 보이지만, 출발지 IP가 서버임!

### 5. 공격자 IP 추출 프로세스

1. **패킷 필터링**: 내 IP로 들어오는 P2P 공격 패킷만 표시
   ```
   (tcp.port >= 10001 && tcp.port <= 10020) && ip.dst == [내 실제 IP] && tcp contains "ATTACK"
   ```

2. **Source IP 확인**: Wireshark 패킷 목록의 "Source" 열 확인
   - 예: 172.20.0.1, 172.20.0.3

3. **IP 변환**: 실제 IP → 가상 IP
   - 172.20.0.1 → 172.20.1.1
   - 172.20.0.3 → 172.20.1.3

4. **방어 제출**: 게임 웹 인터페이스에서 가상 IP 입력

## 실전 팁

### 1. 컬럼 커스터마이징

유용한 컬럼만 표시하려면:

1. 컬럼 헤더 우클릭 > "Column Preferences"
2. 추천 컬럼:
   - **No.** (패킷 번호)
   - **Time** (시간)
   - **Source** (출발지 IP) ⭐ 가장 중요!
   - **Destination** (목적지 IP) ⭐ 가장 중요!
   - **Protocol** (프로토콜)
   - **Src Port** (출발지 포트) - 추가 권장
   - **Dst Port** (목적지 포트) - 추가 권장
   - **Length** (길이)
   - **Info** (정보)

### 2. 색상 규칙 설정

공격 패킷을 빨간색으로 표시하려면:

1. View > Coloring Rules
2. "+" 버튼으로 새 규칙 추가

**규칙 1: P2P 공격 (빨간색)**
- Name: "P2P Attack"
- Filter: `(tcp.port >= 10001 && tcp.port <= 10020) && tcp contains "ATTACK"`
- 전경: 검은색, 배경: 빨간색

**규칙 2: 더미 패킷 (회색)**
- Name: "Dummy Traffic"
- Filter: `tcp.port == 9999 && tcp contains "DUMMY"`
- 전경: 회색, 배경: 연한 회색

**규칙 3: 노이즈 트래픽 (노란색)**
- Name: "Noise Traffic"
- Filter: `tcp.port == 9999 && tcp contains "NOISE"`
- 전경: 검은색, 배경: 노란색

**규칙 4: 가짜 공격 (주황색)**
- Name: "Decoy Attack"
- Filter: `tcp.port == 9999 && tcp contains "DECOY"`
- 전경: 검은색, 배경: 주황색

### 3. 시간 표시 형식

절대 시간으로 변경:

1. View > Time Display Format
2. "Time of Day" 선택
3. 또는 "Seconds Since Beginning of Capture" (상대 시간)

### 4. 패킷 마크

중요한 공격 패킷 표시:

1. 패킷 우클릭 > "Mark/Unmark Packet"
2. 단축키: `Ctrl+M`
3. 마크된 패킷은 검은 배경으로 표시됨
4. 마크된 패킷 간 이동: `Ctrl+Shift+N` (다음), `Ctrl+Shift+B` (이전)

### 5. 패킷 내보내기

분석을 위해 패킷 저장:

1. File > Export Specified Packets
2. 현재 필터링된 패킷만 저장 가능
3. .pcap 또는 .pcapng 형식으로 저장

## 통계 기능

### Conversations

IP별 통신량 확인:

1. Statistics > Conversations
2. "IPv4" 탭 선택
3. 각 IP 쌍 간의 패킷 수와 바이트 수 확인

**활용**:
- 어떤 플레이어가 가장 많이 공격했는지 파악
- 서버와의 통신량 확인

### Endpoints

각 IP의 송수신 통계:

1. Statistics > Endpoints
2. "IPv4" 탭 선택
3. 송신/수신 패킷 수 확인

### Protocol Hierarchy

프로토콜 분포 확인:

1. Statistics > Protocol Hierarchy
2. TCP, JSON 등의 비율 확인

### I/O Graph

시간에 따른 트래픽 그래프:

1. Statistics > I/O Graph
2. 여러 필터를 추가하여 비교 가능

**예시 그래프**:
- Graph 1: `tcp.port == 9999` (서버 통신)
- Graph 2: `tcp.port >= 10001 && tcp.port <= 10020` (P2P 공격)

## 게임 시나리오별 가이드

### 시나리오 1: 기본 공격 탐지 (R1-R2)

**목표**: P2P 공격을 탐지하고 공격자 IP 찾기

**단계**:

1. **필터 적용** (내 실제 IP가 172.20.0.2인 경우):
   ```
   (tcp.port >= 10001 && tcp.port <= 10020) && ip.dst == 172.20.0.2
   ```

2. **공격 패킷 찾기**: Base64 디코딩하여 "ATTACK" 타입 확인

3. **Source IP 기록**:
   - Wireshark에서 보이는 실제 IP 확인 (예: 172.20.0.1)

4. **IP 변환**:
   - 172.20.0.1 → 172.20.1.1

5. **방어 제출**: 게임에서 172.20.1.1 입력

**예상 결과**:
- 공격이 1~2개 정도로 적음
- 더미 패킷도 적음 (2초 간격)

### 시나리오 2: 노이즈 트래픽 구분 (R3-R4)

**목표**: 실제 공격과 노이즈 트래픽 구분

**단계**:

1. **모든 트래픽 보기**:
   ```
   tcp.port == 9999 || (tcp.port >= 10001 && tcp.port <= 10020)
   ```

2. **실제 공격만 필터**:
   ```
   (tcp.port >= 10001 && tcp.port <= 10020) && ip.dst == [내 IP]
   ```

3. **노이즈 트래픽 확인** (참고용):
   ```
   tcp.port == 9999 && tcp contains "NOISE" && ip.dst == [내 IP]
   ```

**핵심 구분 방법**:
- **실제 공격**: P2P 포트 (10001~), 플레이어 IP에서 직접 옴
- **노이즈**: 서버 포트 (9999), 서버 IP에서 옴

**노이즈는 무시하고 실제 공격만 제출하세요!**

### 시나리오 3: 가짜 공격 필터링 (R5)

**목표**: 실제 공격과 가짜 공격 구분

**R5 특징**:
- 더미 패킷 빈도 증가 (0.5초 간격)
- 노이즈 트래픽 활성화
- 10개의 가짜 공격 (DECOY_ATTACK)

**단계**:

1. **실제 P2P 공격만 보기**:
   ```
   (tcp.port >= 10001 && tcp.port <= 10020) && ip.dst == [내 IP] && tcp contains "ATTACK"
   ```

2. **가짜 공격 확인** (참고용):
   ```
   tcp.port == 9999 && ip.dst == [내 IP] && tcp contains "DECOY"
   ```

**핵심 구분 방법**:
| 특징 | 실제 공격 | 가짜 공격 |
|------|----------|----------|
| 출발지 포트 | 플레이어 P2P 포트 | 서버 포트 (9999) |
| 목적지 포트 | 내 P2P 포트 (10001~) | 서버 포트 (9999) |
| 출발지 IP | 플레이어 실제 IP | 서버 IP (172.20.0.254) |
| 전송 방식 | P2P 직접 연결 | 서버 중계 |

**전략**:
1. P2P 포트 필터만 사용하면 가짜 공격이 자동으로 제외됨
2. 실제 공격의 Source IP만 기록하여 제출

### 시나리오 4: 시간대별 공격 분석

**목표**: 라운드 중 받은 공격을 시간순으로 정리

**단계**:

1. **라운드 시작 시각 기록** (게임 화면 또는 Wireshark Time 열)

2. **공격 패킷 필터**:
   ```
   (tcp.port >= 10001 && tcp.port <= 10020) && ip.dst == [내 IP]
   ```

3. **Time 열로 정렬**: 클릭하여 시간순 정렬

4. **라운드 시간 (90초) 내의 패킷만 확인**

5. **중복 IP 확인**: 같은 IP에서 여러 번 공격했는지 체크

**참고**: 동일 IP의 여러 공격 중 1개만 방어 인정 (v2.1)

## 문제 해결

### 패킷이 캡처되지 않음

**원인 1**: 잘못된 네트워크 인터페이스 선택
- **해결**: Docker 네트워크 인터페이스 선택 (`docker0` 등)
- 확인: `ip addr` 또는 `ifconfig` 명령으로 Docker 네트워크 확인

**원인 2**: 권한 부족 (Linux)
- **해결**: `sudo wireshark` 또는 사용자를 wireshark 그룹에 추가
  ```bash
  sudo usermod -aG wireshark $USER
  ```
  로그아웃 후 재로그인

**원인 3**: Npcap 미설치 (Windows)
- **해결**: Wireshark 재설치 시 Npcap 옵션 체크

### Docker 컨테이너 트래픽이 보이지 않음

**원인**: 호스트 네트워크 인터페이스만 캡처 중

**해결책**:
1. Wireshark에서 인터페이스 목록 확인
2. `docker0`, `br-xxx` 등 Docker 관련 인터페이스 선택
3. 또는 `any` 인터페이스 선택 (모든 인터페이스 캡처)

### 필터가 작동하지 않음

**원인**: 잘못된 필터 문법

**해결**: 필터 입력 후 입력창 색상 확인
- **녹색**: 유효한 필터
- **빨간색**: 잘못된 문법
- **노란색**: 경고 (작동하지만 비효율적)

**자주 하는 실수**:
- `tcp.port = 9999` (X) → `tcp.port == 9999` (O)
- `ip.addr = 172.20.0.1` (X) → `ip.addr == 172.20.0.1` (O)
- `&&` 대신 `and` 사용 가능

### Base64 디코딩이 실패함

**원인**: 불완전한 페이로드 복사

**해결**:
1. "Data" 섹션 전체를 확장
2. JSON 구조에서 "payload" 값만 정확히 복사
3. 따옴표 제외하고 복사
4. 공백이나 개행 제거

## 단축키

- `Ctrl+K`: 캡처 시작
- `Ctrl+E`: 캡처 중지
- `Ctrl+F`: 패킷 찾기
- `Ctrl+G`: 특정 패킷 번호로 이동
- `Ctrl+M`: 패킷 마크
- `Ctrl+Shift+M`: 모든 마크 해제
- `Ctrl+Shift+N`: 다음 마크된 패킷
- `Ctrl+Shift+B`: 이전 마크된 패킷
- `Ctrl+→`: 다음 패킷
- `Ctrl+←`: 이전 패킷
- `Alt+→`: 앞으로 가기 (히스토리)
- `Alt+←`: 뒤로 가기 (히스토리)

## 참고 자료

- [Wireshark 공식 문서](https://www.wireshark.org/docs/)
- [Wireshark Display Filters](https://wiki.wireshark.org/DisplayFilters)
- [Wireshark Tutorial](https://www.wireshark.org/docs/wsug_html_chunked/)
- [Wireshark User Guide](https://www.wireshark.org/docs/wsug_html/)

## 연습 문제

### 문제 1: 기본 필터

게임의 모든 트래픽 (서버 통신 + P2P 공격)을 표시하는 필터를 작성하세요.

**정답**:
```
tcp.port == 9999 || (tcp.port >= 10001 && tcp.port <= 10020)
```

### 문제 2: P2P 공격 탐지

내 실제 IP가 172.20.0.3일 때, 나를 공격한 P2P 패킷만 표시하는 필터를 작성하세요.

**정답**:
```
(tcp.port >= 10001 && tcp.port <= 10020) && ip.dst == 172.20.0.3
```

### 문제 3: IP 변환

Wireshark에서 다음 공격 패킷을 발견했습니다:
```
Source: 172.20.0.1
Destination: 172.20.0.3
Dst Port: 10003
Payload: {"type": "ATTACK", ...}
```

게임에서 방어 제출할 IP는?

**정답**: 172.20.1.1 (실제 IP 172.20.0.1 → 가상 IP 172.20.1.1)

### 문제 4: 실제 vs 가짜 공격

R5에서 다음 두 패킷을 발견했습니다. 어느 것이 실제 공격인가요?

**패킷 A**:
- Source: 172.20.0.254
- Dst Port: 9999
- Payload: {"type": "DECOY_ATTACK", "from_ip": "172.20.1.5", ...}

**패킷 B**:
- Source: 172.20.0.2
- Dst Port: 10003
- Payload: {"type": "ATTACK", "attacker_id": "Player2", ...}

**정답**: 패킷 B (출발지가 플레이어 IP이고, 목적지 포트가 P2P 포트)

## 고급 주제

### 1. TCP Stream Index

특정 연결의 모든 패킷 찾기:

```
tcp.stream eq 0
```

각 TCP 연결은 고유 stream index를 가집니다. 패킷을 클릭하면 하단에서 stream index를 확인할 수 있습니다.

### 2. 페이로드 길이 필터

큰 패킷만 표시 (1000바이트 이상):

```
tcp.len > 1000
```

**활용**: 더미 패킷은 작지만, 공격 패킷은 클 수 있음

### 3. 시간 기반 필터

특정 시간 이후의 패킷만 표시:

```
frame.time >= "2025-10-31 14:30:00"
```

### 4. 패킷 비교

두 패킷을 나란히 비교:

1. 첫 번째 패킷 우클릭 > "Set/Unset Time Reference"
2. 두 번째 패킷 선택
3. "Time" 열에 첫 번째 패킷으로부터의 차이 시간 표시됨

### 5. 정규표현식 필터

패킷 내용에서 정규식 매칭:

```
tcp matches "ATTACK.*Player[1-4]"
```

## 빠른 참조 카드

| 목적 | 필터 |
|------|------|
| 모든 게임 트래픽 | `tcp.port == 9999 \|\| (tcp.port >= 10001 && tcp.port <= 10020)` |
| 서버 통신만 | `tcp.port == 9999` |
| P2P 공격만 | `tcp.port >= 10001 && tcp.port <= 10020` |
| 내게 들어오는 공격 | `(tcp.port >= 10001 && tcp.port <= 10020) && ip.dst == [내 IP]` |
| 더미 패킷 | `tcp.port == 9999 && tcp contains "DUMMY"` |
| 노이즈 트래픽 | `tcp.port == 9999 && tcp contains "NOISE"` |
| 가짜 공격 | `tcp.port == 9999 && tcp contains "DECOY"` |
| 특정 IP로부터 | `ip.src == [IP]` |
| 특정 IP로 가는 | `ip.dst == [IP]` |

## 결론

Wireshark는 강력한 패킷 분석 도구입니다. 이 가이드의 기술을 숙지하면 게임에서 공격을 효과적으로 탐지할 수 있습니다.

**게임 중 체크리스트**:
- ✅ Docker 네트워크 인터페이스 선택
- ✅ P2P 공격 필터 적용: `(tcp.port >= 10001 && tcp.port <= 10020) && ip.dst == [내 IP]`
- ✅ Source IP 확인 (실제 IP: 172.20.0.x)
- ✅ IP 변환 (172.20.0.x → 172.20.1.x)
- ✅ 게임에서 가상 IP로 제출
- ✅ R5: 가짜 공격 제외 (서버 포트에서 오는 패킷 무시)

**시간 절약 팁**:
1. 미리 필터를 저장해두세요
2. 색상 규칙을 설정해두세요
3. 공격 패킷의 Source IP만 빠르게 확인하세요
4. 제한 시간이 있으므로 빠른 판단이 중요합니다!
