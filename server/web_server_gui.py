"""
Flask 기반 웹 서버 GUI
브라우저에서 서버 제어 및 모니터링 가능
"""

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import os
import sys
import threading
import time
import socket as sock

# 프로젝트 루트 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.protocol import Protocol, ConnectionManager
from common.constants import (
    DEFAULT_HOST, DEFAULT_PORT,
    MSG_TYPE_ATTACK, MSG_TYPE_DEFENSE, MSG_TYPE_CONNECT,
    MSG_TYPE_ATTACK_REQUEST, MSG_TYPE_ATTACK_CONFIRM
)
from common.message_types import (
    Message, AttackMessage, InfoMessage, PlayerListMessage,
    decode_payload
)
from server.player_manager import PlayerManager
from server.game_manager import GameManager
from server.dummy_generator import DummyGenerator
from server.noise_generator import NoiseGenerator
from server.decoy_generator import DecoyGenerator

app = Flask(__name__)
app.config['SECRET_KEY'] = 'network_game_server_secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# 전역 서버 인스턴스
game_server = None


class WebGameServer:
    """웹 GUI 기반 게임 서버"""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False

        # 매니저 초기화
        self.player_manager = PlayerManager()
        self.dummy_generator = DummyGenerator(self.broadcast_message)
        self.noise_generator = NoiseGenerator(self.player_manager, self._send_to_player)
        self.decoy_generator = DecoyGenerator(self.player_manager, self._send_to_player)
        self.game_manager = GameManager(
            self.player_manager,
            self.broadcast_message,
            self.dummy_generator,
            self.noise_generator,
            self.decoy_generator,
            self._broadcast_player_list  # HP 업데이트 시 플레이어 목록 브로드캐스트
        )

        # 클라이언트 핸들러 스레드
        self.client_threads = []

        # 패킷 로그 (디버깅용)
        self.packet_log = []
        self.max_packet_log = 100

    def start(self):
        """서버 시작"""
        if self.running:
            return False, "서버가 이미 실행 중입니다"

        try:
            self.server_socket = ConnectionManager.create_server_socket(self.host, self.port)
            if not self.server_socket:
                return False, "서버 소켓 생성 실패"

            self.running = True
            self.log_to_gui(f"서버 시작: {self.host}:{self.port}", "success")

            # 클라이언트 연결 대기 스레드
            accept_thread = threading.Thread(target=self._accept_clients, daemon=True)
            accept_thread.start()

            return True, "서버 시작됨"

        except Exception as e:
            return False, f"서버 시작 실패: {e}"

    def stop(self):
        """서버 중지"""
        if not self.running:
            return False, "서버가 실행되지 않았습니다"

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

        self.log_to_gui("서버 중지됨", "warning")
        return True, "서버 중지됨"

    def start_game(self):
        """게임 시작"""
        if not self.running:
            return False, "서버가 실행되지 않았습니다"

        if not self.game_manager.can_start_game():
            return False, f"최소 2명의 플레이어가 필요합니다"

        if self.game_manager.start_game():
            self.dummy_generator.start()
            self.log_to_gui("게임 시작됨", "success")
            return True, "게임 시작됨"
        else:
            return False, "게임 시작 실패"

    def stop_game(self):
        """게임 중지"""
        self.game_manager.stop_game()
        self.dummy_generator.stop()
        self.log_to_gui("게임 중지됨", "warning")
        return True, "게임 중지됨"

    def _accept_clients(self):
        """클라이언트 연결 수락"""
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                self.log_to_gui(f"새 연결: {address}", "info")

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
                    self.log_to_gui(f"클라이언트 수락 오류: {e}", "error")
                break

    def _handle_client(self, client_socket: sock.socket, address: tuple):
        """개별 클라이언트 처리"""
        player_id = None

        try:
            # 첫 메시지: 연결 메시지 수신
            connect_msg = Protocol.receive_message(client_socket)
            if not connect_msg or connect_msg.type != MSG_TYPE_CONNECT:
                self.log_to_gui(f"{address} - 잘못된 연결 메시지", "error")
                return

            player_id = connect_msg.data.get('player_id', f"Player_{address[0]}")

            # 플레이어 추가
            player = self.player_manager.add_player(player_id, client_socket, address)

            # 연결 확인 메시지 전송 (v2.0: player_index 추가)
            player_index = self.player_manager.get_player_index(player_id)
            welcome_msg = InfoMessage(
                info_type="WELCOME",
                message=f"환영합니다, {player_id}!",
                player_id=player_id,
                player_ip=player.ip,
                player_index=player_index  # v2.0: P2P 포트 계산용
            )
            Protocol.send_message(client_socket, welcome_msg)

            # 현재 플레이어 목록 브로드캐스트
            self._broadcast_player_list()
            self.log_to_gui(f"플레이어 접속: {player_id} ({player.ip})", "success")

            # 클라이언트 메시지 수신 루프
            while self.running and player.is_connected:
                message = Protocol.receive_message(client_socket)

                if not message:
                    self.log_to_gui(f"{player_id} 연결 끊김", "warning")
                    break

                # 패킷 로깅 (디버깅용)
                self.log_packet(player_id, message)

                # 메시지 처리
                self._process_message(player, message)

        except Exception as e:
            self.log_to_gui(f"{address} 처리 중 오류: {e}", "error")

        finally:
            # 플레이어 제거
            if player_id:
                self.player_manager.remove_player(player_id)
                self._broadcast_player_list()
                self.log_to_gui(f"플레이어 종료: {player_id}", "info")

            # 소켓 종료
            try:
                ConnectionManager.close_socket(client_socket)
            except:
                pass

    def _process_message(self, player, message: Message):
        """메시지 처리"""
        msg_type = message.type
        print(f"[서버] 메시지 수신: type={msg_type}, from={player.player_id}, data={message.data}")

        if msg_type == MSG_TYPE_ATTACK_REQUEST:
            print(f"[서버] 공격 승인 요청 처리 시작")
            self._handle_attack_request(player, message)

        elif msg_type == MSG_TYPE_ATTACK_CONFIRM:
            print(f"[서버] 공격 확인 메시지 처리")
            self._handle_attack_confirm(player, message)

        elif msg_type == MSG_TYPE_ATTACK:
            self._handle_attack(player, message)

        elif msg_type == MSG_TYPE_DEFENSE:
            self._handle_defense(player, message)

        else:
            print(f"[서버] 알 수 없는 메시지 타입: {msg_type}")

    def _handle_attack_request(self, player, message: Message):
        """공격 승인 요청 처리 (v2.0)"""
        try:
            target_id = message.data.get('target_id')
            print(f"[서버] 공격 승인 요청: {player.player_id} -> {target_id}")

            if not target_id:
                print(f"[서버] 타겟 ID 없음: message.data={message.data}")
                error_msg = InfoMessage(info_type="ERROR", message="타겟 ID가 없습니다")
                Protocol.send_message(player.socket, error_msg)
                return

            print(f"[서버] 게임 매니저에 공격 승인 요청 전달")
            # 게임 매니저에서 공격 승인 처리
            approved, msg, attack_id = self.game_manager.request_attack_approval(
                player.player_id,
                target_id
            )
            print(f"[서버] 게임 매니저 응답: approved={approved}, msg={msg}, attack_id={attack_id}")

            if approved:
                self.log_to_gui(f"공격 승인: {player.player_id} → {target_id} ({attack_id})", "info")
            else:
                error_msg = InfoMessage(info_type="ATTACK_DENIED", message=msg)
                Protocol.send_message(player.socket, error_msg)
                self.log_to_gui(f"공격 거부: {player.player_id} → {target_id} - {msg}", "warning")

        except Exception as e:
            print(f"[서버] 공격 승인 요청 처리 중 예외 발생: {e}")
            import traceback
            traceback.print_exc()

    def _handle_attack_confirm(self, player, message: Message):
        """공격 확인 메시지 처리 (v2.0)"""
        attack_id = message.data.get('attack_id')
        confirm_type = message.data.get('confirm_type')

        if not attack_id or not confirm_type:
            return

        if confirm_type == "SENT":
            self.game_manager.confirm_attack_sent(attack_id)
            self.log_to_gui(f"공격 전송 확인: {attack_id}", "info")
        elif confirm_type == "RECEIVED":
            self.game_manager.confirm_attack_received(attack_id)
            self.log_to_gui(f"공격 수신 확인: {attack_id}", "info")

    def _handle_attack(self, player, message: Message):
        """공격 메시지 처리 (기존 호환성)"""
        to_player_id = message.data.get('to_player')
        target_player = self.player_manager.get_player(to_player_id)

        if not target_player:
            self.log_to_gui(f"공격 대상 없음: {to_player_id}", "warning")
            error_msg = InfoMessage(
                info_type="ERROR",
                message=f"공격 대상을 찾을 수 없습니다: {to_player_id}"
            )
            Protocol.send_message(player.socket, error_msg)
            return

        # 공격 가능 여부 확인
        can_attack, msg = self.game_manager.can_attack(player.player_id)
        if not can_attack:
            self.log_to_gui(f"공격 제한: {player.player_id} - {msg}", "warning")
            error_msg = InfoMessage(info_type="ATTACK_LIMIT", message=msg)
            Protocol.send_message(player.socket, error_msg)
            return

        # 공격 기록
        self.game_manager.record_attack(player.player_id, to_player_id, player.ip)
        self.player_manager.record_attack(to_player_id, player.ip)

        # 공격 메시지를 대상에게 전송
        attack_msg = AttackMessage(
            from_ip=player.ip,
            to_ip=target_player.ip,
            from_player=player.player_id,
            to_player=target_player.player_id,
            payload=message.data.get('payload', f"ATTACK_TARGET_{to_player_id}")
        )

        Protocol.send_message(target_player.socket, attack_msg)

        # 공격 성공 알림
        success_msg = InfoMessage(
            info_type="ATTACK_SUCCESS",
            message=f"{to_player_id}에게 공격 성공! {msg}"
        )
        Protocol.send_message(player.socket, success_msg)

        self.log_to_gui(f"공격: {player.player_id} → {to_player_id}", "attack")

    def _handle_defense(self, player, message: Message):
        """방어 메시지 처리"""
        attacker_ips = message.data.get('attacker_ips', [])
        self.game_manager.submit_defense(player.player_id, attacker_ips)
        self.log_to_gui(f"{player.player_id} 방어 제출: {attacker_ips}", "info")

    def broadcast_message(self, message: Message, target_players=None):
        """메시지 브로드캐스트"""
        if target_players is None:
            target_players = self.player_manager.get_all_players()

        # 더미 패킷 로깅 (디버그용)
        if message.type == "DUMMY":
            print(f"[DummyGenerator] 더미 패킷 브로드캐스트: {len(target_players)}명에게 전송")

        for player in target_players:
            if player.is_connected:
                try:
                    Protocol.send_message(player.socket, message)
                except Exception as e:
                    self.log_to_gui(f"{player.player_id}에게 메시지 전송 실패: {e}", "error")

    def _send_to_player(self, player, message: Message):
        """특정 플레이어에게 메시지 전송"""
        if player.is_connected:
            try:
                Protocol.send_message(player.socket, message)
            except Exception as e:
                self.log_to_gui(f"{player.player_id}에게 메시지 전송 실패: {e}", "error")

    def _broadcast_player_list(self):
        """플레이어 목록 브로드캐스트"""
        players_info = self.player_manager.get_players_info()
        msg = PlayerListMessage(players=players_info)
        self.broadcast_message(msg, None)

        # 웹 GUI에도 업데이트
        socketio.emit('player_list_update', {'players': players_info})

    def log_to_gui(self, message: str, level: str = "info"):
        """웹 GUI에 로그 전송"""
        log_entry = {
            'timestamp': time.strftime("%H:%M:%S"),
            'message': message,
            'level': level
        }
        socketio.emit('server_log', log_entry)

    def log_packet(self, player_id: str, message: Message):
        """패킷 로그 (디버깅용)"""
        packet_data = {
            'timestamp': time.strftime("%H:%M:%S"),
            'player_id': player_id,
            'type': message.type,
            'data': message.data,
            'decoded_payload': None
        }

        # 페이로드 디코딩 시도
        if 'payload' in message.data:
            try:
                packet_data['decoded_payload'] = decode_payload(message.data['payload'])
            except:
                packet_data['decoded_payload'] = message.data['payload']

        self.packet_log.append(packet_data)

        # 로그 크기 제한
        if len(self.packet_log) > self.max_packet_log:
            self.packet_log.pop(0)

        # 웹 GUI에 전송
        socketio.emit('packet_log', packet_data)

    def get_status(self):
        """서버 상태 반환"""
        return {
            'running': self.running,
            'host': self.host,
            'port': self.port,
            'game_state': self.game_manager.state.value,
            'current_round': self.game_manager.current_round,
            'total_rounds': 5,
            'player_count': self.player_manager.get_player_count(),
            'players': self.player_manager.get_players_info()
        }


