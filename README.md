#### A-I(R-A-G) Code Search


- Embedding model use the `cohere`'s embedding models, using `AWS Bedrock boto3` services
- ML algorthims used open-sourced `faiss`'s `squared Euclidean (L2) distance`
- `Socket & Multi-threats` applied, port 3000, 8000 used, auto socket-based port verification, and subprocess handling with proper cleanup
- Auto Logging('.logs/results.json')
- Cross-OS is available to `Windows`, `MacOS`, `Linux`, `Windows(WSL)`

>!Note:
> 1. For Similarity Search counting the distance, use `Euclidean (L2) distance` is better. Don't mixed up with `cosine similarity`. Two differnt concepts<br>
> 2. With more data, performance of the code search enginee is better. e.g. 10k+ items (take reference with the data's attribute example in `./data`
> 3. TroubleShoot, if the FastAPI server fails to start through run.py, try running it directly:
>  ```python
>  # Ensure you are in your virtual environment first
>  # Windows
>  venv\Scripts\activate
>  # macOS/Linux/WSL
>  source venv/bin/activate
>
>  # Ensure you have `pip install -r requirements`
>  
>  # Then run the FastAPI server directly
>  python -m src.api.main
>  ```

In the demo example, it only use 10 rows(just for demo purpose), thus the performance bad is normal.
<img width="902" alt="demo" src="https://github.com/user-attachments/assets/92e58df8-0377-4ed9-a8a5-ed91ab21bad4" />
