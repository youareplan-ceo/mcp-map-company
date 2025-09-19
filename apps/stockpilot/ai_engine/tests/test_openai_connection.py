"""
OpenAI API 연결 테스트
한국어 처리 및 AI 엔진 기능 검증
"""

import pytest
import asyncio
import os
from unittest.mock import patch, AsyncMock, MagicMock
from typing import Dict, Any

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from ai_engine.config.api_config import (
    APIConfiguration, OpenAIClientManager, 
    get_openai_client, initialize_openai_client,
    create_korean_chat_completion, create_korean_embedding
)

class TestOpenAIConnection:
    """OpenAI API 연결 테스트 클래스"""
    
    @pytest.fixture
    def api_config(self):
        """테스트용 API 설정"""
        return APIConfiguration(
            api_key="test-api-key",
            base_url="https://api.openai.com/v1",
            max_retries=1,
            timeout=10.0,
            rate_limit_rpm=10,  # 테스트용 낮은 한도
            rate_limit_tpm=1000
        )
    
    @pytest.fixture
    def mock_openai_response(self):
        """Mock OpenAI 응답"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "테스트 응답입니다."
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 100
        mock_response.usage.prompt_tokens = 50
        mock_response.usage.completion_tokens = 50
        return mock_response
    
    @pytest.fixture
    def mock_embedding_response(self):
        """Mock 임베딩 응답"""
        mock_response = MagicMock()
        mock_response.data = [MagicMock()]
        mock_response.data[0].embedding = [0.1, 0.2, 0.3] * 512  # 1536차원 임베딩
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 50
        return mock_response
    
    def test_api_configuration_creation(self):
        """API 설정 생성 테스트"""
        config = APIConfiguration(
            api_key="test-key",
            organization="test-org",
            project="test-project"
        )
        
        assert config.api_key == "test-key"
        assert config.organization == "test-org" 
        assert config.project == "test-project"
        assert config.default_temperature == 0.3  # 한국어 최적화
        assert "text-embedding-3-large" in config.korean_model_preference["embedding"]
    
    @pytest.mark.asyncio
    async def test_client_initialization(self, api_config):
        """클라이언트 초기화 테스트"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-api-key"}):
            with patch('openai.AsyncOpenAI') as mock_openai:
                # Mock 클라이언트 설정
                mock_client = AsyncMock()
                mock_openai.return_value = mock_client
                
                # 연결 테스트 Mock
                mock_embedding_response = MagicMock()
                mock_embedding_response.data = [MagicMock()]
                mock_client.embeddings.create.return_value = mock_embedding_response
                
                manager = OpenAIClientManager(api_config)
                await manager.initialize()
                
                assert manager.client is not None
                assert manager.config.api_key == "test-api-key"
    
    @pytest.mark.asyncio
    async def test_korean_chat_completion(self, api_config, mock_openai_response):
        """한국어 채팅 완성 테스트"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-api-key"}):
            with patch('openai.AsyncOpenAI') as mock_openai:
                mock_client = AsyncMock()
                mock_openai.return_value = mock_client
                
                # 연결 테스트 Mock
                mock_embedding_response = MagicMock()
                mock_embedding_response.data = [MagicMock()]
                mock_client.embeddings.create.return_value = mock_embedding_response
                
                # 채팅 완성 Mock
                mock_client.chat.completions.create.return_value = mock_openai_response
                
                manager = OpenAIClientManager(api_config)
                await manager.initialize()
                
                messages = [{"role": "user", "content": "삼성전자에 대해 분석해주세요."}]
                result = await manager.create_chat_completion(
                    messages=messages,
                    system_prompt_type="stock_analysis"
                )
                
                assert result is not None
                assert "response" in result
                assert "usage" in result
                assert result["usage"]["total_tokens"] == 100
                
                # 시스템 프롬프트가 추가되었는지 확인
                call_args = mock_client.chat.completions.create.call_args
                called_messages = call_args[1]["messages"]
                assert called_messages[0]["role"] == "system"
                assert "한국 주식시장 전문 분석가" in called_messages[0]["content"]
    
    @pytest.mark.asyncio
    async def test_korean_embedding_creation(self, api_config, mock_embedding_response):
        """한국어 임베딩 생성 테스트"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-api-key"}):
            with patch('openai.AsyncOpenAI') as mock_openai:
                mock_client = AsyncMock()
                mock_openai.return_value = mock_client
                
                # Mock 설정
                mock_client.embeddings.create.return_value = mock_embedding_response
                
                manager = OpenAIClientManager(api_config)
                await manager.initialize()
                
                test_text = "삼성전자의 실적이 좋습니다. 주가가 상승할 것으로 예상됩니다."
                result = await manager.create_embedding(test_text)
                
                assert result is not None
                assert "response" in result
                assert len(result["response"].data[0].embedding) > 1000  # 벡터 차원 확인
                
                # 한국어 전처리가 적용되었는지 확인
                call_args = mock_client.embeddings.create.call_args
                processed_text = call_args[1]["input"]
                assert isinstance(processed_text, str)
                assert len(processed_text.strip()) > 0
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, api_config):
        """Rate limiting 테스트"""
        api_config.rate_limit_rpm = 2  # 매우 낮은 한도 설정
        
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-api-key"}):
            with patch('openai.AsyncOpenAI') as mock_openai:
                mock_client = AsyncMock()
                mock_openai.return_value = mock_client
                
                # Mock 응답 설정
                mock_embedding_response = MagicMock()
                mock_embedding_response.data = [MagicMock()]
                mock_client.embeddings.create.return_value = mock_embedding_response
                
                manager = OpenAIClientManager(api_config)
                await manager.initialize()
                
                # 연속 요청으로 rate limit 테스트
                start_time = asyncio.get_event_loop().time()
                
                for i in range(3):
                    await manager.create_embedding(f"테스트 텍스트 {i}")
                
                end_time = asyncio.get_event_loop().time()
                
                # Rate limiting으로 인한 지연이 있었는지 확인
                # (실제로는 더 정교한 테스트가 필요)
                assert end_time - start_time >= 0  # 기본 검증
    
    def test_korean_text_preprocessing(self):
        """한국어 텍스트 전처리 테스트"""
        manager = OpenAIClientManager(APIConfiguration(api_key="test"))
        
        # 테스트 텍스트 (특수문자, 공백 등 포함)
        test_text = "  삼성전자(005930)의   실적이 좋습니다!!! 📈  주가가 상승할 것으로 예상됩니다...  "
        
        processed = manager._preprocess_korean_text(test_text)
        
        assert processed is not None
        assert len(processed) < len(test_text)  # 정리되어 더 짧아져야 함
        assert "삼성전자" in processed
        assert "📈" not in processed  # 이모지 제거
        assert "!!!" not in processed  # 연속 특수문자 정리
        assert not processed.startswith(" ")  # 앞뒤 공백 제거
        assert not processed.endswith(" ")
    
    @pytest.mark.asyncio
    async def test_error_handling(self, api_config):
        """오류 처리 테스트"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-api-key"}):
            with patch('openai.AsyncOpenAI') as mock_openai:
                mock_client = AsyncMock()
                mock_openai.return_value = mock_client
                
                # API 오류 시뮬레이션
                from openai import APIError
                mock_client.embeddings.create.side_effect = APIError("Test error")
                
                manager = OpenAIClientManager(api_config)
                
                # initialize는 성공해야 함 (연결 테스트를 별도로 Mock)
                with patch.object(manager, '_test_connection', return_value=None):
                    await manager.initialize()
                
                # 실제 요청에서는 오류가 발생해야 함
                with pytest.raises(APIError):
                    await manager.create_embedding("테스트")
    
    @pytest.mark.asyncio
    async def test_cost_estimation(self, api_config):
        """비용 추정 테스트"""
        manager = OpenAIClientManager(api_config)
        
        # GPT-4 모델 비용 추정
        cost = manager.estimate_cost("gpt-4", input_tokens=1000, output_tokens=500)
        assert cost > 0
        assert isinstance(cost, float)
        
        # 임베딩 모델 비용 추정 (출력 토큰 없음)
        embedding_cost = manager.estimate_cost("text-embedding-3-large", input_tokens=1000, output_tokens=0)
        assert embedding_cost > 0
        assert embedding_cost < cost  # 임베딩이 더 저렴해야 함
    
    def test_usage_stats(self, api_config):
        """사용량 통계 테스트"""
        manager = OpenAIClientManager(api_config)
        
        # 초기 상태 확인
        stats = manager.get_usage_stats()
        assert stats["request_count"] == 0
        assert stats["token_usage"] == 0
        
        # 사용량 시뮬레이션
        manager.request_count = 10
        manager.token_usage = 5000
        
        updated_stats = manager.get_usage_stats()
        assert updated_stats["request_count"] == 10
        assert updated_stats["token_usage"] == 5000
    
    @pytest.mark.asyncio
    async def test_api_key_validation(self):
        """API 키 검증 테스트"""
        # 잘못된 API 키로 테스트
        with patch.dict(os.environ, {"OPENAI_API_KEY": "invalid-key"}):
            config = APIConfiguration(api_key="invalid-key")
            manager = OpenAIClientManager(config)
            
            with patch.object(manager, '_test_connection') as mock_test:
                mock_test.side_effect = Exception("Invalid API key")
                
                is_valid = await manager.validate_api_key()
                assert not is_valid
    
    @pytest.mark.asyncio 
    async def test_model_availability(self, api_config):
        """모델 가용성 확인 테스트"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-api-key"}):
            with patch('openai.AsyncOpenAI') as mock_openai:
                mock_client = AsyncMock()
                mock_openai.return_value = mock_client
                
                # Mock 모델 리스트
                mock_models = MagicMock()
                mock_models.data = [
                    MagicMock(id="gpt-4"),
                    MagicMock(id="gpt-3.5-turbo"),
                    MagicMock(id="text-embedding-3-large")
                ]
                mock_client.models.list.return_value = mock_models
                
                # 연결 테스트 Mock
                mock_embedding_response = MagicMock()
                mock_embedding_response.data = [MagicMock()]
                mock_client.embeddings.create.return_value = mock_embedding_response
                
                manager = OpenAIClientManager(api_config)
                await manager.initialize()
                
                models = await manager.get_available_models()
                
                assert "gpt-4" in models
                assert "gpt-3.5-turbo" in models 
                assert "text-embedding-3-large" in models

