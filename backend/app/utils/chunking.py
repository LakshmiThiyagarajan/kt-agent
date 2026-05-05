import tiktoken

def chunk_text(text, max_tokens=300):
    enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(text)

    chunks = []
    for i in range(0, len(tokens), max_tokens):
        chunk = enc.decode(tokens[i:i + max_tokens])
        chunks.append(chunk)

    return chunks