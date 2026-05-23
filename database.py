from Database_API import *
import asyncio
import json

sessions = db_manager("./Data_storage", "User_Data", "sessions", (
    column("UserID").int().primary_key(),
    column("MessageHistory").text().default("[NO MESSAGE HISTORY]"),
    column("SystemMemory").text().default("{}"),
    column("DailyInteractions").int().default(0),
    column("DailyMaxInteractions").int().default(20),
    column("IsPremium").boolean().default(False)
))

async def initialize_db():
    """Creates a file for the database and populate it with tables"""
    await sessions.create_db()

async def update_sql(user_id: int):
    """We check if the user exists in our database, if not then we add them to it"""
    result = await sessions.run(query("sessions").select("UserID").where("UserID = ?", user_id))

    if not result:
        print(f"New user detected [{user_id}]")
        await sessions.run(query("sessions").insert(UserID=user_id))
    
    await sessions.run(query("sessions").update(DailyInteractions=Raw("DailyInteractions + 1")).where("UserID = ?", user_id))

async def can_interact(user_id: int) -> bool:
    # 1) Check premium
    result = await sessions.run(
        query("sessions").select("IsPremium").where("UserID = ?", user_id)
    )

    if not result:
        # user not in DB → treat as non-premium & no interactions yet
        return True  # or False, depending on how strict you want to be

    is_premium = bool(result[0][0])

    if is_premium:
        # Premium bypasses limits
        return True

    # 2) Non-premium → check daily usage
    interactions = await sessions.run(
        query("sessions").select("DailyInteractions").where("UserID = ?", user_id)
    )
    max_interactions = await sessions.run(
        query("sessions").select("DailyMaxInteractions").where("UserID = ?", user_id)
    )

    used = interactions[0][0]
    limit = max_interactions[0][0]

    # 3) Allow only if under limit
    return used < limit

async def give_premium(user_id: int):
    await sessions.run(query("sessions").update(IsPremium=True).where("UserID = ?", user_id))

async def rm_premium(user_id: int):
    await sessions.run(query("sessions").update(IsPremium=False).where("UserID = ?", user_id))

async def get_history(user_id: int) -> list:
    result = await sessions.run(
        query("sessions").select("MessageHistory").where("UserID = ?", user_id)
    )

    if not result:
        return []

    raw = result[0][0]

    if raw == "[NO MESSAGE HISTORY]":
        return []

    try:
        return json.loads(raw)
    except:
        return []


async def save_history(user_id: int, history: list):
    encoded = json.dumps(history)
    await sessions.run(
        query("sessions").update(MessageHistory=encoded).where("UserID = ?", user_id)
    )

async def add_to_history(user_id: int, role: str, content: str, limit: int = 20):
    history = await get_history(user_id)

    history.append({"role": role, "content": content})

    # Trim to last N messages
    if len(history) > limit:
        history = history[-limit:]

    await save_history(user_id, history)

async def get_system_memory(user_id: int) -> dict:
    result = await sessions.run(
        query("sessions").select("SystemMemory").where("UserID = ?", user_id)
    )

    if not result:
        return {}

    raw = result[0][0]

    try:
        return json.loads(raw)
    except:
        return {}

async def save_system_memory(user_id: int, memory: dict):
    encoded = json.dumps(memory)
    await sessions.run(
        query("sessions").update(SystemMemory=encoded).where("UserID = ?", user_id)
    )

async def update_system_memory(user_id: int, key: str, value):
    memory = await get_system_memory(user_id)
    memory[key] = value
    await save_system_memory(user_id, memory)


async def merge_memory(user_id: int, new_mem: dict):
    if not new_mem:
        return

    current = await get_system_memory(user_id)

    for key, value in new_mem.items():
        if isinstance(value, list):
            # merge lists without duplicates
            existing = set(current.get(key, []))
            for item in value:
                existing.add(item)
            current[key] = list(existing)
        else:
            # overwrite simple fields
            current[key] = value

    await save_system_memory(user_id, current)

async def wipe_history(user_id: int):
    await sessions.run(
        query("sessions").update(MessageHistory="[NO MESSAGE HISTORY]").where("UserID = ?", user_id)
    )

async def wipe_system_memory(user_id: int):
    await sessions.run(
        query("sessions").update(SystemMemory="{}").where("UserID = ?", user_id)
    )

async def wipe_all_memory(user_id: int):
    await wipe_history(user_id)
    await wipe_system_memory(user_id)
