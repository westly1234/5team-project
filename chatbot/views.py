import base64, io, json, os, re, time, traceback
from datetime import datetime

import markdown, pandas as pd, requests, fitz, torch
from docx import Document as DocxDocument
from PIL import Image
from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from langchain_community.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings
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
from django.utils.translation import gettext as _
from django.utils import translation, timezone

from .json_translator import translate as _json_t

# --- 설정 ---
VECTORSTORE_PATH = r"C:\Users\Admin\5team-project\project_data\vectorstore_food_and_healthy"
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

# --- 프롬프트 로더 함수 ---
def get_prompt(prompt_name: str, lang_code: str) -> str:
    if not lang_code or lang_code not in ['ko', 'en', 'es']:
        lang_code = 'ko'  # 유효하지 않으면 한국어로 기본 설정

    file_path = os.path.join(settings.BASE_DIR, 'chatbot', 'prompts', f'{prompt_name}_{lang_code}.txt')
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        # 해당 언어의 프롬프트가 없을 경우, 안전하게 한국어 프롬프트를 불러옵니다.
        print(f"경고: '{lang_code}' 언어의 프롬프트 파일이 없어 한국어로 대체합니다.")
        ko_file_path = os.path.join(settings.BASE_DIR, 'chatbot', 'prompts', f'{prompt_name}_ko.txt')
        try:
            with open(ko_file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            # 한국어 프롬프트조차 없는 최악의 경우를 대비합니다.
            return f"Error: Prompt file '{prompt_name}_ko.txt' not found."
    

# --- LLM 제목 생성 함수 ---
def generate_title_with_llm(bot_answer: str, client: OpenAI | None, request: HttpRequest, lang_code) -> str:
    if not client or not bot_answer or len(bot_answer.strip()) < 10:
        lang_code = translation.get_language() or 'ko'
        return _json_t("새 대화",lang_code)
    system_prompt = get_prompt('title_generator', lang_code)
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", 
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": bot_answer}],
            temperature=0.0, max_tokens=20
        )
        title = response.choices[0].message.content.strip().replace('"', '')
        if not title or _json_t("새 대화", lang_code) in title or len(title) > 20:
            return _json_t("새 대화", lang_code)
        return title[:20]
    except Exception as e:
        print(f"LLM 제목 생성 중 오류: {e}")
        return _json_t("새 대화", lang_code)

def _save_conversation_and_get_title(dialog, user, user_msg_db, bot_msg_md, response_type, request: HttpRequest, lang_code):
    lang_code = translation.get_language() or 'ko'
    if response_type == "error":
        print("[DB] 오류가 발생하여 대화를 저장하지 않습니다.")
        final_title = dialog.summary_title if dialog else _json_t("새 대화", lang_code)
        final_id = dialog.id if dialog else None
        return final_id, final_title
    print("[DB] 대화를 데이터베이스에 저장합니다...")
    if dialog:
        dialog.full_text += f"\nuser: {user_msg_db}\nbot: {bot_msg_md}\n"
        final_title = dialog.summary_title
        if not dialog.is_custom_title:
            new_title_candidate = generate_title_with_llm(bot_msg_md, openai_client, request, lang_code)
            if new_title_candidate != _json_t("새 대화", lang_code):
                dialog.summary_title = new_title_candidate
                final_title = new_title_candidate
        dialog.save()
        final_id = dialog.id
    else:
        final_title = generate_title_with_llm(bot_msg_md, openai_client)
        if final_title == _json_t("새 대화", lang_code):
            final_title = user_msg_db.split('\n')[0][:25].strip() or _json_t("새로운 대화", lang_code)
        new_dialog = ChatConversation.objects.create(user=user, summary_title=final_title, full_text=f"user: {user_msg_db}\nbot: {bot_msg_md}\n")
        final_id = new_dialog.id
    print(f"[DB] 저장 완료. (ID: {final_id}, 제목: {final_title})")
    return final_id, final_title

def convert_markdown_to_html(text: str | None) -> str:
    if not text: return ""
    html = markdown.markdown(text, extensions=['fenced_code', 'tables', 'nl2br', 'sane_lists', 'extra'])
    html = re.sub(r"<li>\s*<p>(.*?)</p>\s*</li>", r"<li>\1</li>", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"(?:<br\s*/?>\s*){2,}", "<br>", html)
    return html

