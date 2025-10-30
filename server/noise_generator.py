"""
노이즈 트래픽 생성 모듈
R3 이후 플레이어 간 배경 트래픽을 생성하여 공격 탐지를 어렵게 만듦
"""

import threading
import time
import random
import string
from typing import Callable, List
from common.message_types import Message
from common.constants import MSG_TYPE_NOISE


class NoiseGenerator:
    """노이즈 트래픽 생성기"""

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
        self.interval_min = 3.0  # 최소 노이즈 간격 (초)
        self.interval_max = 8.0  # 최대 노이즈 간격 (초)

    def start(self):
        """노이즈 트래픽 생성 시작"""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._generate_loop, daemon=True)
        self.thread.start()
        print("[NoiseGenerator] 노이즈 트래픽 생성 시작")

    def stop(self):
        """노이즈 트래픽 생성 중지"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=3)
        print("[NoiseGenerator] 노이즈 트래픽 생성 중지")

    def _generate_loop(self):
        """노이즈 트래픽 생성 루프"""
        while self.running:
            try:
                # 랜덤 인터벌로 대기
                interval = random.uniform(self.interval_min, self.interval_max)
                time.sleep(interval)

                if not self.running:
                    break

                # 노이즈 패킷 생성 및 전송
                self._send_noise_packet()

            except Exception as e:
                print(f"[NoiseGenerator] 노이즈 생성 중 오류: {e}")

    def _send_noise_packet(self):
        """
        랜덤한 두 플레이어 간 노이즈 패킷 전송
        """
        players = self.player_manager.get_all_players()

        # 최소 2명의 플레이어가 필요
        if len(players) < 2:
            return

        # 랜덤으로 송신자와 수신자 선택
        sender = random.choice(players)
        receiver = random.choice([p for p in players if p.player_id != sender.player_id])

        # 노이즈 메시지 생성
        noise_msg = self._create_noise_message(sender, receiver)

        # 수신자에게 전송
        self.send_to_player_callback(receiver, noise_msg)

        print(f"[NoiseGenerator] 노이즈: {sender.player_id} ({sender.ip}) -> {receiver.player_id} ({receiver.ip})")

    def _create_noise_message(self, sender, receiver) -> Message:
        """
        노이즈 메시지 생성

        Args:
            sender: 송신 플레이어
            receiver: 수신 플레이어

        Returns:
            Message 객체
        """
        from common.message_types import encode_payload

        # 랜덤 페이로드 생성 (실제 공격과 구분하기 어렵게)
        random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        payload = f"NOISE_{random_suffix}"

        # base64 인코딩
        encoded_payload = encode_payload(payload)

        return Message(
            MSG_TYPE_NOISE,
            from_ip=sender.ip,
            to_ip=receiver.ip,
            from_player=sender.player_id,
            to_player=receiver.player_id,
            payload=encoded_payload,
            _original_payload=payload
        )

    def set_interval(self, min_sec: float, max_sec: float = None):
        """
        노이즈 생성 인터벌 설정

        Args:
            min_sec: 최소 인터벌 (초)
            max_sec: 최대 인터벌 (초), None이면 고정 인터벌
        """
        self.interval_min = min_sec
        self.interval_max = max_sec if max_sec is not None else min_sec
        if max_sec is None or min_sec == max_sec:
            print(f"[NoiseGenerator] 인터벌 설정: {min_sec}초 (고정)")
        else:
            print(f"[NoiseGenerator] 인터벌 설정: {min_sec}~{max_sec}초")
