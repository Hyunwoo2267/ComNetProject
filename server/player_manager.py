"""
플레이어 관리 모듈
서버에 연결된 플레이어들의 정보를 관리
"""

import socket
import threading
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class Player:
    """플레이어 정보"""
    player_id: str
    socket: socket.socket
    address: tuple
    ip: str
    score: int = 0
    hp: int = 100
    is_connected: bool = True
    attacks_received: List[str] = field(default_factory=list)  # 이번 라운드에 받은 공격자 IP 목록

    def reset_round_data(self):
        """라운드 데이터 초기화"""
        self.attacks_received.clear()

    def add_attack(self, attacker_ip: str):
        """공격 받은 기록 추가"""
        if attacker_ip not in self.attacks_received:
            self.attacks_received.append(attacker_ip)

    def to_dict(self) -> dict:
        """딕셔너리로 변환 (전송용)"""
        return {
            'player_id': self.player_id,
            'ip': self.ip,
            'score': self.score,
            'hp': self.hp,
            'is_connected': self.is_connected
        }


class PlayerManager:
    """플레이어 관리 클래스"""

    def __init__(self):
        self.players: Dict[str, Player] = {}
        self.lock = threading.Lock()

    def add_player(self, player_id: str, sock: socket.socket, address: tuple) -> Player:
        """
        새 플레이어 추가

        Args:
            player_id: 플레이어 ID
            sock: 플레이어 소켓
            address: 플레이어 주소

        Returns:
            생성된 Player 객체
        """
        with self.lock:
            ip = address[0]
            player = Player(
                player_id=player_id,
                socket=sock,
                address=address,
                ip=ip
            )
            self.players[player_id] = player
            print(f"[PlayerManager] 플레이어 추가: {player_id} ({ip})")
            return player

    def remove_player(self, player_id: str) -> bool:
        """
        플레이어 제거

        Args:
            player_id: 제거할 플레이어 ID

        Returns:
            성공 여부
        """
        with self.lock:
            if player_id in self.players:
                player = self.players[player_id]
                player.is_connected = False
                print(f"[PlayerManager] 플레이어 제거: {player_id}")
                del self.players[player_id]
                return True
            return False

    def get_player(self, player_id: str) -> Optional[Player]:
        """
        플레이어 정보 조회

        Args:
            player_id: 조회할 플레이어 ID

        Returns:
            Player 객체 또는 None
        """
        with self.lock:
            return self.players.get(player_id)

    def get_player_by_ip(self, ip: str) -> Optional[Player]:
        """
        IP로 플레이어 조회

        Args:
            ip: 조회할 IP

        Returns:
            Player 객체 또는 None
        """
        with self.lock:
            for player in self.players.values():
                if player.ip == ip:
                    return player
            return None

    def get_all_players(self) -> List[Player]:
        """모든 플레이어 목록 반환"""
        with self.lock:
            return list(self.players.values())

    def get_player_count(self) -> int:
        """현재 플레이어 수 반환"""
        with self.lock:
            return len(self.players)

    def get_connected_players(self) -> List[Player]:
        """연결된 플레이어 목록 반환"""
        with self.lock:
            return [p for p in self.players.values() if p.is_connected]

    def update_score(self, player_id: str, score_delta: int) -> int:
        """
        플레이어 점수 업데이트

        Args:
            player_id: 플레이어 ID
            score_delta: 점수 변화량

        Returns:
            업데이트된 점수
        """
        with self.lock:
            if player_id in self.players:
                self.players[player_id].score += score_delta
                return self.players[player_id].score
            return 0

    def update_hp(self, player_id: str, hp_delta: int) -> int:
        """
        플레이어 HP 업데이트

        Args:
            player_id: 플레이어 ID
            hp_delta: HP 변화량

        Returns:
            업데이트된 HP
        """
        with self.lock:
            if player_id in self.players:
                self.players[player_id].hp += hp_delta
                if self.players[player_id].hp < 0:
                    self.players[player_id].hp = 0
                return self.players[player_id].hp
            return 0

    def reset_all_round_data(self):
        """모든 플레이어의 라운드 데이터 초기화"""
        with self.lock:
            for player in self.players.values():
                player.reset_round_data()

    def get_players_info(self) -> List[dict]:
        """모든 플레이어 정보를 딕셔너리 리스트로 반환"""
        with self.lock:
            return [player.to_dict() for player in self.players.values()]

    def record_attack(self, target_player_id: str, attacker_ip: str):
        """
        공격 기록

        Args:
            target_player_id: 공격 대상 플레이어 ID
            attacker_ip: 공격자 IP
        """
        with self.lock:
            if target_player_id in self.players:
                self.players[target_player_id].add_attack(attacker_ip)
                print(f"[PlayerManager] 공격 기록: {attacker_ip} -> {target_player_id}")

    def get_attacks_received(self, player_id: str) -> List[str]:
        """
        플레이어가 받은 공격 목록 반환

        Args:
            player_id: 플레이어 ID

        Returns:
            공격자 IP 리스트
        """
        with self.lock:
            if player_id in self.players:
                return self.players[player_id].attacks_received.copy()
            return []

    def clear(self):
        """모든 플레이어 제거"""
        with self.lock:
            self.players.clear()
            print("[PlayerManager] 모든 플레이어 제거됨")
