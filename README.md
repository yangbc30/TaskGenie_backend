backend(fastapi) 


```cmd
conda install -c conda-forge fastapi uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

test http://127.0.0.1:8000/docs
