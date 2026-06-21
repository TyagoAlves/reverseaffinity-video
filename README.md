# reverseaffinity-video

Video editor — desmembrado do monorepo `reverseaffinity`.

## Estrutura
```
src/
├── python_ui/        # Interface Python (PyQt5)
│   ├── editor/       # Core editor engine
│   ├── reverseaffinity/  # App-specific modules
│   ├── tests/        # Test suite (pytest)
│   └── main.py       # Entry point
└── cpp_backend/      # C++ engine (performance-critical)
    ├── CMakeLists.txt
    ├── include/
    ├── src/
    └── test/
assets/               # Icons, resources
docs/                 # Documentation
```

## Executar (UI Python)
```bash
pip install -r src/python_ui/requirements.txt
python src/python_ui/main.py
```

## Compilar (C++ Backend)
```bash
cd src/cpp_backend
bash build.sh
```
O binário será gerado em `/tmp/reverseaffinity_cpp_build/reverseaffinity`.

## Testes
```bash
cd src/python_ui
QT_QPA_PLATFORM=offscreen python -m pytest tests/ -q
```

## Features
- Timeline com tracks de vídeo e áudio
- Source/Program monitors
- Transport controls (play, pause, loop)
- Suporte a importação de mídia