# Flask 라우트
@app.route('/')
def index():
    """메인 페이지"""
    return render_template('server_control.html')


# SocketIO 이벤트
@socketio.on('connect')
def handle_connect():
    """클라이언트 연결"""
    print("[웹GUI] 클라이언트 연결됨")
    if game_server:
        emit('status_update', game_server.get_status())


@socketio.on('start_server')
def handle_start_server():
    """서버 시작"""
    if game_server:
        success, message = game_server.start()
        emit('command_result', {'success': success, 'message': message})
        emit('status_update', game_server.get_status(), broadcast=True)


@socketio.on('stop_server')
def handle_stop_server():
    """서버 중지"""
    if game_server:
        success, message = game_server.stop()
        emit('command_result', {'success': success, 'message': message})
        emit('status_update', game_server.get_status(), broadcast=True)


@socketio.on('start_game')
def handle_start_game():
    """게임 시작"""
    if game_server:
        success, message = game_server.start_game()
        emit('command_result', {'success': success, 'message': message})
        emit('status_update', game_server.get_status(), broadcast=True)


@socketio.on('stop_game')
def handle_stop_game():
    """게임 중지"""
    if game_server:
        success, message = game_server.stop_game()
        emit('command_result', {'success': success, 'message': message})
        emit('status_update', game_server.get_status(), broadcast=True)


