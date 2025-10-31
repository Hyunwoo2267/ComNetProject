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
from common.constants import (
    DEFAULT_PORT, MSG_TYPE_ATTACK, MSG_TYPE_DEFENSE,
    MSG_TYPE_ATTACK_REQUEST, MSG_TYPE_ATTACK_APPROVED,
    MSG_TYPE_INCOMING_ATTACK_WARNING, MSG_TYPE_ATTACK_CONFIRM,
    PLAYER_ATTACK_PORT_BASE
)
from common.message_types import (
    Message, ConnectMessage, AttackMessage, DefenseMessage,
    AttackRequestMessage, AttackConfirmMessage, InfoMessage,
    AttackApprovedMessage, IncomingAttackWarningMessage
)


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

        # v2.0: P2P 공격 시스템
        self.my_index = -1  # P2P 포트 계산용 플레이어 인덱스
        self.p2p_server_socket: Optional[socket.socket] = None
        self.p2p_server_thread: Optional[threading.Thread] = None
        self.p2p_port: Optional[int] = None
        self.pending_attacks = {}  # 진행 중인 공격 추적

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
            if not Protocol.send_message(self.socket, connect_msg):
                print("[클라이언트] 연결 메시지 전송 실패")
                return False

            # 환영 메시지 수신
            welcome_msg = Protocol.receive_message(self.socket)
            if not welcome_msg or welcome_msg.type != "INFO":
                print(f"[클라이언트] 잘못된 환영 메시지 수신: {welcome_msg.to_dict() if welcome_msg else 'None'}")
                self.disconnect()
                return False

            self.my_ip = welcome_msg.data.get('player_ip', 'Unknown')
            self.my_index = welcome_msg.data.get('player_index', -1)

            if self.my_index == -1:
                print("[클라이언트] 오류: 유효하지 않은 플레이어 인덱스 수신")
                self.disconnect()
                return False

            print(f"[클라이언트] 서버 연결 성공: {self.my_ip} (인덱스: {self.my_index})")

            # P2P 서버 시작
            if not self._start_p2p_server():
                self.disconnect()
                return False

            self.connected = True
            self.running = True

            # 메시지 수신 스레드 시작
            self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.receive_thread.start()

            return True

        except Exception as e:
            print(f"[클라이언트] 연결 실패: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _start_p2p_server(self) -> bool:
        """v2.0: P2P 공격 수신 서버 시작"""
        try:
            self.p2p_port = PLAYER_ATTACK_PORT_BASE + self.my_index
            print(f"[P2P] P2P 서버 시작 시도: player_id={self.player_id}, index={self.my_index}, port={self.p2p_port}")

            self.p2p_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            print(f"[P2P] 소켓 생성 완료")

            self.p2p_server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            print(f"[P2P] SO_REUSEADDR 설정 완료")

            self.p2p_server_socket.bind(('0.0.0.0', self.p2p_port))
            print(f"[P2P] 바인드 완료: 0.0.0.0:{self.p2p_port}")

            self.p2p_server_socket.listen(5)
            print(f"[P2P] listen(5) 완료")

            self.p2p_server_thread = threading.Thread(target=self._p2p_server_loop, daemon=True)
            self.p2p_server_thread.start()
            print(f"[P2P] 서버 스레드 시작됨: thread_id={self.p2p_server_thread.ident}")

            print(f"[클라이언트] P2P 서버 시작 성공: 포트 {self.p2p_port}")
            return True
        except Exception as e:
            print(f"[클라이언트] P2P 서버 시작 실패: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _p2p_server_loop(self):
        """P2P 공격 수신 루프"""
        print(f"[P2P] 서버 루프 시작: player_id={self.player_id}, port={self.p2p_port}, running={self.running}")

        loop_count = 0
        while self.running:
            try:
                loop_count += 1
                if loop_count == 1 or loop_count % 10 == 0:
                    print(f"[P2P] accept() 대기 중... (loop_count={loop_count}, port={self.p2p_port})")

                client_sock, client_addr = self.p2p_server_socket.accept()
                print(f"[P2P] ✅ 공격 연결 수신 성공: {client_addr} (loop_count={loop_count})")

                handler_thread = threading.Thread(
                    target=self._handle_p2p_attack,
                    args=(client_sock, client_addr),
                    daemon=True
                )
                handler_thread.start()
                print(f"[P2P] 핸들러 스레드 시작: thread_id={handler_thread.ident}")
            except Exception as e:
                if self.running:
                    print(f"[P2P] ❌ 연결 수락 오류: {e}")
                    import traceback
                    traceback.print_exc()
                else:
                    print(f"[P2P] 서버 루프 정상 종료 (running=False)")
                break

        print(f"[P2P] 서버 루프 종료: player_id={self.player_id}, loop_count={loop_count}")

    def _handle_p2p_attack(self, client_sock: socket.socket, client_addr: tuple):
        """P2P 공격 처리"""
        print(f"[P2P] 핸들러 시작: client_addr={client_addr}, player_id={self.player_id}")
        try:
            print(f"[P2P] 메시지 수신 대기 중...")
            attack_msg = Protocol.receive_message(client_sock)
            print(f"[P2P] 메시지 수신 완료: type={attack_msg.type if attack_msg else None}")

            if not attack_msg or attack_msg.type != MSG_TYPE_ATTACK:
                print(f"[P2P] ❌ 잘못된 메시지 타입: {attack_msg.type if attack_msg else 'None'}")
                return

            attacker_id = attack_msg.data.get('from_player')
            attack_id = attack_msg.data.get('attack_id')

            print(f"[P2P] ✅ 공격 수신: {attacker_id} -> {self.player_id} (attack_id: {attack_id})")

            # 서버에 공격 수신 확인 전송
            confirm_msg = AttackConfirmMessage(
                attack_id=attack_id,
                from_player=attacker_id,
                to_player=self.player_id,
                status="RECEIVED"
            )

            print(f"[P2P] 서버에 수신 확인 전송 시도...")
            Protocol.send_message(self.socket, confirm_msg)
            print(f"[P2P] ✅ 공격 수신 확인 전송 완료: {attack_id}")
        except Exception as e:
            print(f"[P2P] ❌ 공격 처리 오류: {e}")
            import traceback
            traceback.print_exc()
        finally:
            try:
                client_sock.close()
                print(f"[P2P] 클라이언트 소켓 닫음: {client_addr}")
            except Exception as e:
                print(f"[P2P] 소켓 닫기 오류: {e}")

    def _send_p2p_attack(self, attack_id: str, target_player_id: str, target_ip: str, target_port: int):
        """v2.0: P2P 직접 공격 전송"""
        print(f"[P2P] 공격 전송 시작: {self.player_id} -> {target_player_id} ({target_ip}:{target_port})")
        attack_socket = None
        try:
            print(f"[P2P] 소켓 생성 중...")
            attack_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            attack_socket.settimeout(5.0)

            print(f"[P2P] 연결 시도: {target_ip}:{target_port}")
            attack_socket.connect((target_ip, target_port))
            print(f"[P2P] ✅ 직접 연결 성공: {target_ip}:{target_port}")

            attack_msg = AttackMessage(
                from_player=self.player_id,
                to_player=target_player_id,
                payload=f"ATTACK_{attack_id}",
                attack_id=attack_id
            )

            print(f"[P2P] 공격 메시지 전송 중... (attack_id={attack_id})")
            Protocol.send_message(attack_socket, attack_msg)
            print(f"[P2P] ✅ 공격 패킷 전송 완료: {self.player_id} -> {target_player_id}")

            confirm_msg = AttackConfirmMessage(
                attack_id=attack_id,
                from_player=self.player_id,
                to_player=target_player_id,
                status="SENT"
            )

            print(f"[P2P] 서버에 전송 확인 전송 중...")
            Protocol.send_message(self.socket, confirm_msg)
            print(f"[P2P] ✅ 공격 전송 확인 완료: {attack_id}")
        except socket.timeout:
            print(f"[P2P] ❌ 공격 전송 타임아웃: {target_ip}:{target_port}")
        except ConnectionRefusedError:
            print(f"[P2P] ❌ 연결 거부됨: {target_ip}:{target_port} (대상 P2P 서버가 실행 중이 아님)")
        except Exception as e:
            print(f"[P2P] ❌ 공격 전송 실패: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if attack_socket:
                try:
                    attack_socket.close()
                    print(f"[P2P] 공격 소켓 닫음")
                except:
                    pass

    def disconnect(self):
        """서버 연결 종료"""
        self.running = False
        self.connected = False

        if self.socket:
            try:
                ConnectionManager.close_socket(self.socket)
            except:
                pass

        # P2P 서버 소켓 닫기
        if self.p2p_server_socket:
            try:
                self.p2p_server_socket.close()
                print("[클라이언트] P2P 서버 소켓 닫음")
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
        msg_data = message.data

        # 게임 상태 업데이트
        if msg_type in ["GAME_START", "ROUND_START", "PLAYING", "DEFENSE_PHASE", "ROUND_END", "GAME_END"]:
            self._update_game_state(message)

        # 플레이어 목록 업데이트
        elif msg_type == "PLAYER_LIST":
            self.players = msg_data.get('players', [])
            # 플레이어 인덱스 업데이트
            for idx, player in enumerate(self.players):
                if player['player_id'] == self.player_id:
                    self.my_index = idx
                    break

        # 점수 업데이트
        elif msg_type == "SCORE":
            if msg_data.get('player_id') == self.player_id:
                self.my_score = msg_data.get('score', 0)
                self.my_hp = msg_data.get('hp', 100)

        # v2.0: 공격 승인
        elif msg_type == MSG_TYPE_ATTACK_APPROVED:
            self._handle_attack_approved(message)

        # v2.0: 수신 공격 경고
        elif msg_type == MSG_TYPE_INCOMING_ATTACK_WARNING:
            print(f"[클라이언트] 공격 경고: {msg_data.get('attacker_id')}로부터 공격 예정")

        # 정보 메시지 (공격 거부 등)
        elif msg_type == "INFO":
            if msg_data.get('info_type') == "ATTACK_DENIED":
                print(f"[클라이언트] 공격 거부됨: {msg_data.get('message')}")

        # 더미 패킷 (로깅 외 처리 불필요)
        elif msg_type == "DUMMY":
            pass

        # 콜백 호출
        for callback in self.message_callbacks:
            try:
                callback(message)
            except Exception as e:
                print(f"[클라이언트] 콜백 오류: {e}")

    def _handle_attack_approved(self, message: Message):
        """v2.0: 서버로부터 공격 승인을 받았을 때 처리"""
        attack_id = message.data.get('attack_id')
        target_player_id = message.data.get('target_id')
        target_ip = message.data.get('target_ip')
        target_port = message.data.get('target_port')

        print(f"[클라이언트] 공격 승인됨: {attack_id} -> {target_player_id} ({target_ip}:{target_port})")

        attack_thread = threading.Thread(
            target=self._send_p2p_attack,
            args=(attack_id, target_player_id, target_ip, target_port),
            daemon=True
        )
        attack_thread.start()

    def _update_game_state(self, message: Message):
        """게임 상태 업데이트"""
        self.game_state = message.to_dict()
        self.current_round = message.data.get('round_num', 0)

    def send_attack(self, target: str) -> bool:
        """v2.0: 다른 플레이어에게 공격 요청 (서버 승인 후 P2P 전송)"""
        if not self.connected:
            print("[클라이언트] 서버에 연결되지 않음")
            return False

        try:
            print(f"[클라이언트] 공격 시도: target={target}")
            print(f"[클라이언트] 현재 플레이어 목록: {self.players}")

            target_player = None
            for player in self.players:
                if player['player_id'] == target or player['ip'] == target:
                    target_player = player
                    break

            if not target_player:
                print(f"[클라이언트] 대상 플레이어 없음: {target}")
                print(f"[클라이언트] 가능한 플레이어: {[p['player_id'] for p in self.players]}")
                return False

            request_msg = AttackRequestMessage(
                attacker_id=self.player_id,
                target_id=target_player['player_id']
            )

            Protocol.send_message(self.socket, request_msg)
            print(f"[클라이언트] 공격 승인 요청 전송: {self.player_id} -> {target_player['player_id']}")
            return True
        except Exception as e:
            print(f"[클라이언트] 공격 요청 실패: {e}")
            import traceback
            traceback.print_exc()
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