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

from achievements.services import check_and_award_achievement
from .models import ChatbotInteractionLog

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
        # llm 변수는 현재 직접 사용되지 않으므로, 필요 시 다시 활성화할 수 있도록 주석 처리합니다.
        # llm = ChatOpenAI(model="gpt-4o", temperature=0.3, openai_api_key=OPENAI_API_KEY)
        sub_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=OPENAI_API_KEY)
        print("성공: OpenAI 클라이언트 및 보조 LLM(gpt-4o-mini) 초기화 완료.")
    else:
        print("경고: OPENAI_API_KEY가 없어 LLM 기능이 작동하지 않습니다.")

    if os.path.exists(VECTORSTORE_PATH):
        print("DEBUG: FAISS 벡터 DB를 로드합니다.")
        # device 설정을 HuggingFaceEmbeddings의 encode_kwargs로 이동하는 것이 더 표준적인 방법입니다.
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

    **중요 규칙:**
    1. 제목은 반드시 **한국어**로 작성해야 합니다.
    2. 제목은 **명사 또는 명사구**여야 합니다. (예: '야구 차이', '운동 방법')
    3. 제목은 **13자 이내**로 제한됩니다. 이는 엄격한 기준입니다.
    4. 텍스트에서 핵심 주제를 추출하세요.
    5. 인사, 사과, 대화용 채우기 표현은 최대한 짧게 만들어야 합니다. (예: "안녕하세요"-> "간단한 인사", "죄송합니다"-> "사과")
    6. 만약 답변이 사용자가 원하는 답변이 아니어서 5번을 사용했을 경우, 그 답변과 사과를 바탕으로 만들어야 합니다.
    7. 출력은 제목 텍스트만 포함해야 하며, 다른 설명은 없어야 합니다.

    **예시:**
    - 입력 텍스트: "야구 차이에 대해 말씀드릴게요. 미국은..."
    - 출력: 야구 차이

    - 입력 텍스트: "운동 방법에 대해 알려드립니다. 스쿼트가..."
    - 출력: 운동 방법
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
                try:
                    content = uploaded_file.read().decode('utf-8')
                except UnicodeDecodeError:
                    uploaded_file.seek(0)
                    content = uploaded_file.read().decode('cp949')
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
    if not client:
        print("DALL-E Error: OpenAI 클라이언트가 설정되지 않았습니다.")
        return None, None
    try:
        response = client.images.generate(model="dall-e-3", prompt=prompt, n=1, size="1024x1024", quality="hd", response_format="url")
        image_url = response.data[0].url
        revised_prompt = response.data[0].revised_prompt
        return image_url, revised_prompt
    except Exception as e:
        print(f"DALL-E 3 Error: {e}")
        return None, None


