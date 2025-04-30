"""
OpenAI Tool Implementations

This module implements AI tools using OpenAI's APIs with Layer of Thought processing.
"""

import os
import json
import asyncio
from typing import List, Dict, Any, Optional, Tuple
import openai
from openai import AsyncOpenAI
from datetime import datetime
from dataclasses import dataclass
from ...config import get_openai_config
import numpy as np
from framework.mcp_server.config.openai_config import OpenAIConfig
import hashlib

# Initialize OpenAI client
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@dataclass
class LayerConfig:
    """Configuration for a Layer of Thought processing layer."""
    system_prompt: str
    temperature: float = 0.7
    max_tokens: int = 1000
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0

@dataclass
class ProcessResult:
    """Result from processing with triggers."""
    response: str
    triggered_layers: List[str]

class LayerOfThought:
    """
    Implements the Layer of Thought pattern for OpenAI interactions.
    Supports multiple processing layers with different configurations.
    """

    def __init__(self, config: Optional[OpenAIConfig] = None):
        """Initialize with OpenAI configuration."""
        self.config = config or get_openai_config()
        self.client = openai.AsyncClient(api_key=self.config.api_key)
        self._embedding_cache = {}
        self._layer_result_cache = {}  # In-memory cache for layer results

    def _cache_key(self, input_data: str, layer_config: LayerConfig, context: Dict[str, Any]) -> str:
        # Create a unique key based on input, config, and context
        key_data = json.dumps({
            "input": input_data,
            "config": layer_config.__dict__,
            "context": context
        }, sort_keys=True)
        return hashlib.sha256(key_data.encode()).hexdigest()

    async def process_layer(
        self,
        input_data: str,
        layer_config: LayerConfig,
        context: Dict[str, Any]
    ) -> str:
        """
        Process a single layer with the given configuration, using cache if available.
        """
        cache_key = self._cache_key(input_data, layer_config, context)
        if cache_key in self._layer_result_cache:
            return self._layer_result_cache[cache_key]
        try:
            messages = [
                {"role": "system", "content": layer_config.system_prompt},
                {"role": "user", "content": input_data}
            ]

            if context:
                messages.append({
                    "role": "system",
                    "content": f"Context: {json.dumps(context)}"
                })

            response = await self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=layer_config.temperature,
                max_tokens=layer_config.max_tokens,
                top_p=layer_config.top_p,
                frequency_penalty=layer_config.frequency_penalty,
                presence_penalty=layer_config.presence_penalty
            )

            result = response.choices[0].message.content
            self._layer_result_cache[cache_key] = result  # Cache the result
            return result

        except Exception as e:
            raise Exception(f"Error in layer processing: {str(e)}")

    async def process_sequence(
        self,
        input_data: str,
        layer_configs: List[LayerConfig],
        context: Dict[str, Any]
    ) -> List[str]:
        """
        Process through a sequence of layers, passing results forward.
        
        Args:
            input_data: Initial input text
            layer_configs: List of layer configurations to process through
            context: Additional context for processing
            
        Returns:
            List of results from each layer
        """
        results = []
        current_input = input_data

        for config in layer_configs:
            result = await self.process_layer(current_input, config, context)
            results.append(result)
            current_input = result

        return results

    async def code_analysis(
        self,
        code: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze code using the OpenAI model.
        
        Args:
            code: The code to analyze
            context: Additional context for analysis
            
        Returns:
            Dictionary containing analysis results
        """
        config = LayerConfig(
            system_prompt="""
            Analyze the provided code and return a JSON object with:
            1. suggestions: List of improvement suggestions
            2. metrics: Object containing code quality metrics
            Be specific and actionable in your analysis.
            """,
            temperature=0.3
        )

        result = await self.process_layer(code, config, context)
        return json.loads(result)

    async def batch_get_embeddings(self, texts: List[str]) -> Dict[str, List[float]]:
        """
        Batch get embeddings for a list of texts, using cache where possible.
        """
        uncached = [t for t in texts if t not in self._embedding_cache]
        if uncached:
            response = await self.client.embeddings.create(
                model=self.config.embedding_model,
                input=uncached
            )
            for text, emb in zip(uncached, [d.embedding for d in response.data]):
                self._embedding_cache[text] = emb
        return {t: self._embedding_cache[t] for t in texts}

    async def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for text, using cache if available."""
        if text in self._embedding_cache:
            return self._embedding_cache[text]
        # Use batch_get_embeddings for single text for consistency
        return (await self.batch_get_embeddings([text]))[text]

    async def semantic_search(
        self,
        query: str,
        corpus: List[str],
        top_k: int = 5
    ) -> List[Tuple[float, str]]:
        """
        Perform semantic search using embeddings, batching embedding calls for efficiency.
        """
        # Batch get all embeddings (query + corpus)
        all_texts = [query] + corpus
        embeddings = await self.batch_get_embeddings(all_texts)
        query_embedding = embeddings[query]
        results = []
        for doc in corpus:
            doc_embedding = embeddings[doc]
            similarity = np.dot(query_embedding, doc_embedding)
            results.append((similarity, doc))
        results.sort(reverse=True)
        return results[:top_k]

    async def process_with_triggers(
        self,
        input_data: str,
        layer_config: LayerConfig,
        context: Dict[str, Any],
        triggers: Dict[str, List[str]]
    ) -> ProcessResult:
        """
        Process input with potential triggers for additional processing.
        
        Args:
            input_data: Input text to process
            layer_config: Configuration for the initial layer
            context: Additional context
            triggers: Dictionary of trigger words/phrases and their corresponding layers
            
        Returns:
            ProcessResult containing the response and list of triggered layers
        """
        response = await self.process_layer(input_data, layer_config, context)
        
        triggered = []
        for keyword, layers in triggers.items():
            if keyword.lower() in response.lower():
                triggered.extend(layers)
        
        return ProcessResult(
            response=response,
            triggered_layers=list(set(triggered))  # Remove duplicates
        )

# Initialize Layer of Thought processor
lot_processor = LayerOfThought()

async def text_embedding(text: str, model: str = "text-embedding-3-small") -> List[float]:
    """Generate embeddings for text using OpenAI."""
    response = await client.embeddings.create(
        model=model,
        input=text
    )
    return response.data[0].embedding

async def code_analysis(
    code: str,
    language: str,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Analyze code using Layer of Thought processing"""
    lot = LayerOfThought()
    
    # Process through perception and reasoning layers
    results = await lot.process_sequence(
        input_data=f"Code ({language}):\n{code}",
        layer_sequence=["perception", "reasoning"],
        context=context
    )
    
    # Extract suggestions and metrics from results
    return {
        "suggestions": results[1].get("suggestions", []),
        "metrics": results[1].get("metrics", {})
    }

async def semantic_search(
    query: str,
    corpus: List[str],
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """Perform semantic search using embeddings"""
    client = openai.AsyncClient(api_key=get_openai_config().api_key)
    
    # Get query embedding
    query_response = await client.embeddings.create(
        model="text-embedding-ada-002",
        input=query
    )
    query_embedding = query_response.data[0].embedding
    
    # Get corpus embeddings
    corpus_response = await client.embeddings.create(
        model="text-embedding-ada-002",
        input=corpus
    )
    corpus_embeddings = [item.embedding for item in corpus_response.data]
    
    # Calculate similarities and return top_k results
    similarities = []
    for i, emb in enumerate(corpus_embeddings):
        similarity = sum(a * b for a, b in zip(query_embedding, emb))
        similarities.append((similarity, corpus[i]))
    
    similarities.sort(reverse=True)
    return [{"text": text, "score": score} for score, text in similarities[:top_k]]

async def layer_thought_process(
    input_data: Any,
    context: Dict[str, Any],
    layer_sequence: List[str]
) -> List[Dict[str, Any]]:
    """Process input through a sequence of thought layers."""
    results = []
    current_context = context
    
    for layer_type in layer_sequence:
        result, layer_context = await lot_processor.process_layer(
            input_data,
            layer_type,
            current_context
        )
        results.append({
            "layer_type": layer_type,
            "result": result,
            "context": layer_context
        })
        input_data = result
        current_context = layer_context
        
    return results 