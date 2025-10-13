"""
메인 서버 모듈
TCP 서버 구현 및 클라이언트 연결 관리
"""

import socket
import threading
import sys
import os

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.protocol import Protocol, ConnectionManager
from common.constants import DEFAULT_HOST, DEFAULT_PORT, MSG_TYPE_ATTACK, MSG_TYPE_DEFENSE, MSG_TYPE_CONNECT, MSG_TYPE_DISCONNECT
from common.message_types import Message, AttackMessage, ConnectMessage, PlayerListMessage, InfoMessage
from server.player_manager import PlayerManager
from server.game_manager import GameManager
from server.dummy_generator import DummyGenerator


class GameServer:
    """게임 서버 클래스"""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False

        # 매니저 초기화
        self.player_manager = PlayerManager()
        self.game_manager = GameManager(self.player_manager, self.broadcast_message)
        self.dummy_generator = DummyGenerator(self.broadcast_message)

        # 클라이언트 핸들러 스레드
        self.client_threads = []

    def start(self):
        """서버 시작"""
        self.server_socket = ConnectionManager.create_server_socket(self.host, self.port)
        if not self.server_socket:
            print("[서버] 서버 소켓 생성 실패")
            return

        self.running = True
        print(f"[서버] {self.host}:{self.port}에서 게임 서버 시작")

        # 클라이언트 연결 대기 스레드
        accept_thread = threading.Thread(target=self._accept_clients, daemon=True)
        accept_thread.start()

        # 메인 루프
        try:
            while self.running:
                command = input("명령어 입력 (start/stop/status/quit): ").strip().lower()

                if command == "start":
                    if self.game_manager.can_start_game():
                        self.game_manager.start_game()
                        self.dummy_generator.start()
                        print("[서버] 게임 시작됨")
                    else:
                        print(f"[서버] 최소 2명의 플레이어가 필요합니다.")

                elif command == "stop":
                    self.game_manager.stop_game()
                    self.dummy_generator.stop()
                    print("[서버] 게임 중지됨")

                elif command == "status":
                    self._print_status()

                elif command == "quit":
                    print("[서버] 서버 종료 중...")
                    self.stop()
                    break

        except KeyboardInterrupt:
            print("\n[서버] Ctrl+C 감지, 서버 종료 중...")
            self.stop()

    def stop(self):
        """서버 중지"""
        self.running = False
        self.game_manager.stop_game()
        self.dummy_generator.stop()

        # 모든 클라이언트 연결 종료
        for player in self.player_manager.get_all_players():
            try:
                ConnectionManager.close_socket(player.socket)
            except:
                pass

        # 서버 소켓 종료
        if self.server_socket:
            try:
                ConnectionManager.close_socket(self.server_socket)
            except:
                pass

        print("[서버] 서버 종료됨")

    def _accept_clients(self):
        """클라이언트 연결 수락"""
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                print(f"[서버] 새 연결: {address}")

                # 클라이언트 핸들러 스레드 시작
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, address),
                    daemon=True
                )
                client_thread.start()
                self.client_threads.append(client_thread)

            except Exception as e:
                if self.running:
                    print(f"[서버] 클라이언트 수락 오류: {e}")
                break

    def _handle_client(self, client_socket: socket.socket, address: tuple):
        """
        개별 클라이언트 처리

        Args:
            client_socket: 클라이언트 소켓
            address: 클라이언트 주소
        """
        player_id = None

        try:
            # 첫 메시지: 연결 메시지 수신
            connect_msg = Protocol.receive_message(client_socket)
            if not connect_msg or connect_msg.type != MSG_TYPE_CONNECT:
                print(f"[서버] {address} - 잘못된 연결 메시지")
                return

            player_id = connect_msg.data.get('player_id', f"Player_{address[0]}")

            # 플레이어 추가
            player = self.player_manager.add_player(player_id, client_socket, address)

            # 연결 확인 메시지 전송
            welcome_msg = InfoMessage(
                info_type="WELCOME",
                message=f"환영합니다, {player_id}!",
                player_id=player_id,
                player_ip=player.ip
            )
            Protocol.send_message(client_socket, welcome_msg)

            # 현재 플레이어 목록 브로드캐스트
            self._broadcast_player_list()

            # 클라이언트 메시지 수신 루프
            while self.running and player.is_connected:
                message = Protocol.receive_message(client_socket)

                if not message:
                    print(f"[서버] {player_id} 연결 끊김")
                    break

                # 메시지 처리
                self._process_message(player, message)

        except Exception as e:
            print(f"[서버] {address} 처리 중 오류: {e}")

        finally:
            # 플레이어 제거
            if player_id:
                self.player_manager.remove_player(player_id)
                self._broadcast_player_list()

            # 소켓 종료
            try:
                ConnectionManager.close_socket(client_socket)
            except:
                pass

    def _process_message(self, player, message: Message):
        """
        메시지 처리

        Args:
            player: 송신 플레이어
            message: 수신 메시지
        """
        msg_type = message.type

        if msg_type == MSG_TYPE_ATTACK:
            self._handle_attack(player, message)

        elif msg_type == MSG_TYPE_DEFENSE:
            self._handle_defense(player, message)

        else:
            print(f"[서버] 알 수 없는 메시지 타입: {msg_type}")

    def _handle_attack(self, attacker_player, message: Message):
        """
        공격 메시지 처리

        Args:
            attacker_player: 공격자 플레이어
            message: 공격 메시지
        """
        to_player_id = message.data.get('to_player')
        target_player = self.player_manager.get_player(to_player_id)

        if not target_player:
            print(f"[서버] 공격 대상 없음: {to_player_id}")
            return

        # 공격 기록
        self.player_manager.record_attack(to_player_id, attacker_player.ip)

        # 공격 메시지를 대상에게 전송
        attack_msg = AttackMessage(
            from_ip=attacker_player.ip,
            to_ip=target_player.ip,
            from_player=attacker_player.player_id,
            to_player=target_player.player_id,
            payload=message.data.get('payload', f"ATTACK_TARGET_{to_player_id}")
        )

        Protocol.send_message(target_player.socket, attack_msg)
        print(f"[서버] 공격: {attacker_player.player_id} -> {to_player_id}")

    def _handle_defense(self, player, message: Message):
        """
        방어 메시지 처리

        Args:
            player: 방어 플레이어
            message: 방어 메시지
        """
        attacker_ips = message.data.get('attacker_ips', [])
        self.game_manager.submit_defense(player.player_id, attacker_ips)
        print(f"[서버] {player.player_id} 방어 제출: {attacker_ips}")

    def broadcast_message(self, message: Message, target_players=None):
        """
        메시지 브로드캐스트

        Args:
            message: 브로드캐스트할 메시지
            target_players: 대상 플레이어 목록 (None이면 전체)
        """
        if target_players is None:
            target_players = self.player_manager.get_all_players()

        for player in target_players:
            if player.is_connected:
                try:
                    Protocol.send_message(player.socket, message)
                except Exception as e:
                    print(f"[서버] {player.player_id}에게 메시지 전송 실패: {e}")

    def _broadcast_player_list(self):
        """플레이어 목록 브로드캐스트"""
        players_info = self.player_manager.get_players_info()
        msg = PlayerListMessage(players=players_info)
        self.broadcast_message(msg, None)

    def _print_status(self):
        """서버 상태 출력"""
        print("\n========== 서버 상태 ==========")
        print(f"플레이어 수: {self.player_manager.get_player_count()}")
        print(f"게임 상태: {self.game_manager.state.value}")
        print(f"현재 라운드: {self.game_manager.current_round}")
        print("\n플레이어 목록:")
        for player in self.player_manager.get_all_players():
            print(f"  - {player.player_id} ({player.ip}) | 점수: {player.score} | HP: {player.hp}")
        print("===============================\n")


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="네트워크 보안 게임 서버")
    parser.add_argument('--host', default=DEFAULT_HOST, help=f"서버 호스트 (기본값: {DEFAULT_HOST})")
    parser.add_argument('--port', type=int, default=DEFAULT_PORT, help=f"서버 포트 (기본값: {DEFAULT_PORT})")

    args = parser.parse_args()

    server = GameServer(host=args.host, port=args.port)
    server.start()


if __name__ == "__main__":
    main()
