import aiosqlite
import os
import asyncio, nest_asyncio
import json
from logger import SingleLogger

with open('./src/config.json', 'r', encoding='utf-8') as conf: 
    config = json.load(conf)

logger = SingleLogger().get_logger()

def async_to_sync(future, as_task=True):
    """
    A better implementation of `asyncio.run`.

    :param future: A future or task or call of an async method.
    :param as_task: Forces the future to be scheduled as task (needed for e.g. aiohttp).
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:  # no event loop running:
        loop = asyncio.new_event_loop()
        return loop.run_until_complete(loop.create_task(future))
    else:
        nest_asyncio.apply(loop)
        return loop.run_until_complete(loop.create_task(future))
    
class sql_tables():
    def __init__(self) -> None:
        logger.info("init models")
        async_to_sync(self.connect())

    async def connect(self) -> None:
        logger.info(f"connect to sql {config['db_name']}")
        if not os.path.isfile(config['db_name']):
            self._connection = await aiosqlite.connect(config['db_name'])
            await self._connection.executescript("""--sql
                CREATE TABLE today_complete (
                    userId INTEGER,
                    completeTime TIMESTAMP DEFAULT CURRENT_TIMESTAMP 
                );
                CREATE TABLE scores (
                    userId INTEGER PRIMARY KEY,
                    userName TEXT,
                    score INTEGER DEFAULT 0,
                    regDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await self._connection.commit()
        else:
            self._connection = await aiosqlite.connect(config['db_name'])
            
    async def add_user(self, user_id: int, user_name: str) -> bool:
        async with self._connection.execute("SELECT userId FROM scores WHERE userId = ?", (user_id,)) as cursor:
            if await cursor.fetchone() is not None:
                return False
        await self._connection.execute("INSERT INTO scores (userId, userName) VALUES (?, ?)", (user_id, user_name))
        await self._connection.commit()
        return True
    
    async def users_score(self) -> list[list]:
        async with self._connection.execute("SELECT userName, score FROM scores ORDER BY score DESC") as cursor:
            return await cursor.fetchall()
    
    async def calculate_score(self) -> bool:
        async with self._connection.execute("""--sql
        SELECT MIN( completeTime ) AS time, userId
            FROM today_complete
            GROUP BY userId
        """) as cursor:
            first_id = await cursor.fetchone()
        if first_id is None:
            return False
        else:
            first_id = first_id[1]
        
        async with self._connection.execute("""
                SELECT userId, COUNT(*) AS count_score from today_complete GROUP BY userId
            """) as cursor:
            scores = await cursor.fetchall()
        logger.debug(f"----> {config['points']['first']}, {first_id}")
        await self._connection.execute("UPDATE scores SET score = score + ? WHERE userId = ?", (config['points']['first'], first_id))
        for user_score in scores:
            logger.debug(f"-----> {user_score}")
            await self._connection.execute("UPDATE scores SET score = score + ? WHERE userId = ?", 
                (config['points']['task'] + config['points']['repeat_task'] * (user_score[1] - 1), user_score[0])
            )
        await self._connection.execute("DELETE FROM today_complete")
        await self._connection.commit()
        return True
    
    async def complete(self, user_id: int) -> bool:
        await self._connection.execute("INSERT INTO today_complete (userId) VALUES(?)", (user_id,))
        await self._connection.commit()
        return True
        
    async def delete(self, user_id: int) -> bool:
        await self._connection.execute("DELETE FROM today_complete ORDER BY regDate DESC LIMIT 1")
        await self._connection.commit()
        
    async def all_players(self) -> list:
        async with self._connection.execute("SELECT userId from scores") as cursor:
            return [x[0] for x in await cursor.fetchall()]
        
    async def done_today(self, user_id) -> int:
        async with self._connection.execute("SELECT userId, COUNT(*) AS count_score from today_complete WHERE userId = ? GROUP BY userId", (user_id,)) as cursor:
            count = await cursor.fetchone()
            if count is None:
                return 0
            return count[1]
        