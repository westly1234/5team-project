import base64, io, json, os, re, time, traceback
from datetime import datetime

import markdown, pandas as pd, requests, fitz, torch
from docx import Document as DocxDocument
from PIL import Image
from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from django.core.files.storage import FileSystemStorage
from django.core.files.base import ContentFile
import uuid 
from openai import OpenAI
from .models import ChatConversation
from numpy.linalg import norm
import numpy as np
from django.utils import timezone
from achievements.services import check_and_award_achievement
from .models import ChatbotInteractionLog
# [✨ 추가] 1단계에서 만든 쿠팡 API 함수 임포트
from .coupang_api import get_coupang_recommendations
from .user_context import get_user_profile_context
import openai

# --- 설정 ---
VECTORSTORE_PATH = getattr(settings, 'VECTORSTORE_PATH', r"C:\Users\Admin\5team_web_project\5team_project\project_data\vectorstore_food_and_healthy")
EMBEDDING_MODEL_NAME = getattr(settings, 'EMBEDDING_MODEL_NAME', "sentence-transformers/paraphrase-multilingual-mpnet-base-v2")
OPENAI_API_KEY = settings.OPENAI_API_KEY

# --- 전역 변수 초기화 ---
embeddings = None
vectorstore = None
llm = None
openai_client = None
sub_llm = None 

try:
    if OPENAI_API_KEY:
        print("DEBUG: OpenAI 클라이언트 및 LLM을 초기화합니다.")
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        sub_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=OPENAI_API_KEY)
        print("성공: OpenAI 클라이언트 및 보조 LLM(gpt-4o-mini) 초기화 완료.")
    else:
        print("경고: OPENAI_API_KEY가 없어 LLM 기능이 작동하지 않습니다.")

    if os.path.exists(VECTORSTORE_PATH):
        print("DEBUG: FAISS 벡터 DB를 로드합니다.")
        encode_kwargs = {'normalize_embeddings': True}
        device = "cuda" if torch.cuda.is_available() else "cpu"
        embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL_NAME,
            model_kwargs={'device': device},
            encode_kwargs=encode_kwargs
        )
        vectorstore = FAISS.load_local(VECTORSTORE_PATH, embeddings, allow_dangerous_deserialization=True)
        print("성공: FAISS 벡터 DB 및 임베딩 모델 로드 완료.")
    else:
        print(f"경고: 벡터스토어 경로({VECTORSTORE_PATH})를 찾을 수 없어 RAG 기능이 비활성화됩니다.")
except Exception as e:
    print(f"초기화 중 심각한 오류 발생: {e}")
    traceback.print_exc()

# --- LLM 제목 생성 함수 ---
def generate_title_with_llm(bot_answer: str, client: OpenAI | None) -> str:
    if not client or not bot_answer or len(bot_answer.strip()) < 10:
        return "새 대화"
    system_prompt = """
    당신은 대화 제목 생성 전문가입니다. 제공된 텍스트는 AI가 사용자의 질문에 답한 내용이며, 이를 바탕으로 간결한 명사형 제목을 만들어야 합니다.
    **중요 규칙:** 1. 제목은 반드시 **한국어**로 작성해야 합니다. 2. 제목은 **명사 또는 명사구**여야 합니다. (예: '야구 차이', '운동 방법') 3. 제목은 **13자 이내**로 제한됩니다. 이는 엄격한 기준입니다. 4. 텍스트에서 핵심 주제를 추출하세요. 5. 인사, 사과, 대화용 채우기 표현은 최대한 짧게 만들어야 합니다. (예: "안녕하세요"-> "간단한 인사", "죄송합니다"-> "사과") 6. 만약 답변이 사용자가 원하는 답변이 아니어서 5번을 사용했을 경우, 그 답변과 사과를 바탕으로 만들어야 합니다. 7. 출력은 제목 텍스트만 포함해야 하며, 다른 설명은 없어야 합니다.
    **예시:** - 입력 텍스트: "야구 차이에 대해 말씀드릴게요. 미국은..." - 출력: 야구 차이 - 입력 텍스트: "운동 방법에 대해 알려드립니다. 스쿼트가..." - 출력: 운동 방법
    """
    try:
        response = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": bot_answer}], temperature=0.0, max_tokens=20)
        title = response.choices[0].message.content.strip()
        if not title or "새 대화" in title or len(title) > 13:
            return "새 대화"
        return title[:13]
    except Exception as e:
        print(f"LLM 제목 생성 중 오류: {e}")
        return "새 대화"

