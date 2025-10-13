"""
더미 패킷 생성 모듈
게임 중 더미 패킷을 주기적으로 생성하여 전송
"""

import threading
import time
import random
import string
from typing import Callable, List
from common.message_types import DummyMessage
from common.constants import DUMMY_PACKET_INTERVAL_MIN, DUMMY_PACKET_INTERVAL_MAX


class DummyGenerator:
    """더미 패킷 생성기"""

    def __init__(self, send_callback: Callable[[DummyMessage, List], None]):
        """
        Args:
            send_callback: 더미 패킷 전송 콜백 함수 (message, target_players)
        """
        self.send_callback = send_callback
        self.running = False
        self.thread = None
        self.interval_min = DUMMY_PACKET_INTERVAL_MIN
        self.interval_max = DUMMY_PACKET_INTERVAL_MAX

    def start(self):
        """더미 패킷 생성 시작"""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._generate_loop, daemon=True)
        self.thread.start()
        print("[DummyGenerator] 더미 패킷 생성 시작")

    def stop(self):
        """더미 패킷 생성 중지"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=3)
        print("[DummyGenerator] 더미 패킷 생성 중지")

    def _generate_loop(self):
        """더미 패킷 생성 루프"""
        while self.running:
            try:
                # 랜덤 인터벌로 대기
                interval = random.uniform(self.interval_min, self.interval_max)
                time.sleep(interval)

                if not self.running:
                    break

                # 더미 패킷 생성
                dummy_message = self._create_dummy_packet()

                # 콜백을 통해 전송 (모든 플레이어에게)
                self.send_callback(dummy_message, None)

            except Exception as e:
                print(f"[DummyGenerator] 더미 패킷 생성 중 오류: {e}")

    def _create_dummy_packet(self) -> DummyMessage:
        """
        더미 패킷 생성

        Returns:
            DummyMessage 객체
        """
        # 랜덤 페이로드 생성
        random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        payload = f"DUMMY_{random_suffix}"

        return DummyMessage(payload=payload)

    def set_interval(self, min_sec: float, max_sec: float):
        """
        더미 패킷 생성 인터벌 설정

        Args:
            min_sec: 최소 인터벌 (초)
            max_sec: 최대 인터벌 (초)
        """
        self.interval_min = min_sec
        self.interval_max = max_sec
        print(f"[DummyGenerator] 인터벌 설정: {min_sec}~{max_sec}초")
