"""
서버 GUI 모듈
tkinter 기반 게임 서버 관리 인터페이스
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import sys
import os
from datetime import datetime

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.protocol import ConnectionManager
from common.constants import DEFAULT_HOST, DEFAULT_PORT
from server.player_manager import PlayerManager
from server.game_manager import GameManager
from server.dummy_generator import DummyGenerator
from common.message_types import Message
import socket


class ServerGUI:
    """서버 GUI 클래스"""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
        self.server_thread = None

        # 매니저 초기화
        self.player_manager = PlayerManager()
        self.game_manager = GameManager(self.player_manager, self.broadcast_message)
        self.dummy_generator = DummyGenerator(self.broadcast_message)

        # 클라이언트 핸들러 스레드
        self.client_threads = []

        # 메인 윈도우
        self.root = tk.Tk()
        self.root.title("네트워크 보안 게임 서버")
        self.root.geometry("900x700")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # UI 구성
        self._create_widgets()

        # 자동 상태 업데이트 시작
        self._start_auto_update()

    def _create_widgets(self):
        """UI 위젯 생성"""

        # 상단: 서버 정보 및 제어
        control_frame = ttk.LabelFrame(self.root, text="서버 제어", padding=10)
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        # 서버 정보
        info_frame = ttk.Frame(control_frame)
        info_frame.pack(fill=tk.X, pady=5)

        ttk.Label(info_frame, text="호스트:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.label_host = ttk.Label(info_frame, text=self.host, font=("Arial", 10, "bold"))
        self.label_host.grid(row=0, column=1, sticky=tk.W, padx=5)

        ttk.Label(info_frame, text="포트:").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.label_port = ttk.Label(info_frame, text=str(self.port), font=("Arial", 10, "bold"))
        self.label_port.grid(row=0, column=3, sticky=tk.W, padx=5)

        ttk.Label(info_frame, text="상태:").grid(row=0, column=4, sticky=tk.W, padx=5)
        self.label_status = ttk.Label(info_frame, text="중지됨", foreground="red", font=("Arial", 10, "bold"))
        self.label_status.grid(row=0, column=5, sticky=tk.W, padx=5)

        # 제어 버튼
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill=tk.X, pady=5)

        self.btn_start_server = ttk.Button(button_frame, text="서버 시작", command=self.start_server, width=15)
        self.btn_start_server.pack(side=tk.LEFT, padx=5)

        self.btn_stop_server = ttk.Button(button_frame, text="서버 중지", command=self.stop_server, state=tk.DISABLED, width=15)
        self.btn_stop_server.pack(side=tk.LEFT, padx=5)

        self.btn_start_game = ttk.Button(button_frame, text="게임 시작", command=self.start_game, state=tk.DISABLED, width=15)
        self.btn_start_game.pack(side=tk.LEFT, padx=5)

        self.btn_stop_game = ttk.Button(button_frame, text="게임 중지", command=self.stop_game, state=tk.DISABLED, width=15)
        self.btn_stop_game.pack(side=tk.LEFT, padx=5)

        # 중간: 게임 상태
        status_frame = ttk.LabelFrame(self.root, text="게임 상태", padding=10)
        status_frame.pack(fill=tk.X, padx=10, pady=5)

        status_info = ttk.Frame(status_frame)
        status_info.pack(fill=tk.X)

        ttk.Label(status_info, text="게임 상태:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.label_game_state = ttk.Label(status_info, text="대기 중", font=("Arial", 10))
        self.label_game_state.grid(row=0, column=1, sticky=tk.W, padx=5)

        ttk.Label(status_info, text="현재 라운드:").grid(row=0, column=2, sticky=tk.W, padx=15)
        self.label_round = ttk.Label(status_info, text="0/5", font=("Arial", 10))
        self.label_round.grid(row=0, column=3, sticky=tk.W, padx=5)

        ttk.Label(status_info, text="플레이어 수:").grid(row=0, column=4, sticky=tk.W, padx=15)
        self.label_player_count = ttk.Label(status_info, text="0", font=("Arial", 10))
        self.label_player_count.grid(row=0, column=5, sticky=tk.W, padx=5)

        # 플레이어 목록
        player_frame = ttk.LabelFrame(self.root, text="플레이어 목록", padding=10)
        player_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Treeview
        columns = ('player_id', 'ip', 'score', 'hp', 'status')
        self.tree_players = ttk.Treeview(player_frame, columns=columns, show='headings', height=8)

        self.tree_players.heading('player_id', text='플레이어 ID')
        self.tree_players.heading('ip', text='IP 주소')
        self.tree_players.heading('score', text='점수')
        self.tree_players.heading('hp', text='HP')
        self.tree_players.heading('status', text='상태')

        self.tree_players.column('player_id', width=150)
        self.tree_players.column('ip', width=150)
        self.tree_players.column('score', width=100)
        self.tree_players.column('hp', width=100)
        self.tree_players.column('status', width=100)

        self.tree_players.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 스크롤바
        scrollbar_players = ttk.Scrollbar(player_frame, orient=tk.VERTICAL, command=self.tree_players.yview)
        scrollbar_players.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_players.configure(yscrollcommand=scrollbar_players.set)

        # 하단: 서버 로그
        log_frame = ttk.LabelFrame(self.root, text="서버 로그", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.text_log = scrolledtext.ScrolledText(log_frame, height=10, state=tk.DISABLED, wrap=tk.WORD)
        self.text_log.pack(fill=tk.BOTH, expand=True)

        # 로그 색상 태그
        self.text_log.tag_config('info', foreground='black')
        self.text_log.tag_config('success', foreground='green')
        self.text_log.tag_config('warning', foreground='orange')
        self.text_log.tag_config('error', foreground='red')

    def start_server(self):
        """서버 시작"""
        if self.running:
            return

        try:
            self.server_socket = ConnectionManager.create_server_socket(self.host, self.port)
            if not self.server_socket:
                messagebox.showerror("오류", "서버 소켓 생성 실패")
                return

            self.running = True
            self.label_status.config(text="실행 중", foreground="green")

            # 버튼 상태 변경
            self.btn_start_server.config(state=tk.DISABLED)
            self.btn_stop_server.config(state=tk.NORMAL)
            self.btn_start_game.config(state=tk.NORMAL)

            self.log(f"서버 시작: {self.host}:{self.port}", "success")

            # 클라이언트 수락 스레드 시작
            self.server_thread = threading.Thread(target=self._accept_clients, daemon=True)
            self.server_thread.start()

        except Exception as e:
            self.log(f"서버 시작 실패: {e}", "error")
            messagebox.showerror("오류", f"서버 시작 실패:\n{e}")

    def stop_server(self):
        """서버 중지"""
        if not self.running:
            return

        try:
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

            self.label_status.config(text="중지됨", foreground="red")

            # 버튼 상태 변경
            self.btn_start_server.config(state=tk.NORMAL)
            self.btn_stop_server.config(state=tk.DISABLED)
            self.btn_start_game.config(state=tk.DISABLED)
            self.btn_stop_game.config(state=tk.DISABLED)

            self.log("서버 중지됨", "warning")

        except Exception as e:
            self.log(f"서버 중지 오류: {e}", "error")

    def start_game(self):
        """게임 시작"""
        if not self.running:
            messagebox.showwarning("경고", "서버가 실행되지 않았습니다.")
            return

        if not self.game_manager.can_start_game():
            messagebox.showwarning("경고", "최소 2명의 플레이어가 필요합니다.")
            return

        if self.game_manager.start_game():
            self.dummy_generator.start()
            self.btn_start_game.config(state=tk.DISABLED)
            self.btn_stop_game.config(state=tk.NORMAL)
            self.log("게임 시작됨", "success")
        else:
            messagebox.showerror("오류", "게임 시작 실패")

    def stop_game(self):
        """게임 중지"""
        self.game_manager.stop_game()
        self.dummy_generator.stop()
        self.btn_start_game.config(state=tk.NORMAL)
        self.btn_stop_game.config(state=tk.DISABLED)
        self.log("게임 중지됨", "warning")

    def _accept_clients(self):
        """클라이언트 연결 수락 (서버 스레드)"""
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                self.log(f"새 연결: {address}", "info")

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
                    self.log(f"클라이언트 수락 오류: {e}", "error")
                break

    def _handle_client(self, client_socket: socket.socket, address: tuple):
        """개별 클라이언트 처리"""
        from common.protocol import Protocol
        from common.constants import MSG_TYPE_CONNECT, MSG_TYPE_ATTACK, MSG_TYPE_DEFENSE
        from common.message_types import InfoMessage, AttackMessage

        player_id = None

        try:
            # 첫 메시지: 연결 메시지 수신
            connect_msg = Protocol.receive_message(client_socket)
            if not connect_msg or connect_msg.type != MSG_TYPE_CONNECT:
                self.log(f"{address} - 잘못된 연결 메시지", "error")
                return

            player_id = connect_msg.data.get('player_id', f"Player_{address[0]}")

            # 플레이어 추가
            player = self.player_manager.add_player(player_id, client_socket, address)
            self.log(f"플레이어 접속: {player_id} ({player.ip})", "success")

            # 환영 메시지 전송
            welcome_msg = InfoMessage(
                info_type="WELCOME",
                message=f"환영합니다, {player_id}!",
                player_id=player_id,
                player_ip=player.ip
            )
            Protocol.send_message(client_socket, welcome_msg)

            # 플레이어 목록 브로드캐스트
            self._broadcast_player_list()

            # 클라이언트 메시지 수신 루프
            while self.running and player.is_connected:
                message = Protocol.receive_message(client_socket)

                if not message:
                    self.log(f"{player_id} 연결 끊김", "warning")
                    break

                # 메시지 처리
                self._process_message(player, message)

        except Exception as e:
            self.log(f"{address} 처리 중 오류: {e}", "error")

        finally:
            # 플레이어 제거
            if player_id:
                self.player_manager.remove_player(player_id)
                self._broadcast_player_list()
                self.log(f"플레이어 종료: {player_id}", "info")

            # 소켓 종료
            try:
                ConnectionManager.close_socket(client_socket)
            except:
                pass

    def _process_message(self, player, message: Message):
        """메시지 처리"""
        from common.constants import MSG_TYPE_ATTACK, MSG_TYPE_DEFENSE
        from common.protocol import Protocol
        from common.message_types import AttackMessage

        msg_type = message.type

        if msg_type == MSG_TYPE_ATTACK:
            to_player_id = message.data.get('to_player')
            target_player = self.player_manager.get_player(to_player_id)

            if not target_player:
                self.log(f"공격 대상 없음: {to_player_id}", "warning")
                return

            # 공격 기록
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
            self.log(f"공격: {player.player_id} -> {to_player_id}", "info")

        elif msg_type == MSG_TYPE_DEFENSE:
            attacker_ips = message.data.get('attacker_ips', [])
            self.game_manager.submit_defense(player.player_id, attacker_ips)
            self.log(f"{player.player_id} 방어 제출: {attacker_ips}", "info")

    def broadcast_message(self, message: Message, target_players=None):
        """메시지 브로드캐스트"""
        from common.protocol import Protocol

        if target_players is None:
            target_players = self.player_manager.get_all_players()

        for player in target_players:
            if player.is_connected:
                try:
                    Protocol.send_message(player.socket, message)
                except Exception as e:
                    self.log(f"{player.player_id}에게 메시지 전송 실패: {e}", "error")

    def _broadcast_player_list(self):
        """플레이어 목록 브로드캐스트"""
        from common.message_types import PlayerListMessage

        players_info = self.player_manager.get_players_info()
        msg = PlayerListMessage(players=players_info)
        self.broadcast_message(msg, None)

    def _start_auto_update(self):
        """자동 상태 업데이트 시작"""
        self._update_status()
        self.root.after(1000, self._start_auto_update)

    def _update_status(self):
        """상태 업데이트"""
        # 게임 상태 업데이트
        self.label_game_state.config(text=self.game_manager.state.value)
        self.label_round.config(text=f"{self.game_manager.current_round}/5")
        self.label_player_count.config(text=str(self.player_manager.get_player_count()))

        # 플레이어 목록 업데이트
        for item in self.tree_players.get_children():
            self.tree_players.delete(item)

        for player in self.player_manager.get_all_players():
            status = "연결됨" if player.is_connected else "연결 끊김"
            self.tree_players.insert('', tk.END, values=(
                player.player_id,
                player.ip,
                player.score,
                player.hp,
                status
            ))

    def log(self, message: str, level: str = "info"):
        """로그 출력"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"

        self.text_log.config(state=tk.NORMAL)
        self.text_log.insert(tk.END, log_message, level)
        self.text_log.see(tk.END)
        self.text_log.config(state=tk.DISABLED)

    def on_close(self):
        """창 닫기 이벤트"""
        if messagebox.askokcancel("종료", "서버를 종료하시겠습니까?"):
            if self.running:
                self.stop_server()
            self.root.destroy()

    def run(self):
        """GUI 실행"""
        self.log("서버 GUI 시작", "success")
        self.root.mainloop()


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="네트워크 보안 게임 서버 (GUI)")
    parser.add_argument('--host', default=DEFAULT_HOST, help=f"서버 호스트 (기본값: {DEFAULT_HOST})")
    parser.add_argument('--port', type=int, default=DEFAULT_PORT, help=f"서버 포트 (기본값: {DEFAULT_PORT})")

    args = parser.parse_args()

    gui = ServerGUI(host=args.host, port=args.port)
    gui.run()


if __name__ == "__main__":
    main()
