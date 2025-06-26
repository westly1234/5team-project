# chatbot/keyword_extractor.py
import openai

def extract_keyword(user_input):
    prompt = f"""
    다음 문장에서 가장 중요한 제품 관련 키워드 하나만 추출해서 알려줘.
    문장: "{user_input}"
    출력 형식: 키워드만 한 단어 또는 두 단어로.

    예시:
    - "유당불내증 때문에 먹을 수 있는 단백질 추천해줘" ➜ 유당불내증 프로틴
    - "피부에 좋은 비타민 좀 추천해줘" ➜ 피부 비타민
    - "요즘 여름에 인기 많은 반팔 뭐 있어?" ➜ 여름 반팔
    """

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5
    )
    keyword = response.choices[0].message.content.strip()
    return keyword
