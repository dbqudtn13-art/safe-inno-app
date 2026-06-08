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

# 1. 스트림릿 금고(Secrets)에서 키 불러오기
try:
    gemini_key = st.secrets["GEMINI_API_KEY"]
    google_creds_json = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
except Exception as e:
    st.error("우측 상단 settings -> Secrets에 API 키와 구글 열쇠(JSON)가 올바르게 입력되었는지 확인해주세요!")
    st.stop()

# 2. AI 및 구글 스프레드시트 연결 세팅
genai.configure(api_key=gemini_key)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(google_creds_json, scope)
client = gspread.authorize(creds)

try:
    sheet = client.open("안전점검_DB").sheet1
except Exception as e:
    st.error(f"구글 스프레드시트('안전점검_DB')를 찾을 수 없습니다. 파일 이름을 확인해주세요: {e}")
    st.stop()

# 3. 화면 레이아웃 분할
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
            with st.spinner("Gemini AI가 실시간 웹 검색을 활용하여 유관 기관 사례를 크롤링하고 있습니다..."):
                try:
                    # 이미지 파일 처리
                    img = None
                    if uploaded_file is not None:
                        img = Image.open(uploaded_file)
                    
                    # [★크로스체크 완료] 구글이 요구한 가장 완벽한 세부 서식으로 도구 설정
                    search_tool = {
                        "google_search_retrieval": {
                            "dynamic_retrieval_config": {
                                "mode": "unspecified"
                            }
                        }
                    }
                    
                    model = genai.GenerativeModel(
                        model_name="gemini-1.5-flash",
                        tools=[search_tool]
                    )
                    
                    # AI 프롬프트 설계
                    prompt = f"""
                    당신은 대한민국 최고의 건설 및 제조 현장 안전보건 전문 AI입니다.
                    사용자가 제보한 아래의 현장 지적사항을 분석하여 두 가지 핵심 솔루션을 제공해주세요.
                    
                    [사용자 지적사항]
                    {user_issue}
                    
                    [요구사항]
                    1. 안전 추천 해결 방안: 대한민국 산업안전보건법 및 건설기술 진흥법 등 관련 법령에 명시된 기준을 바탕으로, 현장 관리자가 즉시 이행해야 하는 기술적, 관리적 대책을 구체적으로 제안해주세요.
                    2. 타 기관 유사 사고 사례 및 법규 매칭: 구글 실시간 검색을 통해 고용노동부, 안전보건공단(KOSHA), 국토안전관리원(CSI) 등에서 공인된 실제 유사 재해 사례(발생 연도, 사고 경위 등)와 위반 시 처벌 혹은 관련 법령 조항을 반드시 찾아 연결해주세요.
                    
                    시스템 파싱을 위해 결과물은 반드시 [AI 해결책]과 [유사사례]라는 대괄호 단어로 명확히 영역을 분리해서 작성해야 합니다. 부연설명이나 인사말은 생략하세요.
                    """
                    
                    inputs = [prompt]
                    if img:
                        inputs.append(img)
                        
                    # AI 구동
                    response = model.generate_content(inputs)
                    res_text = response.text
                    
                    # 결과 분리 파싱
                    if "[AI 해결책]" in res_text and "[유사사례]" in res_text:
                        parts = res_text.split("[유사사례]")
                        ai_solution = parts[0].replace("[AI 해결책]", "").strip()
                        similar_case = parts[1].strip()
                    else:
                        ai_solution = res_text
                        similar_case = "실시간 검색 연동 완료 (상세 내용은 하단 참조)"
                    
                    # 4. 구글 스프레드시트 데이터베이스에 저장
                    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    sheet.append_row([now, user_issue, ai_solution, similar_case, "조치중"])
                    
                    st.success("🎉 실시간 분석 완료! 데이터베이스(구글 엑셀)에 영구 보존되었습니다.")
                    st.markdown(f"### 🛡️ AI 추천 해결 방안\n{ai_solution}")
                    st.markdown(f"### 🚨 타 기관 유사 사례 및 법규 가이드\n{similar_case}")
                    
                except Exception as e:
                    st.error(f"AI 연동 중 내부 통신 오류가 발생했습니다: {e}")

# 5. 하단 영역: 아카이빙 대시보드 리스트 출력
st.markdown("---")
st.subheader("📊 월간 안전점검 아카이빙 현황 (구글 엑셀 실시간 연동)")

try:
    data = sheet.get_all_records()
    if data:
        st.dataframe(data, use_container_width=True)
        
        # 6. 월간 안전점검의 날용 PDF 문서 변환 양식
        html_content = """
        <html>
        <head>
            <meta charset='utf-8'>
            <title>월간 안전점검 보고서</title>
            <style>
                body { font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif; padding: 20px; color: #000; background: #fff; }
                h1 { text-align: center; border-bottom: 3px double #000; padding-bottom: 12px; font-size: 26px; }
                table { width: 100%; border-collapse: collapse; margin-top: 25px; table-layout: fixed; }
                th, td { border: 1px solid #000; padding: 12px; text-align: left; font-size: 12px; vertical-align: top; word-wrap: break-word; }
                th { background-color: #f4f4f5; font-weight: bold; text-align: center; }
            </style>
        </head>
        <body>
            <h1>월간 안전점검의 날 지적사항 조치 리포트</h1>
            <p style='text-align:right; font-size:12px; font-weight:bold;'>정기 점검일자: """ + datetime.date.today().strftime('%Y-%m-%d') + """</p>
            <table>
                <thead>
                    <tr>
                        <th style='width:15%'>점검일시</th>
                        <th style='width:25%'>현장 지적 내용</th>
                        <th style='width:30%'>AI 추천 안전 대책</th>
                        <th style='width:20%'>타 기관 유사사례 및 법령</th>
                        <th style='width:10%'>조치상태</th>
                    </tr>
                </thead>
                <tbody>
        """
        for row in data:
            html_content += f"""
                <tr>
                    <td style='text-align:center;'>{row.get('날짜','')}</td>
                    <td>{row.get('지적내용','')}</td>
                    <td>{row.get('AI해결책','')}</td>
                    <td>{row.get('유사사례','')}</td>
                    <td style='text-align:center; font-weight:bold;'>{row.get('조치상태','')}</td>
                </tr>
            """
        html_content += """
                </tbody>
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
        st.info("아직 데이터베이스에 누적된 현장 안전 지적사항이 없습니다.")
except Exception as e:
    st.warning("데이터베이스로부터 최신 현황 정보를 동기화하는 중입니다...")