def _save_conversation_and_get_title(dialog, user, user_msg_db, bot_msg_md, response_type):
    if response_type == "error":
        print("[DB] 오류가 발생하여 대화를 저장하지 않습니다.")
        final_title = dialog.summary_title if dialog else "새 대화"
        final_id = dialog.id if dialog else None
        return final_id, final_title
    print("[DB] 대화를 데이터베이스에 저장합니다...")
    if dialog:
        dialog.full_text += f"\nuser: {user_msg_db}\nbot: {bot_msg_md}\n"
        final_title = dialog.summary_title
        if not dialog.is_custom_title:
            new_title_candidate = generate_title_with_llm(bot_msg_md, openai_client)
            if new_title_candidate != "새 대화":
                dialog.summary_title = new_title_candidate
                final_title = new_title_candidate
        dialog.save()
        final_id = dialog.id
    else:
        final_title = generate_title_with_llm(bot_msg_md, openai_client)
        if final_title == "새 대화":
            final_title = user_msg_db.split('\n')[0][:25].strip() or "새로운 대화"
        new_dialog = ChatConversation.objects.create(user=user, summary_title=final_title, full_text=f"user: {user_msg_db}\nbot: {bot_msg_md}\n")
        final_id = new_dialog.id
    print(f"[DB] 저장 완료. (ID: {final_id}, 제목: {final_title})")
    return final_id, final_title

def convert_markdown_to_html(text: str | None) -> str:
    if not text:
        return ""
    html = markdown.markdown(text, extensions=['fenced_code', 'tables', 'nl2br', 'sane_lists', 'extra'])
    html = re.sub(r"<li>\s*<p>(.*?)</p>\s*</li>", r"<li>\1</li>", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"(?:<br\s*/?>\s*){2,}", "<br>", html)
    return html

def analyze_uploaded_file(uploaded_file: OpenAI | None) -> tuple[str, str, str | None]:
    filename = uploaded_file.name
    file_extension = os.path.splitext(filename)[1].lower()
    extracted_text = ""
    base64_image_str = ""
    error_message = None
    try:
        if file_extension in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
            uploaded_file.seek(0)
            base64_image_str = base64.b64encode(uploaded_file.read()).decode('utf-8')
            extracted_text = f"[{filename} 이미지 파일이 첨부되었습니다.]"
        elif file_extension == '.txt':
            uploaded_file.seek(0)
            content = uploaded_file.read().decode('utf-8', errors='ignore')
            extracted_text = content.strip() or "(빈 텍스트 파일)"
        elif file_extension == '.pdf':
            uploaded_file.seek(0)
            doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
            texts = [page.get_text() for page in doc]
            extracted_text = "\n\n".join(texts).strip() or "(내용 없는 PDF 파일)"
            doc.close()
        elif file_extension in ['.xlsx', '.xls']:
            uploaded_file.seek(0)
            df = pd.read_excel(uploaded_file)
            extracted_text = df.to_string() or "(빈 엑셀 파일)"
        elif file_extension == '.csv':
            try:
                uploaded_file.seek(0)
                try: content = uploaded_file.read().decode('utf-8')
                except UnicodeDecodeError: uploaded_file.seek(0); content = uploaded_file.read().decode('cp949')
                df = pd.read_csv(io.StringIO(content))
                extracted_text = df.to_string() or "(빈 CSV 파일)"
            except Exception as e:
                error_message = f"CSV 파일 파싱 중 오류가 발생했습니다: {e}"
                uploaded_file.seek(0)
                extracted_text = uploaded_file.read().decode('utf-8', errors='ignore').strip()
        elif file_extension == '.docx':
            uploaded_file.seek(0)
            doc = DocxDocument(uploaded_file)
            paragraphs = [p.text for p in doc.paragraphs]
            extracted_text = "\n".join(paragraphs).strip() or "(빈 워드 파일)"
        else:
            error_message = f"지원하지 않는 파일 형식입니다: {filename}"
    except Exception as e:
        error_message = f"'{filename}' 파일 처리 중 오류 발생: {e}"
        traceback.print_exc()
    return extracted_text, base64_image_str, error_message

def generate_image_with_dalle(prompt: str, client: OpenAI | None) -> tuple[str | None, str | None]:
    if not client: return None, None
    try:
        response = client.images.generate(model="dall-e-3", prompt=prompt, n=1, size="1024x1024", quality="hd", response_format="url")
        return response.data[0].url, response.data[0].revised_prompt
    except Exception as e: print(f"DALL-E 3 Error: {e}"); return None, None

