import React, { useState, useCallback, useRef } from 'react';
import styled from 'styled-components';
import { useDropzone } from 'react-dropzone';
import Papa from 'papaparse';
import * as XLSX from 'xlsx';
import { ko } from '../../i18n/locales/ko';

// 스타일드 컴포넌트
const UploadContainer = styled.div`
  max-width: 800px;
  margin: 0 auto;
  padding: 24px;
`;

const DropzoneArea = styled.div`
  border: 2px dashed ${props => props.isDragActive ? '#667eea' : '#d1d5db'};
  border-radius: 12px;
  padding: 48px 24px;
  text-align: center;
  background: ${props => props.isDragActive ? '#f0f4ff' : '#fafbfc'};
  transition: all 0.3s ease;
  cursor: pointer;
  
  &:hover {
    border-color: #667eea;
    background: #f0f4ff;
  }
  
  .upload-icon {
    font-size: 48px;
    color: #9ca3af;
    margin-bottom: 16px;
  }
  
  .upload-text {
    font-size: 18px;
    font-weight: 600;
    color: #374151;
    margin-bottom: 8px;
  }
  
  .upload-subtitle {
    font-size: 14px;
    color: #6b7280;
    margin-bottom: 16px;
  }
  
  .upload-formats {
    font-size: 12px;
    color: #9ca3af;
  }
`;

const ProgressContainer = styled.div`
  margin: 24px 0;
`;

const ProgressBar = styled.div`
  width: 100%;
  height: 8px;
  background: #e5e7eb;
  border-radius: 4px;
  overflow: hidden;
  
  .progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #667eea, #764ba2);
    width: ${props => props.progress}%;
    transition: width 0.3s ease;
  }
`;

const ProgressText = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
  font-size: 14px;
  color: #6b7280;
`;

const ValidationContainer = styled.div`
  margin: 24px 0;
  padding: 20px;
  background: white;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
