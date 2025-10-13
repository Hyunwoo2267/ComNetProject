"""
게임 클라이언트 모듈
서버와 통신하고 게임 로직 처리
"""

import socket
import threading
import sys
import os
from typing import Optional, Callable

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.protocol import Protocol, ConnectionManager
from common.constants import DEFAULT_PORT, MSG_TYPE_ATTACK, MSG_TYPE_DEFENSE
from common.message_types import Message, ConnectMessage, AttackMessage, DefenseMessage


class GameClient:
    """게임 클라이언트 클래스"""

    def __init__(self, player_id: str, host: str = 'localhost', port: int = DEFAULT_PORT):
        """
        Args:
            player_id: 플레이어 ID
            host: 서버 호스트
            port: 서버 포트
        """
        self.player_id = player_id
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.connected = False
        self.running = False

        # 서버로부터 받은 정보
        self.my_ip = None
        self.game_state = {}
        self.players = []
        self.current_round = 0
        self.my_score = 0
        self.my_hp = 100

        # 콜백 함수들
        self.message_callbacks = []
        self.receive_thread = None

    def connect(self) -> bool:
        """
        서버에 연결

        Returns:
            연결 성공 여부
        """
        try:
            self.socket = ConnectionManager.create_client_socket(self.host, self.port)
            if not self.socket:
                return False

            # 연결 메시지 전송
            connect_msg = ConnectMessage(
                player_id=self.player_id,
                player_ip=""  # 서버가 자동으로 감지
            )
            Protocol.send_message(self.socket, connect_msg)

            # 환영 메시지 수신
            welcome_msg = Protocol.receive_message(self.socket)
            if welcome_msg and welcome_msg.type == "INFO":
                self.my_ip = welcome_msg.data.get('player_ip', 'Unknown')
                print(f"[클라이언트] 서버 연결 성공: {self.my_ip}")

            self.connected = True
            self.running = True

            # 메시지 수신 스레드 시작
            self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.receive_thread.start()

            return True

        except Exception as e:
            print(f"[클라이언트] 연결 실패: {e}")
            return False

    def disconnect(self):
        """서버 연결 종료"""
        self.running = False
        self.connected = False

        if self.socket:
            try:
                ConnectionManager.close_socket(self.socket)
            except:
                pass

        print("[클라이언트] 서버 연결 종료")

    def _receive_loop(self):
        """서버로부터 메시지 수신 루프"""
        while self.running and self.connected:
            try:
                message = Protocol.receive_message(self.socket)

                if not message:
                    print("[클라이언트] 서버 연결 끊김")
                    self.connected = False
                    break

                # 메시지 처리
                self._handle_message(message)

            except Exception as e:
                if self.running:
                    print(f"[클라이언트] 메시지 수신 오류: {e}")
                break

        self.connected = False

    def _handle_message(self, message: Message):
        """
        수신한 메시지 처리

        Args:
            message: 수신 메시지
        """
        msg_type = message.type

        # 게임 상태 업데이트
        if msg_type in ["GAME_START", "ROUND_START", "PLAYING", "DEFENSE_PHASE", "ROUND_END", "GAME_END"]:
            self._update_game_state(message)

        # 플레이어 목록 업데이트
        elif msg_type == "PLAYER_LIST":
            self.players = message.data.get('players', [])

        # 점수 업데이트
        elif msg_type == "SCORE":
            if message.data.get('player_id') == self.player_id:
                self.my_score = message.data.get('score', 0)
                self.my_hp = message.data.get('hp', 100)

        # 더미 패킷
        elif msg_type == "DUMMY":
            pass  # Wireshark로 확인하므로 별도 처리 불필요

        # 공격 패킷
        elif msg_type == "ATTACK":
            pass  # Wireshark로 확인하므로 별도 처리 불필요

        # 콜백 호출
        for callback in self.message_callbacks:
            try:
                callback(message)
            except Exception as e:
                print(f"[클라이언트] 콜백 오류: {e}")

    def _update_game_state(self, message: Message):
        """게임 상태 업데이트"""
        self.game_state = message.to_dict()
        self.current_round = message.data.get('round_num', 0)

    def send_attack(self, target_player_id: str) -> bool:
        """
        다른 플레이어에게 공격 전송

        Args:
            target_player_id: 공격 대상 플레이어 ID

        Returns:
            전송 성공 여부
        """
        if not self.connected:
            print("[클라이언트] 서버에 연결되지 않음")
            return False

        try:
            # 대상 플레이어 정보 찾기
            target_ip = None
            for player in self.players:
                if player['player_id'] == target_player_id:
                    target_ip = player['ip']
                    break

            if not target_ip:
                print(f"[클라이언트] 대상 플레이어 없음: {target_player_id}")
                return False

            # 공격 메시지 생성
            attack_msg = Message(
                MSG_TYPE_ATTACK,
                from_player=self.player_id,
                to_player=target_player_id,
                payload=f"ATTACK_TARGET_{target_player_id}"
            )

            # 전송
            Protocol.send_message(self.socket, attack_msg)
            print(f"[클라이언트] 공격 전송: {self.player_id} -> {target_player_id}")
            return True

        except Exception as e:
            print(f"[클라이언트] 공격 전송 실패: {e}")
            return False

    def submit_defense(self, attacker_ips: list) -> bool:
        """
        방어 답안 제출

        Args:
            attacker_ips: 공격자 IP 리스트

        Returns:
            제출 성공 여부
        """
        if not self.connected:
            print("[클라이언트] 서버에 연결되지 않음")
            return False

        try:
            defense_msg = DefenseMessage(
                player_id=self.player_id,
                attacker_ips=attacker_ips
            )

            Protocol.send_message(self.socket, defense_msg)
            print(f"[클라이언트] 방어 제출: {attacker_ips}")
            return True

        except Exception as e:
            print(f"[클라이언트] 방어 제출 실패: {e}")
            return False

    def add_message_callback(self, callback: Callable[[Message], None]):
        """
        메시지 수신 콜백 추가

        Args:
            callback: 콜백 함수
        """
        self.message_callbacks.append(callback)

    def get_game_state(self) -> dict:
        """현재 게임 상태 반환"""
        return self.game_state.copy()

    def get_players(self) -> list:
        """플레이어 목록 반환"""
        return self.players.copy()

    def get_my_info(self) -> dict:
        """내 정보 반환"""
        return {
            'player_id': self.player_id,
            'ip': self.my_ip,
            'score': self.my_score,
            'hp': self.my_hp,
            'round': self.current_round
        }

    def is_connected(self) -> bool:
        """연결 상태 확인"""
        return self.connected


