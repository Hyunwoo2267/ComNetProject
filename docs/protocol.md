# 네트워크 프로토콜 명세

## 개요

이 문서는 네트워크 보안 게임에서 사용되는 TCP 기반 커스텀 프로토콜을 정의합니다.

## 전송 계층

### TCP 연결

- **포트**: 9999 (기본값)
- **프로토콜**: TCP
- **인코딩**: UTF-8

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
  "player_ip": ""
}
```

**필드**:
- `player_id`: 플레이어 ID (문자열)
- `player_ip`: 플레이어 IP (서버가 자동 감지하므로 빈 문자열)

**응답**: INFO (WELCOME)

---

### 2. DUMMY (서버 → 클라이언트)

서버가 게임 중에 주기적으로 전송하는 더미 패킷입니다.

```json
{
  "type": "DUMMY",
  "timestamp": 1234567890.123,
  "payload": "DUMMY_ABCD1234"
}
```

**필드**:
- `payload`: 더미 데이터 (DUMMY_로 시작)

**목적**: 네트워크 트래픽을 복잡하게 만들어 패킷 분석 난이도 증가

---

### 3. ATTACK (클라이언트 → 서버 → 클라이언트)

플레이어가 다른 플레이어를 공격하는 메시지입니다.

**클라이언트 → 서버**:
```json
{
  "type": "ATTACK",
  "timestamp": 1234567890.123,
  "from_player": "PlayerA",
  "to_player": "PlayerB",
  "payload": "ATTACK_TARGET_PlayerB"
}
```

**서버 → 대상 클라이언트**:
```json
{
  "type": "ATTACK",
  "timestamp": 1234567890.123,
  "from_ip": "192.168.1.10",
  "to_ip": "192.168.1.20",
  "from_player": "PlayerA",
  "to_player": "PlayerB",
  "payload": "ATTACK_TARGET_PlayerB"
}
```

**필드**:
- `from_player`: 공격자 ID
- `to_player`: 대상 플레이어 ID
- `from_ip`: 공격자 IP (서버가 추가)
- `to_ip`: 대상 IP (서버가 추가)
- `payload`: 공격 데이터 (ATTACK_로 시작)

---

### 4. DEFENSE (클라이언트 → 서버)

플레이어가 방어 입력 단계에서 공격자 IP를 제출하는 메시지입니다.

```json
{
  "type": "DEFENSE",
  "timestamp": 1234567890.123,
  "player_id": "PlayerA",
  "attacker_ips": ["192.168.1.20", "192.168.1.30"]
}
```

**필드**:
- `player_id`: 제출하는 플레이어 ID
- `attacker_ips`: 탐지한 공격자 IP 목록

---

### 5. SCORE (서버 → 클라이언트)

서버가 플레이어에게 점수 업데이트를 전송하는 메시지입니다.

```json
{
  "type": "SCORE",
  "timestamp": 1234567890.123,
  "player_id": "PlayerA",
  "score": 85,
  "hp": 90,
  "correct": true,
  "reason": "정확한 방어: 2개 (+20점)"
}
```

**필드**:
- `player_id`: 플레이어 ID
- `score`: 현재 점수
- `hp`: 현재 HP
- `correct`: 정답 여부
- `reason`: 점수 변화 이유

---

### 6. GAME_START (서버 → 클라이언트)

게임이 시작될 때 전송되는 메시지입니다.

```json
{
  "type": "GAME_START",
  "timestamp": 1234567890.123,
  "round_num": 0,
  "total_rounds": 5,
  "message": "게임 시작! 총 5 라운드",
  "players": [
    {"player_id": "PlayerA", "ip": "192.168.1.10", "score": 0, "hp": 100},
    {"player_id": "PlayerB", "ip": "192.168.1.20", "score": 0, "hp": 100}
  ]
}
```

**필드**:
- `round_num`: 현재 라운드 (0 = 게임 시작)
- `total_rounds`: 전체 라운드 수
- `message`: 게임 메시지
- `players`: 플레이어 목록

---

### 7. ROUND_START (서버 → 클라이언트)

라운드가 시작될 때 전송되는 메시지입니다.

```json
{
  "type": "ROUND_START",
  "timestamp": 1234567890.123,
  "round_num": 1,
  "time_remaining": 10,
  "total_rounds": 5,
  "message": "라운드 1 준비 중..."
}
```

**필드**:
- `round_num`: 라운드 번호
- `time_remaining`: 준비 시간 (초)
- `total_rounds`: 전체 라운드 수
- `message`: 메시지

---

### 8. PLAYING (서버 → 클라이언트)

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
- `time_remaining`: 게임 시간 (초)
- `message`: 메시지

---

### 9. DEFENSE_PHASE (서버 → 클라이언트)

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
- `time_remaining`: 방어 입력 시간 (초)
- `message`: 메시지

---

### 10. ROUND_END (서버 → 클라이언트)

라운드가 종료될 때 전송되는 메시지입니다.

```json
{
  "type": "ROUND_END",
  "timestamp": 1234567890.123,
  "round_num": 1,
  "message": "라운드 1 종료",
  "players": [
    {"player_id": "PlayerA", "ip": "192.168.1.10", "score": 25, "hp": 90},
    {"player_id": "PlayerB", "ip": "192.168.1.20", "score": 20, "hp": 100}
  ]
}
```

**필드**:
- `round_num`: 라운드 번호
- `message`: 메시지
- `players`: 업데이트된 플레이어 목록

---

### 11. GAME_END (서버 → 클라이언트)

게임이 종료될 때 전송되는 메시지입니다.

```json
{
  "type": "GAME_END",
  "timestamp": 1234567890.123,
  "message": "게임 종료! 우승: PlayerA",
  "rankings": [
    {"rank": 1, "player_id": "PlayerA", "score": 120, "hp": 70},
    {"rank": 2, "player_id": "PlayerB", "score": 95, "hp": 80}
  ],
  "winner": "PlayerA"
}
```

**필드**:
- `message`: 게임 종료 메시지
- `rankings`: 최종 순위
- `winner`: 우승자 ID

---

### 12. PLAYER_LIST (서버 → 클라이언트)

플레이어 목록이 변경될 때 전송되는 메시지입니다.

```json
{
  "type": "PLAYER_LIST",
  "timestamp": 1234567890.123,
  "players": [
    {"player_id": "PlayerA", "ip": "192.168.1.10", "score": 0, "hp": 100, "is_connected": true},
    {"player_id": "PlayerB", "ip": "192.168.1.20", "score": 0, "hp": 100, "is_connected": true}
  ]
}
```

**필드**:
- `players`: 플레이어 목록

---

### 13. INFO (서버 → 클라이언트)

일반 정보 메시지입니다.

```json
{
  "type": "INFO",
  "timestamp": 1234567890.123,
  "info_type": "WELCOME",
  "message": "환영합니다, PlayerA!",
  "player_id": "PlayerA",
  "player_ip": "192.168.1.10"
}
```

**필드**:
- `info_type`: 정보 타입
- `message`: 메시지 내용
- 기타 추가 정보

---

### 14. ERROR (서버 → 클라이언트)

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

## 통신 흐름

### 1. 연결 및 대기

```
Client A                Server                Client B
   |                       |                       |
   |---CONNECT------------>|                       |
   |<--INFO (WELCOME)------|                       |
   |                       |<-----CONNECT----------|
   |                       |------INFO (WELCOME)-->|
   |<--PLAYER_LIST---------|---PLAYER_LIST-------->|
   |                       |                       |
```

### 2. 게임 시작

```
   |                       |                       |
   |<--GAME_START----------|---GAME_START--------->|
   |<--ROUND_START---------|---ROUND_START-------->|
   |                       |                       |
```

### 3. 게임 진행

```
   |                       |                       |
   |<--PLAYING-------------|---PLAYING------------>|
   |<--DUMMY---------------|---DUMMY-------------->|
   |                       |                       |
   |---ATTACK (to B)------>|                       |
   |                       |---ATTACK (from A)---->|
   |                       |                       |
```

### 4. 방어 및 점수 계산

```
   |                       |                       |
   |<--DEFENSE_PHASE-------|---DEFENSE_PHASE------>|
   |---DEFENSE------------>|                       |
   |                       |<-----DEFENSE----------|
   |<--SCORE---------------|                       |
   |                       |------SCORE----------->|
   |<--ROUND_END-----------|---ROUND_END---------->|
   |                       |                       |
```

### 5. 게임 종료

```
   |                       |                       |
   |<--GAME_END------------|---GAME_END----------->|
   |                       |                       |
```

## 확장성

새로운 메시지 타입을 추가하려면:

1. `common/message_types.py`에 새 메시지 클래스 추가
2. `common/constants.py`에 메시지 타입 상수 추가
3. 서버/클라이언트의 메시지 핸들러 업데이트
4. 이 문서에 명세 추가

## 보안 고려사항

이 프로젝트는 교육용이므로 다음 보안 기능은 구현되지 않았습니다:

- 암호화 (TLS/SSL)
- 인증 및 권한 부여
- 입력 검증 및 sanitization
- DDoS 방어

실제 프로덕션 환경에서는 이러한 기능들을 반드시 구현해야 합니다.
