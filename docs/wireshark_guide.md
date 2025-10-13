# Wireshark 사용 가이드

## 개요

이 가이드는 네트워크 보안 게임에서 Wireshark를 사용하여 패킷을 캡처하고 분석하는 방법을 설명합니다.

## Wireshark 설치

### Windows

1. [Wireshark 공식 웹사이트](https://www.wireshark.org/download.html)에서 다운로드
2. 설치 프로그램 실행
3. WinPcap 또는 Npcap 설치 (필수)

### Linux

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install wireshark

# Fedora
sudo dnf install wireshark

# 사용자 권한 설정
sudo usermod -aG wireshark $USER
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
   - Windows: 일반적으로 "Ethernet" 또는 "Wi-Fi"
   - Linux: `eth0`, `wlan0` 등
   - macOS: `en0`, `en1` 등

### 2. 캡처 시작

1. 인터페이스를 더블클릭하거나 선택 후 "Start" 클릭
2. 패킷 캡처가 시작됨

### 3. 캡처 중지

- 메뉴: Capture > Stop
- 단축키: `Ctrl+E` (Windows/Linux) 또는 `Cmd+E` (macOS)

## 게임용 필터 설정

### 기본 필터

게임 포트만 표시하려면 다음 필터를 사용하세요:

```
tcp.port == 9999
```

**적용 방법**:
1. 상단의 필터 입력창에 입력
2. Enter 키를 누르거나 화살표 버튼 클릭
3. 필터가 유효하면 입력창이 녹색으로 표시됨

### 고급 필터

#### 특정 IP로부터의 패킷만 표시

```
tcp.port == 9999 && ip.src == 192.168.1.10
```

#### 특정 IP로 가는 패킷만 표시

```
tcp.port == 9999 && ip.dst == 192.168.1.20
```

#### 두 IP 간의 통신만 표시

```
tcp.port == 9999 && (ip.addr == 192.168.1.10 && ip.addr == 192.168.1.20)
```

#### 페이로드에 특정 문자열 포함

```
tcp.port == 9999 && tcp contains "ATTACK"
```

## 패킷 분석

### 패킷 상세 정보 보기

1. 패킷 목록에서 패킷 클릭
2. 중간 패널에서 계층별 정보 확인:
   - Frame: 프레임 정보
   - Ethernet II: 이더넷 헤더
   - Internet Protocol: IP 헤더
   - Transmission Control Protocol: TCP 헤더
   - Data: 페이로드 (JSON 메시지)

### 페이로드 확인

1. 패킷 선택
2. 하단 패널에서 16진수/ASCII 데이터 확인
3. 또는 "Data" 섹션을 확장하여 내용 확인

### Follow TCP Stream

특정 연결의 전체 대화를 보려면:

1. 패킷 우클릭
2. "Follow" > "TCP Stream" 선택
3. 새 창에서 전체 대화 내용 확인
4. 필터링 옵션:
   - Entire conversation: 양방향 전체
   - Client to Server: 클라이언트 → 서버
   - Server to Client: 서버 → 클라이언트

## 게임 패킷 식별

### 더미 패킷 (DUMMY)

**특징**:
- 출발지: 서버 IP (예: 192.168.1.1)
- 페이로드: `"type": "DUMMY"`로 시작
- 페이로드 내용: `DUMMY_ABCD1234` 형식

**필터**:
```
tcp.port == 9999 && tcp contains "DUMMY"
```

### 공격 패킷 (ATTACK)

**특징**:
- 출발지: 다른 플레이어 IP
- 목적지: 본인 IP
- 페이로드: `"type": "ATTACK"`
- 페이로드 내용: `ATTACK_TARGET_PlayerB` 형식

**본인을 공격한 패킷 찾기**:
```
tcp.port == 9999 && ip.dst == [내 IP] && tcp contains "ATTACK"
```

예시 (내 IP가 192.168.1.20인 경우):
```
tcp.port == 9999 && ip.dst == 192.168.1.20 && tcp contains "ATTACK"
```

### 공격자 IP 추출

1. 공격 패킷 선택
2. IP 계층 확장
3. "Source Address" 확인 → 이것이 공격자 IP
4. 또는 패킷 목록의 "Source" 열 확인

## 실전 팁

### 1. 컬럼 커스터마이징

유용한 컬럼만 표시하려면:

1. 컬럼 헤더 우클릭 > "Column Preferences"
2. 추천 컬럼:
   - No. (패킷 번호)
   - Time (시간)
   - Source (출발지 IP)
   - Destination (목적지 IP)
   - Protocol (프로토콜)
   - Length (길이)
   - Info (정보)

### 2. 색상 규칙

공격 패킷을 빨간색으로 표시하려면:

1. View > Coloring Rules
2. "+" 버튼으로 새 규칙 추가
3. Name: "Attack Packets"
4. Filter: `tcp.port == 9999 && tcp contains "ATTACK"`
5. 전경/배경 색상 설정

### 3. 시간 표시 형식

절대 시간으로 변경:

1. View > Time Display Format
2. "Time of Day" 선택

### 4. 패킷 마크

중요한 패킷 표시:

1. 패킷 우클릭 > "Mark/Unmark Packet"
2. 단축키: `Ctrl+M`
3. 마크된 패킷은 검은 배경으로 표시됨

### 5. 패킷 내보내기

분석을 위해 패킷 저장:

1. File > Export Specified Packets
2. 현재 필터링된 패킷만 저장 가능

## 통계 기능

### Conversations

IP별 통신량 확인:

1. Statistics > Conversations
2. "IPv4" 탭 선택
3. 각 IP 쌍 간의 패킷 수와 바이트 수 확인

### Protocol Hierarchy

프로토콜 분포 확인:

1. Statistics > Protocol Hierarchy
2. TCP, JSON 등의 비율 확인

### I/O Graph

시간에 따른 트래픽 그래프:

1. Statistics > I/O Graph
2. 필터 추가 가능

## 게임 시나리오별 가이드

### 시나리오 1: 공격 탐지

**목표**: 나를 공격한 플레이어의 IP 찾기

**단계**:
1. 필터 적용: `tcp.port == 9999 && ip.dst == [내 IP] && tcp contains "ATTACK"`
2. 공격 패킷의 "Source" 열 확인
3. 발견한 모든 고유 IP를 기록

**예시**:
```
내 IP: 192.168.1.20
필터: tcp.port == 9999 && ip.dst == 192.168.1.20 && tcp contains "ATTACK"
결과: 192.168.1.10, 192.168.1.30 발견
방어 입력: 192.168.1.10, 192.168.1.30
```

### 시나리오 2: 더미와 공격 구분

**목표**: 더미 패킷과 실제 공격 구분

**더미 패킷 특징**:
- 출발지가 서버 IP
- 페이로드에 "DUMMY" 포함

**공격 패킷 특징**:
- 출발지가 클라이언트 IP (서버 아님)
- 페이로드에 "ATTACK" 포함

**필터**:
```
# 더미만
tcp.port == 9999 && tcp contains "DUMMY"

# 공격만
tcp.port == 9999 && tcp contains "ATTACK"
```

### 시나리오 3: 시간대별 공격 분석

**목표**: 특정 시간대의 공격 확인

**단계**:
1. 게임 시작 시각 기록
2. 공격 패킷 필터 적용
3. "Time" 열로 정렬
4. 라운드 시간 (90초) 내의 패킷만 확인

## 문제 해결

### 패킷이 캡처되지 않음

**원인 1**: 잘못된 네트워크 인터페이스 선택
- **해결**: 올바른 인터페이스 선택 (게임 트래픽이 흐르는 인터페이스)

**원인 2**: 권한 부족 (Linux)
- **해결**: `sudo wireshark` 또는 사용자를 wireshark 그룹에 추가

**원인 3**: 방화벽 차단
- **해결**: 방화벽에서 포트 9999 허용

### 다른 플레이어 패킷이 보이지 않음

**원인**: 스위치 환경에서는 다른 포트의 트래픽이 보이지 않음

**해결책**:
1. 서버가 모든 패킷을 재전송하므로 실제로는 모든 패킷 확인 가능
2. 로컬 루프백 (127.0.0.1) 사용 시 모두 동일 호스트이므로 모든 패킷 보임
3. 허브 사용 또는 포트 미러링 설정

### 필터가 작동하지 않음

**원인**: 잘못된 필터 문법

**해결**: 필터 입력 후 입력창 색상 확인
- 녹색: 유효한 필터
- 빨간색: 잘못된 문법
- 노란색: 경고 (작동하지만 비효율적)

## 단축키

- `Ctrl+K`: 캡처 시작
- `Ctrl+E`: 캡처 중지
- `Ctrl+F`: 패킷 찾기
- `Ctrl+G`: 특정 패킷 번호로 이동
- `Ctrl+M`: 패킷 마크
- `Ctrl+Shift+M`: 모든 마크 해제
- `Ctrl+→`: 다음 마크된 패킷
- `Ctrl+←`: 이전 마크된 패킷
- `Alt+→`: 앞으로 가기 (히스토리)
- `Alt+←`: 뒤로 가기 (히스토리)

## 참고 자료

- [Wireshark 공식 문서](https://www.wireshark.org/docs/)
- [Wireshark Display Filters](https://wiki.wireshark.org/DisplayFilters)
- [Wireshark Tutorial](https://www.wireshark.org/docs/wsug_html_chunked/)

## 연습 문제

### 문제 1: 기본 필터

게임 포트(9999)의 모든 트래픽을 표시하는 필터를 작성하세요.

**정답**: `tcp.port == 9999`

### 문제 2: 공격 탐지

192.168.1.20을 목적지로 하는 공격 패킷만 표시하는 필터를 작성하세요.

**정답**: `tcp.port == 9999 && ip.dst == 192.168.1.20 && tcp contains "ATTACK"`

### 문제 3: IP 추출

다음 패킷에서 공격자 IP를 찾으세요:
```
Source: 192.168.1.10
Destination: 192.168.1.20
Payload: {"type": "ATTACK", "from_player": "PlayerA", ...}
```

**정답**: 192.168.1.10

## 고급 주제

### 1. TCP Stream Index

특정 연결의 모든 패킷 찾기:

```
tcp.stream eq 0
```

### 2. 페이로드 길이 필터

큰 패킷만 표시 (1000바이트 이상):

```
tcp.port == 9999 && tcp.len > 1000
```

### 3. JSON 파싱

Wireshark는 JSON을 자동으로 파싱하지 않지만, "Data" 섹션에서 내용을 확인할 수 있습니다.

### 4. 패킷 비교

두 패킷을 나란히 비교:

1. 첫 번째 패킷 우클릭 > "Set/Unset Time Reference"
2. 두 번째 패킷 선택
3. "Time" 열에 차이 시간 표시됨

## 결론

Wireshark는 강력한 패킷 분석 도구입니다. 이 가이드의 기술을 숙지하면 게임에서 공격을 효과적으로 탐지할 수 있습니다.

게임 중에는:
1. 필터를 미리 설정해두세요
2. 공격 패킷의 Source IP만 확인하면 됩니다
3. 시간이 제한되어 있으므로 빠르게 판단하세요
