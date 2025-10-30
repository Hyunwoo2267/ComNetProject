# 네트워크 프로토콜 명세 (v2.0)

## 개요

이 문서는 네트워크 보안 게임에서 사용되는 TCP 기반 커스텀 프로토콜을 정의합니다.

**v2.0 주요 변경사항**:
- P2P (Peer-to-Peer) 공격 시스템 도입
- 서버 승인 기반 공격 메커니즘
- 가상 IP 시스템 (172.20.1.x)

## 네트워크 계층 구조

### Transport Layer (전송 계층)
- **프로토콜**: TCP
- **실제 IP**: Docker 네트워크 (172.20.0.x)
- **서버 포트**: 9999
- **P2P 포트**: 10001 ~ 10020 (플레이어별 고유 포트)

### Application Layer (응용 계층)
- **가상 IP**: 172.20.1.1 ~ 172.20.1.20
- **게임 로직**: 가상 IP 기반
- **패킷 분석**: 실제 IP (172.20.0.x) 사용

**중요**: 게임 내부에서는 가상 IP를 사용하지만, Wireshark로 패킷을 캡처하면 실제 IP (172.20.0.x)가 보입니다.

## 전송 계층

### TCP 연결

#### 서버-클라이언트 연결
- **포트**: 9999 (기본값)
- **프로토콜**: TCP
- **인코딩**: UTF-8
- **용도**: 게임 상태 동기화, 제어 메시지

#### P2P 연결 (v2.0)
- **포트**: 10001 + player_index
- **프로토콜**: TCP
- **인코딩**: UTF-8
- **용도**: 플레이어 간 직접 공격

### 메시지 프레이밍

각 메시지는 다음과 같은 구조로 전송됩니다:

```
[4바이트 헤더][메시지 본문]
```

- **헤더**: 메시지 길이 (unsigned int, 빅 엔디안)
- **본문**: JSON 형식의 메시지 데이터

## 메시지 형식

### 기본 구조

모든 메시지는 다음 필드를 포함합니다:

```json
{
  "type": "메시지 타입",
  "timestamp": 1234567890.123
}
```

- `type`: 메시지 타입 (문자열)
- `timestamp`: 메시지 생성 시각 (UNIX timestamp, float)

## 메시지 타입

### 1. CONNECT (클라이언트 → 서버)

클라이언트가 서버에 처음 연결할 때 전송하는 메시지입니다.

```json
{
  "type": "CONNECT",
  "timestamp": 1234567890.123,
  "player_id": "PlayerA",
  "player_ip": "",
  "p2p_port": 10001
}
```

**필드**:
- `player_id`: 플레이어 ID (문자열)
- `player_ip`: 플레이어 IP (서버가 자동 감지하므로 빈 문자열)
- `p2p_port`: P2P 공격 수신용 포트 (v2.0)

**응답**: INFO (WELCOME) + 할당된 가상 IP

---

### 2. DUMMY (서버 → 클라이언트)

서버가 게임 중에 주기적으로 전송하는 더미 패킷입니다.

```json
{
  "type": "DUMMY",
  "timestamp": 1234567890.123,
  "payload": "base64_encoded_data"
}
```

**필드**:
- `payload`: Base64로 인코딩된 더미 데이터

**목적**: 네트워크 트래픽을 복잡하게 만들어 패킷 분석 난이도 증가

**라운드별 빈도**:
- R1: 2.0초 간격
- R2: 1.5초 간격
- R3: 1.0초 간격
- R4: 0.8초 간격
- R5: 0.5초 간격

---

### 3. NOISE (플레이어 ↔ 플레이어, 서버 중계)

R3부터 추가되는 노이즈 트래픽입니다.

```json
{
  "type": "NOISE",
  "timestamp": 1234567890.123,
  "from_ip": "172.20.1.1",
  "to_ip": "172.20.1.2",
  "payload": "base64_encoded_data"
}
```

**필드**:
- `from_ip`: 송신자 가상 IP
- `to_ip`: 수신자 가상 IP
- `payload`: Base64로 인코딩된 노이즈 데이터

**목적**: 공격이 아닌 일반 트래픽을 시뮬레이션하여 난이도 증가

**활성화**: R3 이상

---

### 4. ATTACK (v2.0 P2P 방식)

#### 4-1. ATTACK_REQUEST (클라이언트 → 서버)

플레이어가 공격을 요청하는 메시지입니다.

