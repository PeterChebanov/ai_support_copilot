from openai import OpenAI

from api.config import Settings, settings as default_settings


def embed_texts(
    texts: list[str],
    *,
    settings: Settings | None = None,
    client: OpenAI | None = None,
) -> list[list[float]]:
    if not texts:
        return []

    cfg = settings or default_settings
    if not cfg.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required for embeddings")

    openai_client = client or OpenAI(api_key=cfg.openai_api_key)
    response = openai_client.embeddings.create(
        model=cfg.embedding_model,
        input=texts,
    )
    return [item.embedding for item in response.data]