def analyze_uploaded_file(uploaded_file: OpenAI | None) -> tuple[str, str, str | None]:
    if not uploaded_file: return "", "", None
    filename = uploaded_file.name
    file_extension = os.path.splitext(filename)[1].lower()
    extracted_text, base64_image_str, error_message = "", "", None
    lang_code = translation.get_language() or 'ko'
    try:
        if file_extension in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
            uploaded_file.seek(0)
            base64_image_str = base64.b64encode(uploaded_file.read()).decode('utf-8')
            extracted_text = _json_t("[{filename} 이미지 파일이 첨부되었습니다.]").format(filename=filename)
        elif file_extension == '.txt':
            uploaded_file.seek(0)
            content = uploaded_file.read().decode('utf-8', errors='ignore')
            extracted_text = content.strip() or _json_t("(빈 텍스트 파일)", lang_code)
        elif file_extension == '.pdf':
            uploaded_file.seek(0)
            doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
            texts = [page.get_text() for page in doc]
            extracted_text = "\n\n".join(texts).strip() or _json_t("(내용 없는 PDF 파일)", lang_code)
            doc.close()
        elif file_extension in ['.xlsx', '.xls']:
            uploaded_file.seek(0)
            df = pd.read_excel(uploaded_file)
            extracted_text = df.to_string() or _json_t("(빈 엑셀 파일)", lang_code)
        elif file_extension == '.csv':
            try:
                uploaded_file.seek(0)
                try: content = uploaded_file.read().decode('utf-8')
                except UnicodeDecodeError:
                    uploaded_file.seek(0)
                    content = uploaded_file.read().decode('cp949')
                df = pd.read_csv(io.StringIO(content))
                extracted_text = df.to_string() or _json_t("(빈 CSV 파일)")
            except Exception as e:
                error_message = _json_t("CSV 파일 파싱 중 오류가 발생했습니다: {error}", lang_code).format(error=e)
                uploaded_file.seek(0)
                extracted_text = uploaded_file.read().decode('utf-8', errors='ignore').strip()
        elif file_extension == '.docx':
            uploaded_file.seek(0)
            doc = DocxDocument(uploaded_file)
            paragraphs = [p.text for p in doc.paragraphs]
            extracted_text = "\n".join(paragraphs).strip() or _json_t("(빈 워드 파일)")
        else:
            error_message = _json_t("지원하지 않는 파일 형식입니다: {filename}", lang_code).format(filename=filename)
    except Exception as e:
        error_message =  _json_t("'{filename}' 파일 처리 중 오류 발생: {error}", lang_code).format(filename=filename, error=e)
        traceback.print_exc()
    return extracted_text, base64_image_str, error_message

