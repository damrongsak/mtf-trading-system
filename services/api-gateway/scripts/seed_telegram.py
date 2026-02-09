from app.database import SessionLocal
from app.models.plugins import Plugin, UserPlugin, PluginCategory
import uuid
import datetime

# Configuration
USER_ID = "93cb8075-0e29-47f9-a939-8f413fb1dac4"
PLUGIN_ID = "telegram-notifier"
BOT_TOKEN = "8367617972:AAE5srGYV2W0iN2knq5Vw5ckyimUJt1XA44"
CHAT_ID = "916700879"

def seed():
    db = SessionLocal()
    try:
        # 1. Ensure Plugin exists
        plugin = db.query(Plugin).filter(Plugin.id == PLUGIN_ID).first()
        if not plugin:
            plugin = Plugin(
                id=PLUGIN_ID,
                name="Telegram Notifier",
                description="Sends trading signals to Telegram",
                version="1.0.0",
                author="System",
                category=PluginCategory.UTILITY,
                base_config_schema={"token": "string", "chat_id": "string"}
            )
            db.add(plugin)
            print(f"Registered plugin: {PLUGIN_ID}")
        
        # 2. Activate for User
        user_plugin = db.query(UserPlugin).filter(
            UserPlugin.user_id == USER_ID,
            UserPlugin.plugin_id == PLUGIN_ID
        ).first()
        
        config = {"token": BOT_TOKEN, "chat_id": CHAT_ID}
        
        if not user_plugin:
            user_plugin = UserPlugin(
                user_id=USER_ID,
                plugin_id=PLUGIN_ID,
                is_active=True,
                config_overrides=config,
                activated_at=datetime.datetime.utcnow()
            )
            db.add(user_plugin)
            print(f"Activated plugin for user: {USER_ID}")
        else:
            user_plugin.is_active = True
            user_plugin.config_overrides = config
            print(f"Updated plugin config for user: {USER_ID}")
            
        db.commit()
    except Exception as e:
        print(f"Seeding failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed()
