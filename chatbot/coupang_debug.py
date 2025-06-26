import hmac
import hashlib
import os
from datetime import datetime, timezone
import requests
import json
from urllib.parse import quote, urlparse

# ==============================================================================
# ✨ 3단계: 여기에 자신의 ACCESS KEY와 SECRET KEY를 직접 입력해주세요.
# (쌍따옴표 안에 정확하게 붙여넣기. 앞뒤 공백이 없는지 확인!)
# ==============================================================================
ACCESS_KEY = "4df334c8-4e15-4e0e-b95f-f8ade5becdb5"
SECRET_KEY = "58c4fc31cfdf4195d336452cdf024c5452b3ae58"

# ==============================================================================

# API 요청 정보
REQUEST_METHOD = "POST"
DOMAIN = "api-gateway.coupang.com"
PATH = "/v2/providers/affiliate_open_api/apis/openapi/v1/deeplink"

def generate_hmac_signature():
    """
    [✨ 최종 수정 - 공식 문서 헤더 포맷 100% 일치]
    Coupang Partners API HMAC-SHA256 인증 헤더를 생성합니다.
    - Authorization 헤더 포맷을 "CEA algorithm=..., access-key=..." 형식으로 변경
    """
    datetime_utc = datetime.now(timezone.utc)
    request_time = datetime_utc.strftime('%y%m%d') + 'T' + datetime_utc.strftime('%H%M%S') + 'Z'
    
    parts = urlparse(PATH)
    path = parts.path
    query = parts.query
            
    # 서명 생성 로직은 동일
    message = request_time + REQUEST_METHOD + path + query
    signature = hmac.new(bytes(SECRET_KEY, 'utf-8'), message.encode('utf-8'), hashlib.sha256).hexdigest()

    # 디버깅 출력 (이전과 동일)
    print("--- 🔑 서명 생성 과정 디버깅 ---")
    print(f"1. 요청 시간 (UTC): {request_time}")
    print(f"2. HTTP 메서드: {REQUEST_METHOD}")
    print(f"3. 요청 경로: {path}")
    print(f"4. 쿼리 스트링: {query}")
    print(f"5. 서명 대상 문자열 (Message): '{message}'")
    print(f"6. 생성된 서명 (Signature): {signature}")
    print("---------------------------------")
    
    # [핵심 수정] 최종 인증 헤더 문자열 포맷을 공식 문서와 완벽하게 일치시킴
    return f"CEA algorithm=HmacSHA256, access-key={ACCESS_KEY}, signed-date={request_time}, signature={signature}"

# (파일의 나머지 부분은 그대로 둡니다)

def test_coupang_api():
    """독립적으로 쿠팡 API를 테스트하는 함수"""
    if ACCESS_KEY == "여기에_발급받은_ACCESS_KEY를_입력하세" or SECRET_KEY == "여기에_발급받은_SECRET_KEY를_입력하세요":
        print("\n\n❌ 오류: 스크립트의 ACCESS_KEY와 SECRET_KEY를 먼저 입력해주세요.")
        return

    print(f"\nAPI 테스트를 시작합니다... (Access Key: ...{ACCESS_KEY[-4:]})")
    
    keyword_to_search = "유당불내증 프로틴"
    encoded_keyword = quote(keyword_to_search)
    search_url = f"https://www.coupang.com/np/search?q={encoded_keyword}"
    
    request_body_dict = {"coupangUrls": [search_url]}
    request_body_json = json.dumps(request_body_dict, separators=(',', ':'))
    
    authorization_header = generate_hmac_signature()
    
    headers = {
        "Authorization": authorization_header,
        "Content-Type": "application/json;charset=UTF-8",
    }
    
    full_url = f"https://{DOMAIN}{PATH}"

    print("\n--- 🚀 실제 API 요청 정보 ---")
    print(f"요청 URL: {full_url}")
    print("요청 헤더 (Authorization):", headers["Authorization"])
    print("요청 본문 (Body):", request_body_json)
    print("----------------------------\n")

    try:
        response = requests.request("POST", full_url, headers=headers, data=request_body_json, timeout=10)
        
        print(f"--- 📈 API 응답 결과 ---")
        print(f"Status Code: {response.status_code}")
        print("Response Body:")
        # JSON 응답을 예쁘게 출력
        try:
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        except json.JSONDecodeError:
            print(response.text)
        print("-----------------------\n")

        if response.status_code == 200:
            print("✅ 인증 성공! API 호출이 정상적으로 완료되었습니다.")
        else:
            print("❌ 인증 실패! 위의 디버깅 정보와 에러 메시지를 확인해주세요.")

    except Exception as e:
        print(f"스크립트 실행 중 예외 발생: {e}")

# 스크립트 실행
if __name__ == "__main__":
    test_coupang_api()