`;

const ValidationHeader = styled.div`
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  
  .status-icon {
    font-size: 20px;
  }
  
  .status-success { color: #10b981; }
  .status-warning { color: #f59e0b; }
  .status-error { color: #ef4444; }
  
  .status-text {
    font-weight: 600;
    font-size: 16px;
  }
`;

const ValidationStats = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 16px;
  margin-bottom: 16px;
  
  .stat-item {
    text-align: center;
    padding: 12px;
    background: #f9fafb;
    border-radius: 8px;
    
    .stat-number {
      font-size: 24px;
      font-weight: 700;
      margin-bottom: 4px;
    }
    
    .stat-label {
      font-size: 12px;
      color: #6b7280;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    
    &.valid .stat-number { color: #10b981; }
    &.warning .stat-number { color: #f59e0b; }
    &.error .stat-number { color: #ef4444; }
  }
`;

const ErrorList = styled.div`
  max-height: 200px;
  overflow-y: auto;
  
  .error-item {
    padding: 8px 12px;
    margin-bottom: 4px;
    background: #fef2f2;
    border: 1px solid #fecaca;
    border-radius: 6px;
    font-size: 14px;
    
    .error-row {
      font-weight: 600;
      color: #dc2626;
    }
    
    .error-message {
      color: #991b1b;
      margin-top: 4px;
    }
  }
`;

const PreviewTable = styled.div`
  margin: 24px 0;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid #e5e7eb;
  
  .table-header {
    background: #f9fafb;
    padding: 16px;
    border-bottom: 1px solid #e5e7eb;
    font-weight: 600;
    font-size: 16px;
  }
  
  .table-content {
    overflow-x: auto;
    
    table {
      width: 100%;
      border-collapse: collapse;
      
      th, td {
        padding: 12px;
        text-align: left;
        border-bottom: 1px solid #f3f4f6;
        font-size: 14px;
      }
      
      th {
        background: #f9fafb;
        font-weight: 600;
        color: #374151;
        position: sticky;
        top: 0;
      }
      
      td {
        color: #6b7280;
      }
      
      tr:hover {
        background: #f9fafb;
      }
    }
  }
`;

const ActionButtons = styled.div`
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 24px;
  
  @media (max-width: 640px) {
    flex-direction: column;
  }
`;

const Button = styled.button`
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 500;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s ease;
  border: none;
  
  &.primary {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    
    &:hover:not(:disabled) {
      box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
      transform: translateY(-1px);
    }
  }
  
  &.secondary {
    background: white;
    color: #374151;
    border: 1px solid #d1d5db;
    
    &:hover:not(:disabled) {
      background: #f9fafb;
      border-color: #9ca3af;
    }
  }
  
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  
  @media (max-width: 640px) {
    width: 100%;
    justify-content: center;
  }
`;

// CSV 업로드 컴포넌트
const CSVUploadComponent = ({ 
  onUpload, 
  onValidationComplete,
  acceptedFormats = ['.csv', '.xlsx', '.xls'],
  maxFileSize = 10 * 1024 * 1024, // 10MB
  requiredColumns = [],
  validationRules = {},
  className = ''
}) => {
  const [uploadState, setUploadState] = useState('idle'); // idle, uploading, processing, validating, complete, error
  const [progress, setProgress] = useState(0);
  const [file, setFile] = useState(null);
  const [csvData, setCsvData] = useState([]);
  const [validationResults, setValidationResults] = useState(null);
  const [previewData, setPreviewData] = useState([]);
  const fileInputRef = useRef(null);

  // 파일 검증 함수
  const validateFile = (file) => {
    const errors = [];
    
    // 파일 크기 검증
    if (file.size > maxFileSize) {
      errors.push(`파일 크기가 너무 큽니다. 최대 ${Math.round(maxFileSize / 1024 / 1024)}MB까지 업로드 가능합니다.`);
    }
    
    // 파일 형식 검증
    const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
    if (!acceptedFormats.includes(fileExtension)) {
      errors.push(`지원하지 않는 파일 형식입니다. (${acceptedFormats.join(', ')})`);
    }
    
    return errors;
  };

  // CSV 데이터 검증 함수
  const validateCSVData = (data) => {
    const errors = [];
    const warnings = [];
    const validRows = [];
    const errorRows = [];
    
    if (!data || data.length === 0) {
      return {
        isValid: false,
        errors: ['파일이 비어있습니다.'],
        warnings: [],
        validRows: [],
        errorRows: [],
        stats: { total: 0, valid: 0, errors: 0, warnings: 0 }
      };
    }

    const headers = Object.keys(data[0] || {});
    
    // 필수 컬럼 검증
    const missingColumns = requiredColumns.filter(col => !headers.includes(col));
    if (missingColumns.length > 0) {
      errors.push(`필수 컬럼이 누락되었습니다: ${missingColumns.join(', ')}`);
    }

    // 각 행 검증
    data.forEach((row, index) => {
      const rowErrors = [];
      const rowWarnings = [];
      
      // 빈 행 체크
      const hasData = Object.values(row).some(value => value && value.toString().trim() !== '');
      if (!hasData) {
        rowWarnings.push('빈 행입니다.');
      }
      
      // 커스텀 검증 규칙 적용
      Object.entries(validationRules).forEach(([column, rules]) => {
        const value = row[column];
        
        if (rules.required && (!value || value.toString().trim() === '')) {
          rowErrors.push(`${column}: 필수 값이 누락되었습니다.`);
        }
        
        if (value && rules.type) {
          switch (rules.type) {
            case 'number':
              if (isNaN(Number(value))) {
                rowErrors.push(`${column}: 숫자 형식이 아닙니다.`);
              }
              break;
            case 'email':
              const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
              if (!emailRegex.test(value)) {
                rowErrors.push(`${column}: 이메일 형식이 올바르지 않습니다.`);
              }
              break;
            case 'date':
              if (isNaN(Date.parse(value))) {
                rowErrors.push(`${column}: 날짜 형식이 올바르지 않습니다.`);
              }
              break;
          }
        }
        
        if (value && rules.min && Number(value) < rules.min) {
          rowErrors.push(`${column}: 최소값 ${rules.min}보다 작습니다.`);
        }
        
        if (value && rules.max && Number(value) > rules.max) {
          rowErrors.push(`${column}: 최대값 ${rules.max}보다 큽니다.`);
        }
        
        if (value && rules.pattern && !new RegExp(rules.pattern).test(value)) {
          rowErrors.push(`${column}: 형식이 올바르지 않습니다.`);
        }
      });
      
      if (rowErrors.length > 0) {
        errorRows.push({ index: index + 1, errors: rowErrors });
      } else {
        validRows.push(row);
      }
      
      if (rowWarnings.length > 0) {
        warnings.push({ index: index + 1, warnings: rowWarnings });
      }
    });

    return {
      isValid: errors.length === 0 && errorRows.length === 0,
      errors,
      warnings,
      validRows,
      errorRows,
      stats: {
        total: data.length,
        valid: validRows.length,
        errors: errorRows.length,
        warnings: warnings.length
      }
    };
  };

  // 파일 파싱 함수
  const parseFile = async (file) => {
    return new Promise((resolve, reject) => {
      const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
      
      if (fileExtension === '.csv') {
        // CSV 파싱
        Papa.parse(file, {
          header: true,
          skipEmptyLines: true,
          complete: (results) => {
            if (results.errors.length > 0) {
              reject(new Error('CSV 파싱 중 오류가 발생했습니다: ' + results.errors[0].message));
            } else {
              resolve(results.data);
            }
          },
          error: (error) => {
            reject(new Error('CSV 파일을 읽을 수 없습니다: ' + error.message));
          }
        });
      } else if (['.xlsx', '.xls'].includes(fileExtension)) {
        // Excel 파싱
        const reader = new FileReader();
        reader.onload = (e) => {
          try {
            const data = new Uint8Array(e.target.result);
            const workbook = XLSX.read(data, { type: 'array' });
            const sheetName = workbook.SheetNames[0];
            const worksheet = workbook.Sheets[sheetName];
            const jsonData = XLSX.utils.sheet_to_json(worksheet);
            resolve(jsonData);
          } catch (error) {
            reject(new Error('Excel 파일을 읽을 수 없습니다: ' + error.message));
          }
        };
        reader.onerror = () => reject(new Error('파일을 읽을 수 없습니다.'));
        reader.readAsArrayBuffer(file);
      } else {
        reject(new Error('지원하지 않는 파일 형식입니다.'));
      }
    });
  };

  // 파일 처리 함수
  const processFile = async (file) => {
    try {
      setUploadState('processing');
      setProgress(20);

      // 파일 파싱
      const data = await parseFile(file);
      setProgress(50);
      
      setCsvData(data);
      setPreviewData(data.slice(0, 5)); // 첫 5행만 미리보기
      
      setUploadState('validating');
      setProgress(70);
      
      // 데이터 검증
      const validation = validateCSVData(data);
      setValidationResults(validation);
      setProgress(100);
      
      setUploadState('complete');
      
      // 검증 완료 콜백
      if (onValidationComplete) {
        onValidationComplete(validation, data);
      }
      
    } catch (error) {
      console.error('파일 처리 중 오류:', error);
      setUploadState('error');
      setValidationResults({
        isValid: false,
        errors: [error.message],
        warnings: [],
        validRows: [],
        errorRows: [],
        stats: { total: 0, valid: 0, errors: 1, warnings: 0 }
      });
    }
  };

  // 드래그 앤 드롭 설정
  const onDrop = useCallback(async (acceptedFiles) => {
    const uploadedFile = acceptedFiles[0];
    if (!uploadedFile) return;

    const fileErrors = validateFile(uploadedFile);
    if (fileErrors.length > 0) {
      setValidationResults({
        isValid: false,
        errors: fileErrors,
        warnings: [],
        validRows: [],
        errorRows: [],
        stats: { total: 0, valid: 0, errors: fileErrors.length, warnings: 0 }
      });
      setUploadState('error');
      return;
    }

    setFile(uploadedFile);
    setProgress(0);
    setUploadState('uploading');
    
    // 업로드 진행률 시뮬레이션
    setTimeout(() => processFile(uploadedFile), 500);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls']
    },
    maxFiles: 1,
    disabled: uploadState === 'uploading' || uploadState === 'processing' || uploadState === 'validating'
  });

  // 업로드 처리
  const handleUpload = async () => {
    if (!validationResults?.isValid || !csvData.length) return;
    
    try {
      if (onUpload) {
        await onUpload(validationResults.validRows, file);
      }
    } catch (error) {
      console.error('업로드 처리 중 오류:', error);
    }
  };

  // 초기화
  const handleReset = () => {
    setUploadState('idle');
    setProgress(0);
    setFile(null);
    setCsvData([]);
    setValidationResults(null);
    setPreviewData([]);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // 상태별 메시지
  const getStatusMessage = () => {
    switch (uploadState) {
      case 'uploading':
        return '파일 업로드 중...';
      case 'processing':
        return '파일 처리 중...';
      case 'validating':
        return '데이터 검증 중...';
      case 'complete':
        return validationResults?.isValid ? '검증 완료' : '검증 실패';
      case 'error':
        return '오류 발생';
      default:
        return '';
    }
  };

  return (
    <UploadContainer className={className}>
      {/* 파일 업로드 영역 */}
      {uploadState === 'idle' && (
        <DropzoneArea {...getRootProps()} isDragActive={isDragActive}>
          <input {...getInputProps()} ref={fileInputRef} />
          <div className="upload-icon">📄</div>
          <div className="upload-text">
            {isDragActive ? '파일을 여기에 놓으세요' : '파일을 드래그하거나 클릭하여 업로드'}
          </div>
          <div className="upload-subtitle">
            CSV, Excel 파일을 지원합니다
          </div>
          <div className="upload-formats">
            지원 형식: {acceptedFormats.join(', ')} | 최대 크기: {Math.round(maxFileSize / 1024 / 1024)}MB
          </div>
        </DropzoneArea>
      )}

      {/* 진행률 표시 */}
      {['uploading', 'processing', 'validating'].includes(uploadState) && (
        <ProgressContainer>
          <ProgressBar progress={progress}>
            <div className="progress-fill" />
          </ProgressBar>
          <ProgressText>
            <span>{getStatusMessage()}</span>
            <span>{progress}%</span>
          </ProgressText>
        </ProgressContainer>
      )}

      {/* 파일 정보 */}
      {file && (
        <div style={{ 
          margin: '16px 0', 
          padding: '12px', 
          background: '#f9fafb', 
          borderRadius: '8px',
          fontSize: '14px'
        }}>
          <strong>파일:</strong> {file.name} ({Math.round(file.size / 1024)}KB)
        </div>
      )}

      {/* 검증 결과 */}
      {validationResults && (
        <ValidationContainer>
          <ValidationHeader>
            <span className={`status-icon ${
              validationResults.isValid ? 'status-success' : 
              validationResults.errors.length > 0 ? 'status-error' : 'status-warning'
            }`}>
              {validationResults.isValid ? '✅' : validationResults.errors.length > 0 ? '❌' : '⚠️'}
            </span>
            <span className="status-text">
              {validationResults.isValid ? '검증 성공' : '검증 실패'}
            </span>
          </ValidationHeader>

          {/* 통계 */}
          <ValidationStats>
            <div className="stat-item">
              <div className="stat-number">{validationResults.stats.total}</div>
              <div className="stat-label">총 행수</div>
            </div>
            <div className="stat-item valid">
              <div className="stat-number">{validationResults.stats.valid}</div>
              <div className="stat-label">유효한 행</div>
            </div>
            {validationResults.stats.errors > 0 && (
              <div className="stat-item error">
                <div className="stat-number">{validationResults.stats.errors}</div>
                <div className="stat-label">오류 행</div>
              </div>
            )}
            {validationResults.stats.warnings > 0 && (
              <div className="stat-item warning">
                <div className="stat-number">{validationResults.stats.warnings}</div>
                <div className="stat-label">경고 행</div>
              </div>
            )}
          </ValidationStats>

          {/* 오류 목록 */}
          {(validationResults.errors.length > 0 || validationResults.errorRows.length > 0) && (
            <ErrorList>
              {validationResults.errors.map((error, index) => (
                <div key={index} className="error-item">
                  <div className="error-message">{error}</div>
                </div>
              ))}
              {validationResults.errorRows.slice(0, 10).map((errorRow, index) => (
                <div key={index} className="error-item">
                  <div className="error-row">행 {errorRow.index}</div>
                  <div className="error-message">{errorRow.errors.join(', ')}</div>
                </div>
              ))}
              {validationResults.errorRows.length > 10 && (
                <div className="error-item">
                  <div className="error-message">
                    ...그리고 {validationResults.errorRows.length - 10}개 행에 추가 오류가 있습니다.
                  </div>
                </div>
              )}
            </ErrorList>
          )}
        </ValidationContainer>
      )}

      {/* 데이터 미리보기 */}
      {previewData.length > 0 && (
        <PreviewTable>
          <div className="table-header">데이터 미리보기 (첫 5행)</div>
          <div className="table-content">
            <table>
              <thead>
                <tr>
                  {Object.keys(previewData[0]).map((header, index) => (
                    <th key={index}>{header}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {previewData.map((row, index) => (
                  <tr key={index}>
                    {Object.values(row).map((value, cellIndex) => (
                      <td key={cellIndex}>{value}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </PreviewTable>
      )}

      {/* 액션 버튼 */}
      {uploadState !== 'idle' && (
        <ActionButtons>
          <Button 
            className="secondary" 
            onClick={handleReset}
          >
            다시 업로드
          </Button>
          {validationResults?.isValid && (
            <Button 
              className="primary" 
              onClick={handleUpload}
            >
              데이터 가져오기 ({validationResults.stats.valid}행)
            </Button>
          )}
        </ActionButtons>
      )}
    </UploadContainer>
  );
};

export default CSVUploadComponent;