def generate_image_with_dalle(prompt: str, client: OpenAI | None) -> tuple[str | None, str | None]:
    if not client:
        print("DALL-E Error: OpenAI 클라이언트가 설정되지 않았습니다.")
        return None, None
    try:
        response = client.images.generate(model="dall-e-3", prompt=prompt, n=1, size="1024x1024", quality="hd", response_format="url")
        image_url, revised_prompt = response.data[0].url, response.data[0].revised_prompt
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
    
    doc_texts = [f"--- 문서 {i+1} ---\n{doc.page_content}" for i, doc in enumerate(documents)]
    docs_str = "\n\n".join(doc_texts)

    recommender_prompt_text = """
        ## 📜 당신의 역할: 수석 정보 분석가
        당신은 여러 개의 문서 조각들 중에서 사용자의 질문에 답변하는 데 가장 결정적인 단서를 제공할 '단 하나의 핵심 문서'를 골라내는 전문가입니다.

        ## 🎯 당신의 임무
        - **[선택 규칙]** 아래 문서 목록 중에서, 사용자의 질문에 가장 큰 도움이 될 **문서 번호 단 하나만**을 추천해 주십시오.
        - **[예외 규칙]** 만약 정말로 관련 있는 문서가 단 하나도 보이지 않는다면, "없음"이라고 답해주십시오.
        - **[출력 형식]** 오직 숫자 하나 또는 "없음"만 출력해야 합니다.
        """
    
    recommender_prompt = ChatPromptTemplate.from_messages([
        ("system", recommender_prompt_text),
        ("human", "사용자 질문: \"{question}\"\n\n--- 검색된 문서 목록 ---\n{documents}")
    ])
    
    recommender_chain = recommender_prompt | sub_llm | StrOutputParser()
    
    try:
        response = recommender_chain.invoke({"question": question, "documents": docs_str})
        print(f"[RAG-Rerank-v3 | 1단계] LLM 추천 응답: '{response}'")

        if "없음" in response.lower() or not re.search(r'\d', response):
            print("[RAG-Rerank-v3 | 1단계] LLM이 관련 문서를 추천하지 않았습니다.")
            return []

        best_doc_index = int(re.findall(r'\d+', response)[0]) - 1
        
        if not (0 <= best_doc_index < len(documents)):
            print(f"[RAG-Rerank-v3 | 1단계] LLM이 유효하지 않은 인덱스({best_doc_index+1})를 추천했습니다.")
            return []

        best_doc_candidate = documents[best_doc_index]

        print("[RAG-Rerank-v3 | 2단계] 최종 안전장치, 벡터 유사도 검증을 시작합니다.")
        question_embedding = np.array(embeddings.embed_query(question))
        doc_embedding = np.array(embeddings.embed_query(best_doc_candidate.page_content))
        denominator = norm(question_embedding) * norm(doc_embedding)
        similarity = np.dot(question_embedding, doc_embedding) / denominator if denominator != 0 else 0.0
        
        SIMILARITY_THRESHOLD = 0.5
        print(f"  - 최고 문서와의 유사도: {similarity:.1f} (임계값: {SIMILARITY_THRESHOLD})")

        if similarity >= SIMILARITY_THRESHOLD:
            print(f"[RAG-Rerank-v3] 최종 통과: LLM이 추천한 문서는 유효합니다.")
            return [best_doc_candidate]
        else:
            print(f"[RAG-Rerank-v3] 최종 기각: LLM 추천 문서가 질문과 관련성이 낮아 기각합니다.")
            return []

    except Exception as e:
        print(f"[RAG-Rerank-v3 치명적 오류] {e}. 안전을 위해 RAG 검색을 실패로 처리합니다.")
        return []

def _handle_dalle_generation(bot_response_md: str | None) -> tuple[bool, bytes | None]:
    if not bot_response_md: return False, None
    dalle_match = re.search(r"Dalle<dalle_prompt>(.*?)</dalle_prompt>", bot_response_md, re.DOTALL)
    if not dalle_match: return False, None
    dalle_prompt = dalle_match.group(1).strip()
    print(f"[후처리] DALL-E 이미지 생성 요청 감지. 프롬프트: {dalle_prompt}")
    try:
        image_url, _ = generate_image_with_dalle(dalle_prompt, openai_client)
        if not image_url:
            print("[후처리 오류] DALL-E API 호출에 실패했습니다.")
            return True, None
        res = requests.get(image_url, stream=True, timeout=30)
        res.raise_for_status()
        img = Image.open(res.raw)
        img.thumbnail((512, 512), Image.Resampling.LANCZOS)
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        print("[후처리] DALL-E 이미지 생성 및 처리 성공.")
        return True, buffered.getvalue()
    except Exception as img_e:
        print(f"[후처리 오류] DALL-E 이미지 처리 중 예외 발생: {img_e}")
        return True, None


