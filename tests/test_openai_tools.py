import pytest
from unittest.mock import AsyncMock, patch, call
from framework.mcp_server.implementations.ai.openai_tools import LayerOfThought, LayerConfig, ProcessResult
from framework.mcp_server.config.openai_config import OpenAIConfig
import json
import openai # Need this for potential exceptions

@pytest.fixture
def mock_openai_config():
    # Using a real-looking but invalid key to ensure mocks are working
    return OpenAIConfig(
        api_key="sk-test_key_mocked_XXXXXXXXXXXXXXXXXXXX", 
        model="gpt-4-turbo-preview",
        embedding_model="text-embedding-ada-002"
    )

@pytest.fixture
def layer_of_thought(mock_openai_config):
    # Instantiates LayerOfThought, which creates its own internal client
    return LayerOfThought(config=mock_openai_config)

# --- Helper to create mock completion response ---
def create_mock_completion(content: str):
    mock_completion = AsyncMock(spec=openai.types.chat.ChatCompletion)
    mock_choice = AsyncMock(spec=openai.types.chat.ChatCompletionMessage)
    mock_choice.message = AsyncMock(spec=openai.types.chat.ChatCompletionMessage)
    mock_choice.message.content = content
    mock_completion.choices = [mock_choice]
    return mock_completion

# --- Helper to create mock embedding response ---
def create_mock_embedding_response(embeddings: list):
    mock_response = AsyncMock(spec=openai.types.CreateEmbeddingResponse)
    mock_data = []
    for emb in embeddings:
        mock_emb_obj = AsyncMock(spec=openai.types.Embedding)
        mock_emb_obj.embedding = emb
        mock_data.append(mock_emb_obj)
    mock_response.data = mock_data
    return mock_response
# -----------------------------------------------

@pytest.mark.asyncio
async def test_process_layer(layer_of_thought):
    # Create mock client and attach it to the instance
    mock_client = AsyncMock(spec=openai.AsyncClient)
    layer_of_thought.client = mock_client 

    # Configure the mock method
    # Explicitly create intermediate mocks
    mock_client.chat = AsyncMock()
    mock_client.chat.completions = AsyncMock()
    mock_client.chat.completions.create.return_value = create_mock_completion("Test response")

    result = await layer_of_thought.process_layer(
        "test input",
        LayerConfig(
            system_prompt="You are a helpful assistant",
            temperature=0.7,
            max_tokens=100
        ),
        {"context": "test"}
    )

    assert result == "Test response"
    mock_client.chat.completions.create.assert_called_once()

@pytest.mark.asyncio
async def test_process_sequence(layer_of_thought):
    # Create mock client and attach it to the instance
    mock_client = AsyncMock(spec=openai.AsyncClient)
    layer_of_thought.client = mock_client

    # Configure the mock method (same response for all calls in this test)
    # Explicitly create intermediate mocks
    mock_client.chat = AsyncMock()
    mock_client.chat.completions = AsyncMock()
    mock_client.chat.completions.create.return_value = create_mock_completion("Layer response")

    configs = [
        LayerConfig(
            system_prompt="Perception layer",
            temperature=0.7,
            max_tokens=100
        ),
        LayerConfig(
            system_prompt="Reasoning layer",
            temperature=0.7,
            max_tokens=100
        )
    ]

    results = await layer_of_thought.process_sequence(
        "test input",
        configs,
        {"context": "test"}
    )

    assert len(results) == 2
    assert all(r == "Layer response" for r in results)
    assert mock_client.chat.completions.create.call_count == 2

@pytest.mark.asyncio
async def test_code_analysis(layer_of_thought):
    # Create mock client and attach it to the instance
    mock_client = AsyncMock(spec=openai.AsyncClient)
    layer_of_thought.client = mock_client

    # Configure the mock method
    mock_content = '{"suggestions": ["Use list comprehension"], "metrics": {"cyclomatic_complexity": 5}}'
    # Explicitly create intermediate mocks
    mock_client.chat = AsyncMock()
    mock_client.chat.completions = AsyncMock()
    mock_client.chat.completions.create.return_value = create_mock_completion(mock_content)

    result = await layer_of_thought.code_analysis(
        "def test():\n  l = []\n  for i in range(10):\n    l.append(i*2)\n  return l",
        {"context": "test"}
    )

    assert "suggestions" in result
    assert result["suggestions"] == ["Use list comprehension"]
    assert "metrics" in result
    assert result["metrics"]["cyclomatic_complexity"] == 5
    mock_client.chat.completions.create.assert_called_once()

