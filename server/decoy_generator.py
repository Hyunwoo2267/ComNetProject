"""
가짜 공격 생성 모듈
R5에서만 작동하며, 서버가 생성한 가짜 공격 패킷을 플레이어에게 전송
실제 공격과 구분하기 어렵게 만들어 난이도 증가
"""

import threading
import time
import random
import string
from typing import Callable, List
from common.message_types import Message
from common.constants import MSG_TYPE_DECOY_ATTACK


class DecoyGenerator:
    """가짜 공격 생성기"""

    def __init__(self, player_manager, send_to_player_callback: Callable):
        """
        Args:
            player_manager: PlayerManager 인스턴스
            send_to_player_callback: 특정 플레이어에게 메시지 전송하는 콜백 (player, message)
        """
        self.player_manager = player_manager
        self.send_to_player_callback = send_to_player_callback
        self.running = False
        self.thread = None
        self.decoy_count = 10  # 라운드당 가짜 공격 개수
        self.round_duration = 90  # 라운드 지속 시간 (초)

    def start(self, round_duration: int = 90, decoy_count: int = 10):
        """
        가짜 공격 생성 시작

        Args:
            round_duration: 라운드 지속 시간 (초)
            decoy_count: 생성할 가짜 공격 개수
        """
        if self.running:
            return

        self.round_duration = round_duration
        self.decoy_count = decoy_count
        self.running = True
        self.thread = threading.Thread(target=self._generate_loop, daemon=True)
        self.thread.start()
        print(f"[DecoyGenerator] 가짜 공격 생성 시작 ({decoy_count}개, {round_duration}초 동안)")

    def stop(self):
        """가짜 공격 생성 중지"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=3)
        print("[DecoyGenerator] 가짜 공격 생성 중지")

    def _generate_loop(self):
        """
        가짜 공격 생성 루프
        라운드 시간 동안 균등하게 분산하여 가짜 공격 전송
        """
        try:
            # 가짜 공격을 라운드 시간 동안 균등하게 분산
            interval = self.round_duration / self.decoy_count if self.decoy_count > 0 else 10

            for i in range(self.decoy_count):
                if not self.running:
                    break

                # 랜덤 지터 추가 (±20%)
                jitter = random.uniform(-0.2, 0.2) * interval
                wait_time = max(1.0, interval + jitter)
                time.sleep(wait_time)

                if not self.running:
                    break

                # 가짜 공격 전송
                self._send_decoy_attack()

        except Exception as e:
            print(f"[DecoyGenerator] 가짜 공격 생성 중 오류: {e}")

    def _send_decoy_attack(self):
        """
        랜덤한 플레이어에게 가짜 공격 전송
        가짜 송신자 IP도 무작위로 선택
        """
        players = self.player_manager.get_all_players()

        # 최소 2명의 플레이어가 필요
        if len(players) < 2:
            return

        # 랜덤으로 가짜 공격자와 실제 타겟 선택
        fake_sender = random.choice(players)
        real_target = random.choice([p for p in players if p.player_id != fake_sender.player_id])

        # 가짜 공격 메시지 생성
        decoy_msg = self._create_decoy_message(fake_sender, real_target)

        # 타겟에게 전송
        self.send_to_player_callback(real_target, decoy_msg)

        print(f"[DecoyGenerator] 가짜 공격: {fake_sender.player_id} ({fake_sender.ip}) -> {real_target.player_id} [FAKE]")

    def _create_decoy_message(self, fake_sender, real_target) -> Message:
        """
        가짜 공격 메시지 생성 (실제 공격과 매우 유사하게)

        Args:
            fake_sender: 가짜 송신자 (실제 플레이어지만 보낸 적 없음)
            real_target: 실제 타겟

        Returns:
            Message 객체
        """
        from common.message_types import encode_payload

        # 실제 공격과 유사한 페이로드 생성
        random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        payload = f"ATTACK_TARGET_{real_target.player_id}_{random_suffix}"

        # base64 인코딩
        encoded_payload = encode_payload(payload)

        return Message(
            MSG_TYPE_DECOY_ATTACK,
            from_ip=fake_sender.ip,  # 실제 플레이어 IP 사용
            to_ip=real_target.ip,
            from_player=fake_sender.player_id,  # 실제 플레이어 ID 사용
            to_player=real_target.player_id,
            payload=encoded_payload,
            
            is_decoy=True  # 내부적으로 가짜임을 표시 (클라이언트는 모름)
        )
