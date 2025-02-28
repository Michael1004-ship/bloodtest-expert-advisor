import os
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Body
import io
from google.cloud import vision
from openai import OpenAI
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import datetime
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict
from pathlib import Path
import re
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from fastapi import HTTPException
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import json

# .env 파일 로드
load_dotenv()

# 현재 파일의 디렉토리 경로 가져오기
BASE_DIR = Path(__file__).resolve().parent

# Google 인증 처리 부분 수정
if os.getenv('GOOGLE_CREDENTIALS'):
    # 환경변수에서 JSON 읽기
    google_creds = json.loads(os.getenv('GOOGLE_CREDENTIALS'))
    # JSON 파일 임시 생성
    with open('temp_credentials.json', 'w') as f:
        json.dump(google_creds, f)
    credentials_path = 'temp_credentials.json'
else:
    # 로컬 개발 환경용
    credentials_path = 'path/to/your/credentials.json'

print(f"Google Cloud 인증 파일 경로: {credentials_path}")
print(f"인증 파일 존재 여부: {os.path.exists(credentials_path)}")

app = FastAPI()

# CORS 설정 (한 번만 설정)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://bloodtest-expert-advisor.vercel.app"],  # 프론트엔드 도메인
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OpenAI 클라이언트 초기화
api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=api_key)

# 폰트 설정 (파일 상단으로 이동)
FONT_DIR = BASE_DIR / 'fonts'
NANUM_GOTHIC_PATH = FONT_DIR / 'NanumGothic.ttf'

# 폰트 등록 (전역 범위에서 한 번만 실행)
try:
    pdfmetrics.registerFont(TTFont('NanumGothic', './fonts/NanumGothic.ttf'))
except:
    print("NanumGothic 폰트 로드 실패, 기본 폰트를 사용합니다.")

def extract_text_from_image(image_data):
    """Google Cloud Vision API를 사용하여 이미지에서 텍스트 추출"""
    try:
        print("Starting text extraction...")
        
        # 인증 파일 존재 확인
        if not os.path.exists(credentials_path):
            raise Exception(f"Google Cloud 인증 파일을 찾을 수 없습니다: {credentials_path}")
        
        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=image_data)
        
        # 이미지 크기 확인
        print(f"Processing image of size: {len(image_data)} bytes")
        
        response = client.text_detection(image=image)
        print("Got response from Vision API")
        
        # 응답 확인
        if not response.text_annotations:
            print("No text found in image")
            return ""
        
        extracted_text = response.text_annotations[0].description
        print(f"Extracted text (first 100 chars): {extracted_text[:100]}...")
        return extracted_text
        
    except Exception as e:
        print(f"Error during text extraction: {str(e)}")
        print(f"Error type: {type(e)}")
        return ""

def clean_extracted_text(text):
    """OCR 결과를 정리하는 함수"""
    if not text:
        return ""
        
    # 기본적인 정리
    text = text.replace("\n", " ")
    text = re.sub(r'\s+', ' ', text)
    
    # 혈액검사 관련 특수문자 보존
    text = text.replace("↑", "↑ ")  # 화살표 뒤에 공백 추가
    text = text.replace("↓", "↓ ")
    
    # 단위 표기 보존
    text = re.sub(r'(\d+)([a-zA-Z]+)', r'\1 \2', text)  # 숫자와 단위 사이에 공백 추가
    
    return text.strip()

@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    try:
        print("OCR 요청 시작...")
        
        if not file:
            return {"error": "파일을 선택해주세요."}
            
        # 이미지 형식 확인
        allowed_types = ['image/jpeg', 'image/png', 'image/gif']
        if file.content_type not in allowed_types:
            return {"error": "지원되지 않는 파일 형식입니다. JPG, PNG, GIF 파일만 업로드 가능합니다."}
        
        image_data = await file.read()
        print(f"File size: {len(image_data)} bytes")
        
        # 텍스트 추출
        extracted_text = extract_text_from_image(image_data)
        if not extracted_text:
            return {"error": "텍스트를 추출할 수 없습니다. 이미지를 확인해주세요."}
        
        # 텍스트 정리
        cleaned_text = clean_extracted_text(extracted_text)
        print(f"Cleaned text: {cleaned_text[:100]}...")
        
        return {"text": cleaned_text}  # 분석 부분 제거
        
    except Exception as e:
        print(f"Upload error: {str(e)}")
        return {"error": f"파일 처리 중 오류가 발생했습니다: {str(e)}"}

# Request 모델 정의
class TextRequest(BaseModel):
    text: str

