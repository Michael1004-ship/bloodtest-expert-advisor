import React, { useState } from "react";
import axios from "axios";

// 백엔드 URL을 환경변수로 관리
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'https://bloodtest-advisor-backend.onrender.com';

const UploadBloodTest = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [extractedText, setExtractedText] = useState("");
  const [aiAnalysis, setAiAnalysis] = useState("");
  const [message, setMessage] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleFileChange = (event) => {
    setSelectedFile(event.target.files[0]);
    setMessage("");
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setMessage("파일을 선택해주세요.");
      return;
    }

    try {
      setLoading(true);
      const formData = new FormData();
      formData.append('file', selectedFile);

      const uploadResponse = await axios.post(`${BACKEND_URL}/upload`, formData);
      setExtractedText(uploadResponse.data.text);

      if (uploadResponse.data.text) {
        const analyzeResponse = await axios.post(`${BACKEND_URL}/analyze`, {
          text: uploadResponse.data.text
        });
        setAiAnalysis(analyzeResponse.data.analysis);
      }
    } catch (error) {
      console.error('Error:', error);
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateReport = async () => {
    try {
      const response = await axios.post(`${BACKEND_URL}/generate_report`,
        { text: aiAnalysis },
        {
          responseType: 'blob',
          headers: { 'Content-Type': 'application/json' }
        }
      );

      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;

      const now = new Date();
      const filename = `clinical_lab_report_${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}_${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}.pdf`;

      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      setMessage("PDF 생성이 완료되었습니다.");
    } catch (error) {
      console.error("PDF 생성 오류:", error);
      setError('PDF 생성 중 오류가 발생했습니다.');
    }
  };

  return (
    <div className="blood-test-container">
      <div className="header">
        <h1>혈액검사 분석 AI</h1>
        <p>혈액검사 결과 이미지를 업로드하면 AI가 분석해드립니다</p>
      </div>

      <div className="upload-section">
        <div className="file-input-container">
          <input
            type="file"
            onChange={handleFileChange}
            accept="image/*"
            className="file-input"
          />
          {selectedFile && (
            <button onClick={handleUpload} className="upload-button">
              업로드
            </button>
          )}
        </div>
      </div>

      {loading && (
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>분석 중입니다...</p>
        </div>
      )}

      {extractedText && (
        <div className="result-section">
          <div className="extracted-text">
            <h3>추출된 텍스트</h3>
            <pre>{extractedText}</pre>
          </div>
        </div>
      )}

      {aiAnalysis && !loading && (
        <div className="analysis-result">
          <h3>분석 결과</h3>
          <pre>{aiAnalysis}</pre>
          <button
            onClick={handleGenerateReport}
            className="generate-pdf-button"
          >
            PDF 생성
          </button>
        </div>
      )}

      {error && <p className="error">{error}</p>}
      {message && <p className="message">{message}</p>}
    </div>
  );
};

// 스타일 정의
const styles = `
  .blood-test-container {
    max-width: 800px;
    margin: 0 auto;
    padding: 20px;
  }

  .header {
    text-align: center;
    margin-bottom: 30px;
  }

  .header h1 {
    color: #2c3e50;
    margin-bottom: 10px;
  }

  .header p {
    color: #7f8c8d;
  }

  .upload-section {
    background-color: #f8f9fa;
    padding: 20px;
    border-radius: 8px;
    margin-bottom: 20px;
  }

  .file-input-container {
    display: flex;
    gap: 10px;
    align-items: center;
  }

  .file-input {
    flex: 1;
    padding: 10px;
    border: 1px solid #ddd;
    border-radius: 4px;
  }

  .upload-button, .analyze-button, .generate-pdf-button {
    padding: 10px 20px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-weight: bold;
    transition: background-color 0.3s;
  }

  .upload-button {
    background-color: #4CAF50;
    color: white;
  }

  .analyze-button {
    background-color: #2196F3;
    color: white;
    margin-top: 15px;
  }

  .generate-pdf-button {
    background-color: #ff9800;
    color: white;
    margin-top: 15px;
  }

  .result-section {
    margin-top: 20px;
  }

  .extracted-text, .analysis-result {
    background-color: white;
    padding: 20px;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    margin-bottom: 20px;
  }

  .extracted-text h3, .analysis-result h3 {
    color: #2c3e50;
    margin-bottom: 15px;
  }

  pre {
    background-color: #f8f9fa;
    padding: 15px;
    border-radius: 4px;
    white-space: pre-wrap;
    word-wrap: break-word;
  }

  .message {
    text-align: center;
    padding: 10px;
    margin-top: 10px;
    border-radius: 4px;
    background-color: #e3f2fd;
    color: #1976d2;
  }
`;

// 스타일 적용
const styleSheet = document.createElement("style");
styleSheet.innerText = styles;
document.head.appendChild(styleSheet);

export default UploadBloodTest;

