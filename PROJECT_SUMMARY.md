# 프로젝트 구현 요약

## 프로젝트 정보

- **프로젝트명**: TCP 패킷 분석 기반 네트워크 방어 게임
- **목적**: TCP/IP 프로토콜 학습 및 패킷 분석 실습
- **구현 언어**: Python 3.8+
- **아키텍처**: 클라이언트-서버 모델, 모듈화 설계

## 구현 완료 항목

### 1. 공통 모듈 (common/)

완전히 분리된 공통 모듈로, 서버와 클라이언트가 공유:

- ✅ **constants.py**: 게임 설정, 네트워크 설정 등 모든 상수 정의
- ✅ **message_types.py**: JSON 메시지 클래스 (객체지향 설계)
  - Message (기본 클래스)
  - DummyMessage, AttackMessage, DefenseMessage
  - ScoreMessage, ConnectMessage, GameStateMessage 등
- ✅ **protocol.py**: TCP 통신 프로토콜 구현
  - 메시지 길이 헤더 기반 프레이밍
  - 안전한 송수신 보장
  - ConnectionManager 유틸리티

### 2. 서버 모듈 (server/)

완전히 모듈화된 서버 구현:

- ✅ **server.py**: 메인 서버 (CLI)
  - TCP 소켓 서버
  - 멀티클라이언트 처리 (threading)
  - 명령어 인터페이스 (start/stop/status/quit)

- ✅ **server_gui.py**: 서버 GUI (권장)
  - tkinter 기반 서버 관리 인터페이스
  - 버튼 클릭으로 서버/게임 제어
  - 실시간 플레이어 목록 및 점수 표시
  - 게임 상태 모니터링
  - 색상별 로그 표시

- ✅ **game_manager.py**: 게임 로직 관리
  - 게임 상태 머신 (FSM)
  - 라운드 진행 관리
  - 점수 계산 시스템
  - 타이머 관리

- ✅ **player_manager.py**: 플레이어 관리
  - 플레이어 정보 저장 (dataclass)
  - 점수/HP 관리
  - 공격 기록 추적
  - 스레드 안전 (Lock)

- ✅ **dummy_generator.py**: 더미 패킷 생성
  - 백그라운드 스레드
  - 랜덤 간격 생성
  - 랜덤 페이로드

### 3. 클라이언트 모듈 (client/)

서버와 완전히 분리된 클라이언트 구현:

- ✅ **client.py**: 클라이언트 핵심 로직
  - 서버 연결 관리
  - 메시지 수신 스레드
  - 공격/방어 기능
  - 콜백 시스템
  - CLI 인터페이스

- ✅ **gui.py**: tkinter 기반 GUI
  - 직관적인 사용자 인터페이스
  - 실시간 게임 상태 표시
  - 플레이어 목록 (Treeview)
  - 공격/방어 인터페이스
  - 게임 로그

### 4. 문서 (docs/)

상세한 문서 작성:

- ✅ **README.md**: 프로젝트 개요 및 사용법
- ✅ **protocol.md**: 프로토콜 명세서 (14가지 메시지 타입)
- ✅ **wireshark_guide.md**: Wireshark 사용 가이드
- ✅ **user_manual.md**: 사용자 매뉴얼
- ✅ **requirements.txt**: 의존성 목록
- ✅ **.gitignore**: Git 무시 파일

## 주요 기능

### 네트워크 통신

1. **커스텀 TCP 프로토콜**
   - 4바이트 헤더 (메시지 길이)
   - JSON 페이로드
   - UTF-8 인코딩
   - 안전한 메시지 프레이밍

2. **멀티플레이어 지원**
   - 동시 2-4명 플레이어
   - 비동기 메시지 처리
   - 스레드 안전 설계

### 게임 메커니즘

1. **라운드 시스템**
   - 5라운드 진행
   - 준비 → 게임 → 방어 → 결과 단계
   - 타이머 기반 진행

2. **더미 패킷 생성**
   - 1-2초 랜덤 간격
   - 백그라운드 자동 생성
   - 난이도 조절 가능

3. **점수 계산**
   - 정확한 방어: +10점
   - 잘못된 방어: -5점
   - 놓친 공격: -10 HP
   - 공격 성공: +5점

### Wireshark 통합

1. **패킷 분석**
   - 필터: `tcp.port == 9999`
   - 더미 패킷 식별
   - 공격 패킷 탐지

2. **IP 추출**
   - Source 필드에서 공격자 IP 확인
   - Follow TCP Stream 지원

## 모듈화 설계

### 계층 구조

```
Application Layer
├── GUI (client/gui.py)
└── CLI (server/server.py, client/client.py)

Business Logic Layer
├── Game Manager (server/game_manager.py)
├── Player Manager (server/player_manager.py)
└── Dummy Generator (server/dummy_generator.py)

Network Layer
├── Protocol (common/protocol.py)
├── Message Types (common/message_types.py)
└── Constants (common/constants.py)

Transport Layer
└── TCP Socket
```

### 모듈 간 의존성

```
server.py
  ├── game_manager.py
  │   └── player_manager.py
  ├── player_manager.py
  ├── dummy_generator.py
  └── common/
      ├── protocol.py
      ├── message_types.py
      └── constants.py

client.py
  └── common/
      ├── protocol.py
      ├── message_types.py
      └── constants.py

gui.py
  └── client.py
      └── common/
```

### 서버-클라이언트 분리

**서버 전용**:
- server/game_manager.py
- server/player_manager.py
- server/dummy_generator.py
- server/server.py (CLI)
- server/server_gui.py (GUI)

**클라이언트 전용**:
- client/client.py
- client/gui.py

**공유**:
- common/ (전체)

### 추후 확장 가능성