```json
{
  "type": "ATTACK_REQUEST",
  "timestamp": 1234567890.123,
  "attacker_id": "Player1",
  "target_id": "Player2"
}
```

**필드**:
- `attacker_id`: 공격자 ID
- `target_id`: 대상 플레이어 ID

**서버 검증**:
- 공격 가능 횟수 체크 (라운드별 제한)
- 대상 플레이어 존재 여부
- 게임 상태 확인 (PLAYING 상태만 허용)

---

#### 4-2. ATTACK_APPROVED (서버 → 공격자)

서버가 공격을 승인하는 메시지입니다.

```json
{
  "type": "ATTACK_APPROVED",
  "timestamp": 1234567890.123,
  "attack_id": "attack_uuid_1234",
  "target_id": "Player2",
  "target_ip": "172.20.0.2",
  "target_port": 10002,
  "timeout": 5.0
}
```

**필드**:
- `attack_id`: 고유 공격 ID (UUID)
- `target_id`: 대상 플레이어 ID
- `target_ip`: 대상 실제 IP (P2P 연결용)
- `target_port`: 대상 P2P 포트
- `timeout`: 공격 타임아웃 (초)

**공격자 동작**:
1. `target_ip:target_port`로 TCP 연결
2. `AttackMessage` 전송
3. 서버에 `ATTACK_CONFIRM` (전송 확인) 전송

---

#### 4-3. AttackMessage (공격자 → 대상, P2P)

실제 공격 데이터입니다.

```json
{
  "type": "ATTACK",
  "timestamp": 1234567890.123,
  "attack_id": "attack_uuid_1234",
  "attacker_id": "Player1",
  "attacker_ip": "172.20.1.1",
  "payload": "base64_encoded_attack_data"
}
```

**필드**:
- `attack_id`: 서버가 발급한 공격 ID
- `attacker_id`: 공격자 ID
- `attacker_ip`: 공격자 가상 IP
- `payload`: Base64로 인코딩된 공격 데이터

**전송 방식**: P2P TCP 직접 연결 (서버 중계 없음)

---

#### 4-4. ATTACK_CONFIRM (양방향, 클라이언트 → 서버)

공격 송신/수신을 서버에 확인하는 메시지입니다.

```json
{
  "type": "ATTACK_CONFIRM",
  "timestamp": 1234567890.123,
  "attack_id": "attack_uuid_1234",
  "confirm_type": "sent",  // "sent" 또는 "received"
  "player_id": "Player1"
}
```

**필드**:
- `attack_id`: 공격 ID
- `confirm_type`:
  - `"sent"`: 공격자가 전송 완료 확인
  - `"received"`: 대상자가 수신 완료 확인
- `player_id`: 확인하는 플레이어 ID

**서버 동작**:
- 양쪽 확인이 모두 도착하면 공격을 정식 기록 (`real_attacks` 리스트에 추가)
- 타임아웃 내에 확인이 안 오면 공격 실패 처리

---

#### 4-5. INCOMING_ATTACK_WARNING (서버 → 대상)

공격이 들어올 것을 대상에게 미리 알림 (P2P 수신 준비용)

```json
{
  "type": "INCOMING_ATTACK_WARNING",
  "timestamp": 1234567890.123,
  "attack_id": "attack_uuid_1234",
  "attacker_id": "Player1"
}
```

**필드**:
- `attack_id`: 공격 ID
- `attacker_id`: 공격자 ID

**대상 동작**:
1. P2P 리스너에서 연결 대기
2. 공격 메시지 수신
3. 서버에 `ATTACK_CONFIRM` (수신 확인) 전송

---

### 5. DECOY_ATTACK (서버 → 클라이언트, R5만)

가짜 공격 패킷입니다. R5에서만 생성됩니다.

```json
{
  "type": "DECOY_ATTACK",
  "timestamp": 1234567890.123,
  "from_ip": "172.20.1.99",
  "to_ip": "172.20.1.2",
  "payload": "base64_encoded_fake_data"
}
```

**필드**:
- `from_ip`: 가짜 송신자 IP (실존하지 않음)
- `to_ip`: 수신자 가상 IP
- `payload`: Base64로 인코딩된 가짜 데이터

**목적**:
- R5 난이도 증가
- 실제 공격과 가짜 공격을 구분하는 능력 테스트

**특징**:
- 서버에서 직접 생성하여 전송
- 실제 플레이어가 보낸 것처럼 위장
- 방어 제출 시 오답으로 간주

---

### 6. DEFENSE (클라이언트 → 서버)

