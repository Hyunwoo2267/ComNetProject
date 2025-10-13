# 네트워크 보안 게임 프로젝트

TCP 패킷 분석 기반 네트워크 방어 게임

## 프로젝트 개요

이 프로젝트는 TCP/IP 프로토콜과 패킷 분석을 학습하기 위한 교육용 멀티플레이어 게임입니다. 플레이어들은 서로 공격 패킷을 전송하고, Wireshark를 사용하여 자신을 향한 공격을 탐지하여 방어합니다.

## 주요 기능

- **멀티플레이어 지원**: 2-4명의 플레이어가 동시에 게임 참여
- **TCP 소켓 통신**: Python 소켓 프로그래밍을 통한 실시간 통신
- **패킷 분석**: Wireshark를 활용한 실제 네트워크 트래픽 분석
- **더미 패킷 생성**: 게임 중 자동으로 더미 패킷 전송
- **점수 시스템**: 정확한 방어와 공격 성공에 따른 점수 계산
- **GUI 인터페이스**: tkinter 기반의 직관적인 사용자 인터페이스

## 시스템 구조

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│  Client A   │◄────────►│    Server    │◄────────►│  Client B   │
│  (GUI)      │          │  - 게임 관리 │          │  (GUI)      │
│  - 공격     │          │  - 더미 생성 │          │  - 공격     │
│  - 방어     │          │  - 점수 계산 │          │  - 방어     │
└─────────────┘          └──────────────┘          └─────────────┘
       │                        │                          │
       └────────────► Wireshark 패킷 캡처 ◄────────────────┘
```

## 프로젝트 구조

```
ComNetProject/
├── common/                 # 공통 모듈 (서버/클라이언트 공유)
│   ├── __init__.py
│   ├── constants.py       # 상수 정의
│   ├── message_types.py   # 메시지 타입 클래스
│   └── protocol.py        # TCP 프로토콜 핸들러
│
├── server/                # 서버 모듈
│   ├── __init__.py
│   ├── server.py          # 메인 서버 (CLI)
│   ├── server_gui.py      # 서버 GUI
│   ├── game_manager.py    # 게임 로직 관리
│   ├── player_manager.py  # 플레이어 관리
│   └── dummy_generator.py # 더미 패킷 생성
│
├── client/                # 클라이언트 모듈
│   ├── __init__.py
│   ├── client.py          # 클라이언트 핵심 로직
│   └── gui.py             # GUI 인터페이스
│
├── docs/                  # 문서
│   ├── protocol.md        # 프로토콜 명세
│   ├── user_manual.md     # 사용자 매뉴얼
│   └── wireshark_guide.md # Wireshark 사용 가이드
│
├── README.md
└── requirements.txt
```

## 설치 및 실행

### 요구사항

- Python 3.8 이상
- Wireshark (패킷 분석용)

### 설치

```bash
# 의존성 설치
pip install -r requirements.txt

# Wireshark 설치 (Windows)
# https://www.wireshark.org/download.html 에서 다운로드
```

### 서버 실행

#### GUI 서버 (권장)

```bash
# GUI 서버 실행
python -m server.server_gui

# 또는 호스트/포트 지정
python -m server.server_gui --host 0.0.0.0 --port 9999
```

GUI 서버 기능:
- 서버 시작/중지 버튼
- 게임 시작/중지 버튼
- 실시간 플레이어 목록 표시
- 게임 상태 모니터링
- 서버 로그 표시

#### CLI 서버 (고급 사용자)

```bash
# 콘솔 서버 실행
python -m server.server

# 또는 호스트/포트 지정
python -m server.server --host 0.0.0.0 --port 9999
```

서버 명령어:
- `start`: 게임 시작
- `stop`: 게임 중지
- `status`: 현재 상태 확인
- `quit`: 서버 종료

### 클라이언트 실행 (GUI)

```bash
# GUI 클라이언트 실행
python -m client.gui --id PlayerA --host localhost --port 9999