def main():
    """테스트용 메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="네트워크 보안 게임 클라이언트")
    parser.add_argument('--id', required=True, help="플레이어 ID")
    parser.add_argument('--host', default='localhost', help="서버 호스트")
    parser.add_argument('--port', type=int, default=DEFAULT_PORT, help="서버 포트")

    args = parser.parse_args()

    # 클라이언트 생성 및 연결
    client = GameClient(player_id=args.id, host=args.host, port=args.port)

    if not client.connect():
        print("서버 연결 실패")
        return

    # 메시지 출력 콜백
    def print_message(msg: Message):
        print(f"[메시지] {msg.type}: {msg.data}")

    client.add_message_callback(print_message)

    print("\n명령어:")
    print("  attack <player_id> - 플레이어 공격")
    print("  defense <ip1,ip2,...> - 방어 제출")
    print("  status - 내 상태 확인")
    print("  players - 플레이어 목록")
    print("  quit - 종료")

    # 명령어 입력 루프
    try:
        while client.is_connected():
            command = input("\n> ").strip().split()

            if not command:
                continue

            cmd = command[0].lower()

            if cmd == "attack" and len(command) == 2:
                target = command[1]
                client.send_attack(target)

            elif cmd == "defense" and len(command) == 2:
                ips = command[1].split(',')
                client.submit_defense(ips)

            elif cmd == "status":
                info = client.get_my_info()
                print(f"플레이어: {info['player_id']}")
                print(f"IP: {info['ip']}")
                print(f"점수: {info['score']}")
                print(f"HP: {info['hp']}")
                print(f"라운드: {info['round']}")

            elif cmd == "players":
                players = client.get_players()
                print("플레이어 목록:")
                for p in players:
                    print(f"  - {p['player_id']} ({p['ip']}) | 점수: {p['score']} | HP: {p['hp']}")

            elif cmd == "quit":
                break

            else:
                print("알 수 없는 명령어")

    except KeyboardInterrupt:
        print("\n종료 중...")

    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
