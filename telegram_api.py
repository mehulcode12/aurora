# main_localhost.py - Polling version for local development
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import asyncio
import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

app = FastAPI(title="Telegram Bot API - Localhost")

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
POLLING_TIMEOUT = 30  # Long polling timeout in seconds

# Global variable to track last update
last_update_id = 0


# Pydantic Models
class SendMessageRequest(BaseModel):
    chat_id: int
    text: str
    parse_mode: Optional[str] = None
    reply_to_message_id: Optional[int] = None


### MESSAGE SENDING FUNCTIONS ###

async def send_message(
    chat_id: int,
    text: str,
    parse_mode: Optional[str] = None,
    reply_to_message_id: Optional[int] = None
) -> dict:
    """Send a text message to a Telegram chat"""
    url = f"{TELEGRAM_API_URL}/sendMessage"
    
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    
    if parse_mode:
        payload["parse_mode"] = parse_mode
    
    if reply_to_message_id:
        payload["reply_to_message_id"] = reply_to_message_id
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()


async def send_photo(chat_id: int, photo_url: str, caption: Optional[str] = None):
    """Send a photo to a chat"""
    url = f"{TELEGRAM_API_URL}/sendPhoto"
    
    payload = {
        "chat_id": chat_id,
        "photo": photo_url
    }
    
    if caption:
        payload["caption"] = caption
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()


@app.post("/api/send-message")
async def api_send_message(request: SendMessageRequest):
    """API endpoint to send messages programmatically"""
    try:
        result = await send_message(
            chat_id=request.chat_id,
            text=request.text,
            parse_mode=request.parse_mode,
            reply_to_message_id=request.reply_to_message_id
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


### POLLING FUNCTIONS ###

async def get_updates(offset: Optional[int] = None, timeout: int = POLLING_TIMEOUT):
    """Get updates from Telegram using long polling"""
    url = f"{TELEGRAM_API_URL}/getUpdates"
    
    params = {
        "timeout": timeout,
        "allowed_updates": ["message", "edited_message"]
    }
    
    if offset:
        params["offset"] = offset
    
    try:
        async with httpx.AsyncClient(timeout=timeout + 5) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f"Error getting updates: {e}")
        return {"ok": False, "result": []}


async def process_message(message: dict):
    """Process incoming messages"""
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")
    message_id = message.get("message_id")
    
    print(f"📨 Received: '{text}' from chat_id: {chat_id}")
    
    # Handle commands
    if text.startswith("/start"):
        await send_message(
            chat_id=chat_id,
            text="👋 Welcome! I'm your Telegram bot running on localhost!\n\nAvailable commands:\n/start - Start the bot\n/help - Show help\n/info - Get chat info\n\nSend me any message and I'll echo it back!"
        )
    
    elif text.startswith("/help"):
        help_text = """
🤖 **Bot Commands:**

/start - Start the bot
/help - Show this help message
/info - Get your chat information
/echo <text> - Echo your message

**Features:**
✅ Receive and send messages
✅ Reply to messages
✅ Handle commands
✅ Running on localhost with polling

Note: Voice/video calls are not supported by Bot API.
        """
        await send_message(
            chat_id=chat_id,
            text=help_text,
            parse_mode="Markdown"
        )
    
    elif text.startswith("/info"):
        user = message.get("from", {})
        info = f"""
📊 **Chat Information:**

Chat ID: `{chat_id}`
Message ID: {message_id}
User ID: {user.get('id')}
Username: @{user.get('username', 'N/A')}
First Name: {user.get('first_name', 'N/A')}
        """
        await send_message(
            chat_id=chat_id,
            text=info,
            parse_mode="Markdown"
        )
    
    elif text.startswith("/echo"):
        echo_text = text.replace("/echo", "").strip()
        if echo_text:
            await send_message(
                chat_id=chat_id,
                text=f"🔊 Echo: {echo_text}",
                reply_to_message_id=message_id
            )
        else:
            await send_message(
                chat_id=chat_id,
                text="Usage: /echo <your message>"
            )
    
    else:
        # Echo back any other message
        if text:
            await send_message(
                chat_id=chat_id,
                text=f"✨ You said: {text}",
                reply_to_message_id=message_id
            )


async def polling_loop():
    """Main polling loop to continuously get updates"""
    global last_update_id
    
    print("🚀 Starting polling loop...")
    print("💡 Send a message to your bot on Telegram to test!")
    print("-" * 50)
    
    while True:
        try:
            # Get updates from Telegram
            result = await get_updates(offset=last_update_id)
            
            if result.get("ok") and result.get("result"):
                updates = result["result"]
                
                for update in updates:
                    # Update the offset
                    last_update_id = update["update_id"] + 1
                    
                    # Process message
                    if "message" in update:
                        await process_message(update["message"])
                    elif "edited_message" in update:
                        await process_message(update["edited_message"])
            
            # Small delay to prevent overwhelming the API
            await asyncio.sleep(0.1)
            
        except Exception as e:
            print(f"❌ Error in polling loop: {e}")
            await asyncio.sleep(5)  # Wait before retrying


@app.on_event("startup")
async def startup_event():
    """Start the polling loop when FastAPI starts"""
    print("\n" + "="*50)
    print("🤖 Telegram Bot Starting...")
    print("="*50)
    
    # Remove any existing webhook to use polling
    try:
        async with httpx.AsyncClient() as client:
            await client.post(f"{TELEGRAM_API_URL}/deleteWebhook", 
                            json={"drop_pending_updates": True})
        print("✅ Webhook removed, ready for polling")
    except Exception as e:
        print(f"⚠️  Warning: Could not remove webhook: {e}")
    
    # Get bot info
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{TELEGRAM_API_URL}/getMe")
            bot_info = response.json()
            if bot_info.get("ok"):
                bot = bot_info["result"]
                print(f"✅ Bot connected: @{bot.get('username')}")
                print(f"   Name: {bot.get('first_name')}")
    except Exception as e:
        print(f"⚠️  Could not fetch bot info: {e}")
    
    print("="*50 + "\n")
    
    # Start polling in background
    asyncio.create_task(polling_loop())


@app.get("/")
async def root():
    return {
        "status": "running",
        "mode": "polling",
        "bot": "Telegram Bot API with FastAPI (Localhost)",
        "version": "1.0.0",
        "message": "Bot is running in polling mode on localhost"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "mode": "polling"}


@app.get("/bot-info")
async def get_bot_info():
    """Get information about the bot"""
    url = f"{TELEGRAM_API_URL}/getMe"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
