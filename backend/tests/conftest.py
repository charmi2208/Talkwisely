import os
import tempfile

# Runs before test modules import the app: keep test vectors out of the real search index
os.environ["CHROMA_PERSIST_DIR"] = tempfile.mkdtemp(prefix="talkwise_test_vectors_")
