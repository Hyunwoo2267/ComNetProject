"""
네트워크 프로토콜 핸들러
TCP 통신을 위한 메시지 송수신 처리
"""

import socket
import json
import struct
from typing import Optional, Dict, Any
from .constants import BUFFER_SIZE, ENCODING
from .message_types import Message


class Protocol:
    """
    TCP 프로토콜 핸들러
    메시지 길이를 헤더에 포함하여 완전한 메시지 송수신 보장
    """

    # 헤더: 4바이트 unsigned int (메시지 길이)
    HEADER_SIZE = 4
    HEADER_FORMAT = '!I'  # 네트워크 바이트 오더 (빅 엔디안)

    @staticmethod
    def send_message(sock: socket.socket, message: Message) -> bool:
        """
        메시지를 소켓으로 전송

        Args:
            sock: 전송할 소켓
            message: 전송할 Message 객체

        Returns:
            성공 여부
        """
        try:
            # 메시지를 JSON으로 직렬화
            json_data = message.to_json()
            message_bytes = json_data.encode(ENCODING)

            # 메시지 길이를 헤더로 패킹
            message_length = len(message_bytes)
            header = struct.pack(Protocol.HEADER_FORMAT, message_length)

            # 헤더 + 메시지 전송
            sock.sendall(header + message_bytes)
            return True

        except Exception as e:
            print(f"[Protocol] 메시지 전송 실패: {e}")
            return False

    @staticmethod
    def receive_message(sock: socket.socket) -> Optional[Message]:
        """
        소켓에서 메시지를 수신

        Args:
            sock: 수신할 소켓

        Returns:
            수신한 Message 객체 또는 None
        """
        try:
            # 헤더 수신 (메시지 길이)
            header_bytes = Protocol._receive_exact(sock, Protocol.HEADER_SIZE)
            if not header_bytes:
                return None

            # 메시지 길이 언패킹
            message_length = struct.unpack(Protocol.HEADER_FORMAT, header_bytes)[0]

            # 메시지 본문 수신
            message_bytes = Protocol._receive_exact(sock, message_length)
            if not message_bytes:
                return None

            # JSON 역직렬화
            json_data = message_bytes.decode(ENCODING)
            message = Message.from_json(json_data)

            return message

        except Exception as e:
            print(f"[Protocol] 메시지 수신 실패: {e}")
            return None

    @staticmethod
    def _receive_exact(sock: socket.socket, num_bytes: int) -> Optional[bytes]:
        """
        정확히 지정된 바이트 수만큼 수신

        Args:
            sock: 수신할 소켓
            num_bytes: 수신할 바이트 수

        Returns:
            수신한 바이트 또는 None
        """
        buffer = b''
        while len(buffer) < num_bytes:
            try:
                chunk = sock.recv(num_bytes - len(buffer))
                if not chunk:
                    return None
                buffer += chunk
            except Exception as e:
                print(f"[Protocol] 데이터 수신 중 오류: {e}")
                return None
        return buffer

    @staticmethod
    def send_json(sock: socket.socket, data: Dict[str, Any]) -> bool:
        """
        딕셔너리를 JSON으로 직접 전송 (레거시 지원)

        Args:
            sock: 전송할 소켓
            data: 전송할 데이터

        Returns:
            성공 여부
        """
        try:
            message = Message.from_dict(data.copy())
            return Protocol.send_message(sock, message)
        except Exception as e:
            print(f"[Protocol] JSON 전송 실패: {e}")
            return False

    @staticmethod
    def receive_json(sock: socket.socket) -> Optional[Dict[str, Any]]:
        """
        JSON을 수신하여 딕셔너리로 반환 (레거시 지원)

        Args:
            sock: 수신할 소켓

        Returns:
            수신한 딕셔너리 또는 None
        """
        message = Protocol.receive_message(sock)
        if message:
            return message.to_dict()
        return None


class ConnectionManager:
    """연결 관리 유틸리티"""

    @staticmethod
    def create_server_socket(host: str, port: int, backlog: int = 5) -> Optional[socket.socket]:
        """
        서버 소켓 생성

        Args:
            host: 바인딩할 호스트
            port: 바인딩할 포트
            backlog: 대기 큐 크기

        Returns:
            생성된 소켓 또는 None
        """
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((host, port))
            server_socket.listen(backlog)
            print(f"[서버] {host}:{port}에서 대기 중...")
            return server_socket
        except Exception as e:
            print(f"[서버] 소켓 생성 실패: {e}")
            return None

    @staticmethod
    def create_client_socket(host: str, port: int) -> Optional[socket.socket]:
        """
        클라이언트 소켓 생성 및 연결

        Args:
            host: 연결할 호스트
            port: 연결할 포트

        Returns:
            연결된 소켓 또는 None
        """
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((host, port))
            print(f"[클라이언트] {host}:{port}에 연결됨")
            return client_socket
        except Exception as e:
            print(f"[클라이언트] 연결 실패: {e}")
            return None

    @staticmethod
    def close_socket(sock: socket.socket):
        """소켓 안전하게 닫기"""
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except:
            pass
        finally:
            sock.close()
