"""
메시지 타입 정의
JSON 메시지 구조체 클래스
"""

from typing import Any, Dict, Optional
import json
import time


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
        super().__init__("DUMMY", payload=payload)


class AttackMessage(Message):
    """공격 패킷 메시지"""

    def __init__(self, from_ip: str, to_ip: str, from_player: str, to_player: str, payload: str):
        super().__init__(
            "ATTACK",
            from_ip=from_ip,
            to_ip=to_ip,
            from_player=from_player,
            to_player=to_player,
            payload=payload
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