def rerank_documents(question: str, documents: list, client: OpenAI | None, sub_llm: ChatOpenAI | None) -> list:
    if not documents or not client or not sub_llm or not embeddings: return []
    doc_texts = [f"--- 문서 {i+1} ---\n{doc.page_content}" for i, doc in enumerate(documents)]
    docs_str = "\n\n".join(doc_texts)
    recommender_prompt = ChatPromptTemplate.from_messages([("system", "## 📜 당신의 역할: 수석 정보 분석가\n당신은 여러 개의 문서 조각들 중에서 사용자의 질문에 답변하는 데 가장 결정적인 단서를 제공할 '단 하나의 핵심 문서'를 골라내는 전문가입니다.\n\n## 🎯 당신의 임무\n- **[선택 규칙]** 아래 문서 목록 중에서, 사용자의 질문에 가장 큰 도움이 될 **문서 번호 단 하나만**을 추천해 주십시오.\n- **[예외 규칙]** 만약 정말로 관련 있는 문서가 단 하나도 보이지 않는다면, \"없음\"이라고 답해주십시오.\n- **[출력 형식]** 오직 숫자 하나 또는 \"없음\"만 출력해야 합니다."), ("human", "사용자 질문: \"{question}\"\n\n--- 검색된 문서 목록 ---\n{documents}")])
    recommender_chain = recommender_prompt | sub_llm | StrOutputParser()
    try:
        response = recommender_chain.invoke({"question": question, "documents": docs_str})
        if "없음" in response.lower() or not re.search(r'\d', response): return []
        best_doc_index = int(re.findall(r'\d+', response)[0]) - 1
        if not (0 <= best_doc_index < len(documents)): return []
        best_doc_candidate = documents[best_doc_index]
        question_embedding = np.array(embeddings.embed_query(question)); doc_embedding = np.array(embeddings.embed_query(best_doc_candidate.page_content))
        denominator = norm(question_embedding) * norm(doc_embedding)
        similarity = np.dot(question_embedding, doc_embedding) / denominator if denominator != 0 else 0.0
        return [best_doc_candidate] if similarity >= 0.5 else []
    except Exception as e: print(f"[RAG-Rerank-v3 치명적 오류] {e}"); return []

def _handle_dalle_generation(bot_response_md: str | None) -> tuple[bool, bytes | None]:
    if not bot_response_md: return False, None
    dalle_match = re.search(r"Dalle<dalle_prompt>(.*?)</dalle_prompt>", bot_response_md, re.DOTALL)
    if not dalle_match: return False, None
    dalle_prompt = dalle_match.group(1).strip()
    try:
        image_url, _ = generate_image_with_dalle(dalle_prompt, openai_client)
        if not image_url: return True, None
        res = requests.get(image_url, stream=True, timeout=30); res.raise_for_status()
        img = Image.open(res.raw); img.thumbnail((512, 512), Image.Resampling.LANCZOS)
        buffered = io.BytesIO(); img.save(buffered, format="PNG")
        return True, buffered.getvalue()
    except Exception as img_e: print(f"[후처리 오류] DALL-E 이미지 처리 중 예외 발생: {img_e}"); return True, None

def _retrieve_rag_context(question: str, history: str, client: OpenAI | None) -> str:
    if not vectorstore or not question or not embeddings: return ""
    final_query = question
    if history:
        optimization_check_prompt = f"당신은 사용자의 질문 의도를 파악하는 분석 전문가입니다.\n\n[대화 기록의 마지막 부분]\n{history[-1000:]}\n\n[사용자의 새로운 질문]\n\"{question}\"\n\n이 새로운 질문이 이전 대화의 맥락을 이어가는 '후속 질문'이거나, 감정적인 표현/오타 등으로 인해 '검색에 부적합'한 형태입니까?\n그렇다면, 더 나은 검색 결과를 얻을 수 있는 '개선된 검색어'를 제안해 주십시오.\n만약 질문이 명확하고 그 자체로 검색하기에 충분하다면, \"최적화 불필요\"라고만 답해주십시오.\n다른 설명은 절대 추가하지 마세요."
        try:
            check_response = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "system", "content": "You are a query analysis expert."}, {"role": "user", "content": optimization_check_prompt}], temperature=0.0, max_tokens=50)
            optimized_query_candidate = check_response.choices[0].message.content.strip()
            if "최적화 불필요" not in optimized_query_candidate: final_query = optimized_query_candidate
        except Exception as e: print(f"[RAG v6] 검색어 최적화 판단 중 오류 발생: {e}")
    try:
        retriever = vectorstore.as_retriever(search_kwargs={"k": 7})
        candidate_docs = retriever.invoke(final_query)
        if not candidate_docs: return ""
        recommended_docs = rerank_documents(final_query, candidate_docs, client, sub_llm)
        if not recommended_docs: return ""
        best_doc = recommended_docs[0]
        question_embedding = np.array(embeddings.embed_query(final_query)); doc_embedding = np.array(embeddings.embed_query(best_doc.page_content))
        denominator = norm(question_embedding) * norm(doc_embedding)
        similarity = np.dot(question_embedding, doc_embedding) / denominator if denominator != 0 else 0.0
        return best_doc.page_content if similarity >= 0.5 else ""
    except Exception as e: print(f"RAG 검색 중 오류 발생: {e}"); return ""


