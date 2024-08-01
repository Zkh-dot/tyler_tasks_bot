import sqlite3
import os
import json

with open('config.json', 'r') as conf: 
    config = json.load(conf)

class sql_tables():
    def __init__(self) -> None:
        print(config['db_name'], os.path.isfile(config['db_name']))
        if not os.path.isfile(config['db_name']):
            self.connection = sqlite3.connect(config['db_name'])
            self._cursor = self.connection.cursor()
            self._cursor.executescript("""--sql
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
            self.connection.commit()
        else:
            self.connection = sqlite3.connect(config['db_name'])
            self._cursor = self.connection.cursor()
            
    def add_user(self, user_id: int, user_name: str) -> bool:
        self._cursor.execute("SELECT userId FROM scores WHERE userId = ?", (user_id,))
        if self._cursor.fetchone() is not None:
            return False
        self._cursor.execute("INSERT INTO scores (userId, userName) VALUES (?, ?)", (user_id, user_name))
        self.connection.commit()
        return True
    
    def users_score(self) -> list[list]:
        self._cursor.execute("SELECT userName, score FROM scores ORDER BY score")
        return self._cursor.fetchall()
    
    def calculate_score(self) -> bool:
        self._cursor.execute("""--sql
        SELECT MIN( completeTime ) AS time, userId
            FROM today_complete
            GROUP BY userId
        """)
        first_id = self._cursor.fetchone()[1]
        
        self._cursor.execute("SELECT userId, COUNT(*) AS count_score from today_complete GROUP BY userId")
        scores = self._cursor.fetchall()
        self._cursor.execute("UPDATE scores SET score = score + ? WHERE userId = ?", (config['points']['first'], first_id))
        for user_score in scores:
            self._cursor.execute("UPDATE scores SET score = score + ? WHERE userId = ?", 
                (config['points']['task'] + config['points']['repeat_task'] * (user_score[1] - 1), user_score[0])
            )
        
        self._cursor.execute("DELETE FROM today_complete")
        self.connection.commit()
    
    def complete(self, user_id: int) -> bool:
        self._cursor.execute("INSERT INTO today_complete (userId) VALUES(?)", (user_id,))
        self.connection.commit()
        return True
        
    def delete(self, user_id: int) -> bool:
        self._cursor.execute("DELETE FROM today_complete ORDER BY regDate DESC LIMIT 1")
        self.connection.commit()
        
    def all_players(self) -> list:
        self._cursor.execute("SELECT userId from scores")
        return [x[0] for x in self._cursor.fetchall()]
        
    def done_today(self, user_id) -> int:
        self._cursor.execute("SELECT userId, COUNT(*) AS count_score from today_complete GROUP BY userId WHERE userId = ?", (user_id))
        return self._cursor.fetchone()[1]
        