def _retrieve_rag_context(question: str, history: str, client: OpenAI | None, lang_code: str) -> str:
    print(f"\n--- [RAG 컨텍스트 검색 v6] | 원본 질문: '{question}' ---")
    if not vectorstore or not question or not embeddings: return ""
    final_query = question
    if history:
        optimization_check_prompt = get_prompt('optimization_check', lang_code).format(history=history[-1000:], question=question)
        try:
            print("[RAG v6] LLM에게 검색어 최적화 필요성 판단을 요청합니다...")
            check_response = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "system", "content": "You are a query analysis expert."}, {"role": "user", "content": optimization_check_prompt}], temperature=0.0, max_tokens=100)
            optimized_query_candidate = check_response.choices[0].message.content.strip()
       
            if optimized_query_candidate == "[NO_CHANGE]":
                print(f"[RAG v6] LLM이 최적화가 불필요하다고 판단했습니다. 원본 질문을 사용합니다.")
            else:
                print(f"[RAG v6] LLM이 검색어 최적화를 제안했습니다: '{question}' -> '{optimized_query_candidate}'")
                final_query = optimized_query_candidate
        except Exception as e:
            print(f"[RAG v6] 검색어 최적화 판단 중 오류 발생: {e}. 원본 질문을 사용합니다.")
            traceback.print_exc()
    try:
        print(f"[RAG v6] 1단계: 최종 검색어 '{final_query}'로 후보 문서를 가져옵니다.")
        retriever = vectorstore.as_retriever(search_kwargs={"k": 7})
        candidate_docs = retriever.invoke(final_query)
        if not candidate_docs:
            print("[RAG v6] 1단계 검색 결과, 후보 문서가 없습니다.")
            return ""
        
        recommended_docs = rerank_documents(final_query, candidate_docs, client, sub_llm)

        if not recommended_docs:
            print("[RAG v6] 2단계 LLM 추천 결과, 핵심 문서가 없습니다.")
            return ""

        best_doc = recommended_docs[0]
        
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