플레이어가 방어 입력 단계에서 공격자 IP를 제출하는 메시지입니다.

```json
{
  "type": "DEFENSE",
  "timestamp": 1234567890.123,
  "player_id": "PlayerA",
  "attacker_ips": ["172.20.1.1", "172.20.1.3"]
}
```

**필드**:
- `player_id`: 제출하는 플레이어 ID
- `attacker_ips`: 탐지한 공격자 **가상 IP** 목록

**중요**:
- Wireshark에서는 실제 IP (172.20.0.x)가 보이지만, 게임에서는 가상 IP (172.20.1.x)로 제출해야 함
- 동일 IP의 여러 공격 중 1개만 방어됨 (v2.1)

**제출 누적**:
- 여러 번 제출 시 누적됨 (덮어쓰기 안 됨)
- 중복 제거하여 최종 제출

---

### 7. SCORE (서버 → 클라이언트)

서버가 플레이어에게 점수 업데이트를 전송하는 메시지입니다.

```json
{
  "type": "SCORE",
  "timestamp": 1234567890.123,
  "player_id": "PlayerA",
  "score": -5,
  "hp": 80,
  "score_change": -14,
  "reason": "정답: 1개 (+10점), 오답: 2개 (-10점), 놓친 공격: 2개 (-6점), HP -20"
}
```

**필드**:
- `player_id`: 플레이어 ID
- `score`: 현재 총점 (음수 가능, v2.1)
- `hp`: 현재 HP
- `score_change`: 이번 라운드 점수 변화
- `reason`: 점수 변화 이유

**점수 계산 (R1-R4)**:
- 정답 방어: +10점
- 오답 방어: -5점
- 놓친 공격: -3점 및 HP -10

**점수 계산 (R5)**:
- 정답 방어: +15점
- 오답 방어: -10점
- 놓친 공격: -5점 및 HP -10

---

### 8. GAME_START (서버 → 클라이언트)

게임이 시작될 때 전송되는 메시지입니다.

```json
{
  "type": "GAME_START",
  "timestamp": 1234567890.123,
  "round_num": 0,
  "total_rounds": 5,
  "message": "게임 시작! 총 5 라운드",
  "players": [
    {"player_id": "Player1", "ip": "172.20.1.1", "score": 0, "hp": 100},
    {"player_id": "Player2", "ip": "172.20.1.2", "score": 0, "hp": 100}
  ]
}
```

**필드**:
- `round_num`: 현재 라운드 (0 = 게임 시작)
- `total_rounds`: 전체 라운드 수 (5)
- `message`: 게임 메시지
- `players`: 플레이어 목록 (가상 IP 포함)

---

### 9. ROUND_START (서버 → 클라이언트)

라운드가 시작될 때 전송되는 메시지입니다.

```json
{
  "type": "ROUND_START",
  "timestamp": 1234567890.123,
  "round_num": 1,
  "time_remaining": 10,
  "total_rounds": 5,
  "message": "라운드 1 준비 중...",
  "difficulty": {
    "name": "입문",
    "attack_limit": 3,
    "dummy_interval": 2.0,
    "noise_traffic": false,
    "decoy_attacks": false,
    "hint": "기본적인 IP 기반 공격 탐지를 학습하세요"
  }
}
```

**필드**:
- `round_num`: 라운드 번호 (1~5)
- `time_remaining`: 준비 시간 (초)
- `total_rounds`: 전체 라운드 수
- `message`: 메시지
- `difficulty`: 라운드별 난이도 정보

---

### 10. PLAYING (서버 → 클라이언트)

게임 진행 단계가 시작될 때 전송되는 메시지입니다.

```json
{
  "type": "PLAYING",
  "timestamp": 1234567890.123,
  "round_num": 1,
  "time_remaining": 90,
  "message": "게임 진행 중! 공격하고 Wireshark로 방어하세요!"
}
```

**필드**:
- `round_num`: 라운드 번호
- `time_remaining`: 게임 시간 (초, 기본 90초)
- `message`: 메시지

---

### 11. DEFENSE_PHASE (서버 → 클라이언트)

방어 입력 단계가 시작될 때 전송되는 메시지입니다.

```json
{
  "type": "DEFENSE_PHASE",
  "timestamp": 1234567890.123,
  "round_num": 1,
  "time_remaining": 20,
  "message": "방어 단계! 공격자 IP를 입력하세요!"
}
```

**필드**:
- `round_num`: 라운드 번호
- `time_remaining`: 방어 입력 시간 (초, 기본 20초)
- `message`: 메시지

