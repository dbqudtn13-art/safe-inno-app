import streamlit as st
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
from PIL import Image
import json

# 웹페이지 기본 설정
st.set_page_config(page_title="Safe-Inno Pro", page_icon="🚨", layout="wide")

st.title("🚨 Safe-Inno Pro | AI 디지털 안전혁신 플랫폼")
st.write("사진과 지적사항을 입력하면 AI가 실시간 웹 검색을 통해 해결책과 타 기관 유사사례를 찾아 아카이빙합니다.")

# 1. 안전하게 숨겨둔 비밀번호(Secrets) 불러오기
try:
    gemini_key = st.secrets["GEMINI_API_KEY"]
    google_creds_json = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
except Exception as e:
    st.error("오른쪽 App settings -> Secrets에 API 키와 구글 열쇠(JSON)를 입력해주세요!")
    st.stop()

# 2. AI 및 데이터베이스 연결 세팅
genai.configure(api_key=gemini_key)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(google_creds_json, scope)
client = gspread.authorize(creds)

# 아까 만든 구글 엑셀 파일 열기
try:
    sheet = client.open("안전점검_DB").sheet1
except Exception as e:
    st.error(f"구글 스프레드시트('안전점검_DB')를 찾을 수 없습니다: {e}")
    st.stop()

# 3. 화면 레이아웃 나누기 (좌측: 입력, 우측: AI결과)
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("✍️ 신규 안전 지적사항 등록")
    uploaded_file = st.file_uploader("현장 사진 업로드 (선택)", type=["png", "jpg", "jpeg"])
    user_issue = st.text_area("지적사항 상세 입력", placeholder="예: 3층 외부 비계 안전난간대 일부 파손 및 추락 위험 존재.")
    
    submit_btn = st.button("⚡ AI 실시간 분석 및 아카이빙 등록")

with col2:
    st.subheader("🧠 AI 실시간 연동 진단 결과")
    
    if submit_btn:
        if not user_issue:
            st.warning("지적사항 내용을 입력해주세요!")
        else:
            with st.spinner("Gemini AI가 실시간 웹 검색(Search Grounding)을 활용하여 유사 사례를 크롤링하고 있습니다..."):
                try:
                    # 이미지 처리
                    img = None
                    if uploaded_file is not None:
                        img = Image.open(uploaded_file)
                    
                    # 실시간 웹 검색 기능이 탑재된 최신 Gemini 모델 호출
                    model = genai.GenerativeModel(
                        model_name="gemini-1.5-pro",
                        tools=[{"google_search": {}}]
                    )
                    
                    # AI에게 줄 명령문(프롬프트)
                    prompt = f"""
                    당신은 대한민국 최고의 건설/제조 현장 안전 전문 AI입니다.
                    사용자가 작성한 아래의 지적사항을 바탕으로 두 가지를 작성해주세요.
                    
                    [사용자 지적사항]
                    {user_issue}
                    
                    [요구사항]
                    1. 안전 추천 해결 방안: 산업안전보건법 등 관련 법령에 근거하여 현장에서 즉시 실시해야 하는 기술적/관리적 대책을 구체적으로 제안해주세요.
                    2. 타 기관 유사 사고 사례 및 법규 매칭: 실시간 구글 검색을 활용하여 안전보건공단(KOSHA), 국토안전관리원(CSI), 고용노동부 등에서 발표한 실제 유사 사고 사례(연도 및 사고 개요)와 관련 처벌/법규 조항을 찾아주세요.
                    
                    구분하기 쉽도록 딱 [AI 해결책]과 [유사사례]라는 단어로 명확히 나누어 작성해주세요. 다른 부연설명은 생략하세요.
                    """
                    
                    inputs = [prompt]
                    if img:
                        inputs.append(img)
                        
                    # AI 실행
                    response = model.generate_content(inputs)
                    res_text = response.text
                    
                    # 텍스트 나누기 파싱
                    if "[AI 해결책]" in res_text and "[유사사례]" in res_text:
                        parts = res_text.split("[유사사례]")
                        ai_solution = parts[0].replace("[AI 해결책]", "").strip()
                        similar_case = parts[1].strip()
                    else:
                        ai_solution = res_text
                        similar_case = "실시간 검색 연동 완료 (상세 내용은 본문 참조)"
                    
                    # 4. 구글 스프레드시트(엑셀)에 저장하기
                    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    sheet.append_row([now, user_issue, ai_solution, similar_case, "조치중"])
                    
                    st.success("🎉 실시간 분석 완료! 데이터베이스(구글 엑셀)에 성공적으로 저장되었습니다.")
                    st.markdown(f"### 🛡️ AI 추천 해결 방안\n{ai_solution}")
                    st.markdown(f"### 🚨 타 기관 유사 사례 및 법규\n{similar_case}")
                    
                except Exception as e:
                    st.error(f"AI 연동 중 오류가 발생했습니다: {e}")

# 5. 하단: 아카이빙 대시보드 현황판
st.markdown("---")
st.subheader("📊 월간 안전점검 아카이빙 현황 (구글 엑셀 실시간 연동)")

try:
    data = sheet.get_all_records()
    if data:
        # 표 형태로 데이터 보여주기
        st.dataframe(data, use_container_width=True)
        
        # 6. 비전공자 맞춤형 원클릭 PDF(인쇄) 보고서 빌드 스크립트
        html_content = """
        <html>
        <head>
            <meta charset='utf-8'>
            <title>월간 안전점검 보고서</title>
            <style>
                body { font-family: 'Malgun Gothic', sans-serif; padding: 20px; color: #000; background: #fff; }
                h1 { text-align: center; border-bottom: 2px solid #000; padding-bottom: 10px; font-size: 24px; }
                table { width: 100%; border-collapse: collapse; margin-top: 20px; }
                th, td { border: 1px solid #000; padding: 10px; text-align: left; font-size: 12px; vertical-align: top; }
                th { background-color: #f2f2f2; font-weight: bold; }
            </style>
        </head>
        <body>
            <h1>월간 안전점검의 날 지적사항 조치 리포트</h1>
            <p style='text-align:right; font-size:12px;'>출력일시: """ + datetime.date.today().strftime('%Y-%m-%d') + """</p>
            <table>
                <tr>
                    <th style='width:15%'>날짜</th>
                    <th style='width:25%'>점검 지적 내용</th>
                    <th style='width:30%'>AI 추천 해결 솔루션</th>
                    <th style='width:20%'>타 기관 유사사례 및 법규</th>
                    <th style='width:10%'>상태</th>
                </tr>
        """
        for row in data:
            html_content += f"""
                <tr>
                    <td>{row.get('날짜','')}</td>
                    <td>{row.get('지적내용','')}</td>
                    <td>{row.get('AI해결책','')}</td>
                    <td>{row.get('유사사례','')}</td>
                    <td>{row.get('조치상태','')}</td>
                </tr>
            """
        html_content += """
            </table>
            <script>window.onload = function() { window.print(); }</script>
        </body>
        </html>
        """
        
        st.download_button(
            label="📄 월간 안전점검 보고서 다운로드 (인쇄/PDF 저장용)",
            data=html_content,
            file_name=f"안전점검_보고서_{datetime.date.today().strftime('%m월')}.html",
            mime="text/html"
        )
    else:
        st.info("아직 엑셀에 저장된 지적사항 데이터가 없습니다.")
except Exception as e:
    st.warning(f"데이터베이스를 불러오는 중입니다... {e}")
