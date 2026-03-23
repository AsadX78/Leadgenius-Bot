import os
import logging
from ddgs import DDGS
from openai import OpenAI
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

openai_client: OpenAI = None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Hello! I am your LeadGenius Bot. Ready to hunt some leads!"
    )


async def find(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            "Please provide a search query.\nUsage: /find tech startups"
        )
        return

    query = " ".join(context.args)
    await update.message.reply_text(f"Searching for: {query}...")

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
    except Exception as e:
        logger.error(f"DuckDuckGo search error: {e}")
        await update.message.reply_text(
            "Search failed. DuckDuckGo may be rate-limiting. Please wait a moment and try again."
        )
        return

    if not results:
        await update.message.reply_text("No results found. Try a different or broader query.")
        return

    lines = [f'Top results for "{query}":\n']
    for i, result in enumerate(results, start=1):
        title = result.get("title", "No title")
        link = result.get("href", "No link")
        snippet = result.get("body", "No description")
        lines.append(
            f"{i}. {title}\n"
            f"   {link}\n"
            f"   {snippet}\n"
        )

    await update.message.reply_text("\n".join(lines))

    first = results[0]
    first_title = first.get("title", "Unknown business")
    first_snippet = first.get("body", "")

    await update.message.reply_text("Generating cold email for the top result...")

    try:
        prompt = (
            f"You are an expert sales copywriter. Based on the following business information, "
            f"write a short, professional 3-sentence cold email pitching custom chatbot development "
            f"services to this specific business. Be personalized and concise.\n\n"
            f"Business name: {first_title}\n"
            f"About them: {first_snippet}\n\n"
            f"Write only the email body, no subject line."
        )

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )

        email_text = response.choices[0].message.content.strip()
        await update.message.reply_text(f"Cold email draft:\n\n{email_text}")
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        await update.message.reply_text("Failed to generate email. Please check your OpenAI API key.")


def main() -> None:
    global openai_client

    telegram_token = os.environ.get("TELEGRAM_TOKEN")
    if not telegram_token:
        telegram_token = input("Please paste your Telegram Bot API token: ").strip()

    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        openai_api_key = input("Please paste your OpenAI API key: ").strip()

    openai_client = OpenAI(api_key=openai_api_key)

    app = ApplicationBuilder().token(telegram_token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("find", find))
    print("Bot is running. Press Ctrl+C to stop.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