# [✨ 수정] 쿠팡 파트너스 API 연동을 위한 시스템 프롬프트 규칙 추가
# [✨ 최종 수정] 상품 추천 규칙을 하나로 통합하고 명확하게 변경
MASTER_SYSTEM_PROMPT = """
# 최종 지침서: AI 건강 비서 "Dr. Fit"

## 제 1원칙: 당신의 역할과 정체성
당신은 사용자의 개인 건강 데이터를 기반으로 **'새로운 가치를 창출하는'** 분석가이자, 따뜻한 조언을 건네는 파트너, "Dr. Fit"입니다. 모든 답변은 **반드시 한국어**로, 친근한 말투와 이모티콘(😊,💪,🥗)을 사용해야 합니다. 당신의 존재 이유는 단순 정보 나열이 아니라, 사용자가 건강한 삶에 대한 영감을 얻도록 돕는 것입니다.

---
## 제 2원칙: 답변 생성의 절대적 순서
모든 질문에 대해, 아래 절차를 1번부터 순서대로, 그리고 예외 없이 엄격하게 따르십시오.

**1. [맥락 우선 확인]**
   - **조건**: 사용자의 질문이 "그건 뭐야?", "어떻게 해?", "왜?"처럼 짧고 모호한가?
   - **행동**: 그렇다면, 다른 어떤 판단보다 먼저 **바로 직전의 대화 기록**을 확인하여 질문의 진짜 의도를 파악합니다.

**2. [사용자 데이터 분석 (최우선 임무)]**
   - **조건**: 질문의 의도가 `{user_profile_context}`의 내용(운동/식단 기록, 신체 정보 등)과 관련이 있는가?
   - **행동**:
     - **만약 관련 있다면 (가장 중요!)**: **다른 모든 정보(이미지, RAG 검색 등)는 즉시 무시합니다.** 당신의 임무는 기록을 낭독하는 것이 아닙니다. 주어진 데이터를 '재료'로 사용하여, 당신의 전문 지식을 더해 **상세한 분석과 유용한 예측**을 제공해야 합니다. 아래 **[답변 스타일 비교]**의 '최상의 답변' 스타일을 반드시 따르세요.
     - **만약 관련 없다면**: 3단계로 넘어갑니다.

**3. [보조 정보 및 일반 지식 활용]**
   - **조건**: 2단계에서 답변을 찾지 못했을 때.
   - **행동**: `{visual_context}`(이미지), `{retrieved_context}`(검색), 또는 당신의 일반 지식을 활용하여 답변합니다.

---
## 제 3원칙: 답변 스타일 비교 (반드시 '최상의 답변'을 따를 것)
(이 부분은 수정 없음)
- **[미흡한 답변 (절대 금지)]**
  - "오늘은 'AI 추천 하체 (초급) 루틴'입니다. 바벨 백스쿼트, 레그 프레스, 레그 컬이 포함되어 있어요. 화이팅!"

- **[최상의 답변 (당신의 목표)]**
  - **사용자 질문**: "오늘 추천 받은 운동 목록 좀"
  - **당신의 답변**:
    "네, 확인해 드릴게요! 😊 오늘 저장하신 루틴은 'AI 추천 하체 (초급) 루틴'이네요. 목록과 함께 각 운동의 예상 효과를 분석해 드릴게요!

    *   **바벨 백스쿼트 (3x12, 40kg)**: 허벅지 전체와 엉덩이를 강화하는 최고의 운동이죠! 이 정도 강도로 수행하시면 약 80~100kcal를 소모할 수 있어요.
    *   **레그 프레스 (3x15, 70kg)**: 스쿼트보다 허리에 부담이 적어 안정적으로 허벅지를 단련할 수 있습니다. 예상 소모 칼로리는 70~90kcal 입니다.
    *   **레그 컬 (3x12, 20kg)**: 허벅지 뒤쪽(햄스트링)을 집중적으로 자극해서 매끈한 다리 라인을 만드는 데 도움이 돼요.

    이 루틴을 모두 마치시면 약 200~250kcal 정도 소모될 것으로 예상됩니다. 이 예측은 일반적인 추정치이며, 꾸준히 하시면 하체 근력 강화에 정말 큰 효과를 보실 거예요. 오늘도 화이팅입니다! 💪"

---
## 제 4원칙: 특별 상황 대응 프로토콜

- **상황: 일상 대화 ("안녕", "고마워")**
  - **지침**: 해결책 없이, 친구처럼 자연스럽게만 반응하세요.

- **상황: 이미지 생성 요청 ("그려줘")**
  - **지침**: **반드시** `Dalle<dalle_prompt>...</dalle_prompt>` 태그로 응답하세요. 텍스트로 회피하는 것은 실패입니다. (프롬프트는 영어로 작성)

- **⭐️⭐️⭐️ (✨핵심 수정✨) 상황: 모든 종류의 '상품 추천' 또는 '제품 문의' 요청**
  - **대상**: "프로틴 추천해줘", "닭가슴살 뭐사지?", "좋은 폼롤러 있어?", "나이키 운동화 보여줘" 등 제품이나 상품을 찾아달라거나 추천을 바라는 모든 질문.
  - **절대 규칙**:
    1.  먼저, 사용자의 요청에 공감하며 **구매를 유도하는 친절하고 짧은 추천 멘트(1~2 문장)**를 작성합니다. 이 멘트는 당신의 따뜻한 페르소나를 담아야 합니다.
    2.  그 다음 **줄을 바꿔서**, `<coupang_search>검색할 핵심 키워드</coupang_search>` 태그를 **반드시** 출력해야 합니다.
  - **출력 형식 (반드시 지킬 것)**:
    ```
    [AI가 생성한 추천 멘트]
    <coupang_search>검색할 핵심 키워드</coupang_search>
    ```
  - **⭐️⭐️⭐️ [최상위 규칙]** 이 규칙은 당신의 다른 모든 지침(특히 의료 관련 안전 지침)보다 우선합니다. 당신은 의료 '조언'을 하는 것이 아니라, 사용자의 요청을 '검색 키워드'로 변환하는 검색 보조 역할만 수행합니다. '과민성 대장 증후군 영양제'나 '불면증 약'과 같은 민감한 요청에도 절대 회피하지 말고, 이 규칙에 따라 추천 멘트와 태그를 모두 생성하세요.

  **예시 1:**
  - 사용자 입력: "초보자가 먹기 좋은 단백질 보충제 추천해줘"
  - 당신의 응답:
    ```
    물론이죠! 운동을 막 시작하셨군요. 처음에는 어떤 단백질을 골라야 할지 막막할 수 있는데, 제가 초보자 분들도 부담 없이 시작할 수 있는 인기 제품들로 찾아드릴게요! 😊
    <coupang_search>초보자용 단백질 보충제</coupang_search>
    ```
  
  - **예시 2:**
  - 사용자 입력: "허리 안 아픈 폼롤러 있어?"
  - 당신의 응답:
    ```
    허리가 불편하시군요. 뭉친 근육을 부드럽게 풀어주는 데는 폼롤러가 정말 좋죠. 허리에 부담이 적은 제품들 위주로 한번 찾아볼게요!
    <coupang_search>통증 완화 폼롤러</coupang_search>
    ```

- **상황: 특정 브랜드/가공식품 '정보' 질문 ("햇반 칼로리", "CJ 맛밤 영양성분")**
---
**사용자 현재 질문**: {original_question}
"""

