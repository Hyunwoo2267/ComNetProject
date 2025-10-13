"""
GUI 클라이언트 모듈
tkinter 기반 게임 GUI 인터페이스
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import sys
import os
from datetime import datetime

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client.client import GameClient
from common.message_types import Message


class GameGUI:
    """게임 GUI 클래스"""

    def __init__(self, player_id: str, host: str = 'localhost', port: int = 9999):
        self.client = GameClient(player_id, host, port)

        # 메인 윈도우
        self.root = tk.Tk()
        self.root.title(f"네트워크 보안 게임 - {player_id}")
        self.root.geometry("800x600")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # UI 구성
        self._create_widgets()

        # 클라이언트 콜백 설정
        self.client.add_message_callback(self.handle_message)

    def _create_widgets(self):
        """UI 위젯 생성"""

        # 상단: 플레이어 정보
        info_frame = ttk.LabelFrame(self.root, text="내 정보", padding=10)
        info_frame.pack(fill=tk.X, padx=10, pady=5)

        self.label_player_id = ttk.Label(info_frame, text=f"플레이어: {self.client.player_id}", font=("Arial", 10, "bold"))
        self.label_player_id.grid(row=0, column=0, sticky=tk.W, padx=5)

        self.label_ip = ttk.Label(info_frame, text="IP: 연결 전")
        self.label_ip.grid(row=0, column=1, sticky=tk.W, padx=5)

        self.label_score = ttk.Label(info_frame, text="점수: 0")
        self.label_score.grid(row=0, column=2, sticky=tk.W, padx=5)

        self.label_hp = ttk.Label(info_frame, text="HP: 100", foreground="green")
        self.label_hp.grid(row=0, column=3, sticky=tk.W, padx=5)

        self.label_round = ttk.Label(info_frame, text="라운드: 0/5")
        self.label_round.grid(row=0, column=4, sticky=tk.W, padx=5)

        # 중간 상단: 게임 상태
        state_frame = ttk.LabelFrame(self.root, text="게임 상태", padding=10)
        state_frame.pack(fill=tk.X, padx=10, pady=5)

        self.label_game_state = ttk.Label(state_frame, text="대기 중...", font=("Arial", 12))
        self.label_game_state.pack()

        # 중간: 플레이어 목록 및 공격
        player_frame = ttk.LabelFrame(self.root, text="플레이어 목록", padding=10)
        player_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 플레이어 리스트
        columns = ('player_id', 'ip', 'score', 'hp')
        self.tree_players = ttk.Treeview(player_frame, columns=columns, show='headings', height=6)

        self.tree_players.heading('player_id', text='플레이어 ID')
        self.tree_players.heading('ip', text='IP 주소')
        self.tree_players.heading('score', text='점수')
        self.tree_players.heading('hp', text='HP')

        self.tree_players.column('player_id', width=150)
        self.tree_players.column('ip', width=150)
        self.tree_players.column('score', width=80)
        self.tree_players.column('hp', width=80)

        self.tree_players.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 스크롤바
        scrollbar = ttk.Scrollbar(player_frame, orient=tk.VERTICAL, command=self.tree_players.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_players.configure(yscrollcommand=scrollbar.set)

        # 공격 버튼
        attack_btn = ttk.Button(player_frame, text="선택한 플레이어 공격", command=self.attack_selected_player)
        attack_btn.pack(pady=5)

        # 방어 입력
        defense_frame = ttk.LabelFrame(self.root, text="방어 입력", padding=10)
        defense_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(defense_frame, text="공격자 IP (쉼표로 구분):").pack(side=tk.LEFT, padx=5)

        self.entry_defense = ttk.Entry(defense_frame, width=40)
        self.entry_defense.pack(side=tk.LEFT, padx=5)

        defense_btn = ttk.Button(defense_frame, text="방어 제출", command=self.submit_defense)
        defense_btn.pack(side=tk.LEFT, padx=5)

        # 하단: 로그
        log_frame = ttk.LabelFrame(self.root, text="게임 로그", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.text_log = scrolledtext.ScrolledText(log_frame, height=8, state=tk.DISABLED, wrap=tk.WORD)
        self.text_log.pack(fill=tk.BOTH, expand=True)

    def run(self):
        """GUI 실행"""
        # 서버 연결
        self.log("서버에 연결 중...")

        if self.client.connect():
            self.log(f"서버 연결 성공: {self.client.my_ip}")
            self.update_my_info()
        else:
            messagebox.showerror("연결 실패", "서버에 연결할 수 없습니다.")
            self.root.destroy()
            return

        # GUI 시작
        self.root.mainloop()

    def handle_message(self, message: Message):
        """
        서버 메시지 처리 (클라이언트 콜백)

        Args:
            message: 수신한 메시지
        """
        msg_type = message.type

        # UI는 메인 스레드에서만 업데이트 가능
        self.root.after(0, self._update_ui, message)

    def _update_ui(self, message: Message):
        """UI 업데이트 (메인 스레드)"""
        msg_type = message.type

        if msg_type == "PLAYER_LIST":
            self.update_player_list()

        elif msg_type in ["GAME_START", "ROUND_START", "PLAYING", "DEFENSE_PHASE", "ROUND_END", "GAME_END"]:
            self.update_game_state()
            msg = message.data.get('message', '')
            if msg:
                self.log(f"[게임] {msg}")

        elif msg_type == "SCORE":
            self.update_my_info()
            reason = message.data.get('reason', '')
            if reason:
                self.log(f"[점수] {reason}")

        elif msg_type == "INFO":
            info_msg = message.data.get('message', '')
            self.log(f"[정보] {info_msg}")

        elif msg_type == "DUMMY":
            # 더미 패킷은 로그에 표시하지 않음 (Wireshark용)
            pass

        elif msg_type == "ATTACK":
            # 공격 받음 알림
            from_player = message.data.get('from_player', '?')
            self.log(f"[경고] {from_player}에게 공격 받음! Wireshark를 확인하세요!")

        elif msg_type == "ERROR":
            error_msg = message.data.get('error_message', '알 수 없는 오류')
            self.log(f"[오류] {error_msg}")

    def update_my_info(self):
        """내 정보 업데이트"""
        info = self.client.get_my_info()
        self.label_ip.config(text=f"IP: {info['ip']}")
        self.label_score.config(text=f"점수: {info['score']}")

        hp = info['hp']
        hp_color = "green" if hp > 60 else "orange" if hp > 30 else "red"
        self.label_hp.config(text=f"HP: {hp}", foreground=hp_color)

        self.label_round.config(text=f"라운드: {info['round']}/5")

    def update_player_list(self):
        """플레이어 목록 업데이트"""
        # 기존 항목 삭제
        for item in self.tree_players.get_children():
            self.tree_players.delete(item)

        # 새 항목 추가
        players = self.client.get_players()
        for player in players:
            self.tree_players.insert('', tk.END, values=(
                player['player_id'],
                player['ip'],
                player['score'],
                player['hp']
            ))

    def update_game_state(self):
        """게임 상태 업데이트"""
        state = self.client.get_game_state()
        state_type = state.get('type', 'WAITING')

        state_text = {
            'WAITING': '대기 중...',
            'GAME_START': '게임 시작!',
            'ROUND_START': f"라운드 {state.get('round_num', 0)} 준비 중...",
            'PLAYING': f"게임 진행 중! (라운드 {state.get('round_num', 0)})",
            'DEFENSE_PHASE': '방어 입력 단계!',
            'ROUND_END': f"라운드 {state.get('round_num', 0)} 종료",
            'GAME_END': '게임 종료!'
        }.get(state_type, '알 수 없는 상태')

        self.label_game_state.config(text=state_text)
        self.update_my_info()

    def attack_selected_player(self):
        """선택한 플레이어 공격"""
        selection = self.tree_players.selection()
        if not selection:
            messagebox.showwarning("경고", "공격할 플레이어를 선택하세요.")
            return

        item = self.tree_players.item(selection[0])
        target_player_id = item['values'][0]

        # 자신은 공격 불가
        if target_player_id == self.client.player_id:
            messagebox.showwarning("경고", "자신을 공격할 수 없습니다.")
            return

        # 공격 전송
        if self.client.send_attack(target_player_id):
            self.log(f"[공격] {target_player_id}를 공격했습니다!")
        else:
            messagebox.showerror("오류", "공격 전송 실패")

    def submit_defense(self):
        """방어 제출"""
        ips_str = self.entry_defense.get().strip()

        if not ips_str:
            messagebox.showwarning("경고", "공격자 IP를 입력하세요.")
            return

        # 쉼표로 구분된 IP 파싱
        ips = [ip.strip() for ip in ips_str.split(',') if ip.strip()]

        if not ips:
            messagebox.showwarning("경고", "유효한 IP를 입력하세요.")
            return

        # 방어 제출
        if self.client.submit_defense(ips):
            self.log(f"[방어] 제출 완료: {ips}")
            self.entry_defense.delete(0, tk.END)
        else:
            messagebox.showerror("오류", "방어 제출 실패")

    def log(self, message: str):
        """로그 출력"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"

        self.text_log.config(state=tk.NORMAL)
        self.text_log.insert(tk.END, log_message)
        self.text_log.see(tk.END)
        self.text_log.config(state=tk.DISABLED)

    def on_close(self):
        """창 닫기 이벤트"""
        if messagebox.askokcancel("종료", "게임을 종료하시겠습니까?"):
            self.client.disconnect()
            self.root.destroy()


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="네트워크 보안 게임 클라이언트 (GUI)")
    parser.add_argument('--id', required=True, help="플레이어 ID")
    parser.add_argument('--host', default='localhost', help="서버 호스트")
    parser.add_argument('--port', type=int, default=9999, help="서버 포트")

    args = parser.parse_args()

    gui = GameGUI(player_id=args.id, host=args.host, port=args.port)
    gui.run()


if __name__ == "__main__":
    main()
