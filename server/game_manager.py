"""
게임 매니저 모듈
게임 로직, 라운드 관리, 점수 계산 담당
"""

import threading
import time
from typing import Dict, List, Optional
from enum import Enum

from common.constants import (
    STATE_WAITING, STATE_PREPARATION, STATE_PLAYING, STATE_DEFENSE,
    STATE_ROUND_END, STATE_GAME_END, MIN_PLAYERS, TOTAL_ROUNDS,
    ROUND_TIME, DEFENSE_INPUT_TIME, PREPARATION_TIME,
    SCORE_CORRECT_DEFENSE, SCORE_WRONG_DEFENSE, SCORE_MISSED_ATTACK,
    SCORE_SUCCESSFUL_ATTACK
)
from common.message_types import GameStateMessage, ScoreMessage, InfoMessage


class GameState(Enum):
    """게임 상태"""
    WAITING = STATE_WAITING
    PREPARATION = STATE_PREPARATION
    PLAYING = STATE_PLAYING
    DEFENSE = STATE_DEFENSE
    ROUND_END = STATE_ROUND_END
    GAME_END = STATE_GAME_END


class GameManager:
    """게임 매니저 클래스"""

    def __init__(self, player_manager, broadcast_callback):
        """
        Args:
            player_manager: PlayerManager 인스턴스
            broadcast_callback: 브로드캐스트 메시지 전송 콜백
        """
        self.player_manager = player_manager
        self.broadcast_callback = broadcast_callback

        self.state = GameState.WAITING
        self.current_round = 0
        self.round_start_time = 0
        self.defense_submissions: Dict[str, List[str]] = {}  # {player_id: [attacker_ips]}

        self.game_thread = None
        self.running = False
        self.lock = threading.Lock()

    def can_start_game(self) -> bool:
        """게임 시작 가능 여부 확인"""
        return self.player_manager.get_player_count() >= MIN_PLAYERS

    def start_game(self):
        """게임 시작"""
        if not self.can_start_game():
            print(f"[GameManager] 게임 시작 불가: 최소 {MIN_PLAYERS}명 필요")
            return False

        if self.running:
            print("[GameManager] 게임이 이미 실행 중")
            return False

        self.running = True
        self.current_round = 0
        self.state = GameState.PREPARATION

        self.game_thread = threading.Thread(target=self._game_loop, daemon=True)
        self.game_thread.start()
        print("[GameManager] 게임 시작")
        return True

    def stop_game(self):
        """게임 중지"""
        self.running = False
        self.state = GameState.GAME_END
        if self.game_thread:
            self.game_thread.join(timeout=5)
        print("[GameManager] 게임 종료")

    def _game_loop(self):
        """게임 메인 루프"""
        try:
            # 게임 시작 알림
            self._broadcast_game_start()

            # 라운드 진행
            for round_num in range(1, TOTAL_ROUNDS + 1):
                if not self.running:
                    break

                self.current_round = round_num
                self._run_round(round_num)

            # 게임 종료
            self._end_game()

        except Exception as e:
            print(f"[GameManager] 게임 루프 오류: {e}")
            self.stop_game()

    def _run_round(self, round_num: int):
        """
        라운드 실행

        Args:
            round_num: 라운드 번호
        """
        print(f"[GameManager] 라운드 {round_num} 시작")

        # 라운드 데이터 초기화
        self.player_manager.reset_all_round_data()
        self.defense_submissions.clear()

        # 준비 단계
        self._preparation_phase(round_num)
        if not self.running:
            return

        # 게임 진행 단계
        self._playing_phase(round_num)
        if not self.running:
            return

        # 방어 입력 단계
        self._defense_phase(round_num)
        if not self.running:
            return

        # 라운드 종료 및 점수 계산
        self._round_end_phase(round_num)

    def _preparation_phase(self, round_num: int):
        """준비 단계"""
        self.state = GameState.PREPARATION

        message = GameStateMessage(
            state="ROUND_START",
            round_num=round_num,
            time_remaining=PREPARATION_TIME,
            total_rounds=TOTAL_ROUNDS,
            message=f"라운드 {round_num} 준비 중..."
        )
        self.broadcast_callback(message, None)

        # 준비 시간 대기
        time.sleep(PREPARATION_TIME)

    def _playing_phase(self, round_num: int):
        """게임 진행 단계"""
        self.state = GameState.PLAYING
        self.round_start_time = time.time()

        message = GameStateMessage(
            state="PLAYING",
            round_num=round_num,
            time_remaining=ROUND_TIME,
            message="게임 진행 중! 공격하고 Wireshark로 방어하세요!"
        )
        self.broadcast_callback(message, None)

        # 라운드 시간 동안 대기 (실시간 타이머 업데이트)
        elapsed = 0
        while elapsed < ROUND_TIME and self.running:
            time.sleep(1)
            elapsed = int(time.time() - self.round_start_time)

            # 10초마다 시간 알림
            remaining = ROUND_TIME - elapsed
            if remaining % 10 == 0 and remaining > 0:
                info = InfoMessage(
                    info_type="TIME_UPDATE",
                    message=f"남은 시간: {remaining}초",
                    time_remaining=remaining
                )
                self.broadcast_callback(info, None)

    def _defense_phase(self, round_num: int):
        """방어 입력 단계"""
        self.state = GameState.DEFENSE

        message = GameStateMessage(
            state="DEFENSE_PHASE",
            round_num=round_num,
            time_remaining=DEFENSE_INPUT_TIME,
            message="방어 단계! 공격자 IP를 입력하세요!"
        )
        self.broadcast_callback(message, None)

        # 방어 입력 시간 대기
        time.sleep(DEFENSE_INPUT_TIME)

    def _round_end_phase(self, round_num: int):
        """라운드 종료 단계"""
        self.state = GameState.ROUND_END

        # 점수 계산
        results = self._calculate_scores()

        # 결과 전송
        for player_id, result in results.items():
            player = self.player_manager.get_player(player_id)
            if player:
                score_msg = ScoreMessage(
                    player_id=player_id,
                    score=player.score,
                    hp=player.hp,
                    correct=result['correct'],
                    reason=result['reason']
                )
                self.broadcast_callback(score_msg, [player])

        # 라운드 결과 요약
        players_info = self.player_manager.get_players_info()
        summary = GameStateMessage(
            state="ROUND_END",
            round_num=round_num,
            message=f"라운드 {round_num} 종료",
            players=players_info
        )
        self.broadcast_callback(summary, None)

        # 다음 라운드 전 대기
        time.sleep(5)

    def _calculate_scores(self) -> Dict[str, dict]:
        """
        점수 계산

        Returns:
            {player_id: {'correct': bool, 'reason': str}}
        """
        results = {}
        players = self.player_manager.get_all_players()

        for player in players:
            # 실제로 받은 공격
            actual_attacks = set(player.attacks_received)

            # 플레이어가 제출한 방어 답변
            submitted = set(self.defense_submissions.get(player.player_id, []))

            # 정답 계산
            correct_defenses = actual_attacks & submitted  # 교집합
            wrong_defenses = submitted - actual_attacks  # 오답
            missed_attacks = actual_attacks - submitted  # 놓친 공격

            # 점수 업데이트
            score_change = 0
            hp_change = 0

            score_change += len(correct_defenses) * SCORE_CORRECT_DEFENSE
            score_change += len(wrong_defenses) * SCORE_WRONG_DEFENSE
            hp_change += len(missed_attacks) * SCORE_MISSED_ATTACK

            self.player_manager.update_score(player.player_id, score_change)
            self.player_manager.update_hp(player.player_id, hp_change)

            # 공격 성공 보너스 (다른 플레이어가 방어 못한 경우)
            for other_player in players:
                if other_player.player_id == player.player_id:
                    continue

                # 내가 공격한 플레이어가 방어에 실패했는지 확인
                if player.ip in other_player.attacks_received:
                    other_submitted = set(self.defense_submissions.get(other_player.player_id, []))
                    if player.ip not in other_submitted:
                        # 공격 성공
                        self.player_manager.update_score(player.player_id, SCORE_SUCCESSFUL_ATTACK)
                        score_change += SCORE_SUCCESSFUL_ATTACK

            # 결과 메시지 생성
            reason_parts = []
            if correct_defenses:
                reason_parts.append(f"정확한 방어: {len(correct_defenses)}개 (+{len(correct_defenses) * SCORE_CORRECT_DEFENSE}점)")
            if wrong_defenses:
                reason_parts.append(f"오답: {len(wrong_defenses)}개 ({len(wrong_defenses) * SCORE_WRONG_DEFENSE}점)")
            if missed_attacks:
                reason_parts.append(f"놓친 공격: {len(missed_attacks)}개 ({len(missed_attacks) * SCORE_MISSED_ATTACK} HP)")

            reason = ", ".join(reason_parts) if reason_parts else "공격 없음"

            results[player.player_id] = {
                'correct': len(wrong_defenses) == 0 and len(missed_attacks) == 0,
                'reason': reason
            }

        return results

    def submit_defense(self, player_id: str, attacker_ips: List[str]):
        """
        방어 답안 제출

        Args:
            player_id: 플레이어 ID
            attacker_ips: 공격자 IP 리스트
        """
        with self.lock:
            self.defense_submissions[player_id] = attacker_ips
            print(f"[GameManager] {player_id} 방어 제출: {attacker_ips}")

    def _broadcast_game_start(self):
        """게임 시작 알림"""
        players_info = self.player_manager.get_players_info()
        message = GameStateMessage(
            state="GAME_START",
            round_num=0,
            total_rounds=TOTAL_ROUNDS,
            message=f"게임 시작! 총 {TOTAL_ROUNDS} 라운드",
            players=players_info
        )
        self.broadcast_callback(message, None)
        time.sleep(3)

    def _end_game(self):
        """게임 종료"""
        self.state = GameState.GAME_END
        players = self.player_manager.get_all_players()

        # 최종 순위 계산
        sorted_players = sorted(players, key=lambda p: (p.score, p.hp), reverse=True)
        winner = sorted_players[0] if sorted_players else None

        rankings = []
        for i, player in enumerate(sorted_players, 1):
            rankings.append({
                'rank': i,
                'player_id': player.player_id,
                'score': player.score,
                'hp': player.hp
            })

        message = GameStateMessage(
            state="GAME_END",
            message=f"게임 종료! 우승: {winner.player_id if winner else 'N/A'}",
            rankings=rankings,
            winner=winner.player_id if winner else None
        )
        self.broadcast_callback(message, None)
        print(f"[GameManager] 게임 종료 - 우승자: {winner.player_id if winner else 'N/A'}")

    def get_current_state(self) -> dict:
        """현재 게임 상태 반환"""
        with self.lock:
            return {
                'state': self.state.value,
                'current_round': self.current_round,
                'total_rounds': TOTAL_ROUNDS,
                'players': self.player_manager.get_players_info()
            }
