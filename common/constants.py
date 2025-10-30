"""
공통 상수 정의
프로젝트 전체에서 사용되는 상수들
"""

# 네트워크 설정
DEFAULT_PORT = 9999
DEFAULT_HOST = '0.0.0.0'
BUFFER_SIZE = 4096
ENCODING = 'utf-8'

# 게임 설정
MIN_PLAYERS = 2
MAX_PLAYERS = 4
TOTAL_ROUNDS = 5
ROUND_TIME = 90  # 초
DEFENSE_INPUT_TIME = 20  # 초
PREPARATION_TIME = 10  # 초

# 더미 패킷 설정 (기본값, 라운드별로 오버라이드됨)
DUMMY_PACKET_INTERVAL_MIN = 1.0  # 초
DUMMY_PACKET_INTERVAL_MAX = 2.0  # 초

# 라운드별 난이도 설정
DIFFICULTY_BY_ROUND = {
    1: {
        "name": "입문",
        "dummy_interval": 2.0,  # 더미 패킷 전송 간격 (초)
        "attack_limit": 3,  # 라운드당 공격 가능 횟수
        "defense_time": 20,  # 방어 입력 시간 (초)
        "noise_traffic": False,  # 노이즈 트래픽 여부
        "decoy_attacks": False,  # 가짜 공격 여부
        "decoy_count": 0,  # 가짜 공격 개수
        "hint": "기본적인 IP 기반 공격 탐지를 학습하세요",
        "warning": None
    },
    2: {
        "name": "초급",
        "dummy_interval": 1.5,
        "attack_limit": 3,
        "defense_time": 20,
        "noise_traffic": False,
        "decoy_attacks": False,
        "decoy_count": 0,
        "hint": "더미 패킷의 빈도가 증가합니다",
        "warning": None
    },
    3: {
        "name": "중급",
        "dummy_interval": 1.0,
        "attack_limit": 4,
        "defense_time": 20,
        "noise_traffic": True,  # 노이즈 트래픽 시작
        "decoy_attacks": False,
        "decoy_count": 0,
        "hint": "플레이어 간 노이즈 트래픽이 추가됩니다",
        "warning": "주의: 공격이 아닌 트래픽도 관찰될 수 있습니다"
    },
    4: {
        "name": "고급",
        "dummy_interval": 0.8,
        "attack_limit": 4,
        "defense_time": 20,
        "noise_traffic": True,
        "decoy_attacks": False,
        "decoy_count": 0,
        "hint": "더미 패킷과 노이즈 트래픽이 더 빈번해집니다",
        "warning": "주의: 패킷 분석이 더 어려워집니다"
    },
    5: {
        "name": "최종 라운드",
        "dummy_interval": 0.5,
        "attack_limit": 5,
        "defense_time": 20,
        "noise_traffic": True,
        "decoy_attacks": True,  # 가짜 공격 추가
        "decoy_count": 10,  # 10개의 가짜 공격
        "hint": "모든 방해 요소가 활성화됩니다",
        "warning": "경고: 가짜 공격이 포함되어 있습니다!"
    }
}

# 점수 설정 (라운드별)
# R1-R4 점수 계산
SCORE_CORRECT_DEFENSE_NORMAL = 10
SCORE_WRONG_DEFENSE_NORMAL = -5
SCORE_MISSED_ATTACK_NORMAL = -3

# R5 점수 계산 (가중치 증가)
SCORE_CORRECT_DEFENSE_FINAL = 15
SCORE_WRONG_DEFENSE_FINAL = -10
SCORE_MISSED_ATTACK_FINAL = -5

# 공격 점수 (사용하지 않음 - IP 기반 탐지로 변경)
SCORE_SUCCESSFUL_ATTACK = 0

# 체력 설정
INITIAL_HP = 100
HP_DAMAGE_PER_ATTACK = 10  # 놓친 공격 1개당 HP 감소량

# 메시지 타입
MSG_TYPE_DUMMY = "DUMMY"
MSG_TYPE_ATTACK = "ATTACK"
MSG_TYPE_DEFENSE = "DEFENSE"
MSG_TYPE_SCORE = "SCORE"
MSG_TYPE_CONNECT = "CONNECT"
MSG_TYPE_DISCONNECT = "DISCONNECT"
MSG_TYPE_GAME_START = "GAME_START"
MSG_TYPE_GAME_END = "GAME_END"
MSG_TYPE_ROUND_START = "ROUND_START"
MSG_TYPE_ROUND_END = "ROUND_END"
MSG_TYPE_PLAYER_LIST = "PLAYER_LIST"
MSG_TYPE_DEFENSE_PHASE = "DEFENSE_PHASE"
MSG_TYPE_ERROR = "ERROR"
MSG_TYPE_INFO = "INFO"
MSG_TYPE_NOISE = "NOISE"  # 노이즈 트래픽
MSG_TYPE_DECOY_ATTACK = "DECOY_ATTACK"  # 가짜 공격 (서버 생성)
MSG_TYPE_ATTACK_REQUEST = "ATTACK_REQUEST"  # 공격 요청
MSG_TYPE_ATTACK_APPROVED = "ATTACK_APPROVED"  # 공격 승인
MSG_TYPE_INCOMING_ATTACK_WARNING = "INCOMING_ATTACK_WARNING"  # 수신 공격 경고
MSG_TYPE_ATTACK_CONFIRM = "ATTACK_CONFIRM"  # 공격 확인 (송신/수신)

# 공격 승인 시스템 설정
ATTACK_APPROVAL_TIMEOUT = 5.0  # 공격 승인 타임아웃 (초)
PLAYER_ATTACK_PORT_BASE = 10001  # 플레이어 P2P 공격 포트 시작

# 게임 상태
STATE_WAITING = "WAITING"
STATE_PREPARATION = "PREPARATION"
STATE_PLAYING = "PLAYING"
STATE_DEFENSE = "DEFENSE"
STATE_ROUND_END = "ROUND_END"
STATE_GAME_END = "GAME_END"
