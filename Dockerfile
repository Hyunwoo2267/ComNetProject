# 네트워크 보안 게임 - Dockerfile
FROM python:3.9-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트 및 네트워크 도구 설치
RUN apt-get update && apt-get install -y \
    net-tools \
    iputils-ping \
    iproute2 \
    tcpdump \
    && rm -rf /var/lib/apt/lists/*

# requirements.txt 복사 및 의존성 설치
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 프로젝트 파일 복사
COPY . /app

# Python 경로 설정
ENV PYTHONPATH=/app

# 포트 노출 (서버: 9999, 웹 클라이언트: 5000)
EXPOSE 9999 5000

# 기본 명령어 (서버 또는 클라이언트 선택 가능)
CMD ["python", "-m", "server.server"]