---

### 12. ROUND_END (서버 → 클라이언트)

라운드가 종료될 때 전송되는 메시지입니다.

```json
{
  "type": "ROUND_END",
  "timestamp": 1234567890.123,
  "round_num": 1,
  "message": "라운드 1 종료",
  "players": [
    {"player_id": "Player1", "ip": "172.20.1.1", "score": 7, "hp": 90},
    {"player_id": "Player2", "ip": "172.20.1.2", "score": -3, "hp": 80}
  ]
}
```

**필드**:
- `round_num`: 라운드 번호
- `message`: 메시지
- `players`: 업데이트된 플레이어 목록

---

### 13. GAME_END (서버 → 클라이언트)

게임이 종료될 때 전송되는 메시지입니다.

```json
{
  "type": "GAME_END",
  "timestamp": 1234567890.123,
  "message": "게임 종료! 우승: Player1",
  "rankings": [
    {"rank": 1, "player_id": "Player1", "score": 85, "hp": 70},
    {"rank": 2, "player_id": "Player2", "score": -10, "hp": 40}
  ],
  "winner": "Player1"
}
```

**필드**:
- `message`: 게임 종료 메시지
- `rankings`: 최종 순위
- `winner`: 우승자 ID

---

### 14. PLAYER_LIST (서버 → 클라이언트)

플레이어 목록이 변경될 때 전송되는 메시지입니다.

```json
{
  "type": "PLAYER_LIST",
  "timestamp": 1234567890.123,
  "players": [
    {"player_id": "Player1", "ip": "172.20.1.1", "score": 0, "hp": 100, "is_connected": true},
    {"player_id": "Player2", "ip": "172.20.1.2", "score": 0, "hp": 100, "is_connected": true}
  ]
}
```

**필드**:
- `players`: 플레이어 목록

**전송 시점**:
- 플레이어 연결/연결 해제
- HP 변경 (v2.1)
- 점수 변경

---

### 15. INFO (서버 → 클라이언트)

일반 정보 메시지입니다.

```json
{
  "type": "INFO",
  "timestamp": 1234567890.123,
  "info_type": "WELCOME",
  "message": "환영합니다, Player1!",
  "player_id": "Player1",
  "player_ip": "172.20.1.1"
}
```

**필드**:
- `info_type`: 정보 타입
- `message`: 메시지 내용
- 기타 추가 정보

---

### 16. ERROR (서버 → 클라이언트)

오류 메시지입니다.

```json
{
  "type": "ERROR",
  "timestamp": 1234567890.123,
  "error_code": "INVALID_TARGET",
  "error_message": "공격 대상이 존재하지 않습니다."
}
```

**필드**:
- `error_code`: 오류 코드
- `error_message`: 오류 메시지

**주요 오류 코드**:
- `INVALID_TARGET`: 공격 대상이 존재하지 않음
- `ATTACK_LIMIT_EXCEEDED`: 공격 횟수 초과
- `INVALID_GAME_STATE`: 잘못된 게임 상태
- `ATTACK_TIMEOUT`: 공격 타임아웃

## 통신 흐름

### 1. 연결 및 대기

```
Client A                Server                Client B
   |                       |                       |
   |---CONNECT------------>|                       |
   |   (p2p_port: 10001)   |                       |
   |<--INFO (WELCOME)------|                       |
   |   (virtual_ip:        |                       |
   |    172.20.1.1)        |                       |
   |                       |<-----CONNECT----------|
   |                       |      (p2p_port: 10002)|
   |                       |------INFO (WELCOME)-->|
   |                       |      (virtual_ip:     |
   |                       |       172.20.1.2)     |
   |<--PLAYER_LIST---------|---PLAYER_LIST-------->|
   |                       |                       |
```

### 2. 게임 시작

```
   |                       |                       |
   |<--GAME_START----------|---GAME_START--------->|
   |<--ROUND_START---------|---ROUND_START-------->|
   |   (난이도 정보 포함)    |   (난이도 정보 포함)   |
   |                       |                       |
```

### 3. 게임 진행 (v2.0 P2P 공격)