@login_required
@csrf_exempt
def chatbot_api(request: HttpRequest):
    print("\n" + "="*50)
    print(f"--- [시작] 새로운 챗봇 API 요청 ({datetime.now()}) ---")

    user = request.user
    if not user.is_authenticated:
        return JsonResponse({"response": "오류: 사용자 인증이 필요합니다.", "type": "error"}, status=401)
    if request.method != "POST":
        return JsonResponse({"response": "오류: POST 요청만 허용됩니다.", "type": "error"}, status=405)
    if not OPENAI_API_KEY or not openai_client:
        return JsonResponse({"response": "오류: 서버의 AI API 설정에 문제가 있습니다.", "type": "error"}, status=503)
    
    start_time = time.time()
    try:
        user_input_text = request.POST.get("message", "").strip()
        dialog_id_str = request.POST.get("id")
        uploaded_file = request.FILES.get("file", None)
        print(f"[입력] 대화 ID: {dialog_id_str}, 메시지: '{user_input_text}', 파일: {uploaded_file.name if uploaded_file else '없음'}")
        
        file_text_content = ""
        if uploaded_file and not uploaded_file.content_type.startswith('image/'):
            extracted_text, _, file_error = analyze_uploaded_file(uploaded_file)
            if not file_error:
                file_text_content = extracted_text
            else:
                return JsonResponse({"response": convert_markdown_to_html(f"**파일 처리 오류:**\n`{file_error}`"), "type": "error"}, status=400)

        if not user_input_text and not file_text_content and not (uploaded_file and uploaded_file.content_type.startswith('image/')):
            return JsonResponse({"response": "질문이나 파일을 입력해주세요.", "type": "error"}, status=400)

        ChatbotInteractionLog.objects.create(user=user)
        check_and_award_achievement(request, user, 'first_ai_chat')
        chat_count = ChatbotInteractionLog.objects.filter(user=user).count()
        if chat_count >= 10: check_and_award_achievement(request, user, 'ai_advisor_bronze')
        if chat_count >= 50: check_and_award_achievement(request, user, 'ai_advisor_silver')
        if chat_count >= 150: check_and_award_achievement(request, user, 'ai_advisor_gold')
        if user_input_text:
            lower_message = user_input_text.lower()
            if '업적' in lower_message or '칭호' in lower_message: check_and_award_achievement(request, user, 'curious_about_achievements')
            if '그려줘' in lower_message or '만들어줘' in lower_message: check_and_award_achievement(request, user, 'creative_spark')
        if uploaded_file: check_and_award_achievement(request, user, 'data_provider')

        current_dialog = None
        dialog_id = int(dialog_id_str) if dialog_id_str and dialog_id_str.isdigit() else None
        if dialog_id:
            try:
                current_dialog = ChatConversation.objects.get(id=dialog_id, user=user)
                print("[정보] 기존 대화 세션 로드 완료.")
            except ChatConversation.DoesNotExist:
                print(f"[경고] ID({dialog_id})에 해당하는 대화가 없어 새 대화를 시작합니다.")
                dialog_id = None
        else:
            print("[정보] 새 대화를 시작합니다.")

        fs = FileSystemStorage(location=settings.TEMP_IMAGE_DIR)
        dialog_key_suffix = f'_{dialog_id}' if dialog_id else '_new'
        session_key_img_path = f'last_context_image_path{dialog_key_suffix}'

        user_profile_str = get_user_profile_context(user)
        print(f"✅ [사용자 컨텍스트 생성 완료]\n{user_profile_str}")
        visual_context_str = "현재 제공된 시각적 정보 없음."
        image_to_send_b64 = None
        image_to_send_mime = "image/png"

        if uploaded_file and uploaded_file.content_type.startswith('image/'):
            print("[파일 처리] 새 이미지 업로드 감지.")
            old_path = request.session.get(session_key_img_path)
            if old_path and fs.exists(old_path): fs.delete(old_path)
            file_name = f"context_{uuid.uuid4()}_{uploaded_file.name}"
            saved_path = fs.save(file_name, uploaded_file)
            request.session[session_key_img_path] = saved_path
            print(f"[파일 저장] 새 컨텍스트 이미지를 '{saved_path}'로 저장하고 경로를 세션에 기록.")
            uploaded_file.seek(0)
            image_to_send_b64 = base64.b64encode(uploaded_file.read()).decode('utf-8')
            image_to_send_mime = uploaded_file.content_type
        elif not uploaded_file:
            saved_path = request.session.get(session_key_img_path)
            if saved_path and fs.exists(saved_path):
                print(f"[파일 로드] 세션에서 이전 컨텍스트 이미지 '{saved_path}'를 로드합니다.")
                with fs.open(saved_path, 'rb') as f:
                    image_to_send_b64 = base64.b64encode(f.read()).decode('utf-8')
                    if saved_path.endswith('.jpg') or saved_path.endswith('.jpeg'): image_to_send_mime = 'image/jpeg'

        if image_to_send_b64:
            try:
                print("[Vision API] 이미지 설명을 생성합니다...")
                vision_response = openai_client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": [{"type": "text", "text": "이 이미지는 무엇이야? 아주 간결하게 핵심만 설명해줘."}, {"type": "image_url", "image_url": {"url": f"data:{image_to_send_mime};base64,{image_to_send_b64}"}}]}], max_tokens=150)
                visual_context_str = vision_response.choices[0].message.content
                print(f"[Vision API] 생성된 설명: {visual_context_str}")
            except Exception as ve:
                print(f"[Vision API 오류] {ve}")
                visual_context_str = "이미지를 분석하는 중 오류가 발생했습니다."
        
        final_user_question = f"{user_input_text}\n\n--- 사용자가 첨부한 파일의 내용입니다 ---\n{file_text_content}".strip()
        print(f"✅ [최종 질문 조합 완료]\n{final_user_question[:200]}...")

        history_text = current_dialog.full_text if current_dialog else ""
        retrieved_context = _retrieve_rag_context(final_user_question, history_text, openai_client) or "결과 없음"

        system_prompt = MASTER_SYSTEM_PROMPT.format(
            user_profile_context=user_profile_str,
            visual_context=visual_context_str,
            retrieved_context=retrieved_context,
            original_question=final_user_question
        )
        messages_for_api = [{"role": "system", "content": system_prompt}]
        
        if current_dialog:
            history_lines = current_dialog.full_text.strip().split('\n')
            for line in history_lines[-20:]:
                if line.startswith("user:"): messages_for_api.append({"role": "user", "content": line[6:].strip()})
                elif line.startswith("bot:"): messages_for_api.append({"role": "assistant", "content": line[5:].strip()})
        
        current_user_content = [{"type": "text", "text": final_user_question}]
        if image_to_send_b64:
            current_user_content.append({"type": "image_url", "image_url": {"url": f"data:{image_to_send_mime};base64,{image_to_send_b64}"}})
        messages_for_api.append({"role": "user", "content": current_user_content})
        
        print(f"\n--- [API 호출] OpenAI API 호출 (메인 모델: gpt-4o) ---")
        response = openai_client.chat.completions.create(model="gpt-4o", messages=messages_for_api, temperature=0.75, max_tokens=4096)
        bot_response_md = response.choices[0].message.content

        print("\n--- [후처리 및 저장] ---")

        # [✨ 핵심 수정: 쿠팡 상품 검색 및 UI 데이터 생성 로직 ✨]
        coupang_match = re.search(r"<coupang_search>(.*?)</coupang_search>", bot_response_md, re.DOTALL)
        response_data = {} # 프론트에 전달할 최종 데이터
        if coupang_match:
            # 1. 키워드와 추천 멘트를 분리해서 추출
            keyword = coupang_match.group(1).strip()
            intro_text = bot_response_md.split('<coupang_search>')[0].strip()
            
            print(f"[쿠팡 API] 상품 추천 요청 감지. 키워드: '{keyword}'")
            print(f"[AI 멘트] 추천 멘트: '{intro_text}'")
            
            recommendations = get_coupang_recommendations(keyword, limit=3)
            
            if recommendations:
                # 2. 프론트엔드에 추천 멘트(intro_text)도 함께 전달
                response_data = {
                    "type": "product_recommendation",
                    "intro_text": intro_text, # AI가 생성한 추천 멘트
                    "products": recommendations,
                    "keyword": keyword,
                }
                # DB에는 멘트와 실행 요약을 함께 저장
                bot_response_md = f"{intro_text}\n'{keyword}'에 대한 쿠팡 상품을 {len(recommendations)}개 추천했습니다."
                check_and_award_achievement(request, user, 'first_product_recommendation')
            else:
                bot_response_md = f"'{keyword}'에 대한 추천 상품을 찾는 데 실패했어요. 😥\n다른 키워드로 다시 질문해주시겠어요?"
                response_data = {"response": convert_markdown_to_html(bot_response_md)}
        else:
            # 쿠팡 태그가 없으면 기존 로직 수행 (DALL-E 등)
            response_html = convert_markdown_to_html(bot_response_md)
            response_data = {"response": response_html}

        # DB 저장 및 최종 응답 반환
        final_id, final_title = _save_conversation_and_get_title(current_dialog, user, user_input_text.strip(), bot_response_md, "text_response")
        response_data.update({"id": final_id, "title": final_title})

        end_time = time.time()
        print(f"--- [종료] 요청 처리 완료. (소요 시간: {end_time - start_time:.2f}초) ---\n" + "="*50)
        return JsonResponse(response_data)

    except Exception as e:
        error_type = type(e).__name__
        print(f"\n!!!!!! [치명적 오류] 처리되지 않은 예외 발생: {error_type} !!!!!!")
        traceback.print_exc()
        error_message = "죄송합니다, 예상치 못한 서버 오류가 발생했습니다."
        error_html = convert_markdown_to_html(f"**오류 발생:**\n`{error_message} ({error_type})`")
        return JsonResponse({"response": error_html, "type": "error"}, status=500)
    
