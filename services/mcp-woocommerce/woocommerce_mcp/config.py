"""Environment-backed service configuration."""

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    url: str = "http://wordpress.default.svc.cluster.local:80"
    consumer_key: str = field(default="", repr=False)
    consumer_secret: str = field(default="", repr=False)
    host_header: str = "store.local"
    port: int = 8000

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            url=os.getenv("WOOCOMMERCE_INTERNAL_URL")
            or os.getenv("WOOCOMMERCE_URL", cls.url),
            consumer_key=os.getenv("WOOCOMMERCE_CONSUMER_KEY", ""),
            consumer_secret=os.getenv("WOOCOMMERCE_CONSUMER_SECRET", ""),
            host_header=os.getenv("WOOCOMMERCE_HOST_HEADER", "store.local"),
            port=int(os.getenv("PORT", "8000")),
        )