def rerank_documents(question: str, documents: list, client: OpenAI | None, sub_llm: ChatOpenAI | None) -> list:
    """
    [파이프라인 v3]
    1. LLM에게 질문에 가장 도움이 될 '최고의 문서 1개'를 추천받습니다.
    2. (안전장치) 추천된 문서와 질문의 벡터 유사도를 계산하여 최종 결정합니다.
    """
    if not documents or not client or not sub_llm or not embeddings:
        return []

    print(f"[RAG-Rerank-v3] {len(documents)}개의 후보 중 최고 문서를 추천받습니다. 질문: '{question}'")
    
    # --- 1단계: LLM을 이용한 '최고의 문서 1개' 추천 ---
    doc_texts = [f"--- 문서 {i+1} ---\n{doc.page_content}" for i, doc in enumerate(documents)]
    docs_str = "\n\n".join(doc_texts)

    # LLM에게 '선택'을 요구하는 명확한 프롬프트
    recommender_prompt = ChatPromptTemplate.from_messages([
        ("system", """
        ## 📜 당신의 역할: 수석 정보 분석가
        당신은 여러 개의 문서 조각들 중에서 사용자의 질문에 답변하는 데 가장 결정적인 단서를 제공할 '단 하나의 핵심 문서'를 골라내는 전문가입니다.

        ## 🎯 당신의 임무
        - **[선택 규칙]** 아래 문서 목록 중에서, 사용자의 질문에 가장 큰 도움이 될 **문서 번호 단 하나만**을 추천해 주십시오.
        - **[예외 규칙]** 만약 정말로 관련 있는 문서가 단 하나도 보이지 않는다면, "없음"이라고 답해주십시오.
        - **[출력 형식]** 오직 숫자 하나 또는 "없음"만 출력해야 합니다.
        """),
        ("human", "사용자 질문: \"{question}\"\n\n--- 검색된 문서 목록 ---\n{documents}")
    ])
    
    recommender_chain = recommender_prompt | sub_llm | StrOutputParser()
    
    try:
        response = recommender_chain.invoke({"question": question, "documents": docs_str})
        print(f"[RAG-Rerank-v3 | 1단계] LLM 추천 응답: '{response}'")

        if "없음" in response.lower() or not re.search(r'\d', response):
            print("[RAG-Rerank-v3 | 1단계] LLM이 관련 문서를 추천하지 않았습니다.")
            return []

        # LLM이 추천한 단 하나의 문서 인덱스
        best_doc_index = int(re.findall(r'\d+', response)[0]) - 1
        
        if not (0 <= best_doc_index < len(documents)):
            print(f"[RAG-Rerank-v3 | 1단계] LLM이 유효하지 않은 인덱스({best_doc_index+1})를 추천했습니다.")
            return []

        # LLM이 추천한 최고의 후보 문서
        best_doc_candidate = documents[best_doc_index]

        # --- 2단계: (최종 안전장치) 벡터 유사도 검증 ---
        print("[RAG-Rerank-v3 | 2단계] 최종 안전장치, 벡터 유사도 검증을 시작합니다.")
        
        question_embedding = np.array(embeddings.embed_query(question))
        doc_embedding = np.array(embeddings.embed_query(best_doc_candidate.page_content))
        
        denominator = norm(question_embedding) * norm(doc_embedding)
        similarity = np.dot(question_embedding, doc_embedding) / denominator if denominator != 0 else 0.0
        
        # [수정] 임계값을 0.5로 설정
        SIMILARITY_THRESHOLD = 0.5 

        print(f"  - 최고 문서와의 유사도: {similarity:.1f} (임계값: {SIMILARITY_THRESHOLD})")

        if similarity >= SIMILARITY_THRESHOLD:
            print(f"[RAG-Rerank-v3] 최종 통과: LLM이 추천한 문서는 유효합니다.")
            return [best_doc_candidate] # 단 하나의, 가장 좋은 문서를 리스트에 담아 반환
        else:
            print(f"[RAG-Rerank-v3] 최종 기각: LLM 추천 문서가 질문과 관련성이 낮아 기각합니다.")
            return []

    except Exception as e:
        print(f"[RAG-Rerank-v3 치명적 오류] {e}. 안전을 위해 RAG 검색을 실패로 처리합니다.")
        return []



def _handle_dalle_generation(bot_response_md: str | None) -> tuple[bool, bytes | None]:
    """
    LLM 응답에서 DALL-E 프롬프트를 파싱하고, 이미지 생성을 시도한 후,
    성공 여부와 이미지의 원본 바이너리 데이터를 반환합니다.

    Returns:
        tuple[bool, bytes | None]: 
        - 첫 번째 값(bool): Dalle 태그가 있어서 이미지 생성을 '시도'했는지 여부.
        - 두 번째 값(bytes | None): 이미지 생성 및 리사이징에 성공했을 경우, 해당 이미지의 PNG 바이너리 데이터. 실패 시 None.
    """
    if not bot_response_md:
        return False, None
    
    dalle_match = re.search(r"Dalle<dalle_prompt>(.*?)</dalle_prompt>", bot_response_md, re.DOTALL)
    
    # Dalle 태그가 없으면, 이미지 생성 시도 자체가 없었음을 의미
    if not dalle_match:
        return False, None

    # Dalle 태그가 있으면, 이미지 생성을 '시도'한 것이므로 첫 번째 반환값은 True
    dalle_prompt = dalle_match.group(1).strip()
    print(f"[후처리] DALL-E 이미지 생성 요청 감지. 프롬프트: {dalle_prompt}")
    
    try:
        # 1. DALL-E API를 통해 이미지 생성 시도
        image_url, _ = generate_image_with_dalle(dalle_prompt, openai_client)
        if not image_url:
            print("[후처리 오류] DALL-E API 호출에 실패했습니다.")
            return True, None # 생성 '시도'는 했지만 결과는 '실패(None)'

        # 2. URL에서 이미지 데이터를 다운로드
        res = requests.get(image_url, stream=True, timeout=30) # 타임아웃 추가
        res.raise_for_status()

        # 3. 이미지 리사이징 및 바이너리 데이터로 변환
        img = Image.open(res.raw)
        img.thumbnail((512, 512), Image.Resampling.LANCZOS)
        
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        
        print("[후처리] DALL-E 이미지 생성 및 처리 성공.")
        # 생성 '시도'도 했고, 결과물(바이너리)도 '있음'
        return True, buffered.getvalue()

    except Exception as img_e:
        print(f"[후처리 오류] DALL-E 이미지 처리 중 예외 발생: {img_e}")
        # 생성 '시도'는 했지만 결과는 '실패(None)'
        return True, None