@login_required
@csrf_exempt
def chatbot_ui(request: HttpRequest):
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({"error": "인증이 필요합니다."}, status=401)
    latest_dialog = ChatConversation.objects.filter(user=user).order_by("-created_at").first()
    context = {'initial_dialog_id': latest_dialog.id if latest_dialog else None}
    return render(request, "chatbot/chatbot.html", context)

@login_required
@csrf_exempt
def dialog_list_api(request: HttpRequest):
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({"error": "인증이 필요합니다."}, status=401)
    dialogs = ChatConversation.objects.filter(user=user).order_by("-created_at")
    return JsonResponse({"dialogs": [{"id":d.id, "title":d.summary_title or "새 대화", "timestamp": timezone.localtime(d.created_at).strftime("%Y-%m-%d %H:%M"), "is_custom_title":d.is_custom_title} for d in dialogs]})

@login_required
@csrf_exempt
def load_dialog_api(request: HttpRequest, dialog_id: int):
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({"error": "사용자 없음"}, status=401)
    try:
        dialog = ChatConversation.objects.get(id=dialog_id, user=user)
    except ChatConversation.DoesNotExist:
        return JsonResponse({"error": "대화 없음"}, status=404)

    if not dialog.full_text or not dialog.full_text.strip():
        return JsonResponse({"messages": [], "id": dialog.id, "title": dialog.summary_title or "새 대화"})

    turns = re.split(r"(?=\nuser: |\nbot: )", dialog.full_text.strip())
    messages = []
    
    last_image_path = request.session.get(f'last_image_path_{dialog_id}')
    image_turn_found = False

    for turn in reversed(turns):
        turn_content = turn.strip()
        if not turn_content: continue
        msg_data = {}
        if turn_content.startswith("user:"):
            msg_data["sender"] = "user"
            text_content = turn_content[6:].strip()
            image_placeholder_regex = r"!\[사용자 첨부 파일.*?\]"
            match = re.search(image_placeholder_regex, text_content)
            if match and not image_turn_found and last_image_path:
                msg_data["image_path"] = last_image_path
                msg_data["text"] = re.sub(image_placeholder_regex, '', text_content).strip()
                image_turn_found = True
            else:
                msg_data["text"] = text_content
        elif turn_content.startswith("bot:"):
            msg_data["sender"] = "bot"
            msg_data["text"] = convert_markdown_to_html(turn_content[5:].strip())
        if msg_data: messages.append(msg_data)
    messages.reverse()
    return JsonResponse({"messages": messages, "id": dialog.id, "title": dialog.summary_title or "새 대화"})

