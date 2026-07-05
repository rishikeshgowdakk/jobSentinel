import sys

def modify_db():
    with open('src/core/db.py', 'r') as f:
        content = f.read()

    new_method = """    def clear_user_matches(self, user_id: str):
        try:
            cur = self.conn.cursor()
            if self.is_sqlite:
                cur.execute("DELETE FROM job_matches WHERE user_id = ?", (user_id,))
            else:
                cur.execute("DELETE FROM job_matches WHERE user_id = %s", (user_id,))
            self.conn.commit()
            cur.close()
        except Exception as e:
            logger.error(f"Error clearing matches: {e}")
            if self.conn:
                self.conn.rollback()

    def save_match(self"""

    if "def clear_user_matches" not in content:
        content = content.replace("    def save_match(self", new_method)
        with open('src/core/db.py', 'w') as f:
            f.write(content)
        print("db.py updated")

def modify_api():
    with open('src/api.py', 'r') as f:
        content = f.read()

    old_block = """@app.post("/api/preferences")
async def update_preferences(prefs: Preferences, request: Request):
    user_id = get_user_id(request)
    db.set_setting(user_id, "keywords", prefs.keywords)
    db.set_setting(user_id, "locations", prefs.locations)
    db.set_setting(user_id, "job_type", prefs.job_type)
    db.set_setting(user_id, "experience_level", prefs.experience_level)
    return {"status": "success", "message": "Preferences updated"}"""

    new_block = """@app.post("/api/preferences")
async def update_preferences(prefs: Preferences, request: Request):
    user_id = get_user_id(request)
    db.set_setting(user_id, "keywords", prefs.keywords)
    db.set_setting(user_id, "locations", prefs.locations)
    db.set_setting(user_id, "job_type", prefs.job_type)
    db.set_setting(user_id, "experience_level", prefs.experience_level)
    
    # Clear old job matches so the feed is fresh and reflects the new config!
    db.clear_user_matches(user_id)
    
    return {"status": "success", "message": "Preferences updated"}"""

    if old_block in content:
        content = content.replace(old_block, new_block)
        with open('src/api.py', 'w') as f:
            f.write(content)
        print("api.py updated")

if __name__ == "__main__":
    modify_db()
    modify_api()