def _retrieve_rag_context(question: str, history: str, client: OpenAI | None) -> str:
    """
    [파이프라인 재설계 v6]
    1. LLM에게 '검색어 최적화가 필요한지' 먼저 판단하게 합니다.
    2. 그 판단에 따라 원본 또는 최적화된 검색어로 검색을 수행합니다.
    """
    print(f"\n--- [RAG 컨텍스트 검색 v6] | 원본 질문: '{question}' ---")
    if not vectorstore or not question or not embeddings:
        return ""
    
    # --- 1. LLM을 이용한 '검색어 최적화 필요성' 판단 ---
    final_query = question
    
    # 대화 기록이 있을 때만 최적화 가능성을 검토
    if history:
        # LLM에게 질문을 분석하고, 더 나은 검색어로 바꿀 수 있는지 물어보는 프롬프트
        optimization_check_prompt = f"""
        당신은 사용자의 질문 의도를 파악하는 분석 전문가입니다.
        아래에 이전 대화 기록과 사용자의 새로운 질문이 있습니다.
        
        [대화 기록의 마지막 부분]
        {history[-1000:]}

        [사용자의 새로운 질문]
        "{question}"

        이 새로운 질문이 이전 대화의 맥락을 이어가는 '후속 질문'이거나, 감정적인 표현/오타 등으로 인해 '검색에 부적합'한 형태입니까?
        그렇다면, 더 나은 검색 결과를 얻을 수 있는 '개선된 검색어'를 제안해 주십시오.
        만약 질문이 명확하고 그 자체로 검색하기에 충분하다면, "최적화 불필요"라고만 답해주십시오.
        다른 설명은 절대 추가하지 마세요.
        """
        try:
            print("[RAG v6] LLM에게 검색어 최적화 필요성 판단을 요청합니다...")
            check_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a query analysis expert."},
                    {"role": "user", "content": optimization_check_prompt}
                ],
                temperature=0.0,
                max_tokens=50
            )
            optimized_query_candidate = check_response.choices[0].message.content.strip()

            if "최적화 불필요" not in optimized_query_candidate:
                print(f"[RAG v6] LLM이 검색어 최적화를 제안했습니다: '{question}' -> '{optimized_query_candidate}'")
                final_query = optimized_query_candidate
            else:
                print("[RAG v6] LLM이 원본 질문이 충분하다고 판단했습니다.")

        except Exception as e:
            print(f"[RAG v6] 검색어 최적화 판단 중 오류 발생: {e}. 원본 질문을 사용합니다.")
    
    try:
        # --- 2. 최종 결정된 검색어로 '직접 검색' 수행 ---
        print(f"[RAG v6] 1단계: 최종 검색어 '{final_query}'로 후보 문서를 가져옵니다.")
        retriever = vectorstore.as_retriever(search_kwargs={"k": 7})
        candidate_docs = retriever.invoke(final_query)

        if not candidate_docs:
            print("[RAG v6] 1단계 검색 결과, 후보 문서가 없습니다.")
            return ""
            
        # --- 3. LLM에게 최고의 문서 1개를 추천받는 과정 ---
        recommended_docs = rerank_documents(final_query, candidate_docs, client, sub_llm)

        if not recommended_docs:
            print("[RAG v6] 2단계 LLM 추천 결과, 핵심 문서가 없습니다.")
            return ""

        best_doc = recommended_docs[0]
        
        # --- 4. 최종 안전장치 (벡터 유사도 검증) ---
        print("[RAG v6] 3단계 최종 안전장치, 벡터 유사도 검증을 시작합니다.")
        question_embedding = np.array(embeddings.embed_query(final_query))
        doc_embedding = np.array(embeddings.embed_query(best_doc.page_content))
        
        denominator = norm(question_embedding) * norm(doc_embedding)
        similarity = np.dot(question_embedding, doc_embedding) / denominator if denominator != 0 else 0.0
        
        SIMILARITY_THRESHOLD = 0.5 

        print(f"  - 최고 문서와의 유사도: {similarity:.4f} (임계값: {SIMILARITY_THRESHOLD})")

        if similarity >= SIMILARITY_THRESHOLD:
            print(f"[RAG v6] 최종 통과: LLM이 추천한 문서는 유효합니다.")
            return best_doc.page_content
        else:
            print(f"[RAG v6] 최종 기각: LLM 추천 문서가 질문과 관련성이 낮아 기각합니다.")
            return ""
            
    except Exception as e:
        print(f"RAG 검색 중 오류 발생: {e}")
        return ""


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
당신은 절대 '미흡한 답변'을 해서는 안 되며, 항상 '최상의 답변' 수준을 유지해야 합니다.

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

