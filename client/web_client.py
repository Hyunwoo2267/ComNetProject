"""
Flask 기반 웹 클라이언트
브라우저에서 게임 플레이 가능
"""

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import os
import sys
import threading

# 프로젝트 루트 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client.client import GameClient
from common.message_types import Message

app = Flask(__name__)
app.config['SECRET_KEY'] = 'network_security_game_secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# 전역 클라이언트 인스턴스
game_client = None
client_lock = threading.Lock()


def message_callback(msg: Message):
    """게임 서버로부터 메시지 수신 시 웹 클라이언트로 전송"""
    msg_type = msg.type

    # 웹 클라이언트에 메시지 전송
    if msg_type == "PLAYER_LIST":
        socketio.emit('player_list', {'players': msg.data.get('players', [])})

    elif msg_type == "SCORE":
        socketio.emit('score_update', msg.data)

    elif msg_type in ["GAME_START", "ROUND_START", "PLAYING", "DEFENSE_PHASE", "ROUND_END", "GAME_END"]:
        socketio.emit('game_state', msg.to_dict())

    elif msg_type == "INFO":
        socketio.emit('info_message', {'message': msg.data.get('message', '')})

    # 모든 메시지 로그
    socketio.emit('log_message', {
        'type': msg_type,
        'data': msg.data
    })


@app.route('/')
def index():
    """메인 페이지"""
    return render_template('game.html')


@socketio.on('connect')
def handle_connect():
    """웹소켓 연결"""
    print("[웹서버] 클라이언트 연결됨")

    # 현재 상태 전송
    if game_client and game_client.is_connected():
        info = game_client.get_my_info()
        emit('connected', {
            'player_id': info['player_id'],
            'ip': info['ip'],
            'score': info['score'],
            'hp': info['hp'],
            'round': info['round']
        })


@socketio.on('game_connect')
def handle_game_connect(data):
    """게임 서버에 연결"""
    global game_client

    player_id = data.get('player_id', 'Player1')
    server_host = data.get('server_host', '172.20.0.10')
    server_port = data.get('server_port', 9999)

    print(f"[웹서버] 게임 서버 연결 시도: player_id={player_id}, host={server_host}, port={server_port}")

    with client_lock:
        try:
            game_client = GameClient(player_id=player_id, host=server_host, port=server_port)
            game_client.add_message_callback(message_callback)

            print(f"[웹서버] GameClient 생성 완료, 연결 시도 중...")

            if game_client.connect():
                info = game_client.get_my_info()
                print(f"[웹서버] 게임 서버 연결 성공: {info}")
                emit('connected', {
                    'success': True,
                    'player_id': info['player_id'],
                    'ip': info['ip'],
                    'score': info['score'],
                    'hp': info['hp'],
                    'round': info['round']
                })
            else:
                print(f"[웹서버] 게임 서버 연결 실패")
                emit('connected', {'success': False, 'error': '서버 연결 실패'})

        except Exception as e:
            print(f"[웹서버] 게임 서버 연결 오류: {e}")
            import traceback
            traceback.print_exc()
            emit('connected', {'success': False, 'error': str(e)})


@socketio.on('send_attack')
def handle_attack(data):
    """공격 전송"""
    print(f"[웹서버] 공격 요청 받음: {data}")

    if not game_client or not game_client.is_connected():
        print(f"[웹서버] 게임 클라이언트 연결되지 않음: game_client={game_client}, connected={game_client.is_connected() if game_client else False}")
        emit('attack_result', {'success': False, 'error': '서버에 연결되지 않음'})
        return

    target = data.get('target', '')
    print(f"[웹서버] 공격 전송 시도: target={target}")

    if game_client.send_attack(target):
        print(f"[웹서버] 공격 전송 성공: {target}")
        emit('attack_result', {'success': True, 'target': target})
    else:
        print(f"[웹서버] 공격 전송 실패: {target}")
        emit('attack_result', {'success': False, 'error': '공격 실패'})


@socketio.on('submit_defense')
def handle_defense(data):
    """방어 제출"""
    if not game_client or not game_client.is_connected():
        emit('defense_result', {'success': False, 'error': '서버에 연결되지 않음'})
        return

    attacker_ips = data.get('attacker_ips', [])
    if game_client.submit_defense(attacker_ips):
        emit('defense_result', {'success': True, 'ips': attacker_ips})
    else:
        emit('defense_result', {'success': False, 'error': '방어 제출 실패'})


@socketio.on('get_status')
def handle_get_status():
    """현재 상태 조회"""
    print(f"[웹서버] get_status 요청 받음. game_client 존재: {game_client is not None}")

    if not game_client or not game_client.is_connected():
        print(f"[웹서버] 게임 클라이언트가 연결되지 않음")
        emit('status', {'connected': False})
        return

    info = game_client.get_my_info()
    players = game_client.get_players()
    game_state = game_client.get_game_state()

    print(f"[웹서버] 상태 전송: {info['player_id']}, 플레이어 수: {len(players)}")

    emit('status', {
        'connected': True,
        'my_info': info,
        'players': players,
        'game_state': game_state
    })

    # 연결 상태와 플레이어 목록도 개별적으로 전송
    emit('connected', info)
    emit('player_list', {'players': players})


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description='웹 기반 게임 클라이언트')
    parser.add_argument('--host', default='0.0.0.0', help='웹서버 호스트')
    parser.add_argument('--port', type=int, default=5000, help='웹서버 포트')
    parser.add_argument('--player-id', default=None, help='플레이어 ID (자동 연결용)')
    parser.add_argument('--server-host', default='172.20.0.10', help='게임 서버 호스트')
    parser.add_argument('--server-port', type=int, default=9999, help='게임 서버 포트')

    args = parser.parse_args()

    # 자동 연결
    if args.player_id:
        global game_client
        game_client = GameClient(player_id=args.player_id, host=args.server_host, port=args.server_port)
        game_client.add_message_callback(message_callback)

        def auto_connect():
            import time
            time.sleep(2)  # 웹서버 시작 대기
            if game_client.connect():
                print(f"[웹클라이언트] 게임 서버에 자동 연결: {args.player_id}")

        threading.Thread(target=auto_connect, daemon=True).start()

    print(f"[웹클라이언트] 웹서버 시작: http://{args.host}:{args.port}")
    try:
        socketio.run(app, host=args.host, port=args.port, debug=False, allow_unsafe_werkzeug=True)
    except TypeError:
        # Python 3.9 이하 버전 호환성
        socketio.run(app, host=args.host, port=args.port, debug=False)


if __name__ == '__main__':
    main()
