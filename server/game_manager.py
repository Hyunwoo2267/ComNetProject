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
    DIFFICULTY_BY_ROUND,
    SCORE_CORRECT_DEFENSE_NORMAL, SCORE_WRONG_DEFENSE_NORMAL, SCORE_MISSED_ATTACK_NORMAL,
    SCORE_CORRECT_DEFENSE_FINAL, SCORE_WRONG_DEFENSE_FINAL, SCORE_MISSED_ATTACK_FINAL,
    ATTACK_APPROVAL_TIMEOUT, PLAYER_ATTACK_PORT_BASE,
    HP_DAMAGE_PER_ATTACK
)
from common.message_types import (
    GameStateMessage, ScoreMessage, InfoMessage,
    AttackApprovedMessage, IncomingAttackWarningMessage
)


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

    def __init__(self, player_manager, broadcast_callback, dummy_generator=None, noise_generator=None, decoy_generator=None, player_list_callback=None):
        """
        Args:
            player_manager: PlayerManager 인스턴스
            broadcast_callback: 브로드캐스트 메시지 전송 콜백
            dummy_generator: DummyGenerator 인스턴스 (선택)
            noise_generator: NoiseGenerator 인스턴스 (선택)
            decoy_generator: DecoyGenerator 인스턴스 (선택)
            player_list_callback: 플레이어 목록 업데이트 콜백 (선택)
        """
        self.player_manager = player_manager
        self.broadcast_callback = broadcast_callback
        self.player_list_callback = player_list_callback
        self.dummy_generator = dummy_generator
        self.noise_generator = noise_generator
        self.decoy_generator = decoy_generator

        self.state = GameState.WAITING
        self.current_round = 0
        self.round_start_time = 0
        self.defense_submissions: Dict[str, List[str]] = {}  # {player_id: [attacker_ips]}
        self.current_difficulty = None  # 현재 라운드 난이도 설정
        self.attack_counts: Dict[str, int] = {}  # 플레이어별 라운드 공격 횟수
        self.real_attacks: List[dict] = []  # 실제 공격 기록 (가짜 공격 판별용)
        self.decoy_ips: set = set()  # 가짜 공격 IP 목록 (점수 계산용)

        # 공격 승인 시스템 (v2.0)
        self.pending_attacks: Dict[str, dict] = {}  # {attack_id: {from, to, timestamp, attacker_sent, target_received, timeout}}
        self.attack_sequence = 0  # attack_id 생성용 시퀀스

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
        if self.game_thread:
            self.game_thread.join(timeout=5)

        # 상태 초기화 (다시 시작할 수 있도록)
        self.state = GameState.WAITING
        self.current_round = 0
        self.player_manager.reset_all_round_data()

        # 게임 종료 브로드캐스트
        end_msg = GameStateMessage(
            state=STATE_GAME_END,
            round_num=0,
            time_remaining=0
        )
        self.broadcast_callback(end_msg, None)

        print("[GameManager] 게임 중지 - 대기 상태로 전환")

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

        # 난이도 설정 로드
        self.current_difficulty = DIFFICULTY_BY_ROUND.get(round_num, DIFFICULTY_BY_ROUND[1])
        print(f"[GameManager] 난이도: {self.current_difficulty['name']}")

        # 더미 생성기 인터벌 조정
        if self.dummy_generator:
            dummy_interval = self.current_difficulty['dummy_interval']
            self.dummy_generator.set_interval(dummy_interval)

        # 라운드 데이터 초기화
        self.player_manager.reset_all_round_data()
        self.defense_submissions.clear()
        self.attack_counts.clear()
        self.real_attacks.clear()

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

        # 난이도 정보 포함
        difficulty = self.current_difficulty
        message = GameStateMessage(
            state="ROUND_START",
            round_num=round_num,
            time_remaining=PREPARATION_TIME,
            total_rounds=TOTAL_ROUNDS,
            message=f"라운드 {round_num} 준비 중...",
            difficulty={
                'name': difficulty['name'],
                'hint': difficulty['hint'],
                'warning': difficulty['warning'],
                'attack_limit': difficulty['attack_limit'],
                'noise_traffic': difficulty['noise_traffic'],
                'decoy_attacks': difficulty['decoy_attacks']
            }
        )
        self.broadcast_callback(message, None)

        # 준비 시간 대기
        time.sleep(PREPARATION_TIME)

    def _playing_phase(self, round_num: int):
        """게임 진행 단계"""
        self.state = GameState.PLAYING
        self.round_start_time = time.time()

        # 노이즈 트래픽 활성화 여부 확인 (R3+)
        if self.noise_generator and self.current_difficulty['noise_traffic']:
            self.noise_generator.start()
            print(f"[GameManager] 노이즈 트래픽 활성화 (R{round_num})")

        # 가짜 공격 활성화 여부 확인 (R5만)
        if self.decoy_generator and self.current_difficulty['decoy_attacks']:
            decoy_count = self.current_difficulty['decoy_count']
            self.decoy_generator.start(ROUND_TIME, decoy_count)
            print(f"[GameManager] 가짜 공격 활성화 (R{round_num}, {decoy_count}개)")

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

        # 노이즈 트래픽 중지
        if self.noise_generator:
            self.noise_generator.stop()

        # 가짜 공격 중지
        if self.decoy_generator:
            self.decoy_generator.stop()

    def _defense_phase(self, round_num: int):
        """방어 입력 단계"""
        self.state = GameState.DEFENSE

        # 난이도별 방어 입력 시간 사용
        defense_time = self.current_difficulty['defense_time']

        message = GameStateMessage(
            state="DEFENSE_PHASE",
            round_num=round_num,
            time_remaining=defense_time,
            message="방어 단계! 공격자 IP를 입력하세요!"
        )
        self.broadcast_callback(message, None)

        # 방어 입력 시간 대기
        time.sleep(defense_time)

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
        점수 계산 (라운드별 가중치 적용, v2.0: 가짜 공격 구분)

        Returns:
            {player_id: {'correct': bool, 'reason': str}}
        """
        results = {}
        players = self.player_manager.get_all_players()

        # 라운드별 점수 가중치 선택
        is_final_round = (self.current_round == 5)
        if is_final_round:
            score_correct = SCORE_CORRECT_DEFENSE_FINAL
            score_wrong = SCORE_WRONG_DEFENSE_FINAL
            score_missed = SCORE_MISSED_ATTACK_FINAL
        else:
            score_correct = SCORE_CORRECT_DEFENSE_NORMAL
            score_wrong = SCORE_WRONG_DEFENSE_NORMAL
            score_missed = SCORE_MISSED_ATTACK_NORMAL

        # 플레이어별 실제 공격자 IP 추출 (real_attacks 기반, v2.0)
        # v2.1: List 사용 (같은 IP의 공격도 모두 카운트)
        real_attacks_by_target = {}
        for attack in self.real_attacks:
            if attack.get('is_real', True):  # 실제 공격만
                target_id = attack['target_id']
                attacker_ip = attack['attacker_ip']
                if target_id not in real_attacks_by_target:
                    real_attacks_by_target[target_id] = []
                real_attacks_by_target[target_id].append(attacker_ip)

        for player in players:
            # v2.1: 실제로 받은 공격 (real_attacks 기반, 가짜 공격 제외, 리스트로 변경)
            actual_attacks = real_attacks_by_target.get(player.player_id, [])
            actual_attacks_unique = set(actual_attacks)  # 중복 제거된 고유 IP 목록

            # 플레이어가 제출한 방어 답변
            submitted = set(self.defense_submissions.get(player.player_id, []))

            print(f"[GameManager] {player.player_id} 점수 계산 - 실제 공격: {actual_attacks}, 제출: {submitted}")

            # 정답 계산
            # 고유 IP 기준으로 정답/오답 판정
            correct_defenses = actual_attacks_unique & submitted  # 교집합 (정답)
            wrong_defenses = submitted - actual_attacks_unique  # 오답 (가짜 공격 포함)

            # 놓친 공격: 실제 공격 횟수 - 정답으로 방어한 공격 횟수
            # v2.1: 정답으로 방어한 IP는 1번만 방어한 것으로 처리
            missed_attacks_count = 0
            for ip in actual_attacks_unique:
                attack_count = actual_attacks.count(ip)  # 해당 IP의 총 공격 횟수
                if ip in submitted:
                    # 정답으로 제출한 경우: 1번만 방어, 나머지는 놓침
                    missed_count = max(0, attack_count - 1)
                    missed_attacks_count += missed_count
                    print(f"[GameManager]   IP {ip}: {attack_count}번 공격, 1번 방어, {missed_count}번 놓침")
                else:
                    # 아예 제출하지 않은 경우: 모든 공격을 놓침
                    missed_attacks_count += attack_count
                    print(f"[GameManager]   IP {ip}: {attack_count}번 공격, 0번 방어, {attack_count}번 놓침")

            print(f"[GameManager] {player.player_id} - 정답: {len(correct_defenses)}개, 오답: {len(wrong_defenses)}개, 놓친 공격: {missed_attacks_count}개")

            # 하위 호환성을 위해 missed_attacks set도 유지
            missed_attacks = actual_attacks_unique - submitted  # 놓친 공격자 IP (고유)

            # 점수 업데이트
            score_change = 0

            score_change += len(correct_defenses) * score_correct
            score_change += len(wrong_defenses) * score_wrong
            score_change += missed_attacks_count * score_missed  # v2.1: 실제 공격 횟수 기준

            # v2.1: 음수 점수 허용 (0점 제한 제거)
            self.player_manager.update_score(player.player_id, score_change)

            # HP 감소 (놓친 공격 1개당 HP_DAMAGE_PER_ATTACK만큼 감소)
            # v2.1: 실제 공격 횟수 기준으로 HP 감소
            if missed_attacks_count > 0:
                hp_damage = missed_attacks_count * HP_DAMAGE_PER_ATTACK
                old_hp = player.hp
                new_hp = self.player_manager.update_hp(player.player_id, -hp_damage)
                print(f"[GameManager] {player.player_id} HP 감소: {old_hp} -> {new_hp} (-{hp_damage}, 놓친 공격: {missed_attacks_count}개)")

                # v2.1: HP 변경 시 플레이어 목록 브로드캐스트
                if self.player_list_callback:
                    self.player_list_callback()

            # 결과 메시지 생성
            reason_parts = []
            if correct_defenses:
                reason_parts.append(f"정확한 방어: {len(correct_defenses)}개 (+{len(correct_defenses) * score_correct}점)")
            if wrong_defenses:
                reason_parts.append(f"오답: {len(wrong_defenses)}개 ({len(wrong_defenses) * score_wrong}점)")
            if missed_attacks_count > 0:
                reason_parts.append(f"놓친 공격: {missed_attacks_count}개 ({missed_attacks_count * score_missed}점)")

            if not reason_parts:
                reason = "공격 없음"
            else:
                reason = ", ".join(reason_parts)

            # v2.0: 가짜 공격 경고 추가 (R5)
            if is_final_round and len(wrong_defenses) > 0:
                reason += f" [경고: 가짜 공격 {len(wrong_defenses)}개 포함 가능]"

            results[player.player_id] = {
                'correct': len(wrong_defenses) == 0 and len(missed_attacks) == 0,
                'reason': reason
            }

        return results

    def submit_defense(self, player_id: str, attacker_ips: List[str]):
        """
        방어 답안 제출 (중복 제출 시 누적)

        Args:
            player_id: 플레이어 ID
            attacker_ips: 공격자 IP 리스트
        """
        with self.lock:
            # v2.1: 기존 제출에 추가 (덮어쓰기 대신 누적)
            if player_id not in self.defense_submissions:
                self.defense_submissions[player_id] = []

            # 중복 제거하면서 추가
            current = set(self.defense_submissions[player_id])
            current.update(attacker_ips)
            self.defense_submissions[player_id] = list(current)

            print(f"[GameManager] {player_id} 방어 제출: {attacker_ips} (누적: {self.defense_submissions[player_id]})")

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

    def can_attack(self, player_id: str) -> tuple[bool, str]:
        """
        플레이어가 공격 가능한지 확인 (라운드별 제한 적용)

        주의: 이 메서드는 이미 self.lock을 획득한 상태에서 호출되어야 합니다.

        Args:
            player_id: 플레이어 ID

        Returns:
            (가능 여부, 메시지)
        """
        # Lock 제거: request_attack_approval에서 이미 lock을 잡고 있음 (중첩 락 방지)
        if self.state != GameState.PLAYING:
            return False, "공격은 게임 진행 중에만 가능합니다"

        if not self.current_difficulty:
            return False, "난이도 설정이 로드되지 않았습니다"

        # 플레이어의 현재 라운드 공격 횟수 확인
        attack_count = self.attack_counts.get(player_id, 0)
        attack_limit = self.current_difficulty['attack_limit']

        if attack_count >= attack_limit:
            return False, f"라운드당 최대 {attack_limit}회 공격 가능합니다 (현재 {attack_count}회)"

        return True, f"공격 가능 ({attack_count}/{attack_limit})"

    def record_attack(self, attacker_id: str, target_id: str, attacker_ip: str):
        """
        공격 기록 (실제 공격만)

        Args:
            attacker_id: 공격자 ID
            target_id: 타겟 ID
            attacker_ip: 공격자 IP
        """
        with self.lock:
            # 공격 횟수 증가
            self.attack_counts[attacker_id] = self.attack_counts.get(attacker_id, 0) + 1

            # 실제 공격 기록 (가짜 공격과 구분)
            self.real_attacks.append({
                'attacker_id': attacker_id,
                'target_id': target_id,
                'attacker_ip': attacker_ip,
                'timestamp': time.time()
            })

            print(f"[GameManager] 공격 기록: {attacker_id} -> {target_id} (횟수: {self.attack_counts[attacker_id]}/{self.current_difficulty['attack_limit']})")

    def get_current_state(self) -> dict:
        """현재 게임 상태 반환"""
        with self.lock:
            return {
                'state': self.state.value,
                'current_round': self.current_round,
                'total_rounds': TOTAL_ROUNDS,
                'players': self.player_manager.get_players_info(),
                'difficulty': self.current_difficulty
            }

    # ========== 공격 승인 시스템 (v2.0) ==========

    def request_attack_approval(self, attacker_id: str, target_id: str) -> tuple[bool, str, Optional[str]]:
        """
        공격 승인 요청 (v2.0 핵심 기능)

        Args:
            attacker_id: 공격자 플레이어 ID
            target_id: 타겟 플레이어 ID

        Returns:
            (승인 여부, 메시지, attack_id)
        """
        with self.lock:
            # 1. 자기 자신에 대한 공격 차단
            if attacker_id == target_id:
                print(f"[GameManager] 공격 거부: {attacker_id} - 자기 자신은 공격할 수 없습니다")
                return False, "자기 자신은 공격할 수 없습니다", None

            # 2. 공격 가능 여부 확인
            can_attack, msg = self.can_attack(attacker_id)
            if not can_attack:
                print(f"[GameManager] 공격 거부: {attacker_id} - {msg}")
                return False, msg, None

            print(f"[GameManager] 공격 가능 확인 통과: {attacker_id}")

            # 3. 타겟 플레이어 확인
            target_player = self.player_manager.get_player(target_id)
            if not target_player:
                return False, f"타겟 플레이어를 찾을 수 없습니다: {target_id}", None

            attacker_player = self.player_manager.get_player(attacker_id)
            if not attacker_player:
                return False, "공격자 정보를 찾을 수 없습니다", None

            # 3. attack_id 생성
            self.attack_sequence += 1
            attack_id = f"{attacker_id}→{target_id}_{int(time.time())}_{self.attack_sequence}"

            # 4. pending_attacks에 등록
            self.pending_attacks[attack_id] = {
                'from': attacker_id,
                'to': target_id,
                'from_ip': attacker_player.ip,
                'to_ip': target_player.ip,
                'timestamp': time.time(),
                'attacker_sent': False,
                'target_received': False,
                'timeout_timer': None
            }

            # 5. 타임아웃 타이머 설정
            timeout_timer = threading.Timer(
                ATTACK_APPROVAL_TIMEOUT,
                self._handle_attack_timeout,
                args=[attack_id]
            )
            timeout_timer.daemon = True
            timeout_timer.start()
            self.pending_attacks[attack_id]['timeout_timer'] = timeout_timer

            # 6. 메시지 준비 (lock 안에서)
            # 공격자에게: 공격 승인 메시지 (타겟의 **실제 컨테이너 IP** 포함)
            target_port = PLAYER_ATTACK_PORT_BASE + self.player_manager.get_player_index(target_id)
            # 실제 컨테이너 IP 가져오기 (address[0])
            target_real_ip = target_player.address[0]

            print(f"[GameManager] 타겟 포트 계산: {target_port} = {PLAYER_ATTACK_PORT_BASE} + {self.player_manager.get_player_index(target_id)}")
            print(f"[GameManager] 타겟 실제 IP: {target_real_ip} (가상 IP: {target_player.ip})")

            approved_msg = AttackApprovedMessage(
                attack_id=attack_id,
                target_ip=target_real_ip,  # 실제 컨테이너 IP 사용!
                target_port=target_port,
                target_id=target_id
            )

            # 타겟에게: 수신 공격 경고 메시지 (공격자 IP 포함)
            warning_msg = IncomingAttackWarningMessage(
                attack_id=attack_id,
                attacker_ip=attacker_player.ip,
                attacker_id=attacker_id
            )

            print(f"[GameManager] 공격 승인: {attacker_id} -> {target_id} (attack_id: {attack_id})")

        # 7. Lock 해제 후 메시지 전송 (데드락 방지)
        print(f"[GameManager] 공격 승인 메시지 전송 중: {attacker_id} -> {target_id} ({target_real_ip}:{target_port})")
        self.broadcast_callback(approved_msg, [attacker_player])
        print(f"[GameManager] 공격 승인 메시지 전송 완료")

        self.broadcast_callback(warning_msg, [target_player])
        print(f"[GameManager] 공격 경고 메시지 전송 완료")

        return True, "공격이 승인되었습니다", attack_id

    def confirm_attack_sent(self, attack_id: str) -> bool:
        """
        공격 전송 확인 (공격자가 P2P로 패킷 전송 완료 시 호출)

        Args:
            attack_id: 공격 ID

        Returns:
            확인 성공 여부
        """
        with self.lock:
            if attack_id not in self.pending_attacks:
                print(f"[GameManager] 알 수 없는 attack_id (SENT): {attack_id}")
                print(f"[GameManager] 현재 pending_attacks: {list(self.pending_attacks.keys())}")
                return False

            self.pending_attacks[attack_id]['attacker_sent'] = True
            attack_info = self.pending_attacks[attack_id]
            print(f"[GameManager] 공격 전송 확인: {attack_id} (attacker_sent={attack_info['attacker_sent']}, target_received={attack_info['target_received']})")

            # 양방향 확인 완료 시 공격 완료 처리
            self._check_attack_complete(attack_id)
            return True

    def confirm_attack_received(self, attack_id: str) -> bool:
        """
        공격 수신 확인 (타겟이 P2P 패킷 수신 완료 시 호출)

        Args:
            attack_id: 공격 ID

        Returns:
            확인 성공 여부
        """
        with self.lock:
            if attack_id not in self.pending_attacks:
                print(f"[GameManager] 알 수 없는 attack_id (RECEIVED): {attack_id}")
                print(f"[GameManager] 현재 pending_attacks: {list(self.pending_attacks.keys())}")
                return False

            self.pending_attacks[attack_id]['target_received'] = True
            attack_info = self.pending_attacks[attack_id]
            print(f"[GameManager] 공격 수신 확인: {attack_id} (attacker_sent={attack_info['attacker_sent']}, target_received={attack_info['target_received']})")

            # 양방향 확인 완료 시 공격 완료 처리
            self._check_attack_complete(attack_id)
            return True

    def _check_attack_complete(self, attack_id: str):
        """
        공격 양방향 확인 완료 시 처리

        Args:
            attack_id: 공격 ID
        """
        if attack_id not in self.pending_attacks:
            print(f"[GameManager] _check_attack_complete: attack_id not in pending_attacks: {attack_id}")
            return

        attack_info = self.pending_attacks[attack_id]
        print(f"[GameManager] _check_attack_complete: {attack_id} - attacker_sent={attack_info['attacker_sent']}, target_received={attack_info['target_received']}")

        # 양방향 확인 완료
        if attack_info['attacker_sent'] and attack_info['target_received']:
            # 타임아웃 타이머 취소
            if attack_info['timeout_timer']:
                attack_info['timeout_timer'].cancel()

            # 공격 횟수 증가
            attacker_id = attack_info['from']
            target_id = attack_info['to']
            attacker_ip = attack_info['from_ip']

            self.attack_counts[attacker_id] = self.attack_counts.get(attacker_id, 0) + 1

            # 실제 공격 기록
            self.real_attacks.append({
                'attacker_id': attacker_id,
                'target_id': target_id,
                'attacker_ip': attacker_ip,
                'timestamp': time.time(),
                'is_real': True
            })

            # 타겟의 attacks_received 업데이트
            self.player_manager.record_attack(target_id, attacker_ip)

            # pending_attacks에서 제거
            del self.pending_attacks[attack_id]

            print(f"[GameManager] ✅ 공격 완료: {attacker_id} -> {target_id} (attack_id: {attack_id}, 횟수: {self.attack_counts[attacker_id]}/{self.current_difficulty['attack_limit']}, total real_attacks: {len(self.real_attacks)})")
        else:
            print(f"[GameManager] 공격 미완료 (대기 중): {attack_id} - attacker_sent={attack_info['attacker_sent']}, target_received={attack_info['target_received']}")

    def _handle_attack_timeout(self, attack_id: str):
        """
        공격 타임아웃 처리

        Args:
            attack_id: 공격 ID
        """
        with self.lock:
            if attack_id in self.pending_attacks:
                attack_info = self.pending_attacks[attack_id]
                print(f"[GameManager] 공격 타임아웃: {attack_id} (attacker_sent={attack_info['attacker_sent']}, target_received={attack_info['target_received']})")

                # pending_attacks에서 제거 (공격 무효화)
                del self.pending_attacks[attack_id]