@login_required
@csrf_exempt
def chatbot_api(request: HttpRequest):
    print("\n" + "="*50)
    print(f"--- [시작] 새로운 챗봇 API 요청 ({datetime.now()}) ---")

    lang_code = translation.get_language_from_request(request).split('-')[0]
    if lang_code not in ['ko', 'en', 'es']:
        lang_code = 'ko'

    user = request.user
    if not user.is_authenticated: return JsonResponse({"response": _json_t("오류: 사용자 인증이 필요합니다."), "type": "error"}, status=401)
    if request.method != "POST": return JsonResponse({"response": _json_t("오류: POST 요청만 허용됩니다."), "type": "error"}, status=405)
    if not OPENAI_API_KEY or not openai_client: return JsonResponse({"response": _json_t("오류: 서버의 AI API 설정에 문제가 있습니다."), "type": "error"}, status=503)
    start_time = time.time()

    try:
        
        user_input_text = request.POST.get("message", "").strip()
        dialog_id_str = request.POST.get("id")
        uploaded_file = request.FILES.get("file", None)
        print(f"[입력] 대화 ID: {dialog_id_str}, 메시지: '{user_input_text}', 파일: {uploaded_file.name if uploaded_file else '없음'}")
        
        file_text_content = ""
        if uploaded_file and not uploaded_file.content_type.startswith('image/'):
            extracted_text, file_meta, file_error = analyze_uploaded_file(uploaded_file)
            if not file_error:
                file_text_content = extracted_text
            else:
                return JsonResponse({"response": convert_markdown_to_html(f"**{_('파일 처리 오류')}:**\n`{file_error}`"), "type": "error"}, status=400)

        if not user_input_text and not file_text_content and not (uploaded_file and uploaded_file.content_type.startswith('image/')):
            translated_msg = _json_t("**파일 처리 오류:**\n`%(error)s`") % {"error": file_error}
            return JsonResponse({
                "response": convert_markdown_to_html(translated_msg),
                "type": "error"
            }, status=400)
        ChatbotInteractionLog.objects.create(user=user)
        check_and_award_achievement(request, user, 'first_ai_chat')
        chat_count = ChatbotInteractionLog.objects.filter(user=user).count()
        if chat_count >= 10: check_and_award_achievement(request, user, 'ai_advisor_bronze')
        if chat_count >= 50: check_and_award_achievement(request, user, 'ai_advisor_silver')
        if chat_count >= 150: check_and_award_achievement(request, user, 'ai_advisor_gold')
        if user_input_text:
            lower_message = user_input_text.lower()
            if _('업적') in lower_message or _('칭호') in lower_message: check_and_award_achievement(request, user, 'curious_about_achievements')
            if _('그려줘') in lower_message or _('만들어줘') in lower_message: check_and_award_achievement(request, user, 'creative_spark')
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

        print(f"[DEBUG] chatbot_api에서 get_user_profile_context 호출 직전, lang_code: '{lang_code}'")
        user_profile_str = get_user_profile_context(user, lang_code=lang_code)
        print(f"✅ [사용자 컨텍스트 생성 완료]\n{user_profile_str}")
        visual_context_str = _json_t("현재 제공된 시각적 정보 없음.", lang_code)
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
                vision_prompt = _json_t("이 이미지는 무엇이야? 아주 간결하게 핵심만 설명해줘.")
                print("[Vision API] 이미지 설명을 생성합니다...")
                vision_response = openai_client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": [{"type": "text", "text": vision_prompt}, {"type": "image_url", "image_url": {"url": f"data:{image_to_send_mime};base64,{image_to_send_b64}"}}]}], max_tokens=150)
                visual_context_str = vision_response.choices[0].message.content
                print(f"[Vision API] 생성된 설명: {visual_context_str}")
            except Exception as ve:
                print(f"[Vision API 오류] {ve}")
                visual_context_str = _json_t("이미지를 분석하는 중 오류가 발생했습니다.")
        
        final_user_question = _(
            "%(question)s\n\n--- 사용자가 첨부한 파일의 내용입니다 ---\n%(file_content)s"
        ) % {
            "question": user_input_text.strip(),
            "file_content": file_text_content.strip()
        }
        print(f"✅ [최종 질문 조합 완료]\n{final_user_question[:200]}...")

        history_text = current_dialog.full_text if current_dialog else ""
        retrieved_context = _retrieve_rag_context(final_user_question, history_text, openai_client, lang_code) or _json_t("결과 없음",lang_code)

        system_prompt = get_prompt('master_system', lang_code).format(user_profile_context=user_profile_str, visual_context=visual_context_str, retrieved_context=retrieved_context, original_question=user_input_text)
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
                bot_response_md = (
                    f"[COUPANG_RECOMMENDATION]\n"
                    f"intro_text={intro_text}\n"
                    f"keyword={keyword}\n"
                    f"count={len(recommendations)}"
                )
                check_and_award_achievement(request, user, 'first_product_recommendation')
            else:
                bot_response_md = _(
                    "'%(keyword)s'에 대한 추천 상품을 찾는 데 실패했어요. 😥\n"
                    "다른 키워드로 다시 질문해주시겠어요?"
                ) % {
                    "keyword": keyword
                }
                response_data = {"response": convert_markdown_to_html(bot_response_md)}
        else:
            # 쿠팡 태그가 없으면 기존 로직 수행 (DALL-E 등)
            response_html = convert_markdown_to_html(bot_response_md)
            response_data = {"response": response_html}

        # DB 저장 및 최종 응답 반환
        final_id, final_title = _save_conversation_and_get_title(current_dialog, user, user_input_text.strip(), bot_response_md, "text_response", request, lang_code)
        response_data.update({"id": final_id, "title": final_title})

        end_time = time.time()
        print(f"--- [종료] 요청 처리 완료. (소요 시간: {end_time - start_time:.2f}초) ---\n" + "="*50)
        return JsonResponse(response_data)

    except Exception as e:
        error_type = type(e).__name__
        print(f"\n!!!!!! [치명적 오류] 처리되지 않은 예외 발생: {error_type} !!!!!!")
        traceback.print_exc()
        error_message = "unexpected_server_error"
        error_html = convert_markdown_to_html(f"**오류 발생:**\n`{error_message} ({error_type})`")
        return JsonResponse({"response": error_html, "type": "error"}, status=500)


def load_translations(lang_code: str) -> dict:
    if lang_code not in ['ko', 'en', 'es']:
        lang_code = 'ko'
    
    # 항상 한국어를 기본으로 로드
    base_path = os.path.join(settings.BASE_DIR, 'locales', 'ko.json')
    try:
        with open(base_path, 'r', encoding='utf-8') as f:
            translations = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        translations = {}

    # 요청된 언어가 한국어가 아니면, 해당 언어 파일로 덮어쓰기
    if lang_code != 'ko':
        lang_path = os.path.join(settings.BASE_DIR, 'locales', f'{lang_code}.json')
        try:
            with open(lang_path, 'r', encoding='utf-8') as f:
                lang_specific_translations = json.load(f)
                translations.update(lang_specific_translations)
        except (FileNotFoundError, json.JSONDecodeError):
            print(f"Warning: Translation file for '{lang_code}' not found. Using Korean as fallback.")
            
    return translations

