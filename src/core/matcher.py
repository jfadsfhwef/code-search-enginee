import numpy as np
import faiss
import pandas as pd
from typing import List, Dict, Union, Optional
import ast
import cohere_aws
import boto3
import logging
from datetime import datetime
import os
import json

class HSCodeSearchResult:
    def __init__(self, id: str, code: str, description: str, similarity: float):
        self.id = id
        self.code = code
        self.description = description
        self.similarity = similarity

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'code': self.code,
            'description': self.description,
            'similarity': self.similarity
        }

    def __str__(self) -> str:
        return f"ID: {self.id}\nCode: {self.code}\nDescription: {self.description}\nSimilarity Score: {self.similarity:.4f}"

class FaissHSCodeMatcher:
    """
    add: Class variable to store singleton instance
    To replace the VectorDB role in this case
    """
    _instance = None
    @classmethod
    def get_instance(cls, csv_path: str) -> 'FaissHSCodeMatcher':
        """Singleton getter"""
        if cls._instance is None:
            cls._instance = cls(csv_path)
        return cls._instance
    
    def __init__(self, csv_path: str, log_dir: str = './logs', embedding_model: str = "cohere.embed-multilingual-v3"):
        """
        Initialize the Faiss index and load data from CSV
        
        Args:
            csv_path: Path to the CSV file containing embeddings
            log_dir: Directory for storing logs
            embedding_model: Model ID for generating embeddings
        """
        # prevent duplicated creation: Check if instance already exists
        if FaissHSCodeMatcher._instance is not None:
            return
    
        # Set up logging
        self._setup_logging(log_dir)
        
        # Initialize Bedrock client
        try:
            self.co = cohere_aws.Client(mode=cohere_aws.Mode.BEDROCK)
            self.embedding_model = embedding_model
            self.logger.info(f"Initialized Bedrock client with model: {embedding_model}")
        except Exception as e:
            self.logger.error(f"Failed to initialize Bedrock client: {str(e)}")
            raise
        
        # Load and process data
        self._load_data(csv_path)
        self._initialize_faiss_index()
        
        # replace vectorDB in this case: Set the instance 
        FaissHSCodeMatcher._instance = self

    def _setup_logging(self, log_dir: str):
        """Set up logging configuration"""
        os.makedirs(log_dir, exist_ok=True)
        
        self.logger = logging.getLogger('HSCodeMatcher')
        self.logger.setLevel(logging.INFO)
        
        # File handler for detailed logs
        fh = logging.FileHandler(
            os.path.join(log_dir, f'hscode_matcher_{datetime.now().strftime("%Y%m%d")}.log')
        )
        fh.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        
        self.logger.addHandler(fh)

    def _load_data(self, csv_path: str):
        """Load and process CSV data"""
        try:
            self.df = pd.read_csv(csv_path)
            self.logger.info(f"Successfully loaded CSV from {csv_path}")
            
            # Convert embedding strings to numpy arrays
            embeddings = self.df['embedding'].apply(ast.literal_eval).values
            self.vectors = np.array(embeddings.tolist()).astype(np.float32)
            self.dimension = self.vectors.shape[1]
            
            self.logger.info(f"Processed {len(self.df)} records with dimension {self.dimension}")
        except Exception as e:
            self.logger.error(f"Error loading CSV data: {str(e)}")
            raise

    def _initialize_faiss_index(self):
        """Initialize and populate Faiss index"""
        try:
            self.index = faiss.IndexFlatIP(self.dimension)
            faiss.normalize_L2(self.vectors)
            self.index.add(self.vectors)
            self.logger.info("Successfully initialized Faiss index")
        except Exception as e:
            self.logger.error(f"Error initializing Faiss index: {str(e)}")
            raise

    def generate_embedding(self, text: str) -> Optional[np.ndarray]:
        """Generate embedding for input text"""
        try:
            response = self.co.embed(
                texts=[text],
                input_type="search_query",
                model_id=self.embedding_model
            )
            embedding = np.array(response.embeddings[0]).astype(np.float32)
            self.logger.info(f"Successfully generated embedding for text: {text[:50]}...")
            return embedding
        except Exception as e:
            self.logger.error(f"Error generating embedding: {str(e)}")
            return None

    def search(self, query: Union[str, np.ndarray], k: int = 10) -> List[HSCodeSearchResult]:
        """
        Search for similar HS codes
        
        Args:
            query: Either text string or numpy array of embeddings
            k: Number of results to return
            
        Returns:
            List of HSCodeSearchResult objects
        """
        try:
            # Generate embedding if text query
            if isinstance(query, str):
                self.logger.info(f"Searching with text query: {query[:50]}...")
                query_vector = self.generate_embedding(query)
                if query_vector is None:
                    return []
            else:
                query_vector = query
                self.logger.info("Searching with vector query")

            # Prepare query vector
            query_vector = query_vector.reshape(1, -1)
            faiss.normalize_L2(query_vector)
            
            # Search
            distances, indices = self.index.search(query_vector, k)
            
            # Prepare results
            results = []
            for idx, distance in zip(indices[0], distances[0]):
                if idx != -1:
                    row = self.df.iloc[idx]
                    result = HSCodeSearchResult(
                        id=str(row['id']),
                        code=str(row['code']),
                        description=str(row['description']),
                        similarity=float(distance)
                    )
                    results.append(result)
                    
                    # Log each result metadata for debugging(if applicable)
                    self.logger.info(f"Found match: {result}")
                    
                    # Log the result details to results.json
                    from src.utils.logger import get_logger
                    search_logger = get_logger()
                    search_logger.log_search_result(
                        query if isinstance(query, str) else "vector_query",
                        [result.to_dict() for result in results]
                    )
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error during search: {str(e)}")
            return []

def get_matcher(csv_path: str) -> FaissHSCodeMatcher:
    """Factory function to get a matcher instance"""
    return FaissHSCodeMatcher.get_instance(csv_path) # prevent duplicated import file