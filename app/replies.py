PERSONA_SELECT: dict[str, str] = {
    "💅 我要預約": "booking_assistant",
    "🏪 了解此服務": "sales_agent",
}

WELCOME_FOLLOW = (
    "嗨！歡迎來到 Hualienvibe 💅\n"
    "請問妳是？"
)
WELCOME_FOLLOW_QUICK_REPLIES: tuple[str, ...] = ("💅 我要預約", "🏪 了解此服務")

HINT_SELECT_PERSONA = "請先選擇妳的身份 👇"

COOLDOWN_HOUR = "您傳的訊息有點頻繁，請等 1 小時後再試 🙏"
COOLDOWN_DAY = "您今天的訊息已達上限，請明天再來 🙏"
KILLED_OFFLINE = "系統暫時休息中，請稍後再試 🙏"
CLAUDE_ERROR = "我這邊出了一點狀況，請稍後再試 🙏"

OWNER_RATE_LIMIT_ALERT = (
    "⚠️ Anthropic 429: nail-bot hit account rate limit; users seeing fallback reply."
)

PORTFOLIO_TRIGGER = "🖼 作品集"
SERVICES_TRIGGER = "本月優惠"