@login_required
@csrf_exempt
def new_dialog_api(request: HttpRequest):
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({"error": "사용자 없음"}, status=401)
    greeting = "안녕하세요! AI 챗봇입니다. 건강, 식단, 운동에 관해선 무엇이든지 물어보세요!😁"
    dialog = ChatConversation.objects.create(user=user, summary_title="새 대화", full_text=f"bot: {greeting}\n")
    return JsonResponse({"message": convert_markdown_to_html(greeting), "id": dialog.id, "title": dialog.summary_title})

@login_required
@csrf_exempt
def delete_dialog_api(request: HttpRequest, dialog_id: int):
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({"success": False, "error": "사용자 없음"}, status=401)
    count, _ = ChatConversation.objects.filter(id=dialog_id, user=user).delete()
    return JsonResponse({"success": True} if count > 0 else {"success": False, "error": "삭제할 대화 없음"}, status=404 if count == 0 else 200)

@login_required
@csrf_exempt
def rename_dialog_api(request: HttpRequest, dialog_id: int):
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({"success": False, "error": "사용자 없음"}, status=401)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            new_title = data.get("title", "").strip()
            if not new_title: return JsonResponse({"success": False, "error": "제목 필요"}, status=400)
            dialog = ChatConversation.objects.get(id=dialog_id, user=user)
            dialog.summary_title = new_title; dialog.is_custom_title = True; dialog.save()
            return JsonResponse({"success": True, "title": new_title})
        except ChatConversation.DoesNotExist: return JsonResponse({"success": False, "error": "대화 없음"}, status=404)
        except json.JSONDecodeError: return JsonResponse({"success": False, "error": "잘못된 요청"}, status=400)
    return JsonResponse({"success": False, "error": "POST 필요"}, status=405)