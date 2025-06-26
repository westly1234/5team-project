# chatbot/coupang_api.py

import hmac
import hashlib
import os
from datetime import datetime, timezone
import requests
import json
from urllib.parse import quote, urlparse
import traceback

# .env 파일에서 키를 안전하게 로드
ACCESS_KEY = os.getenv('COUPANG_ACCESS_KEY')
SECRET_KEY = os.getenv('COUPANG_SECRET_KEY')
DOMAIN = "api-gateway.coupang.com"

def generate_authorization(method, path, secret_key, access_key):
    """
    다양한 API 경로와 메서드에 대응할 수 있도록 수정된 인증 헤더 생성기
    """
    datetime_utc = datetime.now(timezone.utc)
    request_time = datetime_utc.strftime('%y%m%d') + 'T' + datetime_utc.strftime('%H%M%S') + 'Z'
    
    parts = urlparse(path)
    # 서명 생성 (요청시간 + 메서드 + 경로 + 쿼리스트링)
    message = request_time + method.upper() + parts.path + parts.query
    signature = hmac.new(bytes(secret_key, 'utf-8'), message.encode('utf-8'), hashlib.sha256).hexdigest()

    return f"CEA algorithm=HmacSHA256, access-key={access_key}, signed-date={request_time}, signature={signature}"

def search_products(keyword, limit=3):
    """
    상품 검색 API를 호출하여 상품 목록을 가져오는 함수
    """
    PATH = f"/v2/providers/affiliate_open_api/apis/openapi/products/search?keyword={quote(keyword)}&limit={limit}"
    
    authorization_header = generate_authorization("GET", PATH, SECRET_KEY, ACCESS_KEY)
    headers = {"Authorization": authorization_header, "Content-Type": "application/json;charset=UTF-8"}
    full_url = f"https://{DOMAIN}{PATH}"
    
    try:
        response = requests.request("GET", full_url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("data", {}).get("productData", [])
    except Exception as e:
        print(f"ERROR: 쿠팡 상품 검색 API 호출 실패 - {e}")
        return []

# [✨ 수정 적용] subId가 추가된 create_deeplinks 함수
def create_deeplinks(product_urls):
    """
    여러 개의 상품 URL을 받아 파트너스 링크로 변환하는 함수 (subId 추가)
    """
    PATH = "/v2/providers/affiliate_open_api/apis/openapi/v1/deeplink"
    
    request_body_dict = {
        "coupangUrls": product_urls,
        "subId": "ai-chatbot"  # 수익 추적을 위한 sub-ID
    }
    request_body_json = json.dumps(request_body_dict, separators=(',', ':'))
    
    authorization_header = generate_authorization("POST", PATH, SECRET_KEY, ACCESS_KEY)
    headers = {"Authorization": authorization_header, "Content-Type": "application/json;charset=UTF-8"}
    full_url = f"https://{DOMAIN}{PATH}"
    
    try:
        response = requests.request("POST", full_url, headers=headers, data=request_body_json, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("data", [])
    except Exception as e:
        print(f"ERROR: 쿠팡 딥링크 생성 API 호출 실패 - {e}")
        if 'response' in locals() and hasattr(response, 'text'):
            print(f"DEBUG: API 응답 내용: {response.text}")
        return []

# [✅ 복구] views.py에서 필요로 하는 get_coupang_recommendations 함수
# chatbot/coupang_api.py

# ... (파일 상단의 다른 함수들은 그대로 둡니다. search_products, create_deeplinks 등) ...

# [🔥 최종 수정] get_coupang_recommendations 함수를 아래 코드로 통째로 교체해주세요.
def get_coupang_recommendations(keyword, limit=3):
    if not ACCESS_KEY or not SECRET_KEY:
        print("ERROR: 쿠팡 파트너스 API 키가 설정되지 않았습니다.")
        return []

    # 1. 파트너스용 상품 검색 API를 호출합니다.
    products = search_products(keyword, limit)
    print(f"📦 검색된 상품 수: {len(products)}")

    # 2. 검색 결과가 있는지 확인합니다.
    if not products:
        # [비상 계획] 검색된 상품이 없을 경우, 검색 결과 페이지로 가는 파트너스 링크를 생성합니다.
        # 이 경우에만 create_deeplinks가 필요합니다.
        print(f"❌ 검색된 상품 없음 → 검색 페이지 링크로 단일 추천 생성")
        search_url = f"https://www.coupang.com/np/search?q={quote(keyword)}"
        
        deeplinks_data = create_deeplinks([search_url])
        print(f"✅ (비상) 딥링크 변환 수: {len(deeplinks_data)}")

        if deeplinks_data and deeplinks_data[0].get('shortenUrl'):
            return [{
                "product_name": f"'{keyword}' 전체 검색 결과 보기",
                "thumbnail_url": "/static/chatbot_images/default-product.png",
                "price": None,
                "link": deeplinks_data[0]['shortenUrl']
            }]
        else:
            # 비상 계획마저 실패하면 빈 리스트 반환
            return []

    # 3. [핵심] 검색된 상품이 있다면, 불필요한 딥링크 변환 없이 URL을 바로 사용합니다.
    recommendations = []
    for product in products:
        # product.get('productUrl') 자체가 이미 파트너스 링크입니다.
        partner_link = product.get("productUrl")
        
        if partner_link:
            recommendations.append({
                "product_name": product.get("productName"),
                "thumbnail_url": product.get("productImage"),
                "price": product.get("productPrice"),
                "link": partner_link, # 바로 사용!
            })
    
    print(f"✅ 상품 {len(recommendations)}개 추천 목록 생성 완료.")
    return recommendations