1. **독립 실행 가능**:
   - 서버: `python -m server.server`
   - 클라이언트: `python -m client.gui` 또는 `python -m client.client`

2. **모듈 재사용**:
   - common/ 모듈은 다른 네트워크 프로젝트에서도 사용 가능
   - Protocol 클래스는 범용 TCP 통신에 활용 가능

3. **쉬운 확장**:
   - 새 메시지 타입 추가: message_types.py에 클래스 추가
   - 새 게임 모드: game_manager.py 수정
   - 새 UI: client/ 디렉토리에 추가

## 코드 통계

### 파일 수
- Python 파일: 13개
- 문서 파일: 5개
- 총 라인: 약 3,500줄 이상

### 모듈별 라인 수 (추정)
- common/: ~600줄
- server/: ~1,500줄 (GUI 추가)
- client/: ~800줄
- docs/: ~600줄

## 구현 특징

### 1. 객체지향 설계

- 클래스 기반 구조
- 상속 활용 (Message 클래스)
- 캡슐화 (Manager 클래스들)
- dataclass 활용 (Player)

### 2. 스레드 안전

- threading.Lock 사용
- 데이터 경쟁 방지
- 안전한 공유 자원 접근

### 3. 에러 처리

- try-except 블록
- 안전한 소켓 종료
- 연결 끊김 처리

### 4. 확장성

- 모듈화된 구조
- 설정 파일 분리 (constants.py)
- 콜백 시스템

### 5. 문서화

- 모든 함수에 docstring
- 타입 힌트 사용
- 상세한 주석

## 실행 방법

### 서버 실행

**GUI 서버 (권장)**:
```bash
python -m server.server_gui
```

**CLI 서버**:
```bash
python -m server.server
```

명령어:
- `start`: 게임 시작
- `stop`: 게임 중지
- `status`: 상태 확인
- `quit`: 종료

### 클라이언트 실행 (GUI)

```bash
python -m client.gui --id PlayerA
```

### 클라이언트 실행 (CLI)

```bash
python -m client.client --id PlayerB
```

## 테스트 시나리오

### 로컬 테스트

1. 터미널 1: 서버 실행
2. 터미널 2-3: 클라이언트 2개 실행
3. Wireshark에서 Loopback 인터페이스 캡처
4. 서버에서 `start` 명령어 입력
5. 게임 진행

### 네트워크 테스트

1. 서버 컴퓨터: 서버 실행 (IP: 192.168.1.100)
2. 클라이언트 컴퓨터들: `--host 192.168.1.100` 옵션으로 연결
3. 각자 Wireshark로 패킷 캡처
4. 게임 진행

## 학습 목표 달성

### TCP/IP 프로토콜 학습 ✅
- TCP 소켓 프로그래밍
- 클라이언트-서버 모델
- 메시지 프레이밍
- 포트 및 IP 주소 이해

### 패킷 분석 도구 활용 ✅
- Wireshark 필터링
- TCP Stream 분석
- 패킷 구조 이해
- 네트워크 트래픽 분석

### 네트워크 보안 기초 ✅
- 트래픽 분석
- 공격 탐지
- IP 추적
- 네트워크 모니터링

### 멀티스레드 프로그래밍 ✅
- threading 모듈 활용
- 동시성 제어
- 스레드 안전 설계
- 비동기 처리

## 향후 확장 가능 기능

### 추가 가능한 기능

1. **보안 강화**
   - TLS/SSL 암호화
   - 인증 시스템
   - 세션 관리

2. **게임 모드**
   - 팀전
   - 토너먼트 모드
   - 랭킹 시스템

3. **UI 개선**
   - PyQt5로 전환
   - 그래프 시각화
   - 애니메이션

4. **데이터베이스**
   - 플레이어 정보 저장
   - 게임 기록 저장
   - 통계 기능

5. **자동 분석**
   - scapy 통합
   - 자동 패킷 분석
   - AI 플레이어

## 프로젝트 구조 (최종)

```
ComNetProject/
│
├── common/                      # 공통 모듈
│   ├── __init__.py
│   ├── constants.py            # 상수 정의
│   ├── message_types.py        # 메시지 클래스
│   └── protocol.py             # 통신 프로토콜
│
├── server/                      # 서버 모듈
│   ├── __init__.py
│   ├── server.py               # 메인 서버 (CLI)
│   ├── server_gui.py           # 서버 GUI (권장)
│   ├── game_manager.py         # 게임 관리
│   ├── player_manager.py       # 플레이어 관리
│   └── dummy_generator.py      # 더미 패킷 생성
│
├── client/                      # 클라이언트 모듈
│   ├── __init__.py
│   ├── client.py               # 클라이언트 로직
│   └── gui.py                  # GUI 인터페이스
│
├── docs/                        # 문서
│   ├── protocol.md             # 프로토콜 명세
│   ├── wireshark_guide.md      # Wireshark 가이드
│   └── user_manual.md          # 사용자 매뉴얼
│
├── README.md                    # 프로젝트 개요
├── requirements.txt             # 의존성
├── .gitignore                   # Git 무시 파일
└── PROJECT_SUMMARY.md          # 이 파일
```

## 결론

이 프로젝트는 TCP/IP 네트워크 프로그래밍과 패킷 분석을 학습하기 위한 완전한 교육용 게임입니다.

**주요 성과**:
- ✅ 완전한 모듈화 설계
- ✅ 서버-클라이언트 명확한 분리
- ✅ 확장 가능한 아키텍처
- ✅ 상세한 문서화
- ✅ 즉시 실행 가능

프로젝트는 추후 독립적인 프로그램으로 쉽게 분리 및 배포할 수 있으며, 교육 목적뿐만 아니라 실제 네트워크 학습 도구로 활용 가능합니다.