@login_required
@csrf_exempt
def chatbot_ui(request: HttpRequest):
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({"error": _json_t("인증이 필요합니다.")}, status=401)
    
    lang_code = translation.get_language_from_request(request).split('-')[0]
    js_translations = load_translations(lang_code)

    print(f"✅ 요청된 언어 코드: {lang_code}")
    print(f"✅ 생성된 번역(sidebar_header): {js_translations.get('sidebar_header')}")
    
    latest_dialog = ChatConversation.objects.filter(user=user).order_by("-created_at").first()
    context = {
        'initial_dialog_id': latest_dialog.id if latest_dialog else None, 
        'js_translations': json.dumps(js_translations, ensure_ascii=False)
    }
    return render(request, "chatbot/chatbot.html", context)


@login_required
@csrf_exempt
def dialog_list_api(request: HttpRequest):
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({"error": _json_t("인증이 필요합니다.")}, status=401)
    dialogs = ChatConversation.objects.filter(user=user).order_by("-created_at")
    dialog_list = [{
        "id": d.id,
        "title": d.summary_title, # 번역하지 않은 원본 제목 전달
        "timestamp": timezone.localtime(d.created_at).strftime("%Y-%m-%d %H:%M"),
        "is_custom_title": d.is_custom_title
    } for d in dialogs]
    return JsonResponse({"dialogs": dialog_list})

@login_required
@csrf_exempt
def load_dialog_api(request: HttpRequest, dialog_id: int):
    dialog = get_object_or_404(ChatConversation, id=dialog_id, user=request.user)
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({"error": _json_t("사용자 없음")}, status=401)
    lang_code = translation.get_language() or 'ko'

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
    return JsonResponse({"messages": messages, "id": dialog.id, "title": dialog.summary_title or _json_t("새 대화", lang_code)})

@login_required
@csrf_exempt
def new_dialog_api(request: HttpRequest):
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({"error": _json_t("사용자 없음", lang_code)}, status=401)
    lang_code = translation.get_language() or 'ko'
    translated_title = _json_t("새 대화", lang_code)
    translated_greeting = _json_t('new_dialog_greeting', lang_code)
    initial_full_text = f"bot: {translated_greeting}\n"
    dialog = ChatConversation.objects.create(user=request.user, summary_title=translated_title, is_custom_title=False, full_text=initial_full_text)
    return JsonResponse({"id": dialog.id, "title": dialog.summary_title})

@login_required
@csrf_exempt
def delete_dialog_api(request: HttpRequest, dialog_id: int):
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({"success": False, "error": _json_t("사용자 없음")}, status=401)
    count, _deletion_details = ChatConversation.objects.filter(id=dialog_id, user=user).delete()
    lang_code = translation.get_language_from_request(request)
    with translation.override(lang_code):
        error_message = _json_t("삭제할 대화 없음", lang_code)
    return JsonResponse({"success": True} if count > 0 else {"success": False, "error": error_message}, status=200 if count > 0 else 404)

@login_required
@csrf_exempt
def rename_dialog_api(request: HttpRequest, dialog_id: int):
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({"success": False, "error": _json_t("사용자 없음")}, status=401)
    lang_code = translation.get_language_from_request(request)
    with translation.override(lang_code):
        if request.method == 'POST':
            try:
                data = json.loads(request.body)
                new_title = data.get("title", "").strip()
                if not new_title: return JsonResponse({"success": False, "error": _json_t("제목 필요", lang_code)}, status=400)
                dialog = get_object_or_404(ChatConversation, id=dialog_id, user=user)
                dialog.summary_title, dialog.is_custom_title = new_title, True
                dialog.save()
                return JsonResponse({"success": True, "title": new_title})
            except json.JSONDecodeError: return JsonResponse({"success": False, "error": _json_t("잘못된 요청")}, status=400)
        return JsonResponse({"success": False, "error": _json_t("POST 필요")}, status=405)