- ⭐️⭐️⭐️ 상황: 특정 브랜드/가공식품 질문 ("햇반 칼로리", "CJ 맛밤 영양성분")  
  - **지침**:
    1. 먼저, 당신의 일반 지식에서 해당 제품의 정보를 최대한 정확하게 찾아봅니다.
    2. **정보를 찾았든 못 찾았든, 반드시 아래의 '투명성 원칙'에 따라 답변을 시작해야 합니다.**
        - "제가 가진 정보는 실제 제품과 약간의 차이가 있을 수 있으니 참고용으로 봐주세요! 😊"
    3. 영양 성분은 다음 **7개 항목을 모두 포함한 마크다운 리스트**로 제공해야 합니다:
        - 칼로리, 탄수화물, 단백질, 지방, 당류, 나트륨, 식이섬유
    4. 사용자가 "80g 기준으론?", "2개 먹으면?"처럼 양을 조절해서 물어보면, **모든 항목을 비례 계산하여 재제공**해야 합니다.

- ⭐️⭐️⭐️ 상황: 제품 추천 요청 ("프로틴 브래드 추천해줘", "단백질 쉐이크 뭐가 좋아요?" 등)
  - **지침**:
    1. 사용자의 질문이 '추천'을 요청한 경우, 브랜드명이 포함되더라도 응답을 회피하지 마세요.
    2. **추천은 정답이 아니라 예시 제공이라는 관점에서** 3개 이상의 제품을 소개하고, 각 제품에 대해 다음 정보를 마크다운 리스트로 제공하세요:
        - 제품명 (브랜드 포함), 특징 요약, 추천 대상 (예: 다이어트용, 벌크업용 등)
    3. 정확한 정보가 없더라도, 유사한 제품군을 **창의적으로** 제안하세요.
    4. 답변 도입부에는 **"추천은 참고용이지만 😊"** 문구를 포함하세요.

    예시:
    
    물론이에요! 😊 아래는 요즘 인기가 많은 프로틴 브래드 몇 가지 추천이에요. 개인 취향과 목적에 따라 골라보세요!

    * **[머슬밀 프로틴 식빵]** – 1장당 단백질 15g! 고단백/저당으로 다이어트에도 좋아요.
    * **[라이프밀 프로틴 브래드]** – 현미 베이스로 소화가 잘되고, 아침 대용으로 딱이에요 🥪
    * **[코스트코 커클랜드 고단백 브레드]** – 벌크업 하시는 분들에게 인기 많은 든든한 대용식이에요.

    참고용으로 봐주시고, 본인 상황(다이어트/운동/간식 용도)에 맞게 선택해보세요! 💪
    

- **상황: 부정적/무의미한 입력 (욕설, 장난)**
  - **지침**: 모욕에 반응하거나 상처받지 마세요. 장난이라면 가볍게 받아주고, 심하다면 재치있게 건강 주제로 화제를 전환하여 대화를 주도하세요.

- **상황: 피로/일탈 표현 ("움직이기 싫어")**
  - **지침**: **해결책 제시 금지.** 먼저 깊이 공감하고("그 마음 알아요!"), 휴식의 긍정적 가치를 인정하며("푹 쉬는 것도 중요하죠!") 격려하세요.

- **상황: 능력 밖의 질문 (로또 번호 등)**
  - **지침**: 정중하게 할 수 없음을 알리고, "대신 건강에 대해 궁금한 점이 있으신가요?" 와 같이 자연스럽게 당신의 역할로 사용자를 유도하세요.