@pytest.mark.asyncio
async def test_semantic_search(layer_of_thought):
    # Create mock client and attach it to the instance
    mock_client = AsyncMock(spec=openai.AsyncClient)
    layer_of_thought.client = mock_client

    # Configure the mock method
    # Need embeddings for query + corpus
    mock_embeddings_data = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]]
    # Explicitly create intermediate mock
    mock_client.embeddings = AsyncMock()
    mock_client.embeddings.create.return_value = create_mock_embedding_response(mock_embeddings_data)

    corpus = ["test document 1", "test document 2"]
    query = "test query"

    results = await layer_of_thought.semantic_search(query, corpus, top_k=1)

    assert len(results) == 1
    # Correct check for tuple elements
    assert isinstance(results[0], tuple)
    assert isinstance(results[0][0], float) 
    assert isinstance(results[0][1], str)
    # Ensure embeddings create was called once with all texts
    mock_client.embeddings.create.assert_called_once()
    call_args, call_kwargs = mock_client.embeddings.create.call_args
    assert call_kwargs['input'] == [query] + corpus

@pytest.mark.asyncio
async def test_process_with_triggers(layer_of_thought):
    # Create mock client and attach it to the instance
    mock_client = AsyncMock(spec=openai.AsyncClient)
    layer_of_thought.client = mock_client

    # Configure the mock method
    # Explicitly create intermediate mocks
    mock_client.chat = AsyncMock()
    mock_client.chat.completions = AsyncMock()
    mock_client.chat.completions.create.return_value = create_mock_completion("This response mentions a keyword.")

    result = await layer_of_thought.process_with_triggers(
        "test input",
        LayerConfig(
            system_prompt="Test layer",
            temperature=0.7,
            max_tokens=100
        ),
        {"context": "test"},
        triggers={"keyword": ["additional_layer"]}
    )

    assert result.response == "This response mentions a keyword."
    assert result.triggered_layers == ["additional_layer"]
    mock_client.chat.completions.create.assert_called_once()

@pytest.mark.asyncio
async def test_error_handling(layer_of_thought):
    # Create mock client and attach it to the instance
    mock_client = AsyncMock(spec=openai.AsyncClient)
    layer_of_thought.client = mock_client

    # Configure the mock method to raise a specific OpenAI error
    # Use a real OpenAI exception type for better testing
    # Explicitly create intermediate mocks
    mock_client.chat = AsyncMock()
    mock_client.chat.completions = AsyncMock()
    mock_client.chat.completions.create.side_effect = openai.APIConnectionError(request=AsyncMock()) # Simulate connection error

    # Expect the specific OpenAI error wrapped by the layer processing exception
    with pytest.raises(Exception, match="Error in layer processing: Connection error."):
        await layer_of_thought.process_layer(
            "test input",
            LayerConfig(
                system_prompt="Test layer",
                temperature=0.7,
                max_tokens=100
            ),
            {"context": "test"}
        )
    mock_client.chat.completions.create.assert_called_once()

@pytest.mark.asyncio
async def test_system_message_generation(layer_of_thought):
    """Test that process_layer uses the correct system message."""
    test_prompt = "This is the test system prompt."
    test_input = "User input data."
    test_context = {"session_id": 123}
    
    test_config = LayerConfig(system_prompt=test_prompt)

    # Create mock client and attach it to the instance
    mock_client = AsyncMock(spec=openai.AsyncClient)
    layer_of_thought.client = mock_client

    # Configure the mock method
    # Explicitly create intermediate mocks
    mock_client.chat = AsyncMock()
    mock_client.chat.completions = AsyncMock()
    mock_client.chat.completions.create.return_value = create_mock_completion("Mocked response content")

    await layer_of_thought.process_layer(
        input_data=test_input,
        layer_config=test_config,
        context=test_context
    )

    mock_client.chat.completions.create.assert_called_once()
    args, kwargs = mock_client.chat.completions.create.call_args
    
    expected_messages = [
        {"role": "system", "content": test_prompt},
        {"role": "user", "content": test_input},
        {"role": "system", "content": f'Context: {json.dumps(test_context)}'}
    ]
    assert kwargs.get('messages') == expected_messages
    assert kwargs.get('model') == layer_of_thought.config.model
    assert kwargs.get('temperature') == test_config.temperature 