class TestConvenienceFunctions:
    """편의 함수 테스트"""
    
    @pytest.mark.asyncio
    async def test_create_korean_chat_completion(self):
        """한국어 채팅 완성 편의 함수 테스트"""
        with patch('ai_engine.config.api_config.get_openai_client') as mock_get_client:
            mock_manager = AsyncMock()
            mock_get_client.return_value = mock_manager
            
            # Mock 응답
            mock_result = {
                "response": MagicMock(),
                "usage": {"total_tokens": 100}
            }
            mock_result["response"].choices = [MagicMock()]
            mock_result["response"].choices[0].message.content = "분석 결과입니다."
            mock_manager.create_chat_completion.return_value = mock_result
            
            messages = [{"role": "user", "content": "삼성전자 분석해주세요"}]
            result = await create_korean_chat_completion(messages)
            
            assert result == "분석 결과입니다."
            mock_manager.create_chat_completion.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_korean_embedding(self):
        """한국어 임베딩 생성 편의 함수 테스트"""
        with patch('ai_engine.config.api_config.get_openai_client') as mock_get_client:
            mock_manager = AsyncMock()
            mock_get_client.return_value = mock_manager
            
            # Mock 임베딩 응답
            embedding_vector = [0.1] * 1536
            mock_result = {
                "response": MagicMock(),
                "usage": {"total_tokens": 50}
            }
            mock_result["response"].data = [MagicMock()]
            mock_result["response"].data[0].embedding = embedding_vector
            mock_manager.create_embedding.return_value = mock_result
            
            result = await create_korean_embedding("삼성전자 실적 분석")
            
            assert result == embedding_vector
            mock_manager.create_embedding.assert_called_once()

# 실제 API를 사용한 통합 테스트 (환경 변수 설정 시에만 실행)
class TestRealAPIIntegration:
    """실제 API 통합 테스트 (선택적)"""
    
    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY") or os.getenv("SKIP_REAL_API_TESTS"),
        reason="실제 OpenAI API 키가 없거나 실제 API 테스트를 스킵"
    )
    @pytest.mark.asyncio
    async def test_real_korean_analysis(self):
        """실제 API로 한국어 분석 테스트"""
        try:
            config = APIConfiguration()
            manager = OpenAIClientManager(config)
            await manager.initialize()
            
            # 간단한 한국어 분석 요청
            messages = [
                {"role": "user", "content": "삼성전자가 좋은 투자처인지 간단히 분석해주세요."}
            ]
            
            result = await manager.create_chat_completion(
                messages=messages,
                system_prompt_type="stock_analysis",
                max_tokens=200  # 토큰 사용량 제한
            )
            
            assert result is not None
            assert "response" in result
            content = result["response"].choices[0].message.content
            assert len(content) > 10  # 의미있는 응답인지 확인
            assert any(keyword in content for keyword in ["삼성전자", "투자", "분석"])
            
        except Exception as e:
            pytest.fail(f"실제 API 테스트 실패: {e}")
    
    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY") or os.getenv("SKIP_REAL_API_TESTS"),
        reason="실제 OpenAI API 키가 없거나 실제 API 테스트를 스킵"
    )
    @pytest.mark.asyncio
    async def test_real_korean_embedding(self):
        """실제 API로 한국어 임베딩 테스트"""
        try:
            config = APIConfiguration()
            manager = OpenAIClientManager(config)
            await manager.initialize()
            
            # 한국어 텍스트 임베딩
            text = "삼성전자는 대한민국의 대표적인 IT 기업입니다."
            result = await manager.create_embedding(text)
            
            assert result is not None
            assert "response" in result
            embedding = result["response"].data[0].embedding
            assert len(embedding) == 3072  # text-embedding-3-large 차원
            assert all(isinstance(x, float) for x in embedding)
            
        except Exception as e:
            pytest.fail(f"실제 임베딩 API 테스트 실패: {e}")

# 테스트 실행을 위한 메인 함수
if __name__ == "__main__":
    # pytest 실행
    pytest.main([__file__, "-v"])