---
**사용자 현재 질문**: {original_question}"""



from .user_context import get_user_profile_context
@login_required
@csrf_exempt
def chatbot_api(request: HttpRequest):
    print("\n" + "="*50)
    print(f"--- [시작] 새로운 챗봇 API 요청 ({datetime.now()}) ---")

    # --- 1. 기본 설정 및 유효성 검사 ---
    user = request.user # 👈 User.objects.first() 대신 실제 로그인한 사용자 사용
    if not user.is_authenticated:
        return JsonResponse({"response": "오류: 사용자 인증이 필요합니다.", "type": "error"}, status=401)
    if request.method != "POST": return JsonResponse({"response": "오류: POST 요청만 허용됩니다.", "type": "error"}, status=405)
    if not OPENAI_API_KEY or not openai_client: return JsonResponse({"response": "오류: 서버의 AI API 설정에 문제가 있습니다.", "type": "error"}, status=503)
    start_time = time.time()
    try:
        # --- 2. 입력 데이터 파싱 및 대화/파일 시스템 준비 ---
        user_input_text = request.POST.get("message", "").strip()
        dialog_id_str = request.POST.get("id")
        uploaded_file = request.FILES.get("file", None)
        print(f"[입력] 대화 ID: {dialog_id_str}, 메시지: '{user_input_text}', 파일: {uploaded_file.name if uploaded_file else '없음'}")
        ChatbotInteractionLog.objects.create(user=user)

         # 첫 대화 업적
        check_and_award_achievement(request, user, 'first_ai_chat')

        # 누적 대화 업적
        chat_count = ChatbotInteractionLog.objects.filter(user=user).count()
        if chat_count >= 10: check_and_award_achievement(request, user, 'ai_advisor_bronze')
        if chat_count >= 50: check_and_award_achievement(request, user, 'ai_advisor_silver')
        if chat_count >= 150: check_and_award_achievement(request, user, 'ai_advisor_gold')

        # 특정 질문 및 행동 기반 업적
        if user_input_text:
            lower_message = user_input_text.lower()
            if '업적' in lower_message or '칭호' in lower_message:
                check_and_award_achievement(request, user, 'curious_about_achievements')
            if '그려줘' in lower_message or '만들어줘' in lower_message:
                check_and_award_achievement(request, user, 'creative_spark')
        
        if uploaded_file:
            check_and_award_achievement(request, user, 'data_provider')
        
        if not user_input_text and not uploaded_file:
            return JsonResponse({"response": "질문이나 파일을 입력해주세요.", "type": "error"}, status=400)

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

        # 파일 저장을 위한 준비
        fs = FileSystemStorage(location=settings.TEMP_IMAGE_DIR)
        dialog_key_suffix = f'_{dialog_id}' if dialog_id else '_new'
        session_key_img_path = f'last_context_image_path{dialog_key_suffix}'

        # --- 3. 정보 수집 (시각 정보, 전문 정보) ---
        user_profile_str = get_user_profile_context(user)
        print(f"✅ [사용자 컨텍스트 생성 완료]\n{user_profile_str}")
        visual_context_str = "현재 제공된 시각적 정보 없음."
        image_to_send_b64 = None
        image_to_send_mime = "image/png" # 기본값

        # 3-1. [파일 업로드 시] 새 이미지를 컨텍스트로 사용
        if uploaded_file and uploaded_file.content_type.startswith('image/'):
            print("[파일 처리] 새 이미지 업로드 감지.")
            
            # 이전 임시 컨텍스트 파일이 있다면 삭제
            old_path = request.session.get(session_key_img_path)
            if old_path and fs.exists(old_path):
                print(f"[파일 정리] 이전 컨텍스트 이미지 삭제: {old_path}")
                fs.delete(old_path)

            # 새 파일 저장 및 세션에 경로 기록
            file_name = f"context_{uuid.uuid4()}_{uploaded_file.name}"
            saved_path = fs.save(file_name, uploaded_file)
            request.session[session_key_img_path] = saved_path
            print(f"[파일 저장] 새 컨텍스트 이미지를 '{saved_path}'로 저장하고 경로를 세션에 기록.")
            
            uploaded_file.seek(0)
            image_to_send_b64 = base64.b64encode(uploaded_file.read()).decode('utf-8')
            image_to_send_mime = uploaded_file.content_type

        # 3-2. [파일 업로드 없을 시] 세션에 저장된 이전 이미지 경로를 컨텍스트로 사용
        elif not uploaded_file:
            saved_path = request.session.get(session_key_img_path)
            if saved_path and fs.exists(saved_path):
                print(f"[파일 로드] 세션에서 이전 컨텍스트 이미지 '{saved_path}'를 로드합니다.")
                with fs.open(saved_path, 'rb') as f:
                    image_to_send_b64 = base64.b64encode(f.read()).decode('utf-8')
                    # 파일 확장자로 MIME 타입 추론 (더 정확하게)
                    if saved_path.endswith('.jpg') or saved_path.endswith('.jpeg'):
                        image_to_send_mime = 'image/jpeg'

        # 3-3. Vision API로 시각 정보 생성 (보낼 이미지가 있을 경우에만)
        if image_to_send_b64:
            try:
                print("[Vision API] 이미지 설명을 생성합니다...")
                vision_response = openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "이 이미지는 무엇이야? 아주 간결하게 핵심만 설명해줘."},
                            {"type": "image_url", "image_url": {"url": f"data:{image_to_send_mime};base64,{image_to_send_b64}"}}
                        ]
                    }],
                    max_tokens=150
                )
                visual_context_str = vision_response.choices[0].message.content
                print(f"[Vision API] 생성된 설명: {visual_context_str}")
            except Exception as ve:
                print(f"[Vision API 오류] {ve}")
                visual_context_str = "이미지를 분석하는 중 오류가 발생했습니다."

        # 3-4. RAG를 통한 전문 정보 검색
        history_text = current_dialog.full_text if current_dialog else ""
        retrieved_context = _retrieve_rag_context(user_input_text, history_text, openai_client) or "결과 없음"

        # --- 4. 최종 프롬프트 및 API 요청 메시지 구성 ---
        system_prompt = MASTER_SYSTEM_PROMPT.format(
            user_profile_context=user_profile_str,     # 👈 사용자 데이터 주입
            visual_context=visual_context_str,         # 👈 시각 정보 주입
            retrieved_context=retrieved_context,       # 👈 RAG 정보 주입
            original_question=user_input_text
        )
        messages_for_api = [{"role": "system", "content": system_prompt}]
        
        if current_dialog:
            history_lines = current_dialog.full_text.strip().split('\n')
            for line in history_lines[-20:]:
                if line.startswith("user:"): messages_for_api.append({"role": "user", "content": line[6:].strip()})
                elif line.startswith("bot:"): messages_for_api.append({"role": "assistant", "content": line[5:].strip()})

        current_user_content = [{"type": "text", "text": user_input_text}]
        if image_to_send_b64:
            current_user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:{image_to_send_mime};base64,{image_to_send_b64}"}
            })
        messages_for_api.append({"role": "user", "content": current_user_content})
        
        # --- 5. OpenAI API 호출 ---
        print(f"\n--- [API 호출] OpenAI API 호출 (메인 모델: gpt-4o) ---")
        response = openai_client.chat.completions.create(model="gpt-4o", messages=messages_for_api, temperature=0.75, max_tokens=4096)
        bot_response_md = response.choices[0].message.content

        # --- 6. 후처리 및 DB/파일 저장 ---
        print("\n--- [후처리 및 저장] ---")
        
        # 6-1. DALL-E 이미지 생성 후처리
        is_dalle_response, image_binary_data = _handle_dalle_generation(bot_response_md)

        if is_dalle_response:
            if image_binary_data:
                print("[DALL-E 후처리] 생성된 이미지를 파일로 저장하고 컨텍스트를 갱신합니다.")
                
                # 이전 임시 파일 삭제
                old_path = request.session.get(session_key_img_path)
                if old_path and fs.exists(old_path): fs.delete(old_path)

                # 새 DALL-E 이미지 저장 및 경로 기록
                dalle_file_name = f"dalle_{uuid.uuid4()}.png"
                saved_path = fs.save(dalle_file_name, ContentFile(image_binary_data))
                request.session[session_key_img_path] = saved_path
                print(f"[파일 저장] DALL-E 이미지를 '{saved_path}'로 저장하고 세션 경로 갱신.")

                resized_image_data_url = f"data:image/png;base64,{base64.b64encode(image_binary_data).decode('utf-8')}"
                bot_response_md = f"요청하신 이미지를 생성했어요! 짠! ✨\n\n![Generated Image]({resized_image_data_url})"
            else:
                bot_response_md = "죄송하지만 이미지 생성에 실패했습니다. 다시 시도해 주세요."

        # 6-2. 대화 DB 저장
        user_message_for_db = user_input_text
        if uploaded_file:
            user_message_for_db += f"\n![사용자 첨부 파일: {uploaded_file.name}]"
        
        final_id, final_title = _save_conversation_and_get_title(current_dialog, user, user_message_for_db, bot_response_md, "text_response" if not is_dalle_response else "image_response")

        # 6-3. 새 대화 시 세션 키 마이그레이션
        if not dialog_id and final_id:
             print(f"[세션 마이그레이션] 새 대화 ID({final_id})로 세션 키를 이전합니다.")
             new_session_key = f'last_context_image_path_{final_id}'
             if session_key_img_path in request.session:
                 request.session[new_session_key] = request.session.pop(session_key_img_path)
                 print(f"  - 'last_context_image_path_new' -> '{new_session_key}'")

        response_html = convert_markdown_to_html(bot_response_md)
        end_time = time.time()
        print(f"--- [종료] 요청 처리 완료. 응답을 반환합니다. ---\n" + "="*50)
        print(f"[처리 시간] 총 요청 처리 시간: {end_time - start_time:.2f}초")
        return JsonResponse({"response": response_html, "id": final_id, "title": final_title})

    except Exception as e:
        # --- 예외 처리 ---
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
        # 이 부분은 @login_required로 인해 실행되지 않지만, 명확성을 위해 둡니다.
        return JsonResponse({"error": "인증이 필요합니다."}, status=401)

    # 사용자의 가장 최근 대화를 찾습니다.
    latest_dialog = ChatConversation.objects.filter(user=user).order_by("-created_at").first()

    context = {
        # 👇 초기 대화 ID를 템플릿에 전달합니다. 없으면 None.
        'initial_dialog_id': latest_dialog.id if latest_dialog else None
    }
    return render(request, "chatbot/chatbot.html", context)

@login_required
@csrf_exempt
def dialog_list_api(request: HttpRequest):
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({"error": "인증이 필요합니다."}, status=401)
    dialogs = ChatConversation.objects.filter(user=user).order_by("-created_at")
    return JsonResponse({"dialogs": [{"id":d.id, "title":d.summary_title or "새 대화", "timestamp":d.created_at.strftime("%Y-%m-%d %H:%M"), "is_custom_title":d.is_custom_title} for d in dialogs]})

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
    
    # 세션에서 해당 대화의 '가장 마지막' 이미지 경로를 가져옴 (단순화된 방식)
    last_image_path = request.session.get(f'last_image_path_{dialog_id}')
    
    # 이전에 이미지가 있었는지 추적하는 플래그
    image_turn_found = False

    # 대화 기록을 역순으로 순회하여 가장 최근 이미지 턴을 찾음
    for turn in reversed(turns):
        turn_content = turn.strip()
        if not turn_content: continue

        msg_data = {}
        if turn_content.startswith("user:"):
            msg_data["sender"] = "user"
            text_content = turn_content[6:].strip()
            
            image_placeholder_regex = r"!\[사용자 첨부 파일.*?\]"
            match = re.search(image_placeholder_regex, text_content)

            # 플레이스홀더가 있고 & 아직 이 대화에서 이미지 턴을 처리하지 않았고 & 세션에 경로가 있을 때
            if match and not image_turn_found and last_image_path:
                msg_data["image_path"] = last_image_path
                msg_data["text"] = re.sub(image_placeholder_regex, '', text_content).strip()
                image_turn_found = True # 이제 이 대화의 이미지 처리는 끝났음을 표시
            else:
                msg_data["text"] = text_content

        elif turn_content.startswith("bot:"):
            msg_data["sender"] = "bot"
            msg_data["text"] = convert_markdown_to_html(turn_content[5:].strip())
        
        if msg_data:
            messages.append(msg_data)

    # 메시지를 원래 순서대로 다시 뒤집음
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
            dialog.summary_title = new_title
            dialog.is_custom_title = True
            dialog.save()
            return JsonResponse({"success": True, "title": new_title})
        except ChatConversation.DoesNotExist: return JsonResponse({"success": False, "error": "대화 없음"}, status=404)
        except json.JSONDecodeError: return JsonResponse({"success": False, "error": "잘못된 요청"}, status=400)
    return JsonResponse({"success": False, "error": "POST 필요"}, status=405)