# 다른 터미널에서 추가 클라이언트 실행
python -m client.gui --id PlayerB --host localhost --port 9999
```

### 클라이언트 실행 (CLI)

```bash
# 콘솔 클라이언트 실행 (테스트용)
python -m client.client --id PlayerA --host localhost --port 9999
```

## 게임 방법

### 1. 준비 단계

1. Wireshark를 실행하고 네트워크 인터페이스 선택
2. 필터 설정: `tcp.port == 9999`
3. 패킷 캡처 시작

### 2. 게임 진행

1. **대기실**: 최소 2명의 플레이어가 접속할 때까지 대기
2. **라운드 시작**: 서버가 게임을 시작하면 5라운드 진행
3. **게임 단계** (90초):
   - 서버가 더미 패킷을 주기적으로 전송
   - 플레이어들이 서로 공격 패킷 전송
   - Wireshark로 자신을 향한 공격 패킷 탐지
4. **방어 단계** (20초):
   - 탐지한 공격자의 IP 주소를 입력하여 제출
5. **점수 계산**:
   - 정확한 방어: +10점
   - 잘못된 IP 입력: -5점
   - 공격 탐지 실패: -10 HP
   - 공격 성공 (상대가 탐지 못함): +5점

### 3. Wireshark 사용법

#### 필수 필터
```
tcp.port == 9999
```

#### 더미 패킷 식별
- 출발지: 서버 IP
- 페이로드: `DUMMY_`로 시작

#### 공격 패킷 식별
- 출발지: 다른 클라이언트 IP
- 목적지: 본인의 IP
- 페이로드: `ATTACK_`로 시작

#### 분석 팁
1. **Follow TCP Stream**: 우클릭 → Follow → TCP Stream
2. **Statistics > Conversations**: IP별 통신량 확인
3. 시간 순서대로 정렬하여 최근 패킷 확인

## 모듈 설명

### Common 모듈 (공통)

서버와 클라이언트에서 공유되는 코드:

- **constants.py**: 게임 설정, 네트워크 설정 등 상수 정의
- **message_types.py**: JSON 메시지 구조체 클래스
- **protocol.py**: TCP 메시지 송수신 프로토콜 구현

### Server 모듈

서버 측 기능:

- **server.py**: TCP 서버, 클라이언트 연결 관리 (CLI)
- **server_gui.py**: 서버 GUI 인터페이스 (권장)
- **game_manager.py**: 게임 상태, 라운드 진행, 점수 계산
- **player_manager.py**: 플레이어 정보 관리
- **dummy_generator.py**: 더미 패킷 자동 생성

### Client 모듈

클라이언트 측 기능:

- **client.py**: 서버 통신, 게임 로직 처리
- **gui.py**: tkinter 기반 GUI 인터페이스

## 프로토콜 명세

### 메시지 형식

모든 메시지는 JSON 형식이며, 다음 구조를 따릅니다:

```json
{
  "type": "메시지 타입",
  "timestamp": 1234567890.123,
  ... (추가 데이터)
}
```

### 주요 메시지 타입

1. **CONNECT**: 클라이언트 연결
2. **DUMMY**: 더미 패킷
3. **ATTACK**: 공격 패킷
4. **DEFENSE**: 방어 제출
5. **SCORE**: 점수 업데이트
6. **GAME_START/ROUND_START/PLAYING/DEFENSE_PHASE/ROUND_END/GAME_END**: 게임 상태

자세한 내용은 [프로토콜 명세](docs/protocol.md)를 참조하세요.

## 개발 가이드

### 서버 확장

새로운 게임 모드나 기능을 추가하려면:

1. `common/constants.py`에 필요한 상수 추가
2. `server/game_manager.py`의 게임 로직 수정
3. 필요시 새로운 메시지 타입을 `common/message_types.py`에 추가

### 클라이언트 확장

GUI를 개선하거나 새로운 기능을 추가하려면:

1. `client/gui.py`의 UI 위젯 추가/수정
2. `client/client.py`에 새로운 메서드 추가
3. 서버 메시지 핸들러 업데이트

## 문제 해결

### 방화벽 차단

Windows 방화벽에서 포트 9999를 허용해야 합니다:

```
제어판 > Windows Defender 방화벽 > 고급 설정
인바운드 규칙 > 새 규칙 > 포트 > TCP 9999 허용
```

### 다른 클라이언트 패킷이 보이지 않음

서버가 모든 패킷을 각 클라이언트에 재전송하므로, 같은 네트워크가 아니어도 패킷을 확인할 수 있습니다.

### 연결 실패

1. 서버가 실행 중인지 확인
2. 호스트와 포트가 올바른지 확인
3. 방화벽 설정 확인

## 기여

이 프로젝트는 교육 목적으로 제작되었습니다. 개선 사항이나 버그 리포트는 환영합니다.

## 라이센스

이 프로젝트는 교육용으로 제작되었습니다.

## 팀 정보

- 프로젝트명: TCP 패킷 분석 기반 네트워크 방어 게임
- 목적: TCP/IP 프로토콜 학습 및 패킷 분석 실습

## 참고 자료

- [Python Socket 공식 문서](https://docs.python.org/3/library/socket.html)
- [Wireshark 사용자 가이드](https://www.wireshark.org/docs/wsug_html_chunked/)
- [TCP/IP 프로토콜](https://en.wikipedia.org/wiki/Internet_protocol_suite)
