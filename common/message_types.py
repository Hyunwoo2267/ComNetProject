"""
메시지 타입 정의
JSON 메시지 구조체 클래스
"""

from typing import Any, Dict, Optional
import json
import time
import base64


def encode_payload(payload: str) -> str:
    """
    페이로드를 base64로 인코딩
    Wireshark에서 평문이 보이지 않도록 함

    Args:
        payload: 원본 페이로드 문자열

    Returns:
        base64 인코딩된 문자열
    """
    return base64.b64encode(payload.encode('utf-8')).decode('ascii')


def decode_payload(encoded_payload: str) -> str:
    """
    base64로 인코딩된 페이로드를 디코딩

    Args:
        encoded_payload: base64 인코딩된 문자열

    Returns:
        원본 페이로드 문자열
    """
    try:
        return base64.b64decode(encoded_payload.encode('ascii')).decode('utf-8')
    except Exception:
        # 디코딩 실패 시 원본 반환 (하위 호환성)
        return encoded_payload


class Message:
    """기본 메시지 클래스"""

    def __init__(self, msg_type: str, **kwargs):
        self.type = msg_type
        self.timestamp = time.time()
        self.data = kwargs

    def to_json(self) -> str:
        """JSON 문자열로 변환"""
        message_dict = {
            "type": self.type,
            "timestamp": self.timestamp,
            **self.data
        }
        return json.dumps(message_dict, ensure_ascii=False)

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "type": self.type,
            "timestamp": self.timestamp,
            **self.data
        }

    @classmethod
    def from_json(cls, json_str: str) -> 'Message':
        """JSON 문자열에서 메시지 생성"""
        data = json.loads(json_str)
        msg_type = data.pop('type')
        data.pop('timestamp', None)
        return cls(msg_type, **data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """딕셔너리에서 메시지 생성"""
        msg_type = data.pop('type')
        data.pop('timestamp', None)
        return cls(msg_type, **data)


class DummyMessage(Message):
    """더미 패킷 메시지"""

    def __init__(self, payload: str):
        # 페이로드를 base64로 인코딩하여 Wireshark에서 평문이 보이지 않도록 함
        encoded_payload = encode_payload(payload)
        super().__init__("DUMMY", payload=encoded_payload)


class AttackMessage(Message):
    """공격 패킷 메시지 (v2.0: attack_id 추가)"""

    def __init__(self, from_ip: str = "", to_ip: str = "", from_player: str = "",
                 to_player: str = "", payload: str = "", attack_id: str = ""):
        # 페이로드를 base64로 인코딩하여 Wireshark에서 평문이 보이지 않도록 함
        encoded_payload = encode_payload(payload) if payload else ""
        super().__init__(
            "ATTACK",
            from_ip=from_ip,
            to_ip=to_ip,
            from_player=from_player,
            to_player=to_player,
            payload=encoded_payload,
            attack_id=attack_id  # v2.0: 공격 추적용 ID
        )


class DefenseMessage(Message):
    """방어 입력 메시지"""

    def __init__(self, player_id: str, attacker_ips: list):
        super().__init__(
            "DEFENSE",
            player_id=player_id,
            attacker_ips=attacker_ips
        )


class ScoreMessage(Message):
    """점수 업데이트 메시지"""

    def __init__(self, player_id: str, score: int, hp: int, correct: bool, reason: str = ""):
        super().__init__(
            "SCORE",
            player_id=player_id,
            score=score,
            hp=hp,
            correct=correct,
            reason=reason
        )


class ConnectMessage(Message):
    """연결 메시지"""

    def __init__(self, player_id: str, player_ip: str):
        super().__init__(
            "CONNECT",
            player_id=player_id,
            player_ip=player_ip
        )


class GameStateMessage(Message):
    """게임 상태 메시지"""

    def __init__(self, state: str, round_num: int = 0, time_remaining: int = 0, **kwargs):
        super().__init__(
            state,
            round_num=round_num,
            time_remaining=time_remaining,
            **kwargs
        )


class PlayerListMessage(Message):
    """플레이어 목록 메시지"""

    def __init__(self, players: list):
        super().__init__(
            "PLAYER_LIST",
            players=players
        )


class ErrorMessage(Message):
    """에러 메시지"""

    def __init__(self, error_code: str, error_message: str):
        super().__init__(
            "ERROR",
            error_code=error_code,
            error_message=error_message
        )


class InfoMessage(Message):
    """정보 메시지"""

    def __init__(self, info_type: str, message: str, **kwargs):
        super().__init__(
            "INFO",
            info_type=info_type,
            message=message,
            **kwargs
        )


class AttackRequestMessage(Message):
    """공격 요청 메시지"""

    def __init__(self, attacker_id: str, target_id: str):
        super().__init__(
            "ATTACK_REQUEST",
            attacker_id=attacker_id,
            target_id=target_id
        )


class AttackApprovedMessage(Message):
    """공격 승인 메시지"""

    def __init__(self, attack_id: str, target_ip: str, target_port: int, target_id: str):
        super().__init__(
            "ATTACK_APPROVED",
            attack_id=attack_id,
            target_ip=target_ip,
            target_port=target_port,
            target_id=target_id
        )


class IncomingAttackWarningMessage(Message):
    """수신 공격 경고 메시지"""

    def __init__(self, attack_id: str, attacker_ip: str, attacker_id: str):
        super().__init__(
            "INCOMING_ATTACK_WARNING",
            attack_id=attack_id,
            attacker_ip=attacker_ip,
            attacker_id=attacker_id
        )


class AttackConfirmMessage(Message):
    """공격 확인 메시지 (송신자/수신자 확인용, v2.0)"""

    def __init__(self, attack_id: str, from_player: str = "", to_player: str = "",
                 status: str = "", confirm_type: str = ""):
        """
        Args:
            attack_id: 공격 ID
            from_player: 공격자 ID
            to_player: 타겟 ID
            status: "SENT" 또는 "RECEIVED" (하위 호환성)
            confirm_type: "SENT" 또는 "RECEIVED" (새 파라미터)
        """
        # status와 confirm_type 중 하나를 사용
        final_confirm_type = confirm_type or status

        super().__init__(
            "ATTACK_CONFIRM",
            attack_id=attack_id,
            from_player=from_player,
            to_player=to_player,
            confirm_type=final_confirm_type
        )