```
   |                       |                       |
   |<--PLAYING-------------|---PLAYING------------>|
   |<--DUMMY---------------|---DUMMY-------------->|
   |                       |                       |
   |---ATTACK_REQUEST----->|                       |
   |   (target: B)         |                       |
   |                       |--INCOMING_ATTACK----->|
   |                       |  _WARNING             |
   |<--ATTACK_APPROVED-----|                       |
   |   (target_ip:         |                       |
   |    172.20.0.2:10002)  |                       |
   |                       |                       |
   |=========== P2P TCP 연결 (172.20.0.2:10002) ==>|
   |---AttackMessage------>|                       |
   |   (직접 전송)          |                       |
   |                       |                       |
   |---ATTACK_CONFIRM----->|<--ATTACK_CONFIRM------|
   |   (confirm: sent)     |   (confirm: received) |
   |                       |                       |
   |           [서버: 양쪽 확인 완료 → 공격 기록]     |
   |                       |                       |
```

### 4. 노이즈 트래픽 (R3+)

```
   |                       |                       |
   |<--NOISE---------------|---NOISE-------------->|
   |   (from: 172.20.1.1   |   (from: 172.20.1.2   |
   |    to: 172.20.1.2)    |    to: 172.20.1.1)    |
   |                       |                       |
```

### 5. 가짜 공격 (R5)

```
   |                       |                       |
   |                       |---DECOY_ATTACK------->|
   |                       |   (from: 172.20.1.99) |
   |                       |                       |
```

### 6. 방어 및 점수 계산

```
   |                       |                       |
   |<--DEFENSE_PHASE-------|---DEFENSE_PHASE------>|
   |---DEFENSE------------>|                       |
   |   (IPs: [172.20.1.2]) |                       |
   |                       |<-----DEFENSE----------|
   |                       |      (IPs: [172.20.1.1])|
   |<--SCORE---------------|                       |
   |   (score: +7, hp: 90) |                       |
   |                       |------SCORE----------->|
   |                       |      (score: -3, hp: 80)|
   |<--PLAYER_LIST---------|---PLAYER_LIST-------->|
   |   (HP 업데이트 반영)   |   (HP 업데이트 반영)   |
   |<--ROUND_END-----------|---ROUND_END---------->|
   |                       |                       |
```

### 7. 게임 종료

```
   |                       |                       |
   |<--GAME_END------------|---GAME_END----------->|
   |   (rankings, winner)  |   (rankings, winner)  |
   |                       |                       |
```

## 라운드별 난이도 설정

| 라운드 | 이름 | 공격 제한 | 더미 간격 | 노이즈 | 가짜 공격 |
|--------|------|-----------|-----------|--------|-----------|
| R1 | 입문 | 3회 | 2.0초 | ❌ | ❌ |
| R2 | 초급 | 3회 | 1.5초 | ❌ | ❌ |
| R3 | 중급 | 4회 | 1.0초 | ✅ | ❌ |
| R4 | 고급 | 4회 | 0.8초 | ✅ | ❌ |
| R5 | 최종 | 5회 | 0.5초 | ✅ | ✅ (10개) |

## 보안 고려사항

이 프로젝트는 교육용이므로 다음 보안 기능은 **의도적으로** 구현되지 않았습니다:

- ❌ 암호화 (TLS/SSL) - Wireshark 패킷 분석을 위해 평문 전송
- ❌ 인증 및 권한 부여 - 단순한 ID 기반 연결
- ❌ 입력 검증 및 sanitization - 신뢰된 환경 가정
- ❌ DDoS 방어 - 교육용 환경

**실제 프로덕션 환경에서는 이러한 기능들을 반드시 구현해야 합니다.**

## Base64 인코딩

모든 페이로드 데이터는 Base64로 인코딩되어 전송됩니다:

```python
import base64
payload = "ATTACK_TARGET_Player2"
encoded = base64.b64encode(payload.encode()).decode()
```

**목적**:
- 패킷 내용을 약간 난독화 (암호화는 아님)
- 바이너리 데이터 안전 전송
- 게임 난이도 증가 (Wireshark에서 직접 읽기 어렵게)

**복호화**:
```python
decoded = base64.b64decode(encoded).decode()
```

## 확장성

새로운 메시지 타입을 추가하려면:

1. `common/message_types.py`에 새 메시지 클래스 추가
2. `common/constants.py`에 메시지 타입 상수 추가
3. 서버/클라이언트의 메시지 핸들러 업데이트
4. 이 문서에 명세 추가

## 참고 파일

- `common/message_types.py`: 메시지 클래스 정의
- `common/protocol.py`: 프로토콜 송수신 함수
- `common/constants.py`: 상수 정의
- `server/game_manager.py`: 게임 로직 및 공격 관리
- `client/web_client.py`: 웹 클라이언트 구현
