@echo off
REM 실시간 Wireshark 캡처를 위한 스크립트
REM 방법: 컨테이너에서 tcpdump를 실행하여 stdout으로 스트리밍하고, Wireshark로 파이프

echo ========================================
echo 실시간 Wireshark 캡처 시작
echo ========================================
echo.
echo 어느 플레이어의 트래픽을 캡처하시겠습니까?
echo   1. Player1 (172.20.0.11)
echo   2. Player2 (172.20.0.12)
echo   3. Player3 (172.20.0.13)
echo   4. Server (모든 트래픽)
echo.

set /p choice="선택 (1-4): "

if "%choice%"=="1" (
    set CONTAINER=game_player1
    set PLAYER=Player1
)
if "%choice%"=="2" (
    set CONTAINER=game_player2
    set PLAYER=Player2
)
if "%choice%"=="3" (
    set CONTAINER=game_player3
    set PLAYER=Player3
)
if "%choice%"=="4" (
    set CONTAINER=game_server
    set PLAYER=Server
)

echo.
echo %PLAYER%의 트래픽 캡처 시작...
echo.
echo 방법 1: 파일로 저장 후 Wireshark로 열기 (권장)
echo 방법 2: 실시간 스트리밍 (고급)
echo.

set /p method="방법 선택 (1-2): "

if "%method%"=="1" (
    echo.
    echo 캡처 시간을 입력하세요 (초 단위, 예: 60)
    set /p duration="캡처 시간: "

    echo.
    echo %duration%초 동안 패킷 캡처 중...
    docker exec %CONTAINER% timeout %duration% tcpdump -i any -w /app/realtime_capture.pcap

    echo.
    echo 캡처 완료! 파일 위치: realtime_capture.pcap
    echo Wireshark로 파일을 열어주세요.
    pause
)

if "%method%"=="2" (
    echo.
    echo 실시간 스트리밍 모드
    echo Wireshark를 먼저 실행하고 "Capture > Options > Manage Interfaces > Pipes > New"
    echo 파이프 이름: \\.\pipe\wireshark
    echo.
    echo 준비되면 아무 키나 누르세요...
    pause

    echo.
    echo tcpdump를 stdout으로 스트리밍 중...
    docker exec %CONTAINER% tcpdump -i any -U -w - | "C:\Program Files\Wireshark\Wireshark.exe" -k -i -
)