@socketio.on('get_status')
def handle_get_status():
    """상태 조회"""
    if game_server:
        emit('status_update', game_server.get_status())


@socketio.on('get_packet_log')
def handle_get_packet_log():
    """패킷 로그 조회"""
    if game_server:
        emit('packet_log_history', {'packets': game_server.packet_log})


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description='웹 기반 게임 서버 GUI')
    parser.add_argument('--game-host', default='0.0.0.0', help='게임 서버 호스트')
    parser.add_argument('--game-port', type=int, default=DEFAULT_PORT, help='게임 서버 포트')
    parser.add_argument('--web-host', default='0.0.0.0', help='웹 GUI 호스트')
    parser.add_argument('--web-port', type=int, default=8000, help='웹 GUI 포트')

    args = parser.parse_args()

    global game_server
    game_server = WebGameServer(host=args.game_host, port=args.game_port)

    print(f"[웹GUI] 서버 GUI 시작: http://{args.web_host}:{args.web_port}")
    try:
        socketio.run(app, host=args.web_host, port=args.web_port, debug=False, allow_unsafe_werkzeug=True)
    except TypeError:
        # Python 3.9 이하 버전 호환성
        socketio.run(app, host=args.web_host, port=args.web_port, debug=False)


if __name__ == '__main__':
    main()