@app.post("/analyze")
async def analyze_text(request: TextRequest):
    try:
        if not request.text:
            raise HTTPException(status_code=400, detail="텍스트가 없습니다.")
            
        prompt = """임상병리학적 전문 분석 보고서를 작성해주세요. 병리학 전문의가 참고할 수 있도록 매우 전문적인 용어와 최신 의학 지식을 포함하여 작성해주세요.

[임상병리학적 분석 보고서]

1. 검체 분석 결과
| Parameter | Measured Value | Reference Range | Deviation | Clinical Significance |
(각 수치를 SI 단위로 표기하고, 참고치 대비 편차 표시)

2. 병태생리학적 평가
A. 산염기 균형 상태
- Blood Gas Analysis
- Henderson-Hasselbalch Equation 기반 평가
- Anion Gap 분석
- Base Excess/Deficit 해석

B. 호흡기능 평가
- Oxygenation Status
- Ventilation Efficiency
- A-a Gradient 분석
- PaO2/FiO2 Ratio 평가

C. 대사성 상태 평가
- Metabolic Component Analysis
- Compensatory Mechanism 평가
- Winter's Formula 적용 결과
- Delta Gap 분석 (해당 시)

3. 분자생물학적/생화학적 해석
- 각 이상수치의 병태생리학적 기전
- Metabolic Pathway 영향 분석
- Cellular Level Impact 평가
- Potential Molecular Markers 제시

4. 감별진단학적 고찰
- Primary Differential Diagnoses
- Pathophysiological Mechanisms
- Related Biochemical Pathways
- Suggested Additional Markers

5. 임상적 중요도 평가
- Critical Values 판정
- Immediate Clinical Implications
- Risk Stratification
- Therapeutic Window 고려사항

6. 추가 검사 제안
- Confirmatory Tests
- Monitoring Parameters
- Molecular/Genetic Testing 필요성
- Time-sensitive Follow-up 고려사항

7. 학술적 참고사항
- Recent Clinical Guidelines (발행연도 포함)
- Relevant Research Papers
- Meta-analyses References
- Current Clinical Trials

분석할 검체 결과:
{text}

※ 모든 수치 해석은 최신 임상병리학 가이드라인을 기반으로 하며, 관련 문헌 참고를 포함합니다.
※ SI 단위계 사용을 원칙으로 하되, 필요시 기존 단위를 병기합니다.
※ Critical values는 즉시 보고 대상으로 별도 표시합니다."""

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": """You are a highly specialized clinical pathologist with extensive experience in laboratory medicine and molecular diagnostics. 
                Provide extremely detailed, academic-level analysis using professional medical terminology and current scientific evidence. 
                Include specific molecular pathways, biochemical mechanisms, and relevant clinical research. 
                Response should be in Korean, but use international scientific terms where appropriate. 
                Maintain highest level of professional medical writing standards."""},
                {"role": "user", "content": prompt.format(text=request.text)}
            ],
            temperature=0.1,  # 매우 일관된 전문적 응답을 위해 낮은 temperature 사용
            max_tokens=3000   # 상세한 전문 분석을 위해 토큰 수 증가
        )
        
        return {"analysis": response.choices[0].message.content}
    except Exception as e:
        print(f"Analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Request 모델 정의
class ReportRequest(BaseModel):
    text: str

@app.post("/generate_report")
async def generate_pdf_report(request: ReportRequest):
    try:
        if not request.text:
            return {"error": "텍스트가 없습니다."}

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=50
        )

        # 스타일 정의
        styles = getSampleStyleSheet()
        font_name = 'NanumGothic' if 'NanumGothic' in pdfmetrics.getRegisteredFontNames() else 'Helvetica'
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontName=font_name,
            fontSize=20,
            leading=24,
            alignment=1,
            spaceAfter=30,
            textColor=colors.HexColor('#2C3E50')
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading1'],
            fontName=font_name,
            fontSize=14,
            leading=18,
            spaceBefore=20,
            spaceAfter=10,
            textColor=colors.HexColor('#34495E')
        )

        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=10,
            leading=14,
            spaceBefore=8,
            spaceAfter=8,
            firstLineIndent=20
        )

        bullet_style = ParagraphStyle(
            'CustomBullet',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=10,
            leading=14,
            leftIndent=30,
            spaceBefore=4,
            spaceAfter=4
        )

        elements = []
        
        # 제목 및 날짜 추가
        elements.append(Paragraph("임상병리학적 분석 보고서", title_style))
        elements.append(Paragraph(
            f"보고서 생성일시: {datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분')}",
            normal_style
        ))
        elements.append(Spacer(1, 30))

        # 본문 내용 처리
        current_section = []
        in_table = False
        table_data = []

        for line in request.text.split('\n'):
            line = line.strip()
            if not line:
                if in_table and table_data:
                    # 표 생성
                    table = Table(table_data)
                    table.setStyle(TableStyle([
                        ('FONTNAME', (0, 0), (-1, -1), font_name),
                        ('FONTSIZE', (0, 0), (-1, 0), 10),
                        ('FONTSIZE', (0, 1), (-1, -1), 9),
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F5F6FA')),
                        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2C3E50')),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#BDC3C7')),
                        ('PADDING', (0, 0), (-1, -1), 6),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ]))
                    elements.append(table)
                    elements.append(Spacer(1, 10))
                    table_data = []
                    in_table = False
                continue

            # 표 처리
            if '|' in line:
                in_table = True
                row = [cell.strip() for cell in line.split('|') if cell.strip()]
                if row:
                    table_data.append(row)
                continue

            # 섹션 제목 처리
            if any(line.startswith(str(i)) for i in range(1, 8)) or line.endswith(':'):
                elements.append(Paragraph(line, heading_style))
                continue

            # 글머리 기호 처리
            if line.startswith('- ') or line.startswith('• '):
                elements.append(Paragraph(line, bullet_style))
                continue

            # 일반 텍스트 처리
            elements.append(Paragraph(line, normal_style))

        # PDF 생성
        doc.build(elements)
        buffer.seek(0)

        # 파일명 생성
        current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"clinical_lab_report_{current_time}.pdf"

        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )

    except Exception as e:
        print(f"PDF 생성 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "Welcome to Blood Test